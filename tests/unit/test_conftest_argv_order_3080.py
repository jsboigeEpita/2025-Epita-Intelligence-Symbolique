"""#3080 — a directory conftest's fixtures must survive any argv order.

On pytest 9.1.1, running pytest with initial args in the order ``R F P`` —
a directory under ``argumentation_analysis``, then a file directly in
``tests/unit``, then a file under ``argumentation_analysis`` — makes pytest
create TWO Package nodes for ``tests/unit/argumentation_analysis``: the
conftest's fixtures register under the first (during R's walk), while P's
items hang under the second (F's walk re-collects ``tests/unit`` with
``handle_dupes=False`` and its fresh children replace the cached ones).
Fixture matching is by node identity, so both the named fixture
(``dung_attacks_offline`` — the loud "fixture not found" error) and the
autouse ``_shutdown_leaked_communication_threads`` (silently dropped) vanish
from P's items.

Upstream: pytest-dev/pytest#14971, fixed by pytest-dev/pytest#14635
(backport #14968, merged into the 9.1.x branch 2026-09-06 — no release
carries it as of 2026-10-19). ``tests/conftest.py`` ports the upstream fix
until a released pytest supersedes it.

This witness runs the collection in a SUBPROCESS with the exact ``R F P``
argv from the issue and asserts, for every collected ``dung_extensions``
item of P:

- the autouse fixture is in the item's fixture closure (the silent loss);
- the named fixture resolves to at least one visible FixtureDef (the loud loss).

A ``P``-only control run proves the instrument can report true (it is not a
constant-false oracle). Born red on pristine main (#3080).

#3176 — the instrument used to keep the verdict and throw away the evidence.
An empty ``rows`` reached the caller as a bare list: the child's returncode,
stdout and stderr were discarded, and three different causes (a collection
error, an ``-m``/``-k`` deselection, a collection-time skip) were reported by
one sentence. The child now also reports ``session.testsfailed`` and every
``pytest_collectreport`` failure, and ``_run_shape`` returns the whole trail
next to the rows so an empty verdict fails with its cause.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

R = "tests/unit/argumentation_analysis/reporting/restitution/"
F = "tests/unit/test_llm_egress_counter.py"
P = "tests/unit/argumentation_analysis/orchestration/test_unified_pipeline.py"

AUTOUSE = "_shutdown_leaked_communication_threads"
NAMED = "dung_attacks_offline"

# Programmatic driver run in the subprocess. Prints one WITNESS_VERDICT json
# line: per collected dung_extensions item, whether the autouse fixture made
# it into the item's fixture closure and whether the named fixture resolves.
_DRIVER = """
import json
import os
import sys

import pytest

R = {R!r}
F = {F!r}
P = {P!r}
AUTOUSE = {AUTOUSE!r}
NAMED = {NAMED!r}

shape = sys.argv[1]
# #3176: the caller may point P at a different module (the broken-import
# mutation). Everything else stays the argv the issue measured.
if len(sys.argv) > 2:
    P = sys.argv[2]
argv = {{"p": [P], "rfp": [R, F, P]}}[shape]
# #3176 (load replay): an ISOLATED basetemp. With the shared default
# (``pytest-of-<user>``), this child's numbered-dir retention ("keep the 3
# newest") runs against roots the xdist workers are still using: under
# ``-n auto`` it deleted the parent worker's tmp root — and with it the very
# file P pointed at (collection then failed at ``Path.lstat`` with
# FileNotFoundError, 4 replays out of 4). A private basetemp keeps the
# retention scan inside this run's own tmp_path.
basetemp = os.environ.get("WITNESS_BASETEMP")
if basetemp:
    argv = argv + ["--basetemp", basetemp]


class _Verdict:
    def __init__(self):
        self.collect_errors = []

    def pytest_collectreport(self, report):
        # #3176: a collection error is EVIDENCE. Dropping it is what made the
        # one red observed under load unrecoverable.
        if report.failed:
            self.collect_errors.append(
                {{"node": report.nodeid, "text": str(report.longrepr).strip()}}
            )

    def pytest_collection_finish(self, session):
        rows = []
        fm = session.config.pluginmanager.get_plugin("funcmanage")
        for item in session.items:
            if "dung_extensions" not in item.nodeid:
                continue
            closure = list(item._fixtureinfo.names_closure)
            defs = fm.getfixturedefs(NAMED, item) or ()
            rows.append(
                {{
                    "node": item.nodeid.split("::")[-1],
                    "autouse_in_closure": AUTOUSE in closure,
                    "named_defs_visible": len(defs) > 0,
                }}
            )
        # The verdict line carries the rows AND what the session says about
        # an empty collection — never one without the other.
        print(
            "WITNESS_VERDICT "
            + json.dumps(
                {{
                    "rows": rows,
                    "testsfailed": session.testsfailed,
                    "collect_errors": self.collect_errors,
                }}
            )
        )


raise SystemExit(
    pytest.main(
        [
            "-p", "no:cacheprovider",
            "-q", "--collect-only",
            "-m", "not requires_api",
            "-k", "dung_extensions",
            *argv,
        ],
        plugins=[_Verdict()],
    )
)
""".format(R=R, F=F, P=P, AUTOUSE=AUTOUSE, NAMED=NAMED)


_SHAPE_LABELS = {"p": "P alone", "rfp": "R F P"}


class _Run(NamedTuple):
    """One child run: its verdict rows AND the trail behind an empty one.

    #3176 — the rows alone are not a measurement. ``empty_message`` is the
    assertion message every caller uses, so a red names where the child
    stopped and shows what it printed instead of repeating one sentence for
    three unrelated causes.
    """

    shape: str
    label: str
    rows: list
    returncode: int
    testsfailed: int
    collect_errors: list
    stdout: str
    stderr: str

    @property
    def empty_message(self) -> str:
        if self.collect_errors:
            first = self.collect_errors[0]
            head = (
                f"collection error in P ({self.label}): {first['node']}\n"
                f"{first['text']}"
            )
        else:
            head = f"no dung_extensions item collected ({self.label})"
        return (
            f"{head}\n"
            f"child rc={self.returncode} testsfailed={self.testsfailed} "
            f"collect_errors={len(self.collect_errors)}\n"
            f"--- child stdout tail ---\n{self.stdout[-2000:]}\n"
            f"--- child stderr tail ---\n{self.stderr[-2000:]}"
        )


def _run_shape(tmp_path: Path, shape: str, p_target=None) -> _Run:
    """Run the driver in a subprocess; return the rows plus the child's trail.

    ``p_target`` replaces P (the broken-import mutation); the other two argv
    members are unchanged.
    """
    targets = {"R": R, "F": F, "P": p_target or P}
    for name, rel in targets.items():
        if not (REPO_ROOT / rel).exists():
            pytest.skip(f"witness target absent ({name}): {rel}")
    driver = tmp_path / f"driver_3080_{shape}.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    env = dict(os.environ)
    env["OPENAI_API_KEY"] = ""  # keyless idiom (#1167/R1167): the .env reloads anyway
    # #3176 (load replay): a private basetemp for the child — see the driver.
    # Without it the child's numbered-dir retention can delete THIS worker's
    # tmp root under ``-n auto`` (measured: FileNotFoundError at lstat on the
    # very path P pointed at, 4 replays out of 4).
    env["WITNESS_BASETEMP"] = str(tmp_path / f"child_basetemp_{shape}")
    cmd = [sys.executable, str(driver), shape]
    if p_target is not None:
        cmd.append(str(p_target))
    proc = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    payloads = [
        json.loads(line.removeprefix("WITNESS_VERDICT "))
        for line in proc.stdout.splitlines()
        if line.startswith("WITNESS_VERDICT ")
    ]
    assert payloads, (
        f"no verdict line from shape {shape} subprocess "
        f"(rc={proc.returncode}): {proc.stdout[-2000:]} {proc.stderr[-2000:]}"
    )
    payload = payloads[0]
    return _Run(
        shape=shape,
        label=_SHAPE_LABELS[shape],
        rows=payload["rows"],
        returncode=proc.returncode,
        testsfailed=payload["testsfailed"],
        collect_errors=payload["collect_errors"],
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def test_rfp_argv_keeps_the_conftest_fixtures(tmp_path):
    """R F P: both faces of #3080 must stay repaired (born red on main)."""
    run = _run_shape(tmp_path, "rfp")
    rows = run.rows
    assert rows, run.empty_message
    lost_autouse = [r["node"] for r in rows if not r["autouse_in_closure"]]
    lost_named = [r["node"] for r in rows if not r["named_defs_visible"]]
    assert not lost_autouse, (
        f"autouse {AUTOUSE} vanished from the closure of {lost_autouse} "
        f"under the R F P argv (pytest#14971)"
    )
    assert not lost_named, (
        f"fixture {NAMED} resolves to no FixtureDef for {lost_named} "
        f"under the R F P argv (pytest#14971)"
    )


def test_p_alone_control(tmp_path):
    """P alone: the same instrument must report everything intact.

    True-positive control — proves the rfp assertions measure the argv-order
    loss and not a constant-false oracle.
    """
    run = _run_shape(tmp_path, "p")
    rows = run.rows
    assert rows, run.empty_message
    assert all(r["autouse_in_closure"] for r in rows)
    assert all(r["named_defs_visible"] for r in rows)


def test_import_error_in_p_is_named_with_its_trail(tmp_path):
    """#3176 — an empty verdict carries the child's rc and its error.

    The mutation the issue asked for, made permanent: P points at a module
    that raises ``ImportError``, so collection yields no rows for a reason the
    instrument can — and must — name. Before #3176 the same run failed with
    "no dung_extensions item collected" while the returncode, stdout and
    stderr were discarded.

    The sentinel is asserted over ALL collected errors, not the message text
    alone: under load the child may stop on more than one thing, and the
    message carries the first — what must hold is that the import error IS
    in the trail the failure leaves behind.

    The broken module lives under the repo's gitignored ``.tmp/``, NOT under
    pytest's tmp_path. A child whose collected arg sits under %TEMP% walks
    %TEMP% during collection, and under ``-n auto`` a sibling ``tmp*`` dir can
    vanish mid-walk (measured: FileNotFoundError at ``Path.stat`` on a
    foreign dir, 1 replay in 4 after the basetemp isolation below). A
    repo-anchored arg never enumerates %TEMP% — the same property the R/F/P
    targets of the two other tests have always had.
    """
    broken = REPO_ROOT / ".tmp" / f"broken_import_3176_{os.getpid()}.py"
    broken.parent.mkdir(exist_ok=True)
    try:
        broken.write_text(
            "raise ImportError('witness_3176_sentinel')\n", encoding="utf-8"
        )
        # the child must reach the import, not a filesystem hiccup on a file
        # written milliseconds ago — prove it is on disk and readable first.
        assert broken.read_text(encoding="utf-8").startswith("raise ImportError")
        run = _run_shape(tmp_path, "p", p_target=str(broken))
        assert hasattr(
            run, "empty_message"
        ), "the run must carry its child's trail (rc, stdout, stderr) — #3176"
        assert run.rows == [], "a collection error must not invent rows"
        assert run.collect_errors, "a child collection error must be named as such"
        assert (
            run.returncode != 0
        ), "an interrupted collection must not look like a pass"
        message = run.empty_message
        assert "collection error in P" in message
        assert f"rc={run.returncode}" in message
        assert run.stderr or run.stdout, "the trail must carry what the child printed"
        assert any(
            "witness_3176_sentinel" in error["text"] for error in run.collect_errors
        ), (
            "the child never reached the broken import — it stopped on: "
            f"{run.collect_errors[0]['text'][:400]}"
        )
    finally:
        broken.unlink(missing_ok=True)
