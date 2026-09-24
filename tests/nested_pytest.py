# -*- coding: utf-8 -*-
"""Run a pytest session in a fresh interpreter, on probe files under ``tests/``.

The probe lives under ``tests/`` so that ``tests/conftest.py`` applies to it,
as to any test of the suite. Its directory starts with ``_``, which
``norecursedirs`` skips, so an ordinary run never collects it, and it is
deleted when the session ends.

The wait is bounded. ``subprocess.run(timeout=...)`` kills only the child and
then waits for its pipes without a bound, so a grandchild that holds them
keeps the caller waiting: the first CI run of the #2490 probes lost 895 s that
way on one case. Here a timeout kills the process tree, drains the pipes for
at most ``DRAIN`` seconds, and fails with what the child printed.

A probe session also loads this module as a plugin (``-p tests.nested_pytest``).
When the session is over it arms ``faulthandler``: if the process is still
alive ``EXIT_WATCHDOG`` seconds later, every thread's stack goes to stderr.
A session that hangs at exit therefore fails with the place where it waits,
not only with the fact that it waited (#2538). A process that exits cancels
the watchdog, so a normal run prints nothing.
"""

import faulthandler
import os
import shutil
import signal
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# A probe session takes about 20 s on ai-01 and 12 s in CI, JVM start included.
BOUND = 300
# After a kill, how long the pipes may take to close.
DRAIN = 30
# After the session, how long a probe may take to exit before it dumps its
# threads. Well below BOUND, so the dump is in what the kill drains.
EXIT_WATCHDOG = 60
_WATCHDOG_ENV = "NESTED_PYTEST_EXIT_WATCHDOG"


def kill_tree(process):
    """Kill ``process`` and its children, then wait at most ``DRAIN`` s for
    its pipes. ``(stdout, stderr)``, empty when they did not close.

    ``eprover_runner._kill_tree`` kills the same way but drains without a
    bound.
    """
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
    else:
        os.killpg(process.pid, signal.SIGKILL)
    process.kill()
    try:
        return process.communicate(timeout=DRAIN)
    except subprocess.TimeoutExpired:
        return "", ""


def both(out, err):
    """The tail of the child's stdout and stderr, for an assertion message.

    More of stderr, where an exit watchdog writes its thread dump.
    """
    return f"--- stdout\n{out[-3000:]}\n--- stderr\n{err[-8000:]}"


@pytest.hookimpl(trylast=True)
def pytest_unconfigure(config):
    """In a probe session: dump every thread if the process outlives the watchdog."""
    faulthandler.dump_traceback_later(
        float(os.environ.get(_WATCHDOG_ENV, EXIT_WATCHDOG)), file=sys.__stderr__
    )


def run_bounded(argv, bound=BOUND, failure="the process did not end", env=None):
    """Run ``argv`` from the repository root, with the root on ``PYTHONPATH``.

    A ``subprocess.CompletedProcess``. After ``bound`` seconds the process
    tree is killed and the test fails with ``failure`` and the child's output.
    ``env`` adds to the caller's environment.
    """
    env = {**os.environ, **(env or {})}
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    process = subprocess.Popen(
        argv,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        start_new_session=os.name != "nt",
    )
    try:
        out, err = process.communicate(timeout=bound)
    except subprocess.TimeoutExpired:
        out, err = kill_tree(process)
        pytest.fail(f"{failure} within {bound}s\n" + both(out, err))
    return subprocess.CompletedProcess(argv, process.returncode, out, err)


def run_probe(label, files, *argv, bound=BOUND, watchdog=EXIT_WATCHDOG):
    """Run pytest on ``files`` (``{name: source}``). ``(returncode, stdout, stderr)``.

    The first ``.py`` file whose name starts with ``probe`` is the one pytest
    is given; the others (a ``conftest.py``) sit beside it. ``watchdog``: the
    seconds after the session before the probe dumps its threads.
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
            env={_WATCHDOG_ENV: str(watchdog)},
        )
    finally:
        shutil.rmtree(probe_dir, ignore_errors=True)
    return done.returncode, done.stdout, done.stderr
