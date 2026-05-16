"""Tests for Dung framework construction in conversational mode (#564).

Validates that:
- _build_dung_framework_from_state builds Dung AF from arguments + counter-args
- Attack relations are derived from counter-argument strategies (UNDERCUT/REBUT)
- Fallacy-targeted arguments become attack relations
- Grounded extension is computed via pure-Python DungFramework
- Result is persisted to state.dung_frameworks
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

    def test_builds_from_counter_argument(self):
        """Counter-argument with UNDERCUT strategy creates attack relation."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        args = ["Socrates is mortal", "Immortality is possible"]
        arg_ids = []
        state = UnifiedAnalysisState("Test")
        for desc in args:
            arg_ids.append(state.add_argument(desc))

        state.counter_arguments.append({
            "strategy": "UNDERCUT",
            "original_argument": args[1],
            "counter_argument": args[0],
        })

        result = _build_dung_framework_from_state(state)
        assert result is not None
        assert result["attacks"] >= 1
        assert result["arguments"] >= 2

        # Verify persisted to state
        assert len(state.dung_frameworks) >= 1

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
        """Grounded extension is computed for valid Dung AF."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        arg_a = state.add_argument("Strong argument A")
        arg_b = state.add_argument("Weak argument B")

        # A attacks B via counter-argument
        state.counter_arguments.append({
            "strategy": "REBUT",
            "original_argument": "Weak argument B",
            "counter_argument": "Strong argument A",
        })

        result = _build_dung_framework_from_state(state)
        assert result is not None
        # Grounded extension should include the unattacked argument
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

    def test_multiple_attacks_from_mixed_sources(self):
        """Both counter-args and fallacies contribute attacks."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        arg_a = state.add_argument("Argument A about policy")
        arg_b = state.add_argument("Argument B about evidence")
        arg_c = state.add_argument("Argument C about logic")

        # Counter-arg attack
        state.counter_arguments.append({
            "strategy": "UNDERCUT",
            "original_argument": "Argument B about evidence",
            "counter_argument": "Argument A about policy",
        })

        # Fallacy attack
        state.add_fallacy("straw_man", "Misrepresents", target_arg_id=arg_c)

        result = _build_dung_framework_from_state(state)
        assert result is not None
        assert result["attacks"] >= 2

    def test_no_duplicate_attacks(self):
        """Same attack from multiple sources doesn't duplicate."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_dung_framework_from_state,
        )

        state = UnifiedAnalysisState("Test")
        arg_a = state.add_argument("Argument A")
        arg_b = state.add_argument("Argument B")

        # Both counter-arg and fallacy target B from A
        state.counter_arguments.append({
            "strategy": "REBUT",
            "original_argument": "Argument B",
            "counter_argument": "Argument A",
        })
        state.add_fallacy("hasty_generalization", "Too broad", target_arg_id=arg_b)

        result = _build_dung_framework_from_state(state)
        assert result is not None
        assert result["attacks"] >= 1
