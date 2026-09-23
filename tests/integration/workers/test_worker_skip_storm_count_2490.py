# -*- coding: utf-8 -*-
"""#2490: the skip-storm guard reads the count the session decided on.

Measured on ``main``: ``_skip_storm_signal`` read ``len(session.items)``.
The pytest-xdist controller collects nothing itself, so ``session.items``
stays empty there while xdist publishes the workers' count in
``session.testscollected``. Every green ``-n`` run ended "FAIL-LOUD (#2021):
0 test(s) collected" with exit code 1.

Each case is a real pytest session in a fresh interpreter, on a probe file
under ``tests/`` so that ``tests/conftest.py`` applies. The probe directory
starts with ``_``, which ``norecursedirs`` skips, so an ordinary run never
collects it. Three shapes:

* serial;
* the xdist controller's state, modelled serially by a probe conftest that
  empties ``session.items`` before the guard reads it. It runs wherever
  pytest runs, xdist or not;
* a real ``-n 2`` run, where pytest-xdist is installed (``requirements-test``;
  the CI environment does not install it).
"""

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2490 tests run real sessions (jpype mocked by --disable-jvm-session)",
    ),
]

ROOT = Path(__file__).resolve().parents[3]

# A probe session takes about 20 s here, with its own JVM start.
_BOUND = 300

_GREEN = """
def test_one():
    pass


def test_two():
    pass


def test_three():
    pass
"""

_STORM = """
import pytest

_REASON = "Saut du test car la JVM n'est pas reellement demarree (probe #2490)."


def test_one():
    pytest.skip(_REASON)


def test_two():
    pytest.skip(_REASON)


def test_three():
    pytest.skip(_REASON)
"""

_CONTROLLER_STATE = """
import pytest


@pytest.hookimpl(tryfirst=True)
def pytest_sessionfinish(session):
    # The xdist controller's state (#2490): it collects nothing itself, so
    # ``session.items`` is empty, while ``session.testscollected`` holds the
    # count of the tests that ran.
    session.items = []
"""

_SHAPES = {
    "serial": ([], False),
    "the xdist controller's state": ([], True),
    "xdist -n 2": (["-n", "2"], False),
}


def _needs_xdist(shape):
    if _SHAPES[shape][0]:
        pytest.importorskip("xdist", reason="pytest-xdist is not installed here")


def _session(shape, probe, *extra):
    """Run pytest on ``probe`` in ``shape``. ``(returncode, stdout)``."""
    argv, controller_state = _SHAPES[shape]
    probe_dir = ROOT / "tests" / f"_probe_2490_{uuid.uuid4().hex}"
    probe_dir.mkdir()
    try:
        (probe_dir / "probe_2490.py").write_text(probe, encoding="utf-8")
        if controller_state:
            (probe_dir / "conftest.py").write_text(_CONTROLLER_STATE, encoding="utf-8")
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
        try:
            done = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(probe_dir / "probe_2490.py"),
                    "-p",
                    "no:cacheprovider",
                    "-q",
                    *argv,
                    *extra,
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_BOUND,
            )
        except subprocess.TimeoutExpired:
            pytest.fail(f"the probe session did not end within {_BOUND}s")
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
    return done.returncode, done.stdout


@pytest.mark.parametrize("shape", list(_SHAPES))
def test_a_green_session_exits_0_with_its_summary(shape):
    """DoD 1. ``main``: the controller's state and ``-n 2`` shouted "0 test(s)
    collected" and exited 1."""
    _needs_xdist(shape)

    returncode, out = _session(shape, _GREEN)

    assert "FAIL-LOUD" not in out, out[-3000:]
    assert "3 passed" in out, out[-3000:]
    assert returncode == 0, out[-3000:]


@pytest.mark.parametrize("shape", list(_SHAPES))
def test_a_storm_still_shouts(shape):
    """DoD 2, control: a session whose tests all skip with a JVM signature
    exits 1 with the FAIL-LOUD block, naming the storm, not an empty
    collection."""
    _needs_xdist(shape)

    returncode, out = _session(shape, _STORM)

    assert "FAIL-LOUD (#2021): 3 of 3 collected tests" in out, out[-3000:]
    assert returncode == 1, out[-3000:]


@pytest.mark.parametrize("shape", ["serial", "xdist -n 2"])
def test_an_empty_selection_still_fails(shape):
    """DoD 3, control: a selection that matches nothing ends with pytest's
    own code for it. Nothing ran, and the exit is not 0."""
    _needs_xdist(shape)

    returncode, out = _session(shape, _GREEN, "-k", "no_test_is_named_like_this")

    assert returncode == pytest.ExitCode.NO_TESTS_COLLECTED, out[-3000:]
