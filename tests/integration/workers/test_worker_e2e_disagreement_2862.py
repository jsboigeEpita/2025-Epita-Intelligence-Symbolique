# -*- coding: utf-8 -*-
"""#2862 — an argv that predicted e2e while the collection found NO e2e item
must exit non-zero, not exempt the session.

Pre-fix, ``_skip_storm_signal`` returned on ``_argv_decides_e2e_session``
alone. The prediction is what skipped the JVM boot in ``pytest_sessionstart``,
so the session's JVM tests all skipped at setup and the run exited 0 having
measured nothing — the #2021 silent green, on the one path #2021's own
exemption did not cover. The classifier now reads ``--ignore``/``--ignore-glob``
(the sibling unit file), but the guard cannot depend on the classifier being
perfect: a filter it does not model (``--deselect``, ``norecursedirs``, a
future option, an xdist worker's pruned subset) reproduces the same silent
green. The disagreement between prediction and collection is therefore itself
the defect, and this witness pins it.

The nested session is shaped so that ONLY the disagreement can shout: its argv
carries a real path inside ``tests/e2e`` (reaching the e2e dir, and carrying no
test item), plus the probe's own green test — so the collection found zero e2e
items with one non-e2e item collected. The probe's conftest replaces the
``jvm_session`` fixture with a no-op: without it the root fixture would skip
the probe's test with a JVM signature, and the STORM verdict — not the
disagreement branch — would be what exits.

Born-red on ``main``: the nested session reports 1 passed and exits 0.
"""

from pathlib import Path

from tests.nested_pytest import both, run_probe

ROOT = Path(__file__).resolve().parents[3]

_PROBE = """
def test_probe_2862_passes():
    pass
"""

_PROBE_CONFTEST = """
import pytest


@pytest.fixture(scope="session", autouse=True)
def jvm_session():
    # The probe measures the guard, not the JVM: the argv decides this session
    # e2e, so no JVM boots (by design), and the probe's test must not be the
    # one that skips.
    yield
"""

# A committed path inside tests/e2e that carries no test item. The argv reaches
# tests/e2e through it (an ancestor of the path — the classifier reads
# containment, not filesystem contents); the collection collects nothing from
# it. Passing the package's ``__init__`` makes the nested session import that
# one module, never the whole e2e tree.
_E2E_ROOT = "tests/e2e/python/__init__.py"


def test_the_probe_root_still_exists():
    """If the file moves, the nested session dies on pytest's usage error for a
    missing path (exit 4), and ``_skip_storm_signal`` returns early on
    ``exitstatus != 0`` — a red dressed as the silence this issue is about. The
    path is asserted first, so the break is named."""
    assert (ROOT / _E2E_ROOT).is_file(), f"the probe's e2e root moved: {_E2E_ROOT}"


def test_e2e_prediction_with_zero_e2e_items_exits_non_zero():
    """The witness: same argv, main exits 0 (silent), the fix exits 1 naming
    the disagreement."""
    returncode, out, err = run_probe(
        "2862",
        {"probe_2862.py": _PROBE, "conftest.py": _PROBE_CONFTEST},
        _E2E_ROOT,
    )

    assert "FAIL-LOUD (#2862)" in out, both(out, err)
    assert returncode == 1, both(out, err)
