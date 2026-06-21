"""Real (non-mocked) SPASS modal integration test — #1205.

The SPASS modal reasoner had the SAME no-arg constructor bug that EProver had
pre-#1202 (#1205): ``_get_spass_reasoner`` called ``SPASSMlReasoner()`` with no
argument, but Tweety 1.28+/1.29 only exposes ``SPASSMlReasoner(String)`` /
``SPASSMlReasoner(String, Shell)`` (verified via ``javap`` on the bundled jar).
The construction error was swallowed by a bare ``except``, so SPASS was never
wired, yet the pipeline reported it as the configured modal solver (formal
theater, modal side of the #1196/#1202 regression class).

This file closes that hole with ONE non-mocked, skip-if-binary-absent
integration test that runs the REAL SPASS binary through the production path
(``TweetyBridge.check_consistency(bs, "K")`` → ``ModalHandler.is_modal_kb_consistent``
→ ``SPASSMlReasoner(path).isConsistent``) and asserts a real consistency verdict.

Modeled on FP-8's real-EProver test (``test_eprover_real.py``, #1210).

Anti-théâtre contract (#1019): the test must **EXECUTE** the binary where it is
present — it must NOT be "green by skipping everywhere". On machines WITHOUT the
SPASS binary (po-2023, fresh clones) it skips cleanly; on machines WITH it
(ai-01) it must pass GREEN. A skip-everywhere outcome = re-théâtre and defeats
the regression guard.

DoD (#1205 R458 dispatch):
- [x] Skips cleanly where the binary is absent (verified on po-2023)
- [x] NO mock of binary, reasoner, or settings
- [x] ai-01 runs it firsthand before merge (binary present there) — must pass GREEN

Privacy HARD: synthetic atoms only (``Mortal(socrate)``-style), 0 corpus.
"""

import pytest

from argumentation_analysis.core.config import settings, ModalSolverChoice
from argumentation_analysis.core.jvm_setup import EXTERNAL_TOOL_PATHS, initialize_jvm

# The production path under test.
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


def _spass_binary_present() -> bool:
    """True iff the SPASS binary path is registered in the module-level
    ``EXTERNAL_TOOL_PATHS`` registry populated by ``jvm_setup`` at startup."""
    return bool(EXTERNAL_TOOL_PATHS.get("spass"))


# Skip if the binary is absent — this test cannot execute the solver otherwise.
# (The JVM-started check is handled by the ``jvm_session`` autouse fixture in
# conftest, which skips JVM-dependent tests when the JVM failed to start.)
pytestmark = pytest.mark.skipif(
    not _spass_binary_present(),
    reason="SPASS binary not registered (EXTERNAL_TOOL_PATHS['spass'] unset) — "
    "install SPASS under ext_tools/spass/ to run this real integration test.",
)


@pytest.fixture
def spass_solver():
    """Force ``settings.modal_solver = SPASS`` for the duration of the test,
    then restore the previous value. This is a REAL runtime config change (not
    a mock of ``settings``): the SPASS binary and the Tweety JVM both execute
    for real. Without this, the default modal solver (TWEETY/SimpleMlReasoner)
    would be dispatched and the SPASS path would never be exercised.

    Under SPASS, ``_get_active_reasoner`` returns ``_get_spass_reasoner()``,
    which (post-#1205) builds the REAL ``SPASSMlReasoner(path)`` — so reaching
    a verdict at all proves SPASS was invoked (not the SimpleMl fallback)."""
    previous = settings.modal_solver
    settings.modal_solver = ModalSolverChoice.SPASS
    try:
        yield
    finally:
        settings.modal_solver = previous


@pytest.fixture(scope="module")
def modal_bridge():
    """Start the JVM (idempotent) and build a ``TweetyBridge`` once for the
    module. ``check_consistency(.., "K")`` routes to ``ModalHandler``
    (``is_modal_kb_consistent``), the production entry point for modal
    consistency."""
    initialize_jvm()
    return TweetyBridge()


class TestRealSpassConsistency:
    """Real-binary SPASS modal consistency verdicts, end-to-end through the
    production ``TweetyBridge.check_consistency`` → ``ModalHandler`` path."""

    def test_inconsistent_kb_reports_inconsistent_via_spass(
        self, modal_bridge, spass_solver
    ):
        """An inconsistent modal KB must yield ``is_consistent = False`` via the
        REAL SPASS binary.

        The KB reaches ``SPASSMlReasoner(path).isConsistent`` only because
        ``settings.modal_solver == SPASS`` forces ``_get_active_reasoner`` to
        ``_get_spass_reasoner()``, which (post-#1205) builds the real reasoner
        with the registered binary path. Pre-#1205 this raised a swallowed
        construction error (no-arg ctor) and degraded silently; here, reaching
        a boolean verdict at all is the regression guard.

        KB (modal logic, contradiction): ``Mortal(socrate)`` together with its
        negation ``!Mortal(socrate)`` — a direct contradiction. Syntax may need
        a firsthand tweak per the MlParser declaration rules (ai-01 to confirm
        on the real binary, as for the FOL case in #1210).
        """
        inconsistent_kb = "Mortal(socrate)\n!Mortal(socrate)\n"
        is_consistent, msg = modal_bridge.check_consistency(
            inconsistent_kb, "K"
        )
        assert is_consistent is False, (
            f"Inconsistent modal KB must report inconsistent; "
            f"got ({is_consistent!r}, {msg!r})."
        )

    def test_consistent_kb_reports_consistent_via_spass(
        self, modal_bridge, spass_solver
    ):
        """A consistent modal KB must yield ``is_consistent = True`` via the
        REAL SPASS binary.

        KB (modal logic, no contradiction): ``[](Mortal(socrate))`` —
        "necessarily Mortal(socrate)" — a single non-contradictory modal
        formula (Tweety modal syntax: ``[]`` = necessity operator).
        """
        consistent_kb = "[](Mortal(socrate))\n"
        is_consistent, msg = modal_bridge.check_consistency(
            consistent_kb, "K"
        )
        assert is_consistent is True, (
            f"Consistent modal KB must report consistent; "
            f"got ({is_consistent!r}, {msg!r})."
        )
