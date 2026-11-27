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
the test fails with the processes still below it — or with the fact that they
could not be listed, when the walk itself failed (#3702) — how the caller kept
time during the wait, and what the child wrote. The timekeeping tells a child
that hangs from a machine that stalls: on the runners, runs 35972448838 and
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
# How long one process listing may take before the walk below a child gives
# up. The listing is machine work — a WMI query on Windows, ``ps`` on posix —
# and the slowest thing this module asks of a busy seat. Measured 2026-11-26:
# a fixed 60 s was outrun under four workers on a degraded machine, the same
# node passing alone in 79 s (#3702). Derived from the number of workers
# sharing the seat, and capped, so a mis-set variable cannot make the walk
# wait forever.
LISTING_BASE = 60
LISTING_MAX_FACTOR = 3


def listing_budget() -> int:
    """How long one process listing may take: ``LISTING_BASE`` seconds per
    worker sharing the machine, up to ``LISTING_MAX_FACTOR`` of them."""
    try:
        workers = int(os.environ.get("PYTEST_XDIST_WORKER_COUNT", "1"))
    except ValueError:
        workers = 1
    return LISTING_BASE * max(1, min(workers, LISTING_MAX_FACTOR))


class ProcessListingFailed(RuntimeError):
    """The process table could not be read — the walk's own failure (#3702).

    Raised instead of ``subprocess.TimeoutExpired`` so that a run states
    *which* instrument failed. The child the walk was asked about may have
    behaved perfectly; what cannot be said is what it left running.

    It lands on two paths, which do not treat it alike. On the exit path
    (``_left_behind``) it propagates: the child is over, and the failure is
    what the run has to report. At the bound (``_state_at_bound``) it is one
    line of the bound's report: the child's failure is that it outlived its
    bound, and it is killed either way.
    """


# OpenProcess access right, enough for GetProcessTimes.
_QUERY_LIMITED_INFORMATION = 0x1000


def _created(pid):
    """When process ``pid`` was created, in the unit of the Windows process
    table's creation column: a FILETIME (100 ns since 1601), cut to the
    column's microsecond precision. ``None`` on posix.

    The caller's ``Popen`` holds a handle to ``pid``, so the id names the same
    process even after it has exited.
    """
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
        ctypes.POINTER(wintypes.FILETIME)
    ] * 4
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel32.OpenProcess(_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel32.GetProcessTimes(handle, *map(ctypes.byref, times)):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(handle)
    return (times[0].dwHighDateTime << 32 | times[0].dwLowDateTime) // 10 * 10


def descendants(pid, created):
    """The processes below ``pid``, as ``[(pid, name)]``, read from the
    process table. ``created``: when ``pid`` was created (``_created``).

    On Windows a process keeps its parent's id after the parent exits, so the
    walk still finds what a dead child left behind. The id stays after it has
    gone to another process too, so a process counts as below another only if
    it was created at or after it (the rule of ``psutil``'s
    ``Process.children``). Without that rule, a CI run gave a probe the id of
    an exited ``smss.exe``, listed the session's csrss.exe, winlogon.exe,
    dwm.exe and fontdrvhost.exe as left behind by the probe, and killed them
    (#2662). On posix an orphan is re-parented, so a parent id always names a
    live process, and the table has no creation column.

    A listing that does not answer within ``listing_budget()`` seconds raises
    ``ProcessListingFailed`` (#3702), so the run states which instrument failed.
    """
    if os.name == "nt":
        argv = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | ForEach-Object "
            "{ '{0} {1} {2} {3}' -f $_.ProcessId, $_.ParentProcessId, "
            "$(if ($_.CreationDate) { $_.CreationDate.ToFileTimeUtc() } else { 0 }), "
            "$_.Name }",
        ]
        width = 4
    else:
        argv = ["ps", "-eo", "pid=,ppid=,comm="]
        width = 3
    budget = listing_budget()
    try:
        listing = subprocess.run(
            argv, capture_output=True, text=True, timeout=budget, check=True
        ).stdout
    except subprocess.TimeoutExpired as expired:
        raise ProcessListingFailed(
            f"the process listing did not answer within {budget} s "
            f"(listing budget {budget} s = {LISTING_BASE} s per worker, "
            f"PYTEST_XDIST_WORKER_COUNT="
            f"{os.environ.get('PYTEST_XDIST_WORKER_COUNT', '1')}): the walk "
            "found nothing because it could not read the process table. This "
            "is the walk's failure, not the child's — say nothing about what "
            "the child left running."
        ) from expired
    children = {}
    for line in listing.splitlines():
        fields = line.split(None, width - 1)
        if len(fields) == width and all(field.isdigit() for field in fields[:-1]):
            when = int(fields[2]) if width == 4 else None
            children.setdefault(int(fields[1]), []).append(
                (int(fields[0]), when, fields[-1])
            )
    found, seen, todo = [], {pid}, [(pid, created)]
    while todo:
        parent, parent_created = todo.pop()
        for child, child_created, name in children.get(parent, []):
            if child in seen:
                continue
            if None not in (parent_created, child_created) and (
                child_created < parent_created
            ):
                continue
            seen.add(child)
            found.append((child, name))
            todo.append((child, child_created))
    return found


def _state_at_bound(process):
    """What was below ``process`` when the bound expired. ``(text, pids)``.

    Never raises: the walk completes the report, it does not decide anything.
    Whatever stops it — ``ProcessListingFailed``, or a kind nobody listed — the
    caller still reads "not listed" under ``--- at the bound``, and still
    kills the process. Measured 2026-11-26 (#3702): with the walk raising
    outside ``(OSError, subprocess.SubprocessError)``, ``kill_tree`` was
    skipped and the child that had outlived its bound stayed running — on
    ``main`` with a ``ValueError``, and here with the named failure itself,
    which is a ``RuntimeError``. The bound's verdict is the child's; a failure
    of the walk that describes it is a line of that verdict.
    """
    try:
        below = descendants(process.pid, _created(process.pid))
    except Exception as exc:
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
    started; on posix an orphan is re-parented and escapes it. A process
    created before ``process`` is not counted, whatever parent id it names
    (#2662).

    When the first listing fails, the walk has seen nothing, and its message
    says so. When the second fails, it must not erase the first: measured
    2026-11-26 (#3702), the message said "the walk found nothing" while the
    first listing had seen a process, and the sighting was lost. Nothing is
    killed on the first listing alone — a pid is killed only where a listing
    reads it below the child again — so the failure carries the sighting
    instead.
    """
    created = _created(process.pid)
    below = descendants(process.pid, created)
    if not below:
        return []
    time.sleep(SETTLE)
    first = {pid for pid, _ in below}
    try:
        again = descendants(process.pid, created)
    except (OSError, subprocess.SubprocessError, ProcessListingFailed) as failed:
        seen = ", ".join(f"{pid} {name}" for pid, name in below)
        raise ProcessListingFailed(
            f"below the child that had exited, the first listing saw {seen}. "
            f"The second, {SETTLE} s later, could not read the process table: "
            "whether they were still there was not read, and nothing was "
            "killed — a process is killed only where a listing reads it below "
            "the child. The listing is the instrument that failed; the "
            "sighting stands."
        ) from failed
    left = [(pid, name) for pid, name in again if pid in first]
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

    The child is a session of its own, never a worker of the caller's
    xdist run: the caller's ``PYTEST_XDIST_*`` variables are not passed
    on, or ``tests/_jvm_session_flag.py`` would read the child as a worker
    and keep a decision its own argv should make (#2619). A value given
    in ``env`` still reaches the child.
    """
    inherited = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("PYTEST_XDIST_")
    }
    env = {**inherited, **(env or {})}
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
