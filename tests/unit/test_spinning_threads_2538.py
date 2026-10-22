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


# This spinner records nothing, and stops after 30 s, many windows of the
# guard and more: a spinner that never stops holds every thread that waits for
# the GIL. On ai-01, the same two tests with no guard took 0.17 s with the
# waiter alone, and 27.6 s with a spinner that never stopped. (#3125: the
# lifetime was 5 s, then 10 s — under a full ``-n auto`` load that stretches
# every window, the measurement itself can outlive it and the witness flakes
# by the spinner dying of old age mid-measurement, not by the detector
# missing; the nested session ran 72 s loaded where it takes 7 s idle, so the
# cap must clear the stretched measurement with margin. The thread is a
# daemon: the nested process exits right after the second test, and the cap
# only bounds a runaway.)
_LEAVES_A_SPINNER = """
import threading
import time


def _spins():
    end = time.monotonic() + 30
    while time.monotonic() < end:
        pass


def test_leaves_a_spinner():
    threading.Thread(target=_spins, name="the-spinner", daemon=True).start()


def test_leaves_a_waiter():
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
    by the thread's name; the one that left a waiting thread passes."""
    done = _run_leaves(tmp_path)
    out = done.stdout
    assert done.returncode == 1, both(out, done.stderr)
    assert "ERROR at teardown of test_leaves_a_spinner" in out, both(out, done.stderr)
    assert "--- the-spinner" in out, both(out, done.stderr)
    assert "the-waiter" not in out, both(out, done.stderr)
    # The spinner's test passes, then errors at teardown: two passed, one error.
    assert "2 passed, 1 error" in out, both(out, done.stderr)


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
    while time.monotonic() < end:
        pass


def test_leaves_a_spinner():
    threading.Thread(target=_spins, name="the-spinner", daemon=True).start()


def test_leaves_a_waiter():
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
