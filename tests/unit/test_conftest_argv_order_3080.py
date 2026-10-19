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
"""

import json
import os
import subprocess
import sys
from pathlib import Path

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
import sys

import pytest

R = {R!r}
F = {F!r}
P = {P!r}
AUTOUSE = {AUTOUSE!r}
NAMED = {NAMED!r}

shape = sys.argv[1]
argv = {{"p": [P], "rfp": [R, F, P]}}[shape]


class _Verdict:
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
        print("WITNESS_VERDICT " + json.dumps(rows))


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


def _run_shape(tmp_path: Path, shape: str) -> list:
    """Run the driver in a subprocess; return the verdict rows."""
    for rel in (R, F, P):
        if not (REPO_ROOT / rel).exists():
            pytest.skip(f"witness target absent: {rel}")
    driver = tmp_path / f"driver_3080_{{shape}}.py"
    driver.write_text(_DRIVER, encoding="utf-8")
    env = dict(os.environ)
    env["OPENAI_API_KEY"] = ""  # keyless idiom (#1167/R1167): the .env reloads anyway
    proc = subprocess.run(
        [sys.executable, str(driver), shape],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    verdicts = [
        json.loads(line.removeprefix("WITNESS_VERDICT "))
        for line in proc.stdout.splitlines()
        if line.startswith("WITNESS_VERDICT ")
    ]
    assert verdicts, (
        f"no verdict line from shape {shape} subprocess "
        f"(rc={proc.returncode}): {proc.stdout[-2000:]} {proc.stderr[-2000:]}"
    )
    return verdicts[0]


def test_rfp_argv_keeps_the_conftest_fixtures(tmp_path):
    """R F P: both faces of #3080 must stay repaired (born red on main)."""
    rows = _run_shape(tmp_path, "rfp")
    assert rows, "no dung_extensions item collected from P under the R F P argv"
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
    rows = _run_shape(tmp_path, "p")
    assert rows, "no dung_extensions item collected from P alone"
    assert all(r["autouse_in_closure"] for r in rows)
    assert all(r["named_defs_visible"] for r in rows)
