# -*- coding: utf-8 -*-
"""#2490: the skip-storm guard reads the count the session decided on.

Measured on ``main``: ``_skip_storm_signal`` read ``len(session.items)``.
The pytest-xdist controller collects nothing itself, so ``session.items``
stays empty there while xdist publishes the workers' count in
``session.testscollected``. Every green ``-n`` run ended "FAIL-LOUD (#2021):
0 test(s) collected" with exit code 1.

Each case is a real pytest session in a fresh interpreter, on a probe file
under ``tests/`` so that ``tests/conftest.py`` applies
(``tests/nested_pytest.py``, whose wait is bounded). Three shapes:

* serial;
* the xdist controller's state, modelled serially by a probe conftest that
  empties ``session.items`` before the guard reads it. It runs wherever
  pytest runs, xdist or not;
* a real ``-n 2`` run, where pytest-xdist is installed (``requirements-test``;
  the CI environment does not install it).

The probe conftest replaces the root ``jvm_session`` fixture with a no-op, so
the probe's tests pass or skip on their own. The first CI run of this file
showed why: the nested session's JVM failed the root fixture's ``JClass``
health check, the fixture skipped the 3 green tests, and the guard shouted
for a storm the probe did not make. The nested session still starts its JVM
in ``pytest_sessionstart``, like any session the guard watches.
"""

import sys
from unittest.mock import MagicMock

import pytest

from tests.nested_pytest import both, run_probe

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2490 tests run real sessions (jpype mocked by --disable-jvm-session)",
    ),
]

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

_PROBE_CONFTEST = """
import pytest


@pytest.fixture(scope="session", autouse=True)
def jvm_session():
    # Replaces the root fixture for the probe's own tests: the probe measures
    # the skip-storm guard, not the JVM of this nested session.
    yield
"""

_CONTROLLER_STATE = """


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
    """Run pytest on ``probe`` in ``shape``. ``(returncode, stdout, stderr)``."""
    argv, controller_state = _SHAPES[shape]
    conftest = _PROBE_CONFTEST + (_CONTROLLER_STATE if controller_state else "")
    return run_probe(
        "2490", {"probe_2490.py": probe, "conftest.py": conftest}, *argv, *extra
    )


@pytest.mark.parametrize("shape", list(_SHAPES))
def test_a_green_session_exits_0_with_its_summary(shape):
    """DoD 1. ``main``: the controller's state and ``-n 2`` shouted "0 test(s)
    collected" and exited 1."""
    _needs_xdist(shape)

    returncode, out, err = _session(shape, _GREEN)

    assert "FAIL-LOUD" not in out, both(out, err)
    assert "3 passed" in out, both(out, err)
    assert returncode == 0, both(out, err)


@pytest.mark.parametrize("shape", list(_SHAPES))
def test_a_storm_still_shouts(shape):
    """DoD 2, control: a session whose tests all skip with a JVM signature
    exits 1 with the FAIL-LOUD block, naming the storm, not an empty
    collection."""
    _needs_xdist(shape)

    returncode, out, err = _session(shape, _STORM)

    assert "FAIL-LOUD (#2021): 3 of 3 collected tests" in out, both(out, err)
    assert returncode == 1, both(out, err)


@pytest.mark.parametrize("shape", ["serial", "xdist -n 2"])
def test_an_empty_selection_still_fails(shape):
    """DoD 3, control: a selection that matches nothing ends with pytest's
    own code for it. Nothing ran, and the exit is not 0."""
    _needs_xdist(shape)

    returncode, out, err = _session(shape, _GREEN, "-k", "no_test_is_named_like_this")

    assert returncode == pytest.ExitCode.NO_TESTS_COLLECTED, both(out, err)
