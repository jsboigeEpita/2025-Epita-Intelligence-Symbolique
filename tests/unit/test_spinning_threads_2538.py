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
