"""The #2080 exit-hang instrument: name the worker, never mask the hang.

A real campaign froze after a document was fully persisted: the coroutine
had returned (state dump + signature written), but ``asyncio.run``'s
shutdown never came back — the unbounded join of ``shutdown_default_executor``
on a worker stuck in a native call. R1090 named one culprit (an unbounded
JVM enumeration, bounded at its source since #3050); the instrument here is
how any *other* culprit names itself on the next real occurrence.

Three properties, pinned three ways:

1. **Mechanism (runtime, subprocess)** — the R1003 positive control shrunk
   to unit scale: a coroutine that arms the watchdog at its tail, then
   leaks a default-executor worker that outlives it. The teardown join
   really hangs (the child measures it), and the one-shot dump fires
   *during* the hang, carrying the stuck worker's frame. It must run in a
   subprocess: tests/conftest.py applies nest_asyncio, whose patched
   asyncio.run skips the teardown sequence entirely — under pytest the
   join returns in under a millisecond and the hang under test cannot
   exist. The production runner is a plain process; the subprocess is it.
2. **Silence on the healthy path (runtime)** — a fast teardown disarms the
   one-shot in the caller's ``finally``; nothing is dumped, and a raise
   during teardown must not leave a stale one-shot armed against the *next*
   document.
3. **Wiring (AST)** — the runner arms at ``_run_single``'s tail (after
   persistence, before the final return), the batch loop's ``asyncio.run``
   sits inside a ``try/finally`` that cancels the watchdog, and the helper
   dumps with ``exit=False``/``repeat=False``: observation only, nothing is
   killed, no timeout hides the defect.
"""

from __future__ import annotations

import ast
import asyncio
import faulthandler
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from scripts.dataset import run_corpus_batch as runner

REPO_ROOT = Path(runner.__file__).resolve().parents[2]


# The positive control runs in a subprocess: tests/conftest.py applies
# nest_asyncio at module level, and nest_asyncio's patched asyncio.run does
# NOT run the teardown sequence (no shutdown_default_executor) — under
# pytest the join returns in <1 ms and the hang under test cannot exist.
# The production runner is a plain process (real asyncio.run), which is
# what this subprocess reproduces. The child: imports the runner's own
# helper, leaks a default-executor job, arms the watchdog, lets asyncio.run
# tear down for real, and reports the measured teardown time.
_POSITIVE_CONTROL_CHILD = """
import asyncio, faulthandler, json, sys, time
sys.path.insert(0, sys.argv[1])
from scripts.dataset.run_corpus_batch import _arm_teardown_watchdog

def _stuck_worker_2080(seconds):
    time.sleep(seconds)

async def doc():
    # The leak: a default-executor job submitted and abandoned — on the
    # real #2080 occurrences the await side was already dead (a phase
    # budget cancelled it; R1090), so nothing holds a cancellable task
    # over the worker. Dropping the future is what makes the leak
    # deterministic: the submit is synchronous, no task wraps it, and
    # teardown's cancel-all-tasks pass cannot reach it — only the
    # executor join can wait on it, which is the hang under test.
    asyncio.get_running_loop().run_in_executor(None, _stuck_worker_2080, 4.0)
    fh = open(sys.argv[2], "w", encoding="utf-8")
    _arm_teardown_watchdog(opaque_id="doc_A", seconds=0.5, file=fh)
    return "persisted"

t0 = time.perf_counter()
try:
    result = asyncio.run(doc())
finally:
    faulthandler.cancel_dump_traceback_later()
elapsed = time.perf_counter() - t0
with open(sys.argv[3], "w", encoding="utf-8") as out:
    json.dump({"result": result, "elapsed": elapsed}, out)
"""


class TestMechanism:
    def test_positive_control_dump_fires_during_the_hung_teardown(self, tmp_path):
        """The R1003 v3 control, shrunk: the dump must fire while the join
        waits AND name the stuck worker — a dump after the fact, or without
        the culprit's frame, names nothing."""
        dump_file = tmp_path / "watchdog.log"
        report_file = tmp_path / "control.json"
        proc = subprocess.run(
            [
                sys.executable,
                "-c",
                _POSITIVE_CONTROL_CHILD,
                str(REPO_ROOT),
                str(dump_file),
                str(report_file),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            cwd=str(REPO_ROOT),
        )
        assert proc.returncode == 0, proc.stderr[-2000:]
        report = json.loads(report_file.read_text(encoding="utf-8"))
        assert report["result"] == "persisted"
        hang = report["elapsed"]
        assert hang >= 3.5, (
            f"teardown returned in {hang:.2f}s — the join never waited, "
            "so the dump was never proven against a real hang"
        )
        dump = dump_file.read_text(encoding="utf-8")
        assert "_stuck_worker_2080" in dump, (
            "the dump must carry the stuck worker's frame — that frame is "
            "the whole deliverable of #2080"
        )
        assert "Thread" in dump

    def test_healthy_teardown_is_silent(self, tmp_path):
        """Fast teardown: the caller's finally cancels the one-shot before it
        fires — 49 healthy documents must not produce 49 noise dumps."""
        dump_file = tmp_path / "watchdog.log"
        with open(dump_file, "w", encoding="utf-8") as fh:

            async def doc():
                runner._arm_teardown_watchdog(opaque_id="doc_A", seconds=0.5, file=fh)
                return "persisted"

            try:
                assert asyncio.run(doc()) == "persisted"
            finally:
                faulthandler.cancel_dump_traceback_later()
        time.sleep(0.8)  # past the armed threshold: a live one-shot would fire
        assert dump_file.read_text(encoding="utf-8") == ""

    def test_a_raising_teardown_does_not_leave_a_stale_one_shot(self, tmp_path):
        """Exception-safety: if the teardown raises, the disarm still runs —
        a stale one-shot would fire during the NEXT document's healthy
        processing and report a hang where there is none."""
        dump_file = tmp_path / "watchdog.log"
        with open(dump_file, "w", encoding="utf-8") as fh:

            async def doc():
                runner._arm_teardown_watchdog(opaque_id="doc_A", seconds=0.5, file=fh)
                raise RuntimeError("teardown blew up")

            with pytest.raises(RuntimeError):
                try:
                    asyncio.run(doc())
                finally:
                    faulthandler.cancel_dump_traceback_later()
        time.sleep(0.8)
        assert dump_file.read_text(encoding="utf-8") == ""


class TestWiring:
    """The mechanism above is proven on the helper; these guards pin that
    the runner itself is wired the way the mechanism assumes."""

    @staticmethod
    def _tree() -> ast.Module:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        return ast.parse(source)

    @classmethod
    def _function(cls, name: str) -> ast.AST:
        # _run_single is async — match both def flavors or StopIteration
        # misreports "function not found".
        return next(
            n
            for n in ast.walk(cls._tree())
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
        )

    def test_the_helper_is_pure_observation(self):
        helper = self._function("_arm_teardown_watchdog")
        call = next(
            n
            for n in ast.walk(helper)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "dump_traceback_later"
        )
        keywords = {k.arg: k.value for k in call.keywords}
        exit_value = keywords.get("exit")
        repeat_value = keywords.get("repeat")
        assert isinstance(exit_value, ast.Constant) and exit_value.value is False, (
            "exit=False is the anti-mask: a watchdog that kills or exits is a "
            "timeout hiding the defect, not an instrument naming it (#2080)"
        )
        assert isinstance(repeat_value, ast.Constant) and repeat_value.value is False, (
            "repeat=False: one dump names the culprit; re-dumping every "
            "interval only adds noise to a hung run"
        )

    def test_run_single_arms_after_persistence_before_return(self):
        fn = self._function("_run_single")
        arm_calls = [
            n
            for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "_arm_teardown_watchdog"
        ]
        assert arm_calls, "_run_single must arm the #2080 teardown watchdog"
        # Armed at the TAIL: after the signature is persisted — arming
        # earlier would spend the threshold on analysis wall-time (a healthy
        # document runs ~770 s) instead of the teardown window.
        signature_log = next(
            n
            for n in ast.walk(fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "info"
            and any(
                isinstance(a, ast.Constant) and "signature written" in a.value
                for a in n.args
            )
        )
        assert arm_calls[0].lineno > signature_log.lineno, (
            "the watchdog must be armed after the signature is written — the "
            "#2080 hang lives between that line and the caller's loop"
        )

    def test_the_batch_loop_disarms_around_asyncio_run(self):
        main_fn = self._function("main")
        run_calls = [
            n
            for n in ast.walk(main_fn)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "run"
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id == "asyncio"
        ]
        assert (
            len(run_calls) == 1
        ), f"expected exactly one asyncio.run in main(), found {len(run_calls)}"
        target = run_calls[0]
        enclosing = [
            node
            for node in ast.walk(main_fn)
            if isinstance(node, ast.Try)
            and any(sub is target for sub in ast.walk(node))
            and not any(
                sub is target for handler in node.handlers for sub in ast.walk(handler)
            )
        ]
        assert enclosing, (
            "asyncio.run must sit inside a try block — the finally is the "
            "disarm on healthy return and on a raising teardown (#2080)"
        )
        for trier in enclosing:
            disarmed = any(
                isinstance(stmt, ast.Expr)
                and isinstance(stmt.value, ast.Call)
                and isinstance(stmt.value.func, ast.Attribute)
                and stmt.value.func.attr == "cancel_dump_traceback_later"
                for stmt in trier.finalbody
            )
            assert disarmed, (
                "the try around asyncio.run must cancel_dump_traceback_later "
                "in its finally — otherwise every healthy document leaves a "
                "live one-shot that fires mid-analysis of the next one"
            )
