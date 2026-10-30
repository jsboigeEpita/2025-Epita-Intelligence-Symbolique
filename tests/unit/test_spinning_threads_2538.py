# -*- coding: utf-8 -*-
"""#2538: a test that leaves a thread spinning fails, by the thread's name.

The spinning thread here has the shape of the one ``BackendManager`` left: it
reads a ``MagicMock`` stream until ``readline`` returns ``""``, which a mock
never does. Each test stops its own threads.

#3171: the nested witnesses' spinner outlives the measurement by construction
(spun until the session releases it, not for a wall-clock margin), and a
suspect that ends mid-measurement is reported — never cleared by the windows
that followed its death.
"""

import sys
import threading
import time
from unittest.mock import MagicMock

import pytest

from tests.nested_pytest import both, run_bounded
from tests.spinning_threads import describe, left_alive, spinning, verdict_of


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
        trail = []
        spun = spinning(left_alive(before), trail=trail)
        # #3218: the return value alone cannot tell a clear verdict from an
        # exhausted measurement, and this witness reddened in CI (run
        # 40079683346) printing `assert [] == [...]` and nothing else. The
        # trail is the evidence, and it is in the red.
        assert verdict_of(trail) == "caught", describe(spun, trail)
        assert spun == [thread], describe(spun, trail)
        message = describe(spun, trail)
        assert thread.name in message, message
        assert "in _reads_a_mock_stream" in message, message
        assert "window trail" in message, message
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


def test_the_relative_rule_catches_what_the_absolute_bar_missed():
    """#3125: the window decision, on the numbers the ai-01 flake measured.

    A spinner rationed to ~a fifth of the window (~20 ms of 100) by the
    other workers of a full ``-n auto`` run: main's absolute bar (half of
    the nominal window, 50 ms) calls it NOT spinning — the false negative.
    The relative rule compares it with what the calibration burner could
    get in the same rationed window (~40 ms): the spinner tracks what was
    gettable, and counts. (Witnessed on the arithmetic, not on a thread
    race: a racing witness was measured on a live seat and its per-window
    GIL shares skew with the scheduler — the deterministic disagreement
    lives in these numbers, and the real-thread witnesses below carry the
    integration.)"""
    from tests.spinning_threads import _credits

    # Spinner ~20 ms, calibration ~40 ms, in the same rationed window.
    assert _credits(used=0.020, gettable=0.040) is True
    # A spinner keeping pace with everything the window offered.
    assert _credits(used=0.060, gettable=0.060) is True
    # A waiter's blip is noise, never a spinner (healthy calibration).
    assert _credits(used=0.002, gettable=0.040) is False
    # A waiter's blip against a starved calibration: the window carries no
    # signal at all — unmeasurable, the same None as below.
    assert _credits(used=0.002, gettable=0.004) is None
    # The calibration itself starved below accounting noise: the window
    # carries no signal — not a pass, not a fail.
    assert _credits(used=0.020, gettable=0.003) is None


def test_a_window_under_two_charge_ticks_is_unmeasurable():
    """#3218: one charge tick of budget is not a measurement.

    The CI red measured ``gettable=15.6ms, used=0ms`` on a spinner alive
    throughout: one tick against zero is the same reading a spinner gives
    when its charge is booked in the next window, and three such windows in a
    row were a silent ``clear``. Two ticks are the first window where the two
    differ by a whole tick: a spinner at ``FACTOR`` owes one, a waiter owes
    none. The tick is the ai-01 quantum, passed explicitly — the witness
    states the arithmetic, not the seat."""
    from tests.spinning_threads import _credits

    tick = 0.015625
    assert _credits(used=0.0, gettable=tick, quantum=tick) is None
    assert _credits(used=0.0, gettable=1.9 * tick, quantum=tick) is None
    # Two ticks: measurable, and the waiter is not flagged by it.
    assert _credits(used=0.0, gettable=2 * tick, quantum=tick) is False
    assert _credits(used=tick, gettable=2 * tick, quantum=tick) is True


# #3302 — the fourth CI red of the positive control, as a synthetic trail:
# CI run 41092477723 printed exactly these four windows for the-spinner,
# alive throughout (it spins until the session releases it). Every reading is
# a whole number of the seat's 15.6 ms charge tick, and in each False window
# the spinner booked one or two ticks while the burner booked five or six.
_CI_TRAIL = [
    (0.047, 0.078, True),
    (0.031, 0.078, False),
    (0.031, 0.094, False),
    (0.016, 0.094, False),
]
_TICK = 0.015625


def test_a_live_spinner_squeezed_to_ticks_is_not_cleared():
    """#3302, born red: the CI trail above, decided as a rule and with no
    thread race. The suspect is ALIVE throughout — the child session exits 0
    today, which is the false negative; #3218's rule reads three sub-bar
    windows in a row as a clear, and those windows are 1-2 ticks against a
    burner's 5-6, where one tick flips the ratio. On main this assertion
    fails with ``'clear' == 'caught'``: the rule itself, not a missing
    argument."""
    assert verdict_of(_CI_TRAIL) == "caught"


def test_a_thread_on_one_tick_per_window_is_still_running():
    """A spinner never reaching the ratio bar but booking a tick every
    window: still using CPU when the measurement ran out — caught, not
    cleared. The burnt-then-quiet thread below is the other side of the
    line, and the pair is the control this rule must keep apart."""
    trail = [(0.016, 0.094, False)] * 9
    assert verdict_of(trail) == "caught"


def test_a_burned_thread_that_went_quiet_is_cleared():
    """The finished-work control (#3218): a thread that met the bar, then
    booked NO tick for three measured windows, reads as finished. Its
    windows are zero-tick — the reading a waiter gives — not sub-bar
    readings that a scheduler squeeze can produce. Green on main and after
    #3302: this control must never move."""
    trail = [(0.100, 0.100, True)] + [(0.000, 0.100, False)] * 3
    assert verdict_of(trail) == "clear"


def test_a_measurement_ending_on_a_starved_window_stays_undetermined():
    """The #3125 invariant survives #3302: when the calibration starves, the
    windows carry no signal — even a suspect that booked ticks earlier is
    not caught by the windows that follow, and the trail that ENDS on an
    unmeasured window stays undetermined. Green on main and after #3302."""
    trail = [(0.047, 0.078, True)] + [(0.000, 0.003, None)] * 7
    assert verdict_of(trail) == "undetermined"


def test_a_quiet_window_is_a_zero_tick_window():
    """The separation is absolute, in charge ticks: zero is the waiter's
    reading, one tick is already a running thread. The noise floor governs
    only where the seat charges finer than it."""
    from tests.spinning_threads import _booked

    assert _booked(0.0, _TICK) is False
    assert _booked(0.002, _TICK) is False
    assert _booked(_TICK, _TICK) is True
    assert _booked(0.016, _TICK) is True
    # Fine-clock seat: the noise floor decides below one of its ticks.
    assert _booked(0.002, 0.001) is False
    assert _booked(0.004, 0.001) is True


def test_the_tick_floor_uses_this_seat_s_thread_clock():
    """#3218: the quantum is measured on the seat, never hard-coded — a
    hard-coded 15.625 ms would state the wrong resolution wherever the seat
    charges differently (and would silently stop protecting it)."""
    from tests.spinning_threads import _credits, thread_time_quantum

    quantum = thread_time_quantum()
    assert quantum > 0, "the seat exposed no positive thread-time increment"
    assert _credits(used=0.0, gettable=quantum, quantum=quantum) is None
    assert _credits(used=0.0, gettable=2 * quantum, quantum=quantum) is False


def test_the_clear_warning_carries_the_windows_that_produced_it():
    """#3218: a clear is reported with its evidence when the threads did use
    CPU, and a waiter's clear stays quiet (no used window to report)."""
    from tests.spinning_threads import burned, clear_warning

    thread = threading.Thread(target=lambda: None, name="the-burner")
    trail = [
        (0.100, 0.100, True),
        (0.050, 0.100, True),
        (0.000, 0.100, False),
        (0.000, 0.100, False),
        (0.000, 0.100, False),
    ]
    assert burned(trail) is True
    message = clear_warning([thread], trail)
    assert "the-burner" in message, message
    assert "used=100ms" in message and "-> True" in message, message
    assert "5 window(s)" in message, message
    assert "clear" in message.lower(), message
    assert burned([(0.001, 0.100, False)] * 3) is False


# This spinner records nothing and spins until the session releases it: the
# test after it sets _STOP, and by then the teardown hook of the spinner's
# test — the measurement — has necessarily returned (pytest finishes one
# item's teardown before the next item's setup). It outlives the measurement
# by construction, not by a wall-clock margin: every lifetime tried before
# (5 s, 10 s, 30 s) was overtaken by a slower box — CI run 39847560034 took
# 29.10 s against the spinner's 30 s, the spinner died mid-measurement, and
# the verdict was a silent clear (#3171). The 30 s bound stays only against
# a runaway: the thread is a daemon, the nested process exits right after
# the second test, and the bound only limits a hang.
_LEAVES_A_SPINNER = """
import threading
import time

_STOP = threading.Event()


def _spins():
    end = time.monotonic() + 30
    while not _STOP.is_set() and time.monotonic() < end:
        pass


def test_leaves_a_spinner():
    threading.Thread(target=_spins, name="the-spinner", daemon=True).start()


def test_leaves_a_waiter():
    _STOP.set()
    threading.Thread(
        target=threading.Event().wait, name="the-waiter", daemon=True
    ).start()
"""


def test_an_unmeasured_run_is_not_a_verdict():
    """#3125 rework: a starved calibration leaves the run undetermined —
    never a silent pass. (Witnessed on the trail arithmetic, not on a
    starved box: the synthetic-load witness below carries the integration.)"""
    from tests.spinning_threads import verdict_of

    # Every window starved below the calibration floor: no verdict at all.
    assert verdict_of([(0.020, 0.003, None)] * 9) == "undetermined"
    # Three used windows, however interleaved with unmeasured ones.
    caught = [
        (0.020, 0.040, True),
        (0.020, 0.003, None),
        (0.020, 0.040, True),
        (0.020, 0.003, None),
        (0.020, 0.040, True),
    ]
    assert verdict_of(caught) == "caught"
    # Three measured unused windows in a row: a waiter, definitively.
    assert verdict_of([(0.002, 0.040, False)] * 3) == "clear"
    # Two used windows then starvation to exhaustion: still no verdict.
    starved = [(0.020, 0.040, True)] * 2 + [(0.020, 0.003, None)] * 7
    assert verdict_of(starved) == "undetermined"


def test_the_undetermined_warning_names_the_thread_and_the_windows():
    from tests.spinning_threads import undetermined_warning

    thread = threading.Thread(target=lambda: None, name="the-spinner")
    warning = undetermined_warning([thread], [(0.020, 0.003, None)] * 9)
    assert "the-spinner" in warning, warning
    assert "undetermined" in warning, warning
    assert "used=20ms" in warning, warning
    assert "gettable=3ms" in warning, warning
    assert "-> None" in warning, warning
    assert "9 window(s)" in warning, warning


def _burns_then_ends(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        pass


def test_a_thread_that_dies_mid_measurement_gives_no_measurement():
    """#3171 at the function level: the suspect ends during the windows —
    `spinning` returns no verdict (`[]`), records the name, and never lets
    the unused windows after the death accumulate into a clear."""
    thread = _started(_burns_then_ends, 0.15)
    try:
        trail = []
        ended = []
        assert spinning([thread], trail=trail, ended=ended) == []
        assert ended == [thread.name]
    finally:
        thread.join(5)


def test_the_ended_warning_names_the_thread_and_the_windows():
    from tests.spinning_threads import ended_warning

    thread = threading.Thread(target=lambda: None, name="the-spinner")
    warning = ended_warning(
        [thread], ["the-spinner"], [(0.100, 0.100, True), (0.050, 0.100, True)]
    )
    assert "the-spinner" in warning, warning
    assert "ended during measurement" in warning, warning
    assert "used=100ms" in warning, warning
    assert "gettable=100ms" in warning, warning
    assert "-> True" in warning, warning


def test_the_red_message_carries_the_window_trail():
    """#3171: a red fires where it fires — its message carries the evidence
    for the verdict, the attempted windows themselves."""
    from tests.spinning_threads import describe

    thread = threading.Thread(target=lambda: None, name="the-spinner")
    message = describe([thread], [(0.100, 0.100, True)] * 3)
    assert "window trail" in message, message
    assert "used=100ms" in message and "gettable=100ms" in message, message
    assert "3 attempted" in message, message
    # Without a trail the message stands as before.
    assert "window trail" not in describe([thread])


def _run_leaves(tmp_path, bound=180, source=_LEAVES_A_SPINNER):
    """Run the nested plugin session whose tests leave a spinner and a
    waiter; ``-W always`` so an undetermined-verdict warning always reaches
    the output a red witness prints (#3125 rework)."""
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / "test_leaves.py").write_text(source, encoding="utf-8")
    return run_bounded(
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
            "-W",
            "always",
        ],
        bound=bound,
    )


def test_the_plugin_fails_the_test_that_left_it(tmp_path):
    """Through the hooks: the test that left the spinner errors at teardown,
    by the thread's name; the one that left a waiting thread passes. The
    spinner spins until the session releases it (#3171), so it is alive for
    every window of the measurement on any seat — the control: a spinner
    alive throughout is caught, and the red carries its window trail."""
    done = _run_leaves(tmp_path)
    out = done.stdout
    assert done.returncode == 1, both(out, done.stderr)
    assert "ERROR at teardown of test_leaves_a_spinner" in out, both(out, done.stderr)
    assert "--- the-spinner" in out, both(out, done.stderr)
    assert "window trail" in out, both(out, done.stderr)
    assert "the-waiter" not in out, both(out, done.stderr)
    # The spinner's test passes, then errors at teardown: two passed, one error.
    assert "2 passed, 1 error" in out, both(out, done.stderr)


# #3171's CI red in miniature: a spinner whose wall clock expires
# mid-measurement — anchored to the measurement itself. The thread waits for
# the detector's calibration burner (it starts when the teardown measurement
# does), then spins a clock too short for three windows. 0.15 s is under
# SAMPLES * WINDOW (0.3 s) of wall time, and a window never shortens (the
# sleep never returns early), so after the burner appears the thread ends
# before three windows can elapse on any seat: it cannot be caught (three
# used windows) and cannot be cleared (a used window comes first, then three
# unused would be needed). The only honest verdict is that it ended during
# the measurement. The anchor matters: under a full ``-n auto`` run the gap
# between the test body and the teardown measurement can consume a clock
# started at thread start (measured here: 2 of 4 full runs, the thread died
# before left_alive saw it and the run was a plain pass) — anchored, the gap
# only delays the wait, and the death always lands inside the measurement.
# The burner's name is the detector's own; a rename of it reddens this
# witness (the wait never ends, the thread reads as a waiter), loudly.
_LEAVES_A_DYING_SPINNER = """
import threading
import time


def _spins_its_last():
    while not any(
        t.name == "spinning-detector-calibration"
        for t in threading.enumerate()
    ):
        time.sleep(0.005)
    end = time.monotonic() + 0.15
    while time.monotonic() < end:
        pass


def test_leaves_a_dying_spinner():
    threading.Thread(
        target=_spins_its_last, name="the-dying-spinner", daemon=True
    ).start()
"""


def test_a_thread_that_ends_mid_measurement_is_reported(tmp_path):
    """#3171: a suspect that dies during the measurement gives no
    measurement — the nested session reports it (a warning naming the thread
    and the window trail), never a silent clear. On main this run printed
    `1 passed` and nothing else: the spinner died, the windows after it read
    as unused, and the clear was silent."""
    done = _run_leaves(tmp_path, source=_LEAVES_A_DYING_SPINNER)
    out = done.stdout
    assert "ended during measurement" in out, both(out, done.stderr)
    assert "the-dying-spinner" in out, both(out, done.stderr)
    assert "used=" in out and "gettable=" in out, both(out, done.stderr)
    # A report, not a failure: a thread ending is not proof it was spinning
    # — only proof that it cannot be measured.
    assert done.returncode == 0, both(out, done.stderr)
    assert "1 passed" in out, both(out, done.stderr)
    assert "ERROR at teardown" not in out, both(out, done.stderr)


# #3218 has no nested witness for the warned clear, by measurement. Forcing
# one needs a suspect that registers at least one used window (used >= half
# of what the calibration burner got in the same window) and then stops —
# a majority GIL share for exactly two window-cycles. But a window-cycle is
# not WINDOW: the per-window psutil read takes ~60 ms on this seat, during
# which the calibration burns and the suspects may or may not, and the GIL
# split of two burning threads is not 50/50 (measured here, anchored burner
# vs calibration: 125 ms vs 46.9 ms in one cycle, 29%) — so the used window
# is a coin the scheduler flips, and a witness built on it flakes exactly
# the way this issue repairs. The warned clear is witnessed where it is
# deterministic instead: `burned` and `clear_warning` at the function level
# above, and the plugin branch is their four-line composition. A retry
# around the nested run would hide the coin, not remove it — the DoD forbids
# it.


# The rationed regime of the #3125 rework: hogs started at import hold
# their share of the GIL for the whole nested session, so the spinner the
# test leaves gets a fraction of the window (~25 ms of 100 with two hogs —
# below main's absolute half-window bar, above the relative bar once
# compared with what the calibration burner gets under the same hogs).
# External burner processes cannot build this regime on this OS (measured:
# the scheduler rations per process, and the loaded process keeps a full
# core, which the absolute bar catches); the loaded-seat false negative was
# always an in-process GIL split.
#
# The witness of this regime is marked slow, and that is a measurement, not
# a cost note: stacked on the real load of a full ``-n auto`` gate run, the
# marginal window tips below the (unchanged) relative bar often enough that
# the verdict came back *clear* — a measured miss, not a silence (two full
# loaded runs, no undetermined warning, spinner alive at 30 s). The
# under-load guarantee is carried by the unmarked plain witness above (the
# ai-01 family, green in every loaded run of this rework); this one pins
# the deterministic idle separation — red on the absolute bar, green on the
# relative one — and runs under a load-free selection.
_LEAVES_A_RATIONED_SPINNER = """
import threading
import time

_STOP = threading.Event()


def _hog():
    while not _STOP.is_set():
        pass


for _i in range(2):
    threading.Thread(target=_hog, daemon=True, name=f"hog-{_i}").start()


def _spins():
    end = time.monotonic() + 30
    while not _STOP.is_set() and time.monotonic() < end:
        pass


def test_leaves_a_spinner():
    threading.Thread(target=_spins, name="the-spinner", daemon=True).start()


def test_leaves_a_waiter():
    _STOP.set()
    threading.Thread(
        target=threading.Event().wait, name="the-waiter", daemon=True
    ).start()
"""


@pytest.mark.slow
def test_the_plugin_fails_a_rationed_spinner(tmp_path):
    """The DoD witness of the #3125 rework: through the plugin, with hogs
    rationing the GIL, the test that left the spinner still errors at
    teardown — the relative bar catches what the rationing leaves it, where
    main's absolute half-window bar reads the same spinner as a waiter. If
    the seat starves the calibration too, the verdict is undetermined and
    the warning says so; in neither case a silent pass."""
    done = _run_leaves(tmp_path, source=_LEAVES_A_RATIONED_SPINNER)
    out = done.stdout
    assert done.returncode == 1, both(out, done.stderr)
    assert "ERROR at teardown of test_leaves_a_spinner" in out, both(out, done.stderr)
    assert "--- the-spinner" in out, both(out, done.stderr)


def test_the_suite_loads_the_plugin(request):
    assert request.config.pluginmanager.has_plugin("tests.spinning_threads")
