# -*- coding: utf-8 -*-
"""Run a pytest session in a fresh interpreter, on probe files under ``tests/``.

The probe lives under ``tests/`` so that ``tests/conftest.py`` applies to it,
as to any test of the suite. Its directory starts with ``_``, which
``norecursedirs`` skips, so an ordinary run never collects it, and it is
deleted when the session ends.

The child writes its stdout and stderr to files, not to pipes, and the wait
is on the process, not on its output (#2538). With pipes, the child's output
depends on the caller reading it, and the caller's wait depends on every
holder of the pipes closing them. A CI run showed the first dependency: a
probe finished its session and then waited for more than 240 s in
``_console_main``'s ``sys.stdout.flush()`` (run 35968028926), so its write
to the pipe was not being consumed. The first CI run of the #2490 probes
showed the second: a grandchild held the pipes, and the caller lost 895 s.
A file takes every write, and the caller reads it once the process is over,
the way ``pytester.run`` does.

A process the child leaves running no longer holds the caller, but it still
holds the machine: the rest of the suite shares the runner with it. So a child
that exits and leaves processes behind fails the test, and they are killed. On
ai-01, 17 probe sessions with a real JVM left none.

The wait is bounded. After ``BOUND`` seconds the process tree is killed, and
the test fails with the processes still below it, how the caller kept time
during the wait, and what the child wrote. The timekeeping tells a child that
hangs from a machine that stalls: on the runners, runs 35972448838 and
35967808661 lost minutes outside any child (an in-process extraction bounded
at 30 s measured 669 s; one warnings summary printed with 19 min between two
of its lines), and a bound that expires then says nothing about the child.

A probe session also loads this module as a plugin (``-p tests.nested_pytest``).
When the session starts to finish it arms ``faulthandler``: if the process is
still alive ``EXIT_WATCHDOG`` seconds later, every thread's stack goes to
stderr. A session that hangs at exit therefore fails with the place where it
waits, not only with the fact that it waited. A process that exits cancels
the watchdog, so a normal run prints nothing. The watchdog is armed at
``pytest_sessionfinish``: armed at ``pytest_unconfigure``, it never saw a hang
in between.
"""

import faulthandler
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# A probe session takes about 20 s on ai-01 and 12 s in CI, JVM start included.
BOUND = 300
# After a kill, how long the process may take to be gone.
DRAIN = 30
# After the child exits, how long what runs below it may take to end on its own.
SETTLE = 2
# After the session, how long a probe may take to exit before it dumps its
# threads. Well below BOUND, so the dump is in stderr when the bound expires.
EXIT_WATCHDOG = 60
_WATCHDOG_ENV = "NESTED_PYTEST_EXIT_WATCHDOG"


def descendants(pid):
    """The processes below ``pid``, as ``[(pid, name)]``, read from the
    process table.

    On Windows a process keeps its parent's id after the parent exits, so the
    walk still finds what a dead child left behind.
    """
    if os.name == "nt":
        argv = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | ForEach-Object "
            "{ '{0} {1} {2}' -f $_.ProcessId, $_.ParentProcessId, $_.Name }",
        ]
    else:
        argv = ["ps", "-eo", "pid=,ppid=,comm="]
    listing = subprocess.run(
        argv, capture_output=True, text=True, timeout=60, check=True
    ).stdout
    children = {}
    for line in listing.splitlines():
        fields = line.split(None, 2)
        if len(fields) == 3 and fields[0].isdigit() and fields[1].isdigit():
            children.setdefault(int(fields[1]), []).append((int(fields[0]), fields[2]))
    found, seen, todo = [], {pid}, [pid]
    while todo:
        for child, name in children.get(todo.pop(), []):
            if child not in seen:
                seen.add(child)
                found.append((child, name))
                todo.append(child)
    return found


def _state_at_bound(process):
    """What was below ``process`` when the bound expired. ``(text, pids)``."""
    try:
        below = descendants(process.pid)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"--- at the bound\ndescendants: not listed ({exc!r})\n", []
    listed = ", ".join(f"{pid} {name}" for pid, name in below) or "none"
    return f"--- at the bound\ndescendants: {listed}\n", [pid for pid, _ in below]


class _Ticks(threading.Thread):
    """How this process kept time while it waited: the wall clock, the
    monotonic clock, and the longest gap between two of its ticks.

    A late tick means this process could not run, whatever the child did. A
    wall clock ahead of the monotonic one means the machine's clock jumped.
    """

    TICK = 0.5

    def __init__(self):
        super().__init__(daemon=True)
        self._done = threading.Event()
        self.longest = 0.0

    def run(self):
        last = time.monotonic()
        while not self._done.wait(self.TICK):
            now = time.monotonic()
            self.longest = max(self.longest, now - last)
            last = now

    def __enter__(self):
        self._wall, self._mono = time.time(), time.monotonic()
        self.start()
        return self

    def __exit__(self, *exc):
        self._done.set()
        self.join()
        self.wall = time.time() - self._wall
        self.mono = time.monotonic() - self._mono

    def __str__(self):
        return (
            f"--- the wait\nwall clock {self.wall:.0f}s, monotonic clock "
            f"{self.mono:.0f}s, longest gap between two ticks of this process "
            f"{self.longest:.1f}s (one tick every {self.TICK}s)\n"
        )


def _kill(pids):
    """Kill each of ``pids``, and on Windows what runs below it."""
    for pid in pids:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                check=False,
            )
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


def kill_tree(process, pids=()):
    """Kill ``process``, its children and ``pids``, then wait at most ``DRAIN``
    s for ``process`` to be gone.

    ``pids``, what was below the process at the bound, are killed one by one
    as well, for one that left the process group.

    ``eprover_runner._kill_tree`` kills the same way.
    """
    if os.name == "nt":
        _kill([process.pid])
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    _kill(pids)
    process.kill()
    try:
        process.wait(timeout=DRAIN)
    except subprocess.TimeoutExpired:
        pass


def _left_behind(process):
    """What ``process``, which has exited, left running: the processes below
    it that are still there ``SETTLE`` s later. They are killed.

    The walk goes by parent id, so on Windows it finds what the dead process
    started; on posix an orphan is re-parented and escapes it.
    """
    below = descendants(process.pid)
    if not below:
        return []
    time.sleep(SETTLE)
    first = {pid for pid, _ in below}
    left = [(pid, name) for pid, name in descendants(process.pid) if pid in first]
    _kill([pid for pid, _ in left])
    return left


def both(out, err):
    """The tail of the child's stdout and stderr, for an assertion message.

    More of stderr, where an exit watchdog writes its thread dump.
    """
    return f"--- stdout\n{out[-3000:]}\n--- stderr\n{err[-8000:]}"


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_sessionfinish(session):
    """In a probe session: from here on, dump every thread if the process
    outlives the watchdog."""
    faulthandler.dump_traceback_later(
        float(os.environ.get(_WATCHDOG_ENV, EXIT_WATCHDOG)), file=sys.__stderr__
    )
    yield


def run_bounded(argv, bound=BOUND, failure="the process did not end", env=None):
    """Run ``argv`` from the repository root, with the root on ``PYTHONPATH``.

    A ``subprocess.CompletedProcess``. After ``bound`` seconds the process
    tree is killed and the test fails with ``failure``, what was below the
    process at the bound, how the caller kept time, and the child's output.
    A process that exits but leaves others running fails the test too.
    ``env`` adds to the caller's environment.
    """
    env = {**os.environ, **(env or {})}
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    # A process that outlives the child may still hold the files: their
    # directory is then left for the OS to clean.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        out_path, err_path = Path(tmp) / "stdout", Path(tmp) / "stderr"
        with open(out_path, "wb") as out_file, open(err_path, "wb") as err_file:
            process = subprocess.Popen(
                argv,
                cwd=ROOT,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=out_file,
                stderr=err_file,
                start_new_session=os.name != "nt",
            )
        state, left = None, []
        with _Ticks() as ticks:
            try:
                process.wait(timeout=bound)
                expired = False
            except subprocess.TimeoutExpired:
                expired = True
        if expired:
            state, below = _state_at_bound(process)
            kill_tree(process, below)
        else:
            left = _left_behind(process)
        out = out_path.read_text(encoding="utf-8", errors="replace")
        err = err_path.read_text(encoding="utf-8", errors="replace")
    if state is not None:
        pytest.fail(f"{failure} within {bound}s\n{state}{ticks}" + both(out, err))
    if left:
        listed = ", ".join(f"{pid} {name}" for pid, name in left)
        pytest.fail(
            f"the process exited, but left running (now killed): {listed}\n"
            + both(out, err)
        )
    return subprocess.CompletedProcess(argv, process.returncode, out, err)


def run_probe(label, files, *argv, bound=BOUND, watchdog=EXIT_WATCHDOG, env=None):
    """Run pytest on ``files`` (``{name: source}``). ``(returncode, stdout, stderr)``.

    The first ``.py`` file whose name starts with ``probe`` is the one pytest
    is given; the others (a ``conftest.py``) sit beside it. ``watchdog``: the
    seconds after the session before the probe dumps its threads. ``env``:
    entries added to (or overriding) the caller's environment for the probe.
    """
    probe_dir = ROOT / "tests" / f"_probe_{label}_{uuid.uuid4().hex}"
    probe_dir.mkdir()
    try:
        for name, source in files.items():
            (probe_dir / name).write_text(source, encoding="utf-8")
        target = next(name for name in files if name.startswith("probe"))
        done = run_bounded(
            [
                sys.executable,
                "-m",
                "pytest",
                str(probe_dir / target),
                "-p",
                "no:cacheprovider",
                "-p",
                "tests.nested_pytest",
                "-q",
                *argv,
            ],
            bound,
            failure="the probe session did not end",
            env={_WATCHDOG_ENV: str(watchdog), **(env or {})},
        )
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
    return done.returncode, done.stdout, done.stderr
