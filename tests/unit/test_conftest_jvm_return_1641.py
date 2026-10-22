"""#1641 — conftest must propagate ``initialize_jvm``'s bool return into
``jvm_started``, instead of recording a DECIDED init failure as "started".

Pre-fix ``pytest_sessionstart`` (tests/conftest.py) discarded the return of
``initialize_jvm(...)`` and set ``cache["jvm_started"] = True`` unconditionally.
But ``initialize_jvm`` signals a decided failure (no Java / no Tweety JARs /
re-init after shutdown) by RETURNING ``False`` — 5 reachable return-False paths
(``jvm_setup.py`` l.773/781/791/...) — not by raising. So a decided failure was
recorded as "started": the ``jvm_session`` guard ``if not jvm_started`` never
fired, the skip fell through to the ``jpype.isJVMStarted()`` double-check, whose
message ("la JVM n'est pas réellement démarrée") reads as a transient native
crash — which is why the CI guard #1385 says "re-run" where the real cure is a
config correction. A decided failure rendered as an alea (#1019 family, same
shape as #1634: two opposite causes made indistinguishable downstream, always
toward the more reassuring reading).

The fix propagates the return: ``initialize_jvm`` → ``False`` ⇒
``jvm_started = False`` ⇒ the guard fires ⇒ the skip carries the honest
"l'initialisation de la JVM a échoué" message. The ``except`` (genuine raise)
and the ``jpype`` double-check (real post-start crash) are KEPT — three distinct
causes, three distinct messages (anti-pendule: do not collapse them).

Falsifiability — the degenerate substitution of DoD item 1 (force
``initialize_jvm`` to return ``False``) is pinned by
``test_initialize_jvm_false_sets_jvm_started_false``: on the pre-fix code the
return was discarded → ``jvm_started`` forced True regardless → the
``assert_any_call(key, False)`` FAILS. Verified empirically (revert
the propagation, this test goes red; restore, green). The companion
``test_initialize_jvm_true_sets_jvm_started_true`` pins the no-regression path
(passes both pre- and post-fix). A single decided-failure canary is honest here:
unlike #1630 there is ONE defect (the discarded return), not two independent
ones, so a single canary + empirical sub-verification matches the issue's DoD.

#3161 re-pin: the transport moved from ``config.cache`` (on-disk, shared by
every pytest process under the rootdir) to ``config.stash`` (in-process) —
the assertions observe the same write through the sessionstart hook's OWN
accessor pair (``set_jvm_started`` / the ``_JVM_STARTED`` stash key), so they
keep pinning the propagation, not a transport. The early-return guards the
mock must clear changed with it: ``is_e2e_session`` is no longer a cache
lookup but the argv classifier, which answers False for a bare MagicMock
(pinned in test_e2e_session_argv_decision_1820.py).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_CONFTEST_PATH = Path(__file__).resolve().parents[1] / "conftest.py"
_JVM_SETUP = "argumentation_analysis.core.jvm_setup.initialize_jvm"


@pytest.fixture(scope="module")
def _sessionstart():
    """Load the real tests/conftest.py; expose (sessionstart hook, stash key).

    Loaded under a distinct module name so the live conftest registered with
    pytest is untouched; we need the function object to call it with a mock
    session, and the ``_JVM_STARTED`` key its writer uses.
    """
    spec = importlib.util.spec_from_file_location(
        "_conftest_under_test_1641", _CONFTEST_PATH
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.pytest_sessionstart, mod._JVM_STARTED


def _mock_session() -> MagicMock:
    """A session past the three early-return guards (collectonly /
    --disable-jvm-session / argv-classified e2e all False) so execution
    reaches the initialize_jvm call."""
    session = MagicMock()
    # Guard 1: collectonly must be False.
    session.config.option.collectonly = False
    # Guard 2: --disable-jvm-session must be False.
    session.config.getoption.return_value = False
    # Guard 3: the argv classifier reads session.config.args — a bare
    # MagicMock is not a list, so it answers False (pinned in
    # test_e2e_session_argv_decision_1820.py::TestClassifierMockTolerance).
    return session


def _recorded_sets(session: MagicMock) -> set:
    """The (key, value) pairs the hook wrote into the session's stash."""
    return {
        tuple(call.args)
        for call in session.config.stash.__setitem__.call_args_list
        if call.args
    }


class TestJvmReturnPropagatedToStartedFlag:
    """DoD #1641 item 2: initialize_jvm's bool return ⇒ jvm_started matches it."""

    def test_initialize_jvm_false_sets_jvm_started_false(self, _sessionstart):
        """A DECIDED init failure (return False, no raise) must NOT be recorded
        as 'started'. Pre-fix this assertion fails: the return was discarded and
        jvm_started forced True."""
        sessionstart, jvm_key = _sessionstart
        session = _mock_session()
        with patch(_JVM_SETUP, return_value=False):
            sessionstart(session)

        assert (jvm_key, False) in _recorded_sets(session)
        # And it must NOT have been told the JVM started.
        assert (jvm_key, True) not in _recorded_sets(session)

    def test_initialize_jvm_true_sets_jvm_started_true(self, _sessionstart):
        """No-regression: a genuine success still records started=True."""
        sessionstart, jvm_key = _sessionstart
        session = _mock_session()
        with patch(_JVM_SETUP, return_value=True):
            sessionstart(session)

        assert (jvm_key, True) in _recorded_sets(session)

    def test_initialize_jvm_raise_still_records_false(self, _sessionstart):
        """The except branch (genuine raise) is preserved by the fix — a raised
        failure still records False (anti-pendule: the fix only adds propagation
        of the return, it does not weaken exception handling)."""
        sessionstart, jvm_key = _sessionstart
        session = _mock_session()
        with patch(_JVM_SETUP, side_effect=RuntimeError("native crash")):
            sessionstart(session)

        assert (jvm_key, False) in _recorded_sets(session)
