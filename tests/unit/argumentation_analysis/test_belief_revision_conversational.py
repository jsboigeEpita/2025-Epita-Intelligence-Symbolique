"""Tests for AGM belief revision bridge — _run_belief_revision_from_state (#566).

Validates that:
- Fallacies targeting arguments with JTMS beliefs trigger revision
- Original beliefs are contracted (removed from revised list)
- Result persisted to state.belief_revision_results
- No fallacies → no revision
- No beliefs → no revision
- Already populated → skip (idempotent)
"""

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState


class TestBeliefRevision:

    def _make_state_with_belief(self, arg_desc):
        """Helper: state with argument and matching JTMS belief."""
        state = UnifiedAnalysisState("Test text for belief revision")
        arg_id = state.add_argument(arg_desc)
        state.add_jtms_belief(name=arg_id, valid=True, justifications=[])
        return state, arg_id

    def test_returns_none_without_fallacies(self):
        """No fallacies → no revision needed."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_belief_revision_from_state,
        )

        state, _ = self._make_state_with_belief("Test argument")
        result = _run_belief_revision_from_state(state)
        assert result is None

    def test_returns_none_without_beliefs(self):
        """No JTMS beliefs → nothing to revise."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_belief_revision_from_state,
        )

        state = UnifiedAnalysisState("Test")
        arg_id = state.add_argument("Target argument")
        state.add_fallacy("ad_hominem", "Attack", target_arg_id=arg_id)
        # No beliefs added
        result = _run_belief_revision_from_state(state)
        assert result is None

    def test_contracts_belief_on_fallacy(self):
        """Fallacy targeting belief → belief contracted."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_belief_revision_from_state,
        )

        state, arg_id = self._make_state_with_belief("Target argument")
        state.add_fallacy("ad_hominem", "Attack", target_arg_id=arg_id)

        result = _run_belief_revision_from_state(state)
        assert result is not None
        assert result["method"] == "fallacy_contraction"
        assert result["original_count"] >= 1
        assert result["revised_count"] < result["original_count"]
        assert len(result["removed"]) >= 1

    def test_persists_to_state_belief_revision_results(self):
        """Result appears in state.belief_revision_results."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_belief_revision_from_state,
        )

        state, arg_id = self._make_state_with_belief("Target argument")
        state.add_fallacy("ad_hominem", "Attack", target_arg_id=arg_id)
        _run_belief_revision_from_state(state)

        assert len(state.belief_revision_results) >= 1
        entry = state.belief_revision_results[0]
        assert entry["method"] == "fallacy_contraction"
        assert len(entry["original"]) >= 1
        assert len(entry["revised"]) < len(entry["original"])

    def test_skip_if_already_populated(self):
        """Idempotent: skips if belief_revision_results already has entries."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_belief_revision_from_state,
        )

        state, arg_id = self._make_state_with_belief("Target argument")
        state.add_fallacy("ad_hominem", "Attack", target_arg_id=arg_id)
        # Pre-populate
        state.add_belief_revision_result("test", ["a"], ["b"])
        result = _run_belief_revision_from_state(state)
        assert result is None

    def test_multiple_fallacies_contract_multiple_beliefs(self):
        """Multiple fallacies target multiple beliefs."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_belief_revision_from_state,
        )

        state = UnifiedAnalysisState("Test")
        arg_a = state.add_argument("Argument A about policy")
        arg_b = state.add_argument("Argument B about evidence")
        arg_c = state.add_argument("Argument C about logic")

        for aid in [arg_a, arg_b, arg_c]:
            state.add_jtms_belief(name=aid, valid=True, justifications=[])

        # Target A and C with fallacies
        state.add_fallacy("ad_hominem", "Attack A", target_arg_id=arg_a)
        state.add_fallacy("straw_man", "Misrepresents C", target_arg_id=arg_c)

        result = _run_belief_revision_from_state(state)
        assert result is not None
        assert result["original_count"] == 3
        assert result["revised_count"] == 1  # Only B survives
        assert len(result["removed"]) == 2

    def test_unrelated_fallacy_no_revision(self):
        """Fallacy targeting non-existent argument → no revision."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_belief_revision_from_state,
        )

        state, _ = self._make_state_with_belief("Real argument")
        state.add_fallacy("ad_hominem", "Attack", target_arg_id="nonexistent_arg_id")
        result = _run_belief_revision_from_state(state)
        assert result is None

    def test_returns_none_for_empty_state(self):
        """Empty state → None."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_belief_revision_from_state,
        )

        state = UnifiedAnalysisState("Test")
        result = _run_belief_revision_from_state(state)
        assert result is None

    def test_revision_record_has_correct_fields(self):
        """Each revision entry has expected dict keys."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_belief_revision_from_state,
        )

        state, arg_id = self._make_state_with_belief("Target argument")
        state.add_fallacy("ad_hominem", "Attack", target_arg_id=arg_id)
        _run_belief_revision_from_state(state)

        entry = state.belief_revision_results[0]
        assert "id" in entry
        assert "method" in entry
        assert "original" in entry
        assert "revised" in entry
        assert isinstance(entry["original"], list)
        assert isinstance(entry["revised"], list)
