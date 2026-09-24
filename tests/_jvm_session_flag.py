"""#2402 — the ``--disable-jvm-session`` flag has ONE reader.

The defect (#2402, measured): the flag had two kinds of readers in
``tests/conftest.py`` that disagreed inside a pytest-xdist worker. Two
module-level sites read ``sys.argv`` (the early jpype mock at
``conftest.py`` l.101 and the integration-fixtures decision at l.762),
while the hook sites read ``config.getoption(...)`` (``pytest_sessionstart``,
the skip-storm exemption, the ``jvm_session`` guard). An xdist worker is
spawned without the original argv, so the argv sites saw nothing: ``jpype``
stayed real while the JVM was never started — any test reaching
``TweetyBridge()`` raised "JVM is not started" (7 false reds at ``-n 1``
and ``-n 4``, all green serially).

The repair: the meaning of the flag is decided ONCE, from the parsed option
(``pytest_configure``, which runs in the controller AND in each worker,
where the option is forwarded), and exported to an env var that workers
inherit. Every consumer reads that env var — or ``config.getoption`` where a
config is in scope. The ``sys.argv`` polls are gone except one explicit,
pre-parse propagator below, inert in workers by construction (a worker's
argv never carries the flag, measured in #2402).

Import-light (stdlib only) and tolerant of mock config objects, mirroring
``tests/_e2e_session_decision.py``, because ``tests/conftest.py`` loads this
module on every pytest bootstrap.
"""

from __future__ import annotations

import os
import sys

# The single decision channel. Exported by ``export_flag_from_config`` (from
# ``pytest_configure``) and, for the controller's pre-configure bootstrap
# window, by ``propagate_argv_to_env``.
JVM_SESSION_DISABLED_ENV = "PYTEST_JVM_SESSION_DISABLED"


def propagate_argv_to_env() -> None:
    """Controller bootstrap: conftest module-level code runs before any hook,
    so on the CONTROLLER the only pre-parse source of the flag is argv.
    Export that decision to the env var all readers consume.

    In an xdist worker this is inert: the worker's argv never carries the
    flag (the worker is spawned with its own arguments — the measured root
    of #2402), and the env var is already inherited from the controller."""
    if any(arg == "--disable-jvm-session" for arg in sys.argv):
        os.environ.setdefault(JVM_SESSION_DISABLED_ENV, "1")


def jvm_session_disabled() -> bool:
    """The one check for module-level code (no ``config`` in scope)."""
    return os.environ.get(JVM_SESSION_DISABLED_ENV) == "1"


def export_flag_from_config(config) -> None:
    """``pytest_configure`` body: decide the flag from the parsed option — the
    authoritative source, covering an addopts/ini-driven flag that argv never
    saw — and export it for workers and for later module-level reads.

    Tolerant of the mock ``config`` objects the conftest unit tests feed
    around: without a working ``getoption`` the export is skipped."""
    try:
        if config.getoption("--disable-jvm-session"):
            os.environ.setdefault(JVM_SESSION_DISABLED_ENV, "1")
    except (AttributeError, ValueError):
        # AttributeError: mock config without getoption.
        # ValueError: option unregistered (unexpected bootstrapping order).
        pass


def put_back(before):
    """#2530 — a test leaves the flag as it found it.

    ``before`` is the value the variable held when the test started (``None``
    when it was absent). The variable is set back to it, and the return is the
    message naming the change, or ``None`` when nothing moved.

    Why it matters: every pytest session spawned later inherits the variable.
    Such a session is a new controller, so its module-level reader mocks jpype
    while its own ``--disable-jvm-session`` option is off. Its JVM tests are
    then skipped on the ``JClass`` health check (measured in CI, #2530).
    """
    after = os.environ.get(JVM_SESSION_DISABLED_ENV)
    if after == before:
        return None
    if before is None:
        del os.environ[JVM_SESSION_DISABLED_ENV]
    else:
        os.environ[JVM_SESSION_DISABLED_ENV] = before
    return (
        f"#2530: this test left {JVM_SESSION_DISABLED_ENV}={after!r}; it was "
        f"{before!r} when the test started. Every pytest session spawned after "
        "it would mock jpype. The value is put back; undo the write in the test "
        "(monkeypatch.delenv(..., raising=False) records nothing when the "
        "variable is absent)."
    )
