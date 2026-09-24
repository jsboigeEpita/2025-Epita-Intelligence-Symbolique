# -*- coding: utf-8 -*-
"""#2530: a pytest session spawned inside the suite gets a working JVM.

Measured in CI (PR #2522, run 35937095411): every pytest session spawned by
the gate started its JVM, then the root ``jvm_session`` fixture skipped its
tests on the ``JClass`` health check. In the same job the gate's own JVM
worked, and so did the JVM of a ``python -c`` child. The skip dropped the
exception, so the cause was unknown.

Named in CI once the skip carried it (PR #2531, run 35947441266):
``AssertionError`` on ``<MagicMock name='mock.JClass()()'>``, so the child's
jpype was a mock. Two tests of ``test_jvm_session_flag_one_reader_2402.py``
left ``PYTEST_JVM_SESSION_DISABLED=1`` in the gate's environment. Every session
spawned after them inherited it: ``tests/conftest.py`` mocked jpype at import,
while the child's own ``--disable-jvm-session`` option was off.

Each case here is such a session, on a probe under ``tests/``
(``tests/nested_pytest.py``), so that ``tests/conftest.py`` and its
``jvm_session`` apply.
"""

import sys
from unittest.mock import MagicMock

import pytest

from tests.nested_pytest import both, run_probe

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2530 tests run real sessions (jpype mocked by --disable-jvm-session)",
    ),
]

_JVM_PROBE = """
def test_the_session_jvm_answers(jvm_session):
    assert str(jvm_session.JClass("java.lang.String")("ok")) == "ok"
"""

# The storm guard ends a session with pytest.exit, before the ``-rs`` summary,
# so the probe prints each skip reason when it happens.
_PRINT_SKIP_REASONS = """
def pytest_runtest_logreport(report):
    if report.skipped:
        print("\\nskip reason:", report.longrepr[2])
"""

_REFUSING_JCLASS = """
import jpype


def _refuse(name, *args, **kwargs):
    raise RuntimeError("probe 2530 refuses " + name)


# Imported at collection, after pytest_sessionstart started the JVM and before
# the jvm_session fixture runs its health check.
jpype.JClass = _refuse
"""


_LEAKING_PROBE = """
import os

FLAG = "PYTEST_JVM_SESSION_DISABLED"


def test_a_leaks_the_flag():
    os.environ[FLAG] = "1"


def test_b_finds_the_flag_put_back():
    assert FLAG not in os.environ
"""


def test_a_nested_session_gets_a_working_jvm():
    """DoD 2. CI: the probe's one test was skipped on the health check."""
    returncode, out, err = run_probe(
        "2530", {"probe_2530.py": _JVM_PROBE, "conftest.py": _PRINT_SKIP_REASONS}
    )

    assert "1 passed" in out, both(out, err)
    assert returncode == 0, both(out, err)


def test_the_health_check_skip_names_the_exception():
    """DoD 1, through the real fixture: the skip reason ends with the
    exception, and the session's storm guard still counts it as unhealthy."""
    returncode, out, err = run_probe(
        "2530",
        {
            "probe_2530.py": _JVM_PROBE,
            "conftest.py": _REFUSING_JCLASS + _PRINT_SKIP_REASONS,
        },
    )

    assert (
        "(JClass health check échoué) : RuntimeError: probe 2530 refuses "
        "java.lang.String" in out
    ), both(out, err)
    assert "1 x JVM started but unhealthy (JClass health check)" in out, both(out, err)
    assert returncode == 1, both(out, err)


def test_a_test_that_leaves_the_flag_errors_by_name():
    """DoD 3, the guard: the test that changed the flag errors at teardown,
    by name, and the next test finds the flag put back."""
    returncode, out, err = run_probe("2530", {"probe_2530.py": _LEAKING_PROBE})

    assert "ERROR at teardown of test_a_leaks_the_flag" in out, both(out, err)
    assert "#2530: this test left PYTEST_JVM_SESSION_DISABLED='1'" in out, both(
        out, err
    )
    assert "2 passed" in out, both(out, err)
    assert "1 error" in out, both(out, err)
    assert returncode == 1, both(out, err)
