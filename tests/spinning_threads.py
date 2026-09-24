"""#2538 — a test must not leave a thread that spins.

Two tests of ``BackendManager`` handed it a ``MagicMock`` process. The manager
starts two ``_log_stream`` threads that read ``stream.readline`` until it
returns ``""``, and a mock's ``readline`` never does. Both threads ran for the
rest of the session and recorded every call on the mocks: on ai-01, 10.5 s of
CPU and 650 MB in the next 10 s, while the next test only slept. On CI, run
35981931020 (#2557) still had both at the 900 s timeout of a test that ran an
hour later.

A thread a test leaves alive is harmless while it waits. So after each test,
the threads started since its setup that are still alive are timed while this
thread sleeps ``WINDOW`` s. If they used at least ``SHARE`` of it ``SAMPLES``
times in a row, the test fails, and the message says where each one runs. The
threads share the GIL, so the share is summed over them.

Loaded as a plugin by ``tests/conftest.py``. ``psutil``, which times each
thread, is imported only when a test leaves a thread alive.
"""

from __future__ import annotations

import sys
import threading
import time
import traceback

import pytest

# How long this thread sleeps while the others are timed, in seconds.
WINDOW = 0.1
# The share of a window the new threads must use to count as spinning.
SHARE = 0.5
# How many windows in a row: a thread that finishes its work after the test
# stops using CPU within them.
SAMPLES = 3

_BEFORE = pytest.StashKey[frozenset]()


def left_alive(before):
    """The threads alive now that were not in ``before``."""
    return [
        thread
        for thread in threading.enumerate()
        if thread not in before and thread.is_alive() and thread.native_id
    ]


def _cpu(threads):
    """Seconds of CPU each of ``threads`` has used, by native id."""
    import psutil

    wanted = {thread.native_id for thread in threads}
    return {
        entry.id: entry.user_time + entry.system_time
        for entry in psutil.Process().threads()
        if entry.id in wanted
    }


def spinning(threads, window=WINDOW, share=SHARE, samples=SAMPLES):
    """``threads``, if together they used at least ``share`` of a ``window``
    s sleep of this thread, ``samples`` times in a row; else ``[]``."""
    if not threads:
        return []
    for _ in range(samples):
        first = _cpu(threads)
        time.sleep(window)
        second = _cpu(threads)
        used = sum(second.get(i, 0) - first.get(i, 0) for i in second)
        if used < share * window:
            return []
    return threads


def describe(threads):
    """The message for ``threads``: the name of each, and where it runs."""
    frames = sys._current_frames()
    parts = []
    for thread in threads:
        frame = frames.get(thread.ident)
        where = (
            "".join(traceback.format_stack(frame, limit=6))
            if frame is not None
            else "  (it ended meanwhile)\n"
        )
        parts.append(f"--- {thread.name}\n{where}")
    return (
        f"this test left {len(threads)} thread(s) running that use CPU while "
        f"nothing waits on them (#2538):\n" + "".join(parts)
    )


@pytest.hookimpl(wrapper=True)
def pytest_runtest_setup(item):
    item.stash[_BEFORE] = frozenset(threading.enumerate())
    return (yield)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    result = yield
    if _BEFORE in item.stash:
        spun = spinning(left_alive(item.stash[_BEFORE]))
        if spun:
            pytest.fail(describe(spun), pytrace=False)
    return result
