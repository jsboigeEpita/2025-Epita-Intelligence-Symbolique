"""Tests for Track FF (#642): Belief Revision Trace reads AGM source.

The DeepSynthesis report Section 6 must surface contractions from BOTH:
  - jtms_retraction_chain (JTMS cascade retractions)
  - belief_revision_results (AGM belief revision contractions)
"""
import pytest

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    BeliefRetraction,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _make_state():
    return UnifiedAnalysisState(initial_text="test text for BR trace")


class TestBeliefRetractionAGMSource:
    """_build_belief_retractions must read belief_revision_results."""

    def test_agm_contraction_surfaces_in_retractions(self):
        state = _make_state()
        state.add_belief_revision_result(
            method="fallacy_contraction",
            original=["b1", "b2", "b3", "b4"],
            revised=[],
        )
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        assert len(retractions) == 4
        names = {r.belief_name for r in retractions}
        assert names == {"b1", "b2", "b3", "b4"}

    def test_agm_partial_contraction(self):
        state = _make_state()
        state.add_belief_revision_result(
            method="consistency_check",
            original=["b1", "b2", "b3"],
            revised=["b2"],
        )
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        contracted = {r.belief_name for r in retractions}
        assert contracted == {"b1", "b3"}
        assert all(r.was_valid is True for r in retractions)

    def test_agm_no_contraction(self):
        state = _make_state()
        state.add_belief_revision_result(
            method="fallacy_contraction",
            original=["b1", "b2"],
            revised=["b1", "b2"],
        )
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        assert len(retractions) == 0

    def test_agm_trigger_includes_method(self):
        state = _make_state()
        state.add_belief_revision_result(
            method="fallacy_contraction",
            original=["b1"],
            revised=[],
        )
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        assert retractions[0].trigger == "fallacy_contraction_contraction"

    def test_both_sources_merged(self):
        state = _make_state()
        # JTMS source
        state.jtms_retraction_chain.append(
            {"belief_name": "jtms_b1", "was_valid": True, "trigger": "cascade"}
        )
        # AGM source
        state.add_belief_revision_result(
            method="fallacy_contraction",
            original=["agm_b1", "agm_b2"],
            revised=["agm_b1"],
        )
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        assert len(retractions) == 2  # 1 JTMS + 1 AGM contracted
        names = {r.belief_name for r in retractions}
        assert names == {"jtms_b1", "agm_b2"}

    def test_empty_state_returns_empty(self):
        state = _make_state()
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        assert retractions == []

    def test_multiple_agm_entries(self):
        state = _make_state()
        state.add_belief_revision_result(
            method="m1",
            original=["a", "b"],
            revised=["a"],
        )
        state.add_belief_revision_result(
            method="m2",
            original=["c", "d", "e"],
            revised=["e"],
        )
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        contracted = {r.belief_name for r in retractions}
        assert contracted == {"b", "c", "d"}

    def test_agm_result_shape_is_belief_retraction(self):
        state = _make_state()
        state.add_belief_revision_result(
            method="test",
            original=["x"],
            revised=[],
        )
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        r = retractions[0]
        assert isinstance(r, BeliefRetraction)
        assert r.belief_name == "x"
        assert r.was_valid is True
        assert "test" in r.trigger
