# -*- coding: utf-8 -*-
"""#2519: a process whose main thread never calls Java exits.

Measured on ``main``: ``initialize_jvm`` starts the JVM on an executor thread,
and jpype's atexit handler ``_JTerminate`` never returns when the thread
running it was never attached. A process that started the JVM and never
called Java from its main thread hung forever at exit: the xdist controller,
a pytest session that runs no test, a script that uses Java from other
threads only.

Each case runs in its own interpreter: the hang is at interpreter exit, which
the test process cannot reach for itself.
"""

import sys
from unittest.mock import MagicMock

import pytest

from tests.nested_pytest import run_bounded

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="#2519 tests require the real JVM (jpype mocked by --disable-jvm-session)",
    ),
]

# A start and a clean exit take about 15 s here. On ``main`` the hang never
# ends, so any bound well above the start separates the two.
_BOUND = 120

_START = """
import logging, threading
logging.disable(logging.CRITICAL)
from argumentation_analysis.core.jvm_setup import initialize_jvm
started = []
def start():
    started.append(initialize_jvm())
{call}
{after}
print("started", started[0], flush=True)
"""


def _run(argv, bound=_BOUND):
    # Bounded after the kill too: ``subprocess.run(timeout=...)`` waits for the
    # pipes without a bound once it has killed the child (#2530).
    return run_bounded(argv, bound, failure="the #2519 hang: the process did not exit")


def _start_and_exit(call, after=""):
    return _run([sys.executable, "-c", _START.format(call=call, after=after)])


@pytest.mark.parametrize(
    "call",
    ["start()", "t = threading.Thread(target=start); t.start(); t.join()"],
    ids=["from the main thread", "from another thread"],
)
def test_a_process_that_never_calls_java_exits(call):
    """DoD 1 and 2: red on ``main``, where both hung until killed."""
    done = _start_and_exit(call)

    assert "started True" in done.stdout, done.stdout + done.stderr[-2000:]
    assert done.returncode == 0, done.stderr[-2000:]


def test_a_process_that_called_java_exits_as_before():
    """DoD 4, control: green on ``main``."""
    done = _start_and_exit(
        "start()", after="import jpype; jpype.JClass('java.lang.String')"
    )

    assert "started True" in done.stdout, done.stdout + done.stderr[-2000:]
    assert done.returncode == 0, done.stderr[-2000:]


def test_a_pytest_session_that_runs_no_test_exits():
    """DoD 3: ``pytest_sessionstart`` starts the JVM and no test attaches the
    main thread. The session ends with pytest's own code for an empty
    selection. ``main``: the process never exited."""
    done = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_local_skip_storm_signal_2021.py",
            "-k",
            "no_test_is_named_like_this_2519",
            "-p",
            "no:cacheprovider",
            "-q",
        ]
    )

    assert "deselected" in done.stdout, done.stdout[-2000:]
    assert done.returncode == pytest.ExitCode.NO_TESTS_COLLECTED, done.stdout[-2000:]
