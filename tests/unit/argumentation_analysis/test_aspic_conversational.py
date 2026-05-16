"""Tests for ASPIC+ framework bridge — _build_aspic_from_state (#565).

Validates that:
- Arguments are classified as strict (factual) or defeasible (hedged)
- Fallacy-targeted arguments become defeasible
- Surviving vs defeated arguments computed from fallacy attacks
- Result persisted to state.aspic_results via add_aspic_result
- Empty state returns None
- Statistics reflect correct rule counts
"""

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState


class TestASPICFramework:

    def _make_state_with_args(self, descriptions):
        """Helper: create state with arguments."""
        state = UnifiedAnalysisState("Test text for ASPIC analysis")
        arg_ids = []
        for desc in descriptions:
            arg_ids.append(state.add_argument(desc))
        return state, arg_ids

    def test_returns_none_for_empty_state(self):
        """No arguments → no ASPIC framework."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state = UnifiedAnalysisState("Test")
        result = _build_aspic_from_state(state)
        assert result is None

    def test_classifies_factual_as_strict(self):
        """'is/are/always' → strict rule."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, _ = self._make_state_with_args([
            "The sky is blue and always has been",
            "Water is essential for life",
        ])
        result = _build_aspic_from_state(state)
        assert result is not None
        assert result["strict_rules"] >= 1

    def test_classifies_hedged_as_defeasible(self):
        """'usually/might/probably' → defeasible rule."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, _ = self._make_state_with_args([
            "This approach usually works well",
            "It might be possible to improve",
        ])
        result = _build_aspic_from_state(state)
        assert result is not None
        assert result["defeasible_rules"] >= 1

    def test_fallacy_makes_arg_defeasible(self):
        """Argument targeted by fallacy becomes defeasible."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, arg_ids = self._make_state_with_args([
            "The authority claims this is true",
            "Another unrelated claim",
        ])
        # Add fallacy targeting first arg
        state.add_fallacy("appeal_to_authority", "Uses authority", target_arg_id=arg_ids[0])

        result = _build_aspic_from_state(state)
        assert result is not None
        assert result["defeated"] >= 1

    def test_surviving_without_fallacy(self):
        """Arguments not targeted by fallacies survive."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, _ = self._make_state_with_args([
            "The sky is blue",
            "Water freezes at zero",
        ])
        result = _build_aspic_from_state(state)
        assert result is not None
        assert result["surviving"] >= 2
        assert result["defeated"] == 0

    def test_persists_to_state_aspic_results(self):
        """Result appears in state.aspic_results."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, _ = self._make_state_with_args([
            "This is a factual claim",
        ])
        _build_aspic_from_state(state)

        assert len(state.aspic_results) >= 1
        entry = state.aspic_results[0]
        assert entry["reasoner_type"] == "python_fallback"
        assert "extensions" in entry
        assert "statistics" in entry

    def test_statistics_reflect_rule_counts(self):
        """Statistics include correct rule counts."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, _ = self._make_state_with_args([
            "The data is clear and proven",
            "This might be a valid approach",
        ])
        _build_aspic_from_state(state)

        entry = state.aspic_results[0]
        stats = entry["statistics"]
        assert stats["total_arguments"] == 2
        assert stats["strict_rules"] + stats["defeasible_rules"] == 2

    def test_french_strict_cues(self):
        """French factual cues (est, sont) produce strict rules."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, _ = self._make_state_with_args([
            "Le ciel est bleu",
            "Tous les hommes sont mortels",
        ])
        result = _build_aspic_from_state(state)
        assert result is not None
        assert result["strict_rules"] >= 1

    def test_default_defeasible_when_no_cues(self):
        """Arguments with no strict or defeasible cues default to defeasible."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, _ = self._make_state_with_args([
            "Something about the topic",
        ])
        result = _build_aspic_from_state(state)
        assert result is not None
        assert result["defeasible_rules"] >= 1

    def test_mixed_strict_and_defeasible(self):
        """Mix of factual and hedged arguments produces both rule types."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, _ = self._make_state_with_args([
            "Gravity always pulls objects down",
            "This probably won't matter",
            "The experiment was proven correct",
            "We might consider alternatives",
        ])
        result = _build_aspic_from_state(state)
        assert result is not None
        assert result["strict_rules"] >= 1
        assert result["defeasible_rules"] >= 1

    def test_extensions_contain_surviving_args(self):
        """Extensions list contains surviving argument texts."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _build_aspic_from_state,
        )

        state, arg_ids = self._make_state_with_args([
            "Strong factual argument A",
            "Weak argument B that is targeted",
            "Another strong argument C",
        ])
        # Target B with fallacy
        state.add_fallacy("ad_hominem", "Personal attack", target_arg_id=arg_ids[1])

        _build_aspic_from_state(state)
        entry = state.aspic_results[0]
        extensions = entry["extensions"]
        assert len(extensions) >= 1
        # A and C should survive, B should not
        surviving_text = " ".join(extensions[0])
        assert "Strong factual" in surviving_text
        assert "Another strong" in surviving_text
