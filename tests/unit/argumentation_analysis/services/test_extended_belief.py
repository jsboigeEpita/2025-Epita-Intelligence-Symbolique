"""Tests for ExtendedBelief, JTMSSession, and ConflictResolver (#214)."""

import pytest
from datetime import datetime

from argumentation_analysis.services.jtms.extended_belief import (
    ExtendedBelief,
    JTMSSession,
)
from argumentation_analysis.services.jtms.conflict_resolution import ConflictResolver
from argumentation_analysis.services.jtms.jtms_core import JTMS, Belief, Justification

# ── ExtendedBelief ──────────────────────────────────────────────────


class TestExtendedBelief:
    def test_creation_with_defaults(self):
        eb = ExtendedBelief("test_belief")
        assert eb.name == "test_belief"
        assert eb.agent_source == "unknown"
        assert eb.confidence == 0.0
        assert eb.valid is None
        assert eb.modification_history == []

    def test_creation_with_metadata(self):
        eb = ExtendedBelief(
            "hyp_1",
            agent_source="sherlock",
            context={"domain": "evidence"},
            confidence=0.85,
        )
        assert eb.agent_source == "sherlock"
        assert eb.confidence == 0.85
        assert eb.context["domain"] == "evidence"
        assert isinstance(eb.creation_timestamp, datetime)

    def test_wraps_jtms_belief(self):
        eb = ExtendedBelief("wrapped")
        assert isinstance(eb._jtms_belief, Belief)
        assert eb._jtms_belief.name == "wrapped"

    def test_valid_property_delegates(self):
        eb = ExtendedBelief("b1")
        assert eb.valid is None
        eb._jtms_belief.valid = True
        assert eb.valid is True

    def test_record_modification(self):
        eb = ExtendedBelief("b1", agent_source="watson")
        eb.record_modification("test_action", {"key": "value"})
        assert len(eb.modification_history) == 1
        assert eb.modification_history[0]["action"] == "test_action"
        assert eb.modification_history[0]["agent"] == "watson"

    def test_to_dict(self):
        eb = ExtendedBelief("b1", agent_source="sherlock", confidence=0.9)
        d = eb.to_dict()
        assert d["name"] == "b1"
        assert d["agent_source"] == "sherlock"
        assert d["confidence"] == 0.9
        assert d["valid"] is None
        assert "creation_timestamp" in d

    def test_non_monotonic_delegates(self):
        eb = ExtendedBelief("b1")
        assert eb.non_monotonic is False
        eb._jtms_belief.non_monotonic = True
        assert eb.non_monotonic is True


# ── JTMSSession ─────────────────────────────────────────────────────


class TestJTMSSession:
    def test_creation(self):
        session = JTMSSession("sess1", "agent_a")
        assert session.session_id == "sess1"
        assert session.owner_agent == "agent_a"
        assert len(session.extended_beliefs) == 0
        assert session.total_inferences == 0

    def test_add_belief(self):
        session = JTMSSession("s1", "agent")
        eb = session.add_belief("b1", "sherlock", confidence=0.8)
        assert eb.name == "b1"
        assert eb.agent_source == "sherlock"
        assert eb.confidence == 0.8
        assert "b1" in session.extended_beliefs
        assert "b1" in session.jtms.beliefs

    def test_add_belief_update_existing(self):
        session = JTMSSession("s1", "agent")
        session.add_belief("b1", "sherlock", confidence=0.5)
        session.add_belief("b1", "watson", confidence=0.9)
        # Confidence takes max
        assert session.extended_beliefs["b1"].confidence == 0.9
        # Modification recorded
        assert len(session.extended_beliefs["b1"].modification_history) == 1

    def test_add_justification(self):
        session = JTMSSession("s1", "agent")
        session.add_belief("A", "agent", confidence=0.8)
        session.add_belief("B", "agent", confidence=0.7)
        session.add_justification(["A"], [], "B", agent_source="agent")
        assert session.total_inferences == 1
        assert len(session.jtms.beliefs["B"].justifications) >= 1

    def test_add_justification_with_out_list_creates_contradiction(self):
        session = JTMSSession("s1", "agent")
        session.add_belief("A", "agent")
        session.add_belief("B", "agent")
        session.add_justification(["A"], ["B"], "C", agent_source="agent")
        # Should create _CONTRADICTION_ belief
        assert "_CONTRADICTION_" in session.extended_beliefs

    def test_set_fact(self):
        session = JTMSSession("s1", "agent")
        session.add_belief("fact_1", "agent")
        session.set_fact("fact_1", True)
        assert session.jtms.beliefs["fact_1"].valid is True

    def test_set_fact_auto_creates(self):
        session = JTMSSession("s1", "agent")
        session.set_fact("new_fact", True)
        assert "new_fact" in session.jtms.beliefs
        assert session.jtms.beliefs["new_fact"].valid is True

    def test_check_consistency_clean(self):
        session = JTMSSession("s1", "agent")
        session.add_belief("A", "agent")
        session.set_fact("A", True)
        result = session.check_consistency()
        assert result["is_consistent"] is True
        assert result["conflicts"] == []

    def test_get_session_summary(self):
        session = JTMSSession("s1", "agent_a")
        session.add_belief("b1", "agent_a")
        session.add_justification(["b1"], [], "b2", agent_source="agent_a")
        summary = session.get_session_summary()
        assert summary["session_id"] == "s1"
        assert summary["owner_agent"] == "agent_a"
        assert summary["belief_count"] == 2
        assert summary["total_inferences"] == 1

    def test_propagation_through_session(self):
        session = JTMSSession("s1", "agent")
        session.add_belief("premise", "agent")
        session.add_belief("conclusion", "agent")
        session.add_justification(["premise"], [], "conclusion", agent_source="agent")
        session.set_fact("premise", True)
        assert session.jtms.beliefs["conclusion"].valid is True


# ── ConflictResolver ────────────────────────────────────────────────


class TestConflictResolver:
    def _make_conflict(self, beliefs_data):
        return {
            "belief_name": "test_belief",
            "beliefs": beliefs_data,
            "context": {"type": "hypothesis"},
        }

    def test_resolve_by_confidence(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            {
                "sherlock": {"belief_name": "hyp_X", "confidence": 0.9},
                "watson": {"belief_name": "hyp_X", "confidence": 0.3},
            }
        )
        result = resolver.resolve(conflict, strategy="confidence_based")
        assert result["resolved"] is True
        assert result["chosen_agent"] == "sherlock"
        assert result["confidence_score"] == 0.9

    def test_resolve_by_evidence(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            {
                "agent_a": {
                    "belief_name": "b1",
                    "confidence": 0.5,
                    "justification_count": 4,
                },
                "agent_b": {
                    "belief_name": "b1",
                    "confidence": 0.9,
                    "justification_count": 1,
                },
            }
        )
        result = resolver.resolve(conflict, strategy="evidence_based")
        assert result["resolved"] is True
        # agent_a: 4*0.5=2.0, agent_b: 1*0.9=0.9 → agent_a wins
        assert result["chosen_agent"] == "agent_a"

    def test_resolve_by_consensus_needs_3_agents(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            {
                "a": {"belief_name": "b1", "valid": True},
                "b": {"belief_name": "b1", "valid": False},
            }
        )
        result = resolver.resolve(conflict, strategy="consensus")
        assert result["resolved"] is False

    def test_resolve_by_consensus_majority(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            {
                "a": {"belief_name": "b1", "valid": True},
                "b": {"belief_name": "b1", "valid": True},
                "c": {"belief_name": "b1", "valid": False},
            }
        )
        result = resolver.resolve(conflict, strategy="consensus")
        assert result["resolved"] is True

    def test_resolve_by_expertise(self):
        resolver = ConflictResolver()
        conflict = {
            "belief_name": "hyp_1",
            "beliefs": {
                "sherlock_agent": {"belief_name": "hyp_1", "confidence": 0.5},
                "watson_agent": {"belief_name": "hyp_1", "confidence": 0.9},
            },
            "context": {"type": "hypothesis"},
        }
        result = resolver.resolve(conflict, strategy="agent_expertise")
        assert result["resolved"] is True
        # hypothesis → sherlock expertise
        assert result["chosen_agent"] == "sherlock_agent"

    def test_resolve_by_temporal(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            {
                "a": {"belief_name": "b1", "timestamp": "2026-03-25T10:00:00"},
                "b": {"belief_name": "b1", "timestamp": "2026-03-25T12:00:00"},
            }
        )
        result = resolver.resolve(conflict, strategy="temporal")
        assert result["resolved"] is True
        assert result["chosen_agent"] == "b"

    def test_invalid_strategy_falls_back(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            {
                "a": {"belief_name": "b1", "confidence": 0.5},
            }
        )
        result = resolver.resolve(conflict, strategy="nonexistent")
        assert result["strategy_used"] == "confidence_based"

    def test_resolution_history(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            {
                "a": {"belief_name": "b1", "confidence": 0.5},
            }
        )
        resolver.resolve(conflict)
        resolver.resolve(conflict)
        assert len(resolver.get_history()) == 2

    def test_stats(self):
        resolver = ConflictResolver()
        conflict = self._make_conflict(
            {
                "a": {"belief_name": "b1", "confidence": 0.5},
            }
        )
        resolver.resolve(conflict, strategy="confidence_based")
        resolver.resolve(conflict, strategy="evidence_based")
        stats = resolver.get_stats()
        assert stats["total_conflicts"] == 2
        assert stats["resolved"] == 2
        assert stats["by_strategy"]["confidence_based"] == 1
        assert stats["by_strategy"]["evidence_based"] == 1


# ── Integration: imports from __init__ ──────────────────────────────


class TestServiceImports:
    def test_import_extended_belief_from_init(self):
        from argumentation_analysis.services.jtms import ExtendedBelief

        eb = ExtendedBelief("test")
        assert eb.name == "test"

    def test_import_session_from_init(self):
        from argumentation_analysis.services.jtms import JTMSSession

        s = JTMSSession("s1", "agent")
        assert s.session_id == "s1"

    def test_import_resolver_from_init(self):
        from argumentation_analysis.services.jtms import ConflictResolver

        r = ConflictResolver()
        assert len(r.STRATEGIES) == 5

    def test_import_core_still_works(self):
        from argumentation_analysis.services.jtms import JTMS, Belief, Justification

        jtms = JTMS()
        jtms.add_belief("test")
        assert "test" in jtms.beliefs
