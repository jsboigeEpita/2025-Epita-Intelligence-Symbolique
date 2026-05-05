"""Unit tests for JTMS ConflictResolver — covers all 5 strategies + edge cases.

Target: argumentation_analysis/services/jtms/conflict_resolution.py (19% → 80%+)
"""

import pytest

from argumentation_analysis.services.jtms.conflict_resolution import ConflictResolver


@pytest.fixture
def resolver():
    return ConflictResolver()


@pytest.fixture
def simple_conflict():
    return {
        "conflict_id": "test_1",
        "belief_name": "hypothesis_X",
        "beliefs": {
            "agent_1": {
                "belief_name": "hypothesis_X",
                "confidence": 0.8,
                "valid": True,
            },
            "agent_2": {
                "belief_name": "hypothesis_X",
                "confidence": 0.3,
                "valid": False,
            },
        },
        "context": {"type": "hypothesis"},
    }


@pytest.fixture
def multi_agent_conflict():
    return {
        "conflict_id": "multi_1",
        "belief_name": "claim_A",
        "beliefs": {
            "agent_1": {
                "belief_name": "claim_A",
                "confidence": 0.7,
                "valid": True,
                "justification_count": 2,
                "timestamp": "2026-01-01T10:00:00",
            },
            "agent_2": {
                "belief_name": "claim_A",
                "confidence": 0.9,
                "valid": False,
                "justification_count": 5,
                "timestamp": "2026-01-01T12:00:00",
            },
            "agent_3": {
                "belief_name": "claim_A",
                "confidence": 0.4,
                "valid": True,
                "justification_count": 1,
                "timestamp": "2026-01-01T09:00:00",
            },
        },
        "context": {"type": "evidence"},
    }


class TestConflictResolverInit:
    def test_empty_history(self, resolver):
        assert resolver.resolution_history == []

    def test_strategies_listed(self, resolver):
        assert len(ConflictResolver.STRATEGIES) == 5
        assert "confidence_based" in ConflictResolver.STRATEGIES


class TestConfidenceBased:
    def test_picks_highest_confidence(self, resolver, simple_conflict):
        result = resolver.resolve(simple_conflict, strategy="confidence_based")
        assert result["resolved"] is True
        assert result["chosen_agent"] == "agent_1"
        assert result["chosen_belief"] == "hypothesis_X"
        assert result["confidence_score"] == 0.8

    def test_empty_beliefs(self, resolver):
        result = resolver.resolve({"beliefs": {}}, strategy="confidence_based")
        assert result["resolved"] is False
        assert result["chosen_belief"] is None

    def test_equal_confidence(self, resolver):
        conflict = {
            "beliefs": {
                "a": {"belief_name": "x", "confidence": 0.5},
                "b": {"belief_name": "x", "confidence": 0.5},
            }
        }
        result = resolver.resolve(conflict, strategy="confidence_based")
        assert result["resolved"] is True


class TestEvidenceBased:
    def test_picks_best_evidence_score(self, resolver, multi_agent_conflict):
        result = resolver.resolve(multi_agent_conflict, strategy="evidence_based")
        assert result["resolved"] is True
        # agent_2: 5 * 0.9 = 4.5 > agent_1: 2 * 0.7 = 1.4 > agent_3: 1 * 0.4 = 0.4
        assert result["chosen_agent"] == "agent_2"

    def test_no_justification_count_defaults_to_1(self, resolver, simple_conflict):
        result = resolver.resolve(simple_conflict, strategy="evidence_based")
        assert result["resolved"] is True
        # agent_1: 1 * 0.8 = 0.8 > agent_2: 1 * 0.3 = 0.3
        assert result["chosen_agent"] == "agent_1"


class TestConsensus:
    def test_majority_true_wins(self, resolver, multi_agent_conflict):
        result = resolver.resolve(multi_agent_conflict, strategy="consensus")
        assert result["resolved"] is True
        assert result["chosen_belief"] == "claim_A"

    def test_requires_three_agents(self, resolver, simple_conflict):
        result = resolver.resolve(simple_conflict, strategy="consensus")
        assert result["resolved"] is False
        assert "3+" in result["reasoning"]

    def test_tie_returns_unresolved(self, resolver):
        conflict = {
            "beliefs": {
                "a": {"belief_name": "x", "valid": True},
                "b": {"belief_name": "x", "valid": False},
                "c": {"belief_name": "x", "valid": True},
                "d": {"belief_name": "x", "valid": False},
            }
        }
        result = resolver.resolve(conflict, strategy="consensus")
        assert result["resolved"] is False
        assert "tie" in result["reasoning"].lower()


class TestAgentExpertise:
    def test_expert_match(self, resolver, multi_agent_conflict):
        conflict = {
            "beliefs": {
                "sherlock_agent": {
                    "belief_name": "hypothesis_X",
                    "confidence": 0.3,
                },
                "watson_agent": {
                    "belief_name": "hypothesis_X",
                    "confidence": 0.9,
                },
            },
            "context": {"type": "hypothesis"},
        }
        result = resolver.resolve(conflict, strategy="agent_expertise")
        assert result["resolved"] is True
        assert result["chosen_agent"] == "sherlock_agent"

    def test_falls_back_to_confidence_when_no_expert(self, resolver):
        conflict = {
            "beliefs": {
                "agent_a": {"belief_name": "x", "confidence": 0.5},
                "agent_b": {"belief_name": "x", "confidence": 0.9},
            },
            "context": {"type": "unknown_domain"},
        }
        result = resolver.resolve(conflict, strategy="agent_expertise")
        assert result["resolved"] is True
        assert result["chosen_agent"] == "agent_b"


class TestTemporal:
    def test_most_recent_wins(self, resolver, multi_agent_conflict):
        result = resolver.resolve(multi_agent_conflict, strategy="temporal")
        assert result["resolved"] is True
        assert result["chosen_agent"] == "agent_2"

    def test_no_timestamps_falls_back_to_confidence(self, resolver, simple_conflict):
        result = resolver.resolve(simple_conflict, strategy="temporal")
        assert result["resolved"] is True


class TestInvalidStrategy:
    def test_falls_back_to_confidence(self, resolver, simple_conflict):
        result = resolver.resolve(simple_conflict, strategy="nonexistent_strategy")
        assert result["resolved"] is True
        assert result["strategy_used"] == "confidence_based"


class TestHistoryAndStats:
    def test_history_recorded(self, resolver, simple_conflict):
        resolver.resolve(simple_conflict)
        assert len(resolver.resolution_history) == 1
        assert resolver.resolution_history[0]["conflict_id"] == "test_1"

    def test_get_stats(self, resolver, simple_conflict):
        resolver.resolve(simple_conflict, strategy="confidence_based")
        resolver.resolve(simple_conflict, strategy="evidence_based")
        stats = resolver.get_stats()
        assert stats["total_conflicts"] == 2
        assert stats["resolved"] == 2
        assert stats["by_strategy"]["confidence_based"] == 1

    def test_auto_conflict_id(self, resolver):
        result = resolver.resolve(
            {"beliefs": {"a": {"belief_name": "x", "confidence": 0.5}}}
        )
        assert "conflict_" in result["conflict_id"]

    def test_timestamp_in_result(self, resolver, simple_conflict):
        result = resolver.resolve(simple_conflict)
        assert "timestamp" in result
        assert result["timestamp"] != ""
