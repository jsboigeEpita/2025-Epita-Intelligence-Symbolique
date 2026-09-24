"""#2344: phase conflicts reach the resolver, and the resolver names what it could not decide.

Measured on ``main`` ``dc463b0a5``, with the real ``ConflictResolver``:
- ``_resolve_phase_conflicts`` handed its conflict under ``"agents"``; the
  resolver reads ``"beliefs"``. It saw nobody and answered "Highest
  confidence: -1.00 by None" under all five strategies, and the caller kept
  only resolved conflicts: the feature never resolved one, and never said so.
- Behind the key, the fallacy's confidence was an invented 0.7 (stored
  fallacies carry none), so a constant would have decided the outcome.
- ``agent_expertise`` and ``temporal`` fell back to confidence while
  ``strategy_used`` still named them; an unknown domain crowned Sherlock the
  expert; a misspelt strategy silently became ``confidence_based``.
- The item's own claim (``consensus`` a placeholder falling back to
  confidence) did not hold: it is a majority vote, see the control below.
  Only the module docstring called it a placeholder.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.orchestration.conversational_orchestrator import (
    _conflict_resolution_log_entry,
    _resolve_phase_conflicts,
)
from argumentation_analysis.services.jtms.conflict_resolution import ConflictResolver


def _state_with_conflict(fallacy_confidence=None) -> RhetoricalAnalysisState:
    state = RhetoricalAnalysisState("Test")
    fid = state.add_fallacy("ad_hominem", "Attacks person", target_arg_id="arg_1")
    if fallacy_confidence is not None:
        state.identified_fallacies[fid]["confidence"] = fallacy_confidence
    state.argument_quality_scores = {"arg_1": {"note_finale": 7.0}}
    return state


async def _handed_conflict(state) -> dict:
    """Run the phase resolver with the real ConflictResolver, return what it received."""
    handed = []
    real_resolve = ConflictResolver.resolve

    def spy(self, conflict, strategy="confidence_based"):
        handed.append(conflict)
        return real_resolve(self, conflict, strategy)

    with patch.object(ConflictResolver, "resolve", spy):
        await _resolve_phase_conflicts(state, "p1")
    assert len(handed) == 1
    return handed[0]


class TestThePhaseConflictReachesTheResolver:
    async def test_the_conflict_is_handed_as_beliefs(self):
        conflict = await _handed_conflict(_state_with_conflict())
        assert set(conflict["beliefs"]) == {"InformalAgent", "QualityAgent"}

    async def test_a_fallacy_confidence_is_not_invented(self):
        conflict = await _handed_conflict(_state_with_conflict())
        informal = conflict["beliefs"]["InformalAgent"]
        assert "confidence" not in informal
        assert informal["evidence"] == "Attacks person"

    async def test_an_undecidable_conflict_is_reported_with_its_cause(self):
        result = await _resolve_phase_conflicts(_state_with_conflict(), "p1")
        assert len(result) == 1
        resolution = result[0]["resolution"]
        assert resolution["resolved"] is False
        assert resolution["missing_confidence"] == ["InformalAgent"]

    async def test_a_fallacy_with_a_confidence_is_resolved(self):
        # 0.9 against the quality belief's 7/9: the fallacy wins on a real value.
        result = await _resolve_phase_conflicts(_state_with_conflict(0.9), "p1")
        resolution = result[0]["resolution"]
        assert resolution["resolved"] is True
        assert resolution["chosen_agent"] == "InformalAgent"


class TestTheLogEntryCountsBothOutcomes:
    def test_resolved_and_unresolved_are_counted_apart(self):
        entry = _conflict_resolution_log_entry(
            "p1",
            [
                {"conflict_id": "a", "resolution": {"resolved": True}},
                {"conflict_id": "b", "resolution": {"resolved": False}},
            ],
        )
        assert entry["type"] == "conflict_resolution"
        assert entry["resolution_count"] == 1
        assert entry["unresolved_count"] == 1

    def test_no_conflict_no_entry(self):
        assert _conflict_resolution_log_entry("p1", []) is None


class TestTheResolverNamesItsFallbacks:
    @pytest.fixture
    def resolver(self) -> ConflictResolver:
        return ConflictResolver()

    def test_a_misspelt_strategy_raises(self, resolver):
        with pytest.raises(ValueError, match="confidance_based"):
            resolver.resolve({"beliefs": {}}, strategy="confidance_based")

    def test_a_conflict_without_beliefs_raises(self, resolver):
        with pytest.raises(ValueError, match="beliefs"):
            resolver.resolve({"agents": {"a": {"confidence": 0.5}}})

    def test_a_missing_confidence_is_not_a_zero(self, resolver):
        conflict = {
            "beliefs": {
                "a": {"belief_name": "x", "confidence": 0.4},
                "b": {"belief_name": "y"},
            }
        }
        for strategy in ("confidence_based", "evidence_based"):
            result = resolver.resolve(conflict, strategy=strategy)
            assert result["resolved"] is False, strategy
            assert result["missing_confidence"] == ["b"], strategy

    def test_no_expert_is_a_named_fallback(self, resolver):
        conflict = {
            "beliefs": {
                "agent_a": {"belief_name": "x", "confidence": 0.5},
                "agent_b": {"belief_name": "y", "confidence": 0.9},
            },
            "context": {"type": "hypothesis"},
        }
        result = resolver.resolve(conflict, strategy="agent_expertise")
        assert result["chosen_agent"] == "agent_b"
        assert result["strategy_used"] == "confidence_based"
        assert result["fallback_from"] == "agent_expertise"

    def test_an_unknown_domain_has_no_expert(self, resolver):
        conflict = {
            "beliefs": {
                "sherlock_agent": {"belief_name": "x", "confidence": 0.2},
                "watson_agent": {"belief_name": "y", "confidence": 0.9},
            },
            "context": {"type": "weather"},
        }
        result = resolver.resolve(conflict, strategy="agent_expertise")
        assert result["chosen_agent"] == "watson_agent"
        assert result["fallback_from"] == "agent_expertise"

    def test_no_timestamp_is_a_named_fallback(self, resolver):
        conflict = {
            "beliefs": {
                "a": {"belief_name": "x", "confidence": 0.5},
                "b": {"belief_name": "y", "confidence": 0.9},
            }
        }
        result = resolver.resolve(conflict, strategy="temporal")
        assert result["strategy_used"] == "confidence_based"
        assert result["fallback_from"] == "temporal"

    def test_consensus_is_a_vote_not_a_placeholder(self, resolver):
        # Control, passes on main: the item's literal claim does not hold.
        conflict = {
            "beliefs": {
                "a": {"belief_name": "x", "valid": False, "confidence": 0.99},
                "b": {"belief_name": "x", "valid": True, "confidence": 0.1},
                "c": {"belief_name": "x", "valid": True, "confidence": 0.1},
            }
        }
        result = resolver.resolve(conflict, strategy="consensus")
        assert result["resolved"] is True
        assert result["chosen_agent"] == "b"
        assert result["strategy_used"] == "consensus"
