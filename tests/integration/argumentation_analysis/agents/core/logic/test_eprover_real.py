"""Real (non-mocked) EProver integration test — #1204.

The EProver 3-layer regression (#1204) stayed hidden across FP-3 because the
existing ``test_eprover_spass_integration`` is **100% mocked**: it patches
``_get_eprover_path`` / ``jpype`` / ``settings`` and asserts Python *dispatch*,
never running the binary. This file closes that hole with ONE non-mocked,
skip-if-binary-absent integration test that runs the REAL EProver binary
through the production path (``TweetyBridge.check_consistency(bs, "first_order")``
→ ``FOLHandler.check_consistency`` → ``EFOLReasoner(path)``) and asserts a real
consistency verdict.

Modeled on FP-8's real-Prover9 test (``test_real_binary_inconsistent_kb_emits_theorem_proved``
in ``tests/unit/argumentation_analysis/core/test_prover9_runner.py``).

Anti-théâtre contract (#1019): the test must **EXECUTE** the binary where it is
present — it must NOT be "green by skipping everywhere". On machines WITHOUT the
EProver binary (po-2023, fresh clones) it skips cleanly; on machines WITH it
(ai-01, po-2025) it must pass GREEN. A skip-everywhere outcome = re-théâtre and
defeats the regression guard.

DoD (#1204 R455 dispatch):
- [x] Skips cleanly where the binary is absent (verified on po-2023)
- [x] NO mock of binary, reasoner, or settings
- [x] ai-01 runs it firsthand before merge (binary present there) — must pass GREEN

Privacy HARD: synthetic atoms only (``Mortal(socrate)``), 0 corpus.
"""

import pytest

from argumentation_analysis.core.config import settings, SolverChoice
from argumentation_analysis.core.jvm_setup import EXTERNAL_TOOL_PATHS, initialize_jvm

# The production path under test.
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


def _eprover_binary_present() -> bool:
    """True iff the EProver binary path is registered in the module-level
    ``EXTERNAL_TOOL_PATHS`` registry populated by ``jvm_setup`` at startup."""
    return bool(EXTERNAL_TOOL_PATHS.get("eprover"))


# Skip if the binary is absent — this test cannot execute the solver otherwise.
# (The JVM-started check is handled by the ``jvm_session`` autouse fixture in
# conftest, which skips JVM-dependent tests when the JVM failed to start.)
pytestmark = pytest.mark.skipif(
    not _eprover_binary_present(),
    reason="EProver binary not registered (EXTERNAL_TOOL_PATHS['eprover'] unset) — "
    "install EProver under ext_tools/EProver/ to run this real integration test.",
)


@pytest.fixture
def eprover_solver():
    """Force ``settings.solver = EPROVER`` for the duration of the test, then
    restore the previous value. This is a REAL runtime config change (not a
    mock of ``settings``): the EProver binary and the Tweety JVM both execute
    for real. Without this, the default solver (TWEETY/PROVER9) would be
    dispatched and the EProver path would never be exercised."""
    previous = settings.solver
    settings.solver = SolverChoice.EPROVER
    try:
        yield
    finally:
        settings.solver = previous


@pytest.fixture(scope="module")
def fol_bridge():
    """Start the JVM (idempotent) and build a ``TweetyBridge`` once for the
    module. ``check_consistency(.., "first_order")`` is the production entry
    point (path B in the #1202 cross-verification table)."""
    initialize_jvm()
    return TweetyBridge()


class TestRealEProverConsistency:
    """Real-binary EProver consistency verdicts, end-to-end through the
    production ``TweetyBridge.check_consistency`` path."""

    def test_inconsistent_kb_reports_inconsistent_via_eprover(
        self, fol_bridge, eprover_solver
    ):
        """An inconsistent FOL KB (``P(a)`` and ``¬P(a)``) must yield
        ``is_consistent = False`` via the REAL EProver binary, and the message
        must identify the EProver solver (so the verdict is traceable to a real
        decision, not a degraded fallback).

        KB (Tweety native FOL syntax — sort + predicate declarations are
        mandatory): a one-element sort ``human = {socrate}``, the predicate type
        ``type(Mortal(human))``, then ``Mortal(socrate)`` together with its
        negation ``!Mortal(socrate)`` — a direct contradiction.
        """
        inconsistent_kb = (
            "human = {socrate}\n"
            "type(Mortal(human))\n"
            "\n"
            "Mortal(socrate)\n"
            "!Mortal(socrate)\n"
        )
        is_consistent, msg = fol_bridge.check_consistency(
            inconsistent_kb, "first_order"
        )
        assert (
            is_consistent is False
        ), f"Inconsistent KB must report inconsistent; got ({is_consistent!r}, {msg!r})."
        assert (
            "EProver" in msg
        ), f"Verdict must be traceable to the EProver solver; got msg={msg!r}."

    def test_consistent_kb_reports_consistent_via_eprover(
        self, fol_bridge, eprover_solver
    ):
        """A consistent FOL KB must yield ``is_consistent = True`` via the REAL
        EProver binary.

        KB (Tweety native FOL syntax — sort + predicate declarations are
        mandatory): ``∀x(Human(x) → Mortal(x))`` + ``Human(socrate)`` +
        ``Mortal(socrate)`` — the classic syllogism, no contradiction.
        """
        consistent_kb = (
            "human = {socrate}\n"
            "type(Human(human))\n"
            "type(Mortal(human))\n"
            "\n"
            "forall X: (Human(X) => Mortal(X))\n"
            "Human(socrate)\n"
            "Mortal(socrate)\n"
        )
        is_consistent, msg = fol_bridge.check_consistency(consistent_kb, "first_order")
        assert (
            is_consistent is True
        ), f"Consistent KB must report consistent; got ({is_consistent!r}, {msg!r})."
        assert (
            "EProver" in msg
        ), f"Verdict must be traceable to the EProver solver; got msg={msg!r}."
