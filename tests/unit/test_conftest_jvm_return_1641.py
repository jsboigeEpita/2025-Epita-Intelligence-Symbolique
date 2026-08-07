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
return was discarded → ``cache.set("jvm_started", True)`` regardless → the
``assert_any_call("jvm_started", False)`` FAILS. Verified empirically (revert
the propagation, this test goes red; restore, green). The companion
``test_initialize_jvm_true_sets_jvm_started_true`` pins the no-regression path
(passes both pre- and post-fix). A single decided-failure canary is honest here:
unlike #1630 there is ONE defect (the discarded return), not two independent
ones, so a single canary + empirical sub-verification matches the issue's DoD.
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
    """Load the real tests/conftest.py and expose its pytest_sessionstart hook.

    Loaded under a distinct module name so the live conftest registered with
    pytest is untouched; we only need the function object to call it with a mock
    session.
    """
    spec = importlib.util.spec_from_file_location(
        "_conftest_under_test_1641", _CONFTEST_PATH
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.pytest_sessionstart


def _mock_session() -> MagicMock:
    """A session past the three early-return guards (collectonly / --disable-jvm-
    session / is_e2e_session all False) so execution reaches the initialize_jvm
    call."""
    session = MagicMock()
    # l.404 guard: collectonly must be False.
    session.config.option.collectonly = False
    # l.411 guard: --disable-jvm-session must be False.
    session.config.getoption.return_value = False
    # l.417: is_e2e_session cache lookup must return False.
    session.config.cache.get.return_value = False
    return session


class TestJvmReturnPropagatedToStartedFlag:
    """DoD #1641 item 2: initialize_jvm's bool return ⇒ jvm_started matches it."""

    def test_initialize_jvm_false_sets_jvm_started_false(self, _sessionstart):
        """A DECIDED init failure (return False, no raise) must NOT be recorded
        as 'started'. Pre-fix this assertion fails: the return was discarded and
        jvm_started forced True."""
        session = _mock_session()
        with patch(_JVM_SETUP, return_value=False):
            _sessionstart(session)

        session.config.cache.set.assert_any_call("jvm_started", False)
        # And it must NOT have been told the JVM started.
        set_calls = {
            tuple(c.args) for c in session.config.cache.set.call_args_list if c.args
        }
        assert ("jvm_started", True) not in set_calls

    def test_initialize_jvm_true_sets_jvm_started_true(self, _sessionstart):
        """No-regression: a genuine success still records started=True."""
        session = _mock_session()
        with patch(_JVM_SETUP, return_value=True):
            _sessionstart(session)

        session.config.cache.set.assert_any_call("jvm_started", True)

    def test_initialize_jvm_raise_still_records_false(self, _sessionstart):
        """The except branch (genuine raise) is preserved by the fix — a raised
        failure still records False (anti-pendule: the fix only adds propagation
        of the return, it does not weaken exception handling)."""
        session = _mock_session()
        with patch(_JVM_SETUP, side_effect=RuntimeError("native crash")):
            _sessionstart(session)

        session.config.cache.set.assert_any_call("jvm_started", False)
