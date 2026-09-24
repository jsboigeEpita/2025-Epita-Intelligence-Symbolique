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

The child's output goes to files and the caller waits on the process, so a
process that the child leaves behind no longer holds the caller; it fails the
test instead, and is killed.
"""

import os
import re
import signal
import subprocess
import sys
import threading
import time

import pytest

from tests.nested_pytest import both, run_bounded, run_probe

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


_HANGS_IN_SESSIONFINISH = """
import time


def pytest_sessionfinish(session):
    time.sleep(3600)
"""


def test_a_hang_before_unconfigure_names_where_it_waits():
    """Runs 35969732872 and 35968028926: probes hung and no dump came.
    Armed at ``pytest_unconfigure``, the watchdog never saw a hang that
    happens before it."""
    with pytest.raises(pytest.fail.Exception) as failed:
        run_probe(
            "2538",
            {"probe_2538.py": _PROBE, "conftest.py": _HANGS_IN_SESSIONFINISH},
            bound=45,
            watchdog=2,
        )

    message = str(failed.value)
    assert "the probe session did not end within 45s" in message, message
    assert "Timeout (0:00:02)!" in message, message
    assert "in pytest_sessionfinish" in message, message


def _starts_a_holder(then):
    """A child that starts a process holding its stdout, prints its pid, then
    runs ``then``."""
    return f"""
import subprocess
import sys
import time

holder = subprocess.Popen(
    [sys.executable, "-c", "import time; time.sleep(600)"], stdout=sys.stdout
)
print("holder", holder.pid, flush=True)
{then}
"""


def _alive(pid):
    if os.name == "nt":
        listing = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        return re.search(rf"\b{pid}\b", listing) is not None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _kill(pid):
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


@pytest.mark.skipif(
    os.name != "nt", reason="on posix the orphan is re-parented and escapes the walk"
)
def test_a_process_left_behind_is_named_killed_and_fails():
    """The child exits at once; the process it started keeps its stdout open
    for 600 s. With pipes, the caller waited for that process (the first CI
    run of the #2490 probes lost 895 s so). With files, the caller is back as
    soon as the child is done, and the process left behind fails the test and
    is killed, since it would go on sharing the runner with the suite."""
    start = time.monotonic()
    with pytest.raises(pytest.fail.Exception) as failed:
        run_bounded([sys.executable, "-c", _starts_a_holder("")], bound=60)
    elapsed = time.monotonic() - start

    message = str(failed.value)
    holder = re.search(r"holder (\d+)", message)
    assert holder, message
    pid = int(holder.group(1))
    try:
        assert "the process exited, but left running (now killed)" in message, message
        assert re.search(rf"left running \(now killed\): .*\b{pid} ", message), message
        assert not _alive(pid), f"{pid} still runs"
        assert elapsed < 30, elapsed
    finally:
        _kill(pid)


def test_what_is_below_a_process_at_the_bound_is_named_and_killed():
    with pytest.raises(pytest.fail.Exception) as failed:
        run_bounded(
            [sys.executable, "-c", _starts_a_holder("time.sleep(600)")], bound=10
        )

    message = str(failed.value)
    assert "the process did not end within 10s" in message, message
    holder = re.search(r"holder (\d+)", message)
    assert holder, message
    pid = int(holder.group(1))
    try:
        assert re.search(rf"descendants: .*\b{pid} ", message), message
        assert not _alive(pid), f"{pid} still runs"
    finally:
        _kill(pid)


def _holds_the_interpreter(after, seconds):
    """After ``after`` s, keep every other thread of this process from running
    for up to 3 s at a time, for ``seconds`` s."""
    time.sleep(after)
    interval = sys.getswitchinterval()
    sys.setswitchinterval(3)
    try:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            pass
    finally:
        sys.setswitchinterval(interval)


def test_a_caller_that_could_not_run_says_so():
    """A bound can expire because the caller could not run, not because the
    child hung: on the runners, whole minutes went missing outside any child.
    The failure measures how late the caller's own ticks came."""
    holder = threading.Thread(target=_holds_the_interpreter, args=(2, 4))
    holder.start()
    try:
        with pytest.raises(pytest.fail.Exception) as failed:
            run_bounded(
                [sys.executable, "-c", "import time; time.sleep(600)"], bound=10
            )
    finally:
        holder.join()

    message = str(failed.value)
    gap = re.search(r"longest gap between two ticks of this process ([\d.]+)s", message)
    assert gap and float(gap.group(1)) >= 2, message
    assert re.search(r"wall clock \d+s, monotonic clock \d+s", message), message
