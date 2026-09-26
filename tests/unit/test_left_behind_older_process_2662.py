# -*- coding: utf-8 -*-
"""#2662: a process older than the probe is not something the probe left behind.

On Windows a process keeps its parent's id after the parent exits, and the id
can later go to another process. CI run 36195032275 gave a probe the id that
an exited ``smss.exe`` had held. ``_left_behind`` then listed the session's
csrss.exe, winlogon.exe, dwm.exe and fontdrvhost.exe as left running by the
probe, and ran ``taskkill /F /T`` on them.

The reuse cannot be produced on demand: 400 process creations on ai-01 did
not reuse the id of an exited process. What the walk decides on can be. Here
a real process names an exited parent as its own. The walk starts either
from that parent, or from a root created later, as the next holder of the id
would be.
"""

import os
import re
import subprocess
import sys
import time

import pytest

from tests import nested_pytest

pytestmark = pytest.mark.skipif(
    os.name != "nt",
    reason="on posix an orphan is re-parented: no process keeps a dead parent's id",
)

# Starts a sleeper, prints its id and exits. The sleeper keeps this process's
# id as its parent id.
_STARTS_A_SLEEPER = (
    "import subprocess, sys; "
    "sleeper = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'], "
    "stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); "
    "print(sleeper.pid, flush=True)"
)

# 100 ns intervals from 1601-01-01 to 1970-01-01.
_UNIX_EPOCH_AS_FILETIME = 116444736000000000


def _filetime(seconds):
    return int(seconds * 10**7) + _UNIX_EPOCH_AS_FILETIME


def _orphan():
    """A process that started a sleeper and exited, and the sleeper's id.

    The ``Popen`` still holds the exited process, so its id goes to no other
    process while the test runs.
    """
    parent = subprocess.Popen(
        [sys.executable, "-c", _STARTS_A_SLEEPER], stdout=subprocess.PIPE, text=True
    )
    sleeper = int(parent.stdout.readline())
    parent.wait()
    parent.stdout.close()
    return parent, sleeper


def _alive(pid):
    listing = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return re.search(rf"\b{pid}\b", listing) is not None


def _kill(pid):
    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)


def test_a_process_older_than_the_root_is_neither_reported_nor_killed(monkeypatch):
    """The root was created a second after the sleeper, as the next holder of
    the exited parent's id would be. The sleeper names that id as its parent,
    but the root did not start it."""
    parent, sleeper = _orphan()
    later = _filetime(time.time() + 1)
    monkeypatch.setattr(nested_pytest, "_created", lambda pid: later, raising=False)
    try:
        assert nested_pytest._left_behind(parent) == []
        assert _alive(sleeper), f"{sleeper}, which the root did not start, was killed"
    finally:
        _kill(sleeper)


def test_a_process_the_root_started_is_still_reported_and_killed():
    """Counter-pendulum: the root is the sleeper's real parent, and the
    harness reads its creation time itself."""
    parent, sleeper = _orphan()
    try:
        left = nested_pytest._left_behind(parent)
        assert sleeper in [pid for pid, _ in left], left
        assert not _alive(sleeper), f"{sleeper} still runs"
    finally:
        _kill(sleeper)


def test_an_exited_childs_creation_time_is_read_in_the_tables_unit():
    """Read through the handle the ``Popen`` holds, as a FILETIME at the
    microsecond precision of the process table's ``CreationDate``."""
    before = _filetime(time.time() - 1)
    child = subprocess.Popen([sys.executable, "-c", "pass"])
    child.wait()
    after = _filetime(time.time() + 1)
    created = nested_pytest._created(child.pid)
    assert before <= created <= after, (before, created, after)
    assert created % 10 == 0, created
