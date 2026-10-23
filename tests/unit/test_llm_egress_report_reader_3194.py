"""#3194 — a nested pytest child's egress reaches the session that spawned it.

Measured on the coordinator seat (2026-10-23): ``write_report`` gave every
session without ``--junitxml`` a per-pid file in the CURRENT DIRECTORY.
#1872 chose the per-pid name so a child could not overwrite the gate's
canonical report — that still holds — but no reader was ever added:

- a child that made a real LLM call recorded it in a file nobody read, so
  the gate's tally could not see a recurrence of the #1872 incident (a
  launcher spawning an unfiltered child that really posts);
- 803 of those files accumulated in one checkout root in nine days (all
  gitignored, so ``git status`` never showed them).

What the repair adds is a handshake, not a second channel: a session
publishes an inbox directory in ``LLM_EGRESS_CHILD_DIR`` for the
subprocesses it spawns; a child writes its report there and marks that it
started; the parent folds every report it finds into its own snapshot under
``child:<pid>::``, deletes what it read, and names any child that started
and never reported.

Both witnesses run zero network. The child's request is answered by an
``httpx.MockTransport`` and marked ``network`` through the counter's own
transport hook — the same path #2422 measures — so nothing leaves the
machine and no key is needed.

The child sessions run under ``LLM_EGRESS_GUARD_CENSUS=1``: the hermeticity
guard (#3069) is right to fail a real test that reaches an LLM over the
network, and this witness fabricates exactly such a record on purpose.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Dict, Iterator, Optional

_REPO = Path(__file__).resolve().parents[2]

# The handshake this witness drives, spelled here rather than imported so the
# witness can also run against pre-#3194 code and show the red. A rename of
# the constant would make the fabricated row leak into the caller's tally —
# loud, never silent — and the last test below pins the two names together.
CHILD_REPORT_DIR_ENV = "LLM_EGRESS_CHILD_DIR"

CHILD_TEST = "test_child_records_one_watched_llm_network_request"

CHILD_SOURCE = '''
import httpx

from tests.llm_egress_counter import get_counter


def {test_name}():
    """One watched-LLM request, marked network by the counter's own hook."""
    counter = get_counter()
    assert counter is not None, "the child session has no egress counter"

    def handler(request):
        # The production network-transport hook, driven from a MockTransport:
        # the entry is marked network and no socket is opened (#2422).
        counter.observe_network_transport()
        return httpx.Response(200, json={{"ok": True}})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        client.post("https://api.openai.com/v1/chat/completions", json={{"p": 1}})

    # Vacuity control: the child's own counter must have seen it, or the
    # parent could pass while nothing was ever recorded.
    assert counter.snapshot()["per_test_llm_network"], (
        "the child's counter did not mark the request as network"
    )
'''.format(test_name=CHILD_TEST)

QUIET_SOURCE = """
from tests.llm_egress_counter import get_counter


def test_the_session_counter_is_installed():
    # Vacuity control: this session really had the instrument, so a missing
    # report is about WHERE it went, not about a counter that never ran.
    assert get_counter() is not None
"""

# The parent session: a real pytest session with --junitxml that spawns one
# child through the repository's own bounded probe runner.
PARENT_SOURCE = (
    "from tests.nested_pytest import run_probe\n"
    "\n"
    "CHILD_SOURCE = " + repr(CHILD_SOURCE) + "\n"
    "\n"
    "\n"
    "def test_the_parent_session_spawns_one_child_session():\n"
    "    code, out, err = run_probe(\n"
    '        "egress_3194_child",\n'
    '        {"probe_child.py": CHILD_SOURCE},\n'
    '        "--disable-jvm-session",\n'
    "    )\n"
    "    assert code == 0, (\n"
    '        f"the child session exited {code}"\n'
    '        f"\\n--- stdout\\n{out[-2000:]}\\n--- stderr\\n{err[-4000:]}"\n'
    "    )\n"
)


def _child_env(overrides: Optional[Dict[str, str]]) -> Dict[str, str]:
    """The caller's environment, minus what must not cross into a child.

    ``PYTEST_XDIST_*`` would make the child read itself as a worker of the
    caller's run (``tests/_jvm_session_flag.py``); ``PYTEST_CURRENT_TEST``
    describes the test in progress here, not in there.
    """
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("PYTEST_XDIST_") and name != "PYTEST_CURRENT_TEST"
    }
    env.update(overrides or {})
    return env


@contextlib.contextmanager
def _probe_dir(files: Dict[str, str]) -> Iterator[Path]:
    """A throwaway directory under ``tests/``, so ``tests/conftest.py`` applies.

    ``norecursedirs`` skips the leading underscore, so an ordinary run never
    collects it, and it is deleted when the block ends.
    """
    directory = _REPO / "tests" / f"_probe_3194_{uuid.uuid4().hex}"
    directory.mkdir()
    try:
        for name, source in files.items():
            (directory / name).write_text(source, encoding="utf-8")
        yield directory
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def _run_pytest(
    cwd: Path,
    files: Dict[str, str],
    *args: str,
    env: Optional[Dict[str, str]] = None,
) -> "subprocess.CompletedProcess[str]":
    """Run one nested pytest session from ``cwd`` on ``files``."""
    with _probe_dir(files) as probe:
        target = next(name for name in files if name.startswith("probe"))
        return subprocess.run(
            [
                sys.executable,
                "-I",
                # ``-I`` isolates the child, but it does not decide its stdout
                # encoding: on a runner whose ANSI code page is not UTF-8, the
                # child encodes in cp1252 while this parent decodes in UTF-8,
                # and the reader thread dies on the first accented character
                # (#3210 CI run 39962753215: byte 0xe9, position 36). ``-X``
                # options survive ``-I``, so the child is pinned to UTF-8.
                "-X",
                "utf8",
                "-m",
                "pytest",
                str(probe / target),
                "-q",
                "-p",
                "no:cacheprovider",
                "--disable-jvm-session",
                *args,
            ],
            cwd=str(cwd),
            env=_child_env(env),
            capture_output=True,
            # Strict decoding turns one stray byte into a dead reader thread
            # and a silent ``stdout is None`` — a green-looking witness that
            # measured nothing (#3210). ``tests/nested_pytest.run_bounded``
            # decodes the same way.
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )


def test_a_nested_childs_network_llm_request_reaches_the_parent_report(
    tmp_path: Path,
) -> None:
    """DoD 1 (#3194): the parent's canonical report carries the child's row."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    junit = tmp_path / "junit.xml"
    # Quarantine the fabricated row: the parent session writes a per-pid copy
    # of its report to the directory its own caller handed it, and this one
    # names a directory owned by the witness — never the enclosing session's
    # inbox, where a deliberate network row would fail the real gate.
    collected = tmp_path / "collected"
    proc = _run_pytest(
        cwd,
        {"probe_parent.py": PARENT_SOURCE},
        f"--junitxml={junit}",
        env={
            CHILD_REPORT_DIR_ENV: str(collected),
            "LLM_EGRESS_GUARD_CENSUS": "1",
        },
    )
    assert proc.returncode == 0, (
        f"the parent session exited {proc.returncode}"
        f"\n--- stdout\n{proc.stdout[-4000:]}\n--- stderr\n{proc.stderr[-4000:]}"
    )

    report = json.loads((tmp_path / "llm_egress_report.json").read_text("utf-8"))
    network = report["per_test_llm_network"]
    assert len(network) == 1, (
        "the parent's tally must carry exactly the child's one network "
        f"watched-LLM request, reads {network}"
    )
    label, count = next(iter(network.items()))
    assert count == 1
    assert label.startswith("child:"), (
        "a folded record must name the child process it came from, " f"reads {label!r}"
    )
    assert CHILD_TEST in label, f"the row must name the child's test, reads {label!r}"
    assert any(
        r["class"] == "llm" and r["host"] == "api.openai.com"
        for r in report["requests"]
    ), "the folded row must keep its class and host as the child measured them"
    nested = report.get("nested_children") or {}
    assert (
        nested.get("read") == 1
    ), f"the report must say one child report was folded, reads {nested}"
    assert "Nested egress (#3194): 1 child report(s) folded" in proc.stdout, (
        "the terminal summary must name the fold:\n" + proc.stdout[-3000:]
    )


def test_a_session_without_junitxml_leaves_no_report_in_the_cwd(
    tmp_path: Path,
) -> None:
    """DoD 2 (#3194): the nested report leaves the current directory."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    collected = tmp_path / "collected"
    proc = _run_pytest(
        cwd,
        {"probe_quiet.py": QUIET_SOURCE},
        env={CHILD_REPORT_DIR_ENV: str(collected)},
    )
    assert proc.returncode == 0, (
        f"the session exited {proc.returncode}"
        f"\n--- stdout\n{proc.stdout[-4000:]}\n--- stderr\n{proc.stderr[-4000:]}"
    )
    assert list(cwd.glob("llm_egress_report*.json")) == [], (
        "a session without --junitxml must not write its report into the "
        f"current directory (#3194); it left {os.listdir(cwd)}"
    )
    lines = [
        line for line in proc.stdout.splitlines() if line.startswith("Egress report: ")
    ]
    assert lines, (
        "the session must still say where its report went:\n" + proc.stdout[-3000:]
    )
    written = Path(lines[-1].split("Egress report: ", 1)[1].strip())
    assert written.exists(), f"the printed report path does not exist: {written}"
    assert (
        cwd.resolve() not in written.resolve().parents
    ), f"the report went into the current directory: {written}"
    assert written.parent.resolve() == collected.resolve(), (
        "a child writes into the directory its parent handed it, " f"reads {written}"
    )


def test_the_witness_uses_the_handshake_env_var_name() -> None:
    """Pin the string this witness drives to the constant production uses."""
    from tests.llm_egress_counter import CHILD_REPORT_DIR_ENV as production_name

    assert production_name == CHILD_REPORT_DIR_ENV, (
        "the witness overrides a directory for its own children; if the "
        "handshake is renamed, the fabricated network row would reach the "
        "enclosing session's tally"
    )


# #3210 — a child that emits a byte the parent cannot decode.
#
# CI run 39962753215 reddened both witnesses above with ``proc.stdout is
# None``: the runner's ANSI code page is not UTF-8, the child encoded
# ``[auto_env] WARNING: aucun .env chargé`` in cp1252, and the parent's
# strict UTF-8 reader thread died on the ``é`` at position 36. The thread's
# exception is swallowed, so ``stdout`` is simply ``None`` — a witness that
# reports nothing instead of reporting a decoding problem.
#
# ``os.write`` to fd 1 with ``-s`` bypasses the child's text layer entirely,
# so this probe emits a byte no child encoding choice can rescue: the defect
# is only ever about the PARENT's decoder, and the witness measures it on
# every seat, including seats whose code page already is UTF-8.
LATIN1_SOURCE = r"""
import os


def test_emits_one_byte_that_is_not_valid_utf8():
    os.write(1, b"trail-before:\xe9:trail-after:\n")
"""


def test_a_byte_the_parent_cannot_decode_does_not_blank_its_stdout(
    tmp_path: Path,
) -> None:
    """#3210: strict decoding cost the caller the WHOLE child's output."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    proc = _run_pytest(cwd, {"probe_latin1.py": LATIN1_SOURCE}, "-s")
    assert (
        proc.returncode == 0
    ), f"the child session exited {proc.returncode}\n--- stderr\n{proc.stderr[-2000:]}"
    assert proc.stdout is not None, (
        "the child's stdout did not reach the parent at all: one undecodable "
        "byte killed the reader thread, which is exactly how #3210's CI red "
        "looked (``proc.stdout is None``, no exception raised)"
    )
    assert "trail-before:" in proc.stdout and "trail-after:" in proc.stdout, (
        "everything the child wrote around the stray byte must survive; reads "
        f"{proc.stdout[:400]!r}"
    )
    # 0xe9 alone is not valid UTF-8, so a decoder that survives must say so
    # rather than dropping the byte: a silent drop would hide a truncated
    # trail just as well as a dead thread does.
    assert "�" in proc.stdout, (
        "the undecodable byte must be replaced, not silently dropped; reads "
        f"{proc.stdout[:400]!r}"
    )


def test_the_child_is_pinned_to_utf8_despite_isolation() -> None:
    """#3210: ``-I`` does not pick the child's stdout encoding, ``-X utf8`` does.

    Blind on a seat whose code page is already UTF-8 (measured: ACP 65001 on
    this lane), so it pins the ARGV rather than a decoding outcome — the CI
    runner is where the outcome is visible.
    """
    import inspect

    source = inspect.getsource(_run_pytest)
    assert '"-X",\n                "utf8"' in source or '"-X", "utf8"' in source, (
        "the child must be launched with -X utf8: -I isolates it but leaves "
        "its stdout encoding to the seat's ANSI code page (#3210)"
    )
    assert "text=True" not in source, (
        "text=True decodes strictly; one stray byte then blanks the whole "
        "child's output instead of being reported (#3210)"
    )
