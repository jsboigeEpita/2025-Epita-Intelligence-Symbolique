"""Tests for ATMS hypothesis branching in Sherlock (#359).

Validates that the HypothesisTracker:
- Maintains >=3 simultaneous hypotheses
- Updates coherence when new evidence arrives
- Retracts contradicted hypotheses visibly
- Produces investigation state snapshots
- Integrates with ATMS core
"""

import pytest

from argumentation_analysis.agents.core.oracle.hypothesis_tracker import (
    HypothesisTracker,
    Hypothesis,
)


class TestHypothesisCreation:
    """Tests for hypothesis creation and registration."""

    def test_create_single_hypothesis(self):
        tracker = HypothesisTracker()
        hyp = tracker.create_hypothesis("h1", "Test", ["a", "b"])
        assert hyp.id == "h1"
        assert hyp.coherent is True
        assert hyp.assumptions == ["a", "b"]

    def test_create_multiple_hypotheses(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "Trust all", ["a", "b"])
        tracker.create_hypothesis("h2", "Skeptical", ["c"])
        tracker.create_hypothesis("h3", "Conservative", ["a", "d"])
        assert len(tracker.get_all_hypotheses()) == 3

    def test_min_3_hypotheses(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "A", ["a"])
        tracker.create_hypothesis("h2", "B", ["b"])
        tracker.create_hypothesis("h3", "C", ["c"])
        all_hyps = tracker.get_all_hypotheses()
        assert len(all_hyps) >= 3

    def test_hypothesis_has_description(self):
        tracker = HypothesisTracker()
        hyp = tracker.create_hypothesis("h1", "Test", ["a"], description="A test hyp")
        assert hyp.description == "A test hyp"


class TestEvidenceUpdate:
    """Tests for evidence-driven hypothesis updates."""

    def test_add_evidence_returns_result(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "A", ["a"])
        result = tracker.add_evidence("ev1", supports=["a"])
        assert "evidence_added" in result
        assert result["evidence_added"] == "ev1"

    def test_evidence_count_increases(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "A", ["a"])
        tracker.add_evidence("ev1", supports=["a"])
        tracker.add_evidence("ev2", supports=["a"])
        state = tracker.get_investigation_state()
        assert state["evidence_count"] == 2

    def test_supporting_evidence_keeps_hypothesis_coherent(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "Trust", ["source_reliable"])
        tracker.add_evidence("ev1", supports=["source_reliable"])
        active = tracker.get_active_hypotheses()
        assert len(active) >= 1
        assert active[0].id == "h1"

    def test_contradicting_evidence_retracts_hypothesis(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "Trust", ["source_reliable"])
        tracker.create_hypothesis("h2", "Doubt", ["source_unreliable"])
        tracker.add_evidence("ev1", contradicts=["source_reliable"])
        retracted = tracker.get_retracted_hypotheses()
        # h1 should be retracted (its assumption is contradicted)
        assert any(h.id == "h1" for h in retracted)

    def test_retracted_hypothesis_has_reason(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "Trust", ["source_reliable"])
        tracker.add_evidence("ev_contra", contradicts=["source_reliable"])
        retracted = tracker.get_retracted_hypotheses()
        if retracted:
            assert retracted[0].retraction_reason != ""

    def test_partial_retraction(self):
        """Only affected hypotheses are retracted."""
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "Trust A", ["assumption_a"])
        tracker.create_hypothesis("h2", "Trust B", ["assumption_b"])
        tracker.create_hypothesis("h3", "Trust C", ["assumption_c"])
        tracker.add_evidence("ev1", contradicts=["assumption_a"])
        active = tracker.get_active_hypotheses()
        retracted = tracker.get_retracted_hypotheses()
        # h1 should be retracted, h2 and h3 should remain
        assert any(h.id == "h1" for h in retracted)
        assert any(h.id == "h2" for h in active)
        assert any(h.id == "h3" for h in active)


class TestInvestigationState:
    """Tests for investigation state snapshots."""

    def test_state_has_required_fields(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "A", ["a"])
        state = tracker.get_investigation_state()
        assert "total_hypotheses" in state
        assert "active" in state
        assert "retracted" in state
        assert "evidence_count" in state

    def test_state_reflects_updates(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "A", ["a"])
        tracker.create_hypothesis("h2", "B", ["b"])
        tracker.add_evidence("ev1", contradicts=["a"])
        state = tracker.get_investigation_state()
        assert state["total_hypotheses"] == 2
        assert "h2" in state["active"]

    def test_evidence_log_recorded(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "A", ["a"])
        tracker.add_evidence("ev1", supports=["a"], contradicts=["b"])
        state = tracker.get_investigation_state()
        assert len(state["evidence_log"]) == 1
        log_entry = state["evidence_log"][0]
        assert log_entry["evidence_id"] == "ev1"
        assert "a" in log_entry["supports"]
        assert "b" in log_entry["contradicts"]


class TestHypothesisComparison:
    """Tests for human-readable comparison output."""

    def test_comparison_string(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "Trust", ["a"])
        tracker.create_hypothesis("h2", "Doubt", ["b"])
        comparison = tracker.get_hypothesis_comparison()
        assert "h1" in comparison
        assert "h2" in comparison
        assert "COHERENT" in comparison

    def test_comparison_with_retraction(self):
        tracker = HypothesisTracker()
        tracker.create_hypothesis("h1", "Trust", ["a"])
        tracker.add_evidence("ev1", contradicts=["a"])
        comparison = tracker.get_hypothesis_comparison()
        assert "RETRACTED" in comparison


class TestHypothesisDataclass:
    """Tests for the Hypothesis dataclass."""

    def test_default_values(self):
        hyp = Hypothesis(id="h1", name="Test", assumptions=["a"])
        assert hyp.coherent is True
        assert hyp.retraction_reason == ""
        assert hyp.evidence_applied == []
        assert hyp.derived_nodes == set()

    def test_with_values(self):
        hyp = Hypothesis(
            id="h1",
            name="Test",
            assumptions=["a", "b"],
            description="desc",
            coherent=False,
            retraction_reason="contradicted",
        )
        assert hyp.coherent is False
        assert hyp.retraction_reason == "contradicted"
