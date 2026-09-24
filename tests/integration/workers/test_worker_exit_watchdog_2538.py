# -*- coding: utf-8 -*-
"""#2538: a probe session that hangs at exit fails with where it waits.

Nested pytest sessions sometimes hang in CI after printing their summary
(runs 35951252463 and 35952547373), and the failure said only that they
waited. ``tests/nested_pytest`` arms a ``faulthandler`` watchdog at the end of
every probe session, so the bounded failure also carries every thread's stack.

Here the hang is built on purpose: a non-daemon thread that never ends holds
the interpreter in ``threading._shutdown``. ``faulthandler`` heads its dump
with ``Timeout (h:mm:ss)!``, which the JVM's own first-chance-exception
reports (``Windows fatal exception``) never carry.
"""

import pytest

from tests.nested_pytest import both, run_probe

_PROBE = """
def test_green():
    assert True
"""

_HOLDS_THE_EXIT = """
import threading


def _holds_the_exit():
    threading.Event().wait()


def pytest_sessionfinish(session):
    threading.Thread(target=_holds_the_exit, daemon=False).start()
"""


def test_a_hang_at_exit_names_where_it_waits():
    with pytest.raises(pytest.fail.Exception) as failed:
        run_probe(
            "2538",
            {"probe_2538.py": _PROBE, "conftest.py": _HOLDS_THE_EXIT},
            bound=45,
            watchdog=2,
        )

    message = str(failed.value)
    assert "the probe session did not end within 45s" in message, message
    assert "Timeout (0:00:02)!" in message, message
    assert "_holds_the_exit" in message, message


def test_a_session_that_exits_dumps_nothing():
    returncode, out, err = run_probe("2538", {"probe_2538.py": _PROBE}, watchdog=30)

    assert returncode == 0, both(out, err)
    assert "Timeout (" not in err, both(out, err)
