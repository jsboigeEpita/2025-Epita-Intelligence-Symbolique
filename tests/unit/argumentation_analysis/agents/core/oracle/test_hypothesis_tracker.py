"""Tests for HypothesisTracker — locks in the review #386 corrections."""

from argumentation_analysis.agents.core.oracle.hypothesis_tracker import (
    HypothesisTracker,
)


def test_create_three_hypotheses_all_active():
    t = HypothesisTracker()
    t.create_hypothesis("h1", "Trust", ["src_reliable"])
    t.create_hypothesis("h2", "Doubt", ["src_unreliable"])
    t.create_hypothesis("h3", "Mixed", ["src_partial"])
    assert len(t.get_active_hypotheses()) == 3
    assert len(t.get_retracted_hypotheses()) == 0


def test_evidence_contradicts_assumption_retracts_hypothesis():
    t = HypothesisTracker()
    t.create_hypothesis("h1", "Trust", ["src_reliable"])
    t.create_hypothesis("h2", "Doubt", ["src_unreliable"])
    t.create_hypothesis("h3", "Mixed", ["src_partial"])
    t.add_evidence("e1", supports=["src_reliable"], contradicts=["src_unreliable"])
    active = {h.id for h in t.get_active_hypotheses()}
    retracted = {h.id for h in t.get_retracted_hypotheses()}
    assert active == {"h1", "h3"}
    assert retracted == {"h2"}


def test_retraction_reason_blames_first_contradicting_evidence():
    """Review #386: retraction reason must identify the actual contradicting
    evidence, not the latest evidence call."""
    t = HypothesisTracker()
    t.create_hypothesis("h1", "Trust", ["x"])
    t.create_hypothesis("h2", "Doubt", ["y"])
    t.create_hypothesis("h3", "Mixed", ["z"])
    t.add_evidence("e1", supports=[], contradicts=["y"])
    t.add_evidence("e2", supports=[], contradicts=["y"])
    retracted = t.get_retracted_hypotheses()
    assert len(retracted) == 1
    assert "e1" in retracted[0].retraction_reason
    assert "e2" not in retracted[0].retraction_reason


def test_shared_assumption_across_hypotheses():
    """Review #386: assumptions can be shared between hypotheses (no overwrite)."""
    t = HypothesisTracker()
    t.create_hypothesis("h1", "Both A", ["shared", "only_a"])
    t.create_hypothesis("h2", "Both B", ["shared", "only_b"])
    t.create_hypothesis("h3", "Just shared", ["shared"])
    t.add_evidence("e1", supports=[], contradicts=["shared"])
    retracted = {h.id for h in t.get_retracted_hypotheses()}
    assert retracted == {"h1", "h2", "h3"}


def test_evidence_with_supports_is_derived_not_assumption():
    """Review #386: evidence backed by supporting assumptions must be a
    derived node, not a free-standing assumption (avoids circular ATMS)."""
    t = HypothesisTracker()
    t.create_hypothesis("h1", "Backed", ["base"])
    t.add_evidence("derived_evidence", supports=["base"])
    assert "derived_evidence" in t._atms.nodes  # type: ignore[attr-defined]
    node = t._atms.nodes["derived_evidence"]  # type: ignore[attr-defined]
    assert node.is_assumption is False


def test_evidence_without_supports_is_assumption():
    t = HypothesisTracker()
    t.create_hypothesis("h1", "Anything", ["x"])
    t.add_evidence("free_evidence", supports=[], contradicts=[])
    node = t._atms.nodes["free_evidence"]  # type: ignore[attr-defined]
    assert node.is_assumption is True


def test_investigation_state_snapshot():
    t = HypothesisTracker()
    t.create_hypothesis("h1", "T", ["a"])
    t.create_hypothesis("h2", "D", ["b"])
    t.create_hypothesis("h3", "M", ["c"])
    t.add_evidence("e1", supports=[], contradicts=["b"])
    state = t.get_investigation_state()
    assert state["total_hypotheses"] == 3
    assert state["active"] == ["h1", "h3"]
    assert len(state["retracted"]) == 1
    assert state["retracted"][0]["id"] == "h2"
    assert state["evidence_count"] == 1
