# -*- coding: utf-8 -*-
"""#2538: a test that leaves a thread spinning fails, by the thread's name.

The spinning thread here has the shape of the one ``BackendManager`` left: it
reads a ``MagicMock`` stream until ``readline`` returns ``""``, which a mock
never does. Each test stops its own threads.
"""

import sys
import threading
import time
from unittest.mock import MagicMock

import pytest

from tests.nested_pytest import both, run_bounded
from tests.spinning_threads import describe, left_alive, spinning


def _reads_a_mock_stream(stop):
    stream = MagicMock()
    for line in iter(stream.readline, ""):
        if stop.is_set():
            return


def _started(target, *args):
    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()
    return thread


def test_a_thread_that_spins_is_named():
    before = frozenset(threading.enumerate())
    stop = threading.Event()
    thread = _started(_reads_a_mock_stream, stop)
    try:
        spun = spinning(left_alive(before))
        assert spun == [thread]
        message = describe(spun)
        assert thread.name in message, message
        assert "in _reads_a_mock_stream" in message, message
    finally:
        stop.set()
        thread.join(5)


def test_a_thread_that_waits_is_not():
    before = frozenset(threading.enumerate())
    stop = threading.Event()
    thread = _started(stop.wait)
    try:
        assert left_alive(before) == [thread]
        assert spinning([thread]) == []
    finally:
        stop.set()
        thread.join(5)


def _works_then_waits(seconds, stop):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        pass
    stop.wait()


def test_a_thread_that_finishes_its_work_is_not():
    """Busy for 0.15 s after the test, then waiting: the third window at the
    latest sees it idle."""
    stop = threading.Event()
    thread = _started(_works_then_waits, 0.15, stop)
    try:
        assert spinning([thread]) == []
    finally:
        stop.set()
        thread.join(5)


def test_a_thread_that_ended_is_not_left_alive():
    before = frozenset(threading.enumerate())
    thread = _started(lambda: None)
    thread.join(5)
    assert thread not in left_alive(before)


# This spinner records nothing, and stops after 5 s, three windows of the
# guard and more: a spinner that never stops holds every thread that waits for
# the GIL. On ai-01, the same two tests with no guard took 0.17 s with the
# waiter alone, and 27.6 s with a spinner that never stopped.
_LEAVES_A_SPINNER = """
import threading
import time


def _spins():
    end = time.monotonic() + 5
    while time.monotonic() < end:
        pass


def test_leaves_a_spinner():
    threading.Thread(target=_spins, name="the-spinner", daemon=True).start()


def test_leaves_a_waiter():
    threading.Thread(
        target=threading.Event().wait, name="the-waiter", daemon=True
    ).start()
"""


def test_the_plugin_fails_the_test_that_left_it(tmp_path):
    """Through the hooks: the test that left the spinner errors at teardown,
    by the thread's name; the one that left a waiting thread passes."""
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / "test_leaves.py").write_text(_LEAVES_A_SPINNER, encoding="utf-8")
    done = run_bounded(
        [
            sys.executable,
            "-m",
            "pytest",
            str(tmp_path / "test_leaves.py"),
            "-c",
            str(tmp_path / "pytest.ini"),
            "-p",
            "no:cacheprovider",
            "-p",
            "tests.spinning_threads",
            "-p",
            "no:randomly",
            "-rE",
        ],
        bound=120,
    )
    out = done.stdout
    assert done.returncode == 1, both(out, done.stderr)
    assert "ERROR at teardown of test_leaves_a_spinner" in out, both(out, done.stderr)
    assert "--- the-spinner" in out, both(out, done.stderr)
    assert "the-waiter" not in out, both(out, done.stderr)
    # The spinner's test passes, then errors at teardown: two passed, one error.
    assert "2 passed, 1 error" in out, both(out, done.stderr)


def test_the_suite_loads_the_plugin(request):
    assert request.config.pluginmanager.has_plugin("tests.spinning_threads")
