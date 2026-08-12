"""Tests for Dung framework construction in conversational mode (#564, rev #1668).

Validates that:
- _build_dung_framework_from_state builds a Dung AF from arguments + fallacy targets
- Fallacy-targeted arguments become attack relations
- Grounded extension is computed via pure-Python DungFramework
- Result is persisted to state.dung_frameworks

#1668 — the counter-argument strategy branch (the ``("UNDERCUT","REBUT","REBUTTAL")``
gate) was removed. The producer never emitted that vocabulary (0/66 pipeline +
0/16 conversational matches on real runs), so the branch populated zero attacks.
``test_counter_argument_no_longer_populates_framework`` is the armed proof of the
removal (a gated strategy that used to populate the framework no longer does);
the fallacy-driven tests prove behavioural neutrality (the framework is still
populated by the fallacy branch, unchanged).
"""

import pytest

from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)


class TestBuildDungFramework:
    """Tests for _build_dung_framework_from_state helper."""

    def _make_state_with_args(self, args, counter_args=None, fallacies=None):
        """Helper: create state with arguments, optional counter-args and fallacies."""
        state = UnifiedAnalysisState("Test text for Dung framework")
        for desc in args:
            state.add_argument(desc)

        if counter_args:
            for ca in counter_args:
                state.counter_arguments.append(ca)

        if fallacies:
            for f_type, f_just, f_target in fallacies:
                state.add_fallacy(f_type, f_just, target_arg_id=f_target)

        return state

    def test_returns_none_for_insufficient_args(self):
        """Need at least 2 arguments for a Dung AF."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        state.add_argument("Only one argument")
        result = _build_dung_framework_from_state(state)
        assert result is None

    def test_returns_none_without_attacks(self):
        """2 arguments but no counter-args/fallacies → no attacks → None."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = self._make_state_with_args(["Arg A text", "Arg B text"])
        result = _build_dung_framework_from_state(state)
        assert result is None

    def test_counter_argument_no_longer_populates_framework(self):
        """#1668 armed proof: a gated counter-argument strategy does NOT populate
        the framework after the CA branch was removed.

        Before #1668, a counter-argument whose ``strategy`` was in
        ``("UNDERCUT","REBUT","REBUTTAL")`` created an attack relation here.
        The branch was removed because the producer never emitted that
        vocabulary (0/66 + 0/16 real-run matches). This test pins the removal:
        with no fallacies, a gated-strategy counter-argument yields no attack,
        so the builder returns ``None``. If this assertion ever flips back to
        "populated", someone reintroduced a live CA branch — investigate.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        args = ["Socrates is mortal", "Immortality is possible"]
        arg_ids = []
        state = UnifiedAnalysisState("Test")
        for desc in args:
            arg_ids.append(state.add_argument(desc))

        # A counter-argument whose strategy is in the (removed) gate vocabulary.
        # No fallacy is added, so the fallacy branch cannot mask the removal.
        state.counter_arguments.append(
            {
                "strategy": "UNDERCUT",
                "original_argument": args[1],
                "counter_argument": args[0],
            }
        )

        result = _build_dung_framework_from_state(state)
        # No attacks (CA branch gone, no fallacies) → builder short-circuits.
        assert result is None
        assert len(state.dung_frameworks) == 0

    def test_builds_from_fallacy_target(self):
        """Fallacy targeting an argument creates a pseudo-attacker node."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        arg_id = state.add_argument("Claim about authority")
        state.add_argument("Another unrelated claim")

        state.add_fallacy("appeal_to_authority", "Uses authority", target_arg_id=arg_id)

        result = _build_dung_framework_from_state(state)
        assert result is not None
        assert result["attacks"] >= 1

    def test_computes_grounded_extension(self):
        """Grounded extension is computed for a valid Dung AF.

        #1668: previously this test drove the attack via a counter-argument
        (``REBUT`` strategy); it now drives it via a fallacy target, which is
        the only attack source after the CA branch removal. The grounded
        extension semantics under test are unchanged.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        arg_a = state.add_argument("Strong argument A")
        arg_b = state.add_argument("Weak argument B")

        # A fallacy targeting arg_b makes a pseudo-attacker attack arg_b.
        state.add_fallacy("ad_hominem", "Attacks the speaker", target_arg_id=arg_b)

        result = _build_dung_framework_from_state(state)
        assert result is not None
        # Grounded extension should include the unattacked argument (arg_a).
        grounded = result.get("grounded_extension", [])
        assert arg_a in grounded

    def test_handles_empty_state(self):
        """Empty state → None."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        result = _build_dung_framework_from_state(state)
        assert result is None

    def test_persists_to_state_dung_frameworks(self):
        """Result is written to state.dung_frameworks dict."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        arg_a = state.add_argument("First argument about X")
        arg_b = state.add_argument("Second argument about Y")

        state.add_fallacy("ad_hominem", "Personal attack", target_arg_id=arg_b)

        result = _build_dung_framework_from_state(state)
        assert result is not None

        # Check state has the framework
        assert len(state.dung_frameworks) >= 1
        df_data = list(state.dung_frameworks.values())[0]
        assert df_data["name"] == "conversational_dung"
        assert len(df_data["arguments"]) >= 2
        assert len(df_data["attacks"]) >= 1

    def test_multiple_attacks_from_distinct_fallacy_targets(self):
        """Fallacies targeting distinct arguments each contribute one attack.

        #1668: previously asserted ``attacks >= 2`` from one counter-argument
        (``UNDERCUT``) + one fallacy. With the CA branch removed only the
        fallacy attack remains per source; this test now uses two distinct
        fallacy targets to preserve multi-attack coverage on the live branch.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        state.add_argument("Argument A about policy")
        arg_b = state.add_argument("Argument B about evidence")
        arg_c = state.add_argument("Argument C about logic")

        # The CA below would have contributed an attack pre-#1668; it is now
        # inert. It is kept here to prove the removal is neutral even when a
        # gated counter-argument is present alongside live fallacy sources.
        state.counter_arguments.append(
            {
                "strategy": "UNDERCUT",
                "original_argument": "Argument B about evidence",
                "counter_argument": "Argument A about policy",
            }
        )

        # Two distinct fallacy targets → two attacks via the live branch.
        state.add_fallacy("straw_man", "Misrepresents", target_arg_id=arg_b)
        state.add_fallacy("ad_hominem", "Attacks speaker", target_arg_id=arg_c)

        result = _build_dung_framework_from_state(state)
        assert result is not None
        assert result["attacks"] >= 2

    def test_no_duplicate_attacks(self):
        """Two fallacies targeting the same argument don't duplicate the node.

        #1668: the counter-argument previously present here (``REBUT``) is now
        inert; the test still passes because the fallacy branch alone populates
        at least one attack.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        state.add_argument("Argument A")
        arg_b = state.add_argument("Argument B")

        # Inert post-#1668; kept to show neutrality in the presence of a
        # gated counter-argument.
        state.counter_arguments.append(
            {
                "strategy": "REBUT",
                "original_argument": "Argument B",
                "counter_argument": "Argument A",
            }
        )
        state.add_fallacy("hasty_generalization", "Too broad", target_arg_id=arg_b)

        result = _build_dung_framework_from_state(state)
        assert result is not None
        assert result["attacks"] >= 1

    def test_fallacy_population_unaffected_by_gate_removal(self):
        """#1668 neutrality proof: a realistic state (fallacies + gated CAs) is
        still populated, entirely by the fallacy branch.

        This is the behavioural-neutrality leg of the removal: the gate never
        matched on real runs, so the framework's population came only from
        fallacies. With gated counter-arguments present (as on a real run) the
        framework still builds and carries the fallacy-driven attacks. If the
        attack count here ever drops to 0, the fallacy branch was damaged —
        that would be a real regression, unlike the dead CA branch removal.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        arg_a = state.add_argument("Argument A about policy")
        arg_b = state.add_argument("Argument B about evidence")

        # Gated-strategy counter-arguments, as a real producer emits (free-text
        # strategies that don't match the gate). Inert post-#1668.
        state.counter_arguments.append(
            {
                "strategy": "reductio ad absurdum",
                "original_argument": "Argument B about evidence",
                "counter_argument": "Argument A about policy",
            }
        )

        # Fallacies targeting each argument — the live population source.
        state.add_fallacy("ad_hominem", "Attacks the speaker", target_arg_id=arg_a)
        state.add_fallacy("straw_man", "Misrepresents", target_arg_id=arg_b)

        result = _build_dung_framework_from_state(state)
        assert result is not None
        # Two distinct fallacy targets → at least two attacks, none from CAs.
        assert result["attacks"] >= 2
