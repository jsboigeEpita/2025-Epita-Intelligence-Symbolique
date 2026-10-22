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
thread sleeps ``WINDOW`` s. If they kept using, ``SAMPLES`` measurable windows
in a row, at least ``FACTOR`` of the CPU a calibration burner could get in the
same windows (``#3125``: the bar is relative — the absolute half-core-per-
window share was an idle-seat calibration, and under a full ``-n auto`` run a
rationed spinner never reached it), the test fails, and the message says
where each one runs. The threads share the GIL, so the use is summed over
them.

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
# How many windows in a row: a thread that finishes its work after the test
# stops using CPU within them.
SAMPLES = 3
# #3125: the suspects count as spinning when their CPU tracks what a
# core-hungry thread could actually get in the same windows — measured by
# the detector's own calibration burner, which runs while the suspects are
# timed and shares their rationing (GIL, scheduler, ``-n auto`` load alike).
FACTOR = 0.5
# A window where the calibration itself burned less than this carries no
# signal (the process was starved below accounting noise): it credits
# nothing and resets nothing — the loop retries it, up to MAX_ATTEMPTS.
CAL_FLOOR = 0.005
# Absolute floor per window: below this a thread is scheduler noise (a
# waiter's blip), however little the calibration got.
USED_FLOOR = 0.003
# Total windows attempted, measurable or not: SAMPLES measured windows must
# fit within it, so a starved run ends instead of hanging.
MAX_ATTEMPTS = 3 * SAMPLES

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


def _burn_until(stop: threading.Event) -> None:
    while not stop.is_set():
        pass


def _credits(used: float, gettable: float) -> bool | None:
    """The #3125 window decision, apart from the timing so it can be
    witnessed without a thread race.

    ``None`` — the window is unmeasurable (the calibration burner itself
    got less than ``CAL_FLOOR``: the process was starved below accounting
    noise). ``True`` — the suspects kept at least ``FACTOR`` of what was
    gettable, and something absolute (``USED_FLOOR``): scheduler noise
    alone never flags a waiter. ``False`` — a measured window the suspects
    did not use."""
    if gettable < CAL_FLOOR:
        return None
    return used >= max(FACTOR * gettable, USED_FLOOR)


def spinning(threads, window=WINDOW, samples=SAMPLES):
    """``threads``, if together they kept using, in ``samples`` measurable
    windows in a row, at least ``FACTOR`` of the CPU the calibration burner
    could get in the same windows; else ``[]``.

    The calibration burner is a thread of this process started for the
    measurement: whatever rationing the suspects live under — GIL
    contention or an ``-n auto`` OS load — it lives under it too, so
    ``FACTOR * gettable`` is what "still burning" means here, not an
    absolute share of a core (#3125).

    One thread enumeration per window boundary, shared with the next window
    (measured: under a loaded seat each ``psutil`` call can take more than
    the window itself, and a per-window cost of two calls let a 5 s spinner
    expire mid-measurement — the suspect set is snapshotted once, and a
    thread absent from a snapshot counts as ended: its delta is clamped at
    zero, never negative)."""
    if not threads:
        return []
    streak = 0
    attempts = 0
    cal_stop = threading.Event()
    cal = threading.Thread(
        target=_burn_until,
        args=(cal_stop,),
        daemon=True,
        name="spinning-detector-calibration",
    )
    cal.start()
    try:
        watched = list(threads) + [cal]
        cal_id = cal.native_id
        first = _cpu(watched)
        while streak < samples and attempts < MAX_ATTEMPTS:
            attempts += 1
            time.sleep(window)
            second = _cpu(watched)
            used = sum(
                max(0.0, second.get(i, 0.0) - first.get(i, 0.0))
                for i in first
                if i != cal_id
            )
            gettable = max(0.0, second.get(cal_id, 0.0) - first.get(cal_id, 0.0))
            first = second
            decision = _credits(used, gettable)
            if decision is None:
                # Unmeasurable window (the process was starved below
                # accounting noise): retry it, bounded by MAX_ATTEMPTS.
                continue
            if decision:
                streak += 1
            else:
                # A measured window without use ends the measurement, as it
                # always did: a thread that stopped burning is not spinning.
                break
        return threads if streak >= samples else []
    finally:
        cal_stop.set()
        cal.join(1)


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
