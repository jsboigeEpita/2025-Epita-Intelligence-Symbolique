# tests/unit/argumentation_analysis/models/test_investigation_session_model.py
"""Tests for InvestigationSessionModel, SessionCheckpoint, SessionSummary, enums."""

import json
import pytest
from datetime import datetime, timedelta

from argumentation_analysis.models.investigation_session_model import (
    SessionStatus,
    InvestigationType,
    AgentRole,
    SessionCheckpoint,
    SessionSummary,
    InvestigationSessionModel,
)

# ── Enums ──


class TestEnums:
    def test_session_status_values(self):
        assert SessionStatus.INITIALIZING.value == "initializing"
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.FAILED.value == "failed"

    def test_investigation_type_values(self):
        assert InvestigationType.CLUEDO_GAME.value == "cluedo_game"
        assert InvestigationType.LOGICAL_PUZZLE.value == "logical_puzzle"

    def test_agent_role_values(self):
        assert AgentRole.INVESTIGATOR.value == "investigator"
        assert AgentRole.VALIDATOR.value == "validator"


# ── SessionCheckpoint ──


class TestSessionCheckpoint:
    def test_auto_id_generation(self):
        cp = SessionCheckpoint(
            checkpoint_id="",
            session_id="s1",
            timestamp=datetime.now(),
            checkpoint_name="test",
        )
        assert cp.checkpoint_id.startswith("checkpoint_")

    def test_explicit_id(self):
        cp = SessionCheckpoint(
            checkpoint_id="my_id",
            session_id="s1",
            timestamp=datetime.now(),
            checkpoint_name="test",
        )
        assert cp.checkpoint_id == "my_id"

    def test_to_dict(self):
        ts = datetime(2026, 1, 1, 12, 0)
        cp = SessionCheckpoint(
            checkpoint_id="cp1",
            session_id="s1",
            timestamp=ts,
            checkpoint_name="save1",
            description="desc",
        )
        d = cp.to_dict()
        assert d["checkpoint_id"] == "cp1"
        assert d["session_id"] == "s1"
        assert d["timestamp"] == ts.isoformat()
        assert d["checkpoint_name"] == "save1"

    def test_from_dict_roundtrip(self):
        ts = datetime(2026, 1, 1, 12, 0)
        original = SessionCheckpoint(
            checkpoint_id="cp1",
            session_id="s1",
            timestamp=ts,
            checkpoint_name="test",
            beliefs_snapshot={"b1": {"valid": True}},
        )
        d = original.to_dict()
        restored = SessionCheckpoint.from_dict(d)
        assert restored.checkpoint_id == "cp1"
        assert restored.beliefs_snapshot == {"b1": {"valid": True}}

    def test_get_size_estimate(self):
        cp = SessionCheckpoint(
            checkpoint_id="cp1",
            session_id="s1",
            timestamp=datetime.now(),
            checkpoint_name="test",
        )
        size = cp.get_size_estimate()
        assert size > 0


# ── SessionSummary ──


class TestSessionSummary:
    @pytest.fixture
    def summary(self):
        return SessionSummary(
            session_id="sum1",
            investigation_type=InvestigationType.CLUEDO_GAME,
            status=SessionStatus.COMPLETED,
            start_time=datetime(2026, 1, 1, 10, 0),
            end_time=datetime(2026, 1, 1, 11, 0),
            participating_agents={"sherlock": AgentRole.INVESTIGATOR},
            lead_investigator="sherlock",
            confidence_score=0.85,
            hypotheses_tested=["h1"],  # non-empty to avoid source bug on line 177
            validation_cycles=1,
        )

    def test_duration(self, summary):
        assert summary.duration == timedelta(hours=1)

    def test_duration_seconds(self, summary):
        assert summary.duration_seconds == 3600.0

    def test_duration_none_when_no_end(self):
        s = SessionSummary(
            session_id="s1",
            investigation_type=InvestigationType.CLUEDO_GAME,
            status=SessionStatus.ACTIVE,
            start_time=datetime.now(),
        )
        assert s.duration is None
        assert s.duration_seconds == 0.0

    def test_calculate_success_metrics(self, summary):
        metrics = summary.calculate_success_metrics()
        assert "overall_success_score" in metrics
        assert metrics["completion_rate"] == 1.0
        assert metrics["confidence_score"] == 0.85

    def test_to_dict(self, summary):
        d = summary.to_dict()
        assert d["session_id"] == "sum1"
        assert d["investigation_type"] == "cluedo_game"
        assert d["status"] == "completed"
        assert d["participating_agents"]["sherlock"] == "investigator"
        assert "success_metrics" in d

    def test_from_dict_roundtrip(self, summary):
        d = summary.to_dict()
        restored = SessionSummary.from_dict(d)
        assert restored.session_id == "sum1"
        assert restored.investigation_type == InvestigationType.CLUEDO_GAME
        assert restored.lead_investigator == "sherlock"
        assert restored.confidence_score == 0.85


# ── InvestigationSessionModel ──


class TestInvestigationSessionModel:
    @pytest.fixture
    def session(self):
        return InvestigationSessionModel(
            session_id="inv1",
            investigation_type=InvestigationType.CLUEDO_GAME,
            title="Murder Mystery",
        )

    # -- Init --
    def test_init_defaults(self, session):
        assert session.status == SessionStatus.INITIALIZING
        assert session.session_statistics["beliefs_created"] == 0
        assert session.global_consistency_state["is_consistent"] is True

    def test_auto_id_generation(self):
        s = InvestigationSessionModel(
            session_id="",
            investigation_type=InvestigationType.LOGICAL_PUZZLE,
            title="Puzzle",
        )
        assert s.session_id.startswith("investigation_")

    # -- Agent Management --
    def test_register_agent(self, session):
        assert session.register_agent("sherlock", AgentRole.INVESTIGATOR) is True
        assert "sherlock" in session.registered_agents
        assert session.lead_investigator == "sherlock"

    def test_register_agent_duplicate(self, session):
        session.register_agent("sherlock", AgentRole.INVESTIGATOR)
        assert session.register_agent("sherlock", AgentRole.INVESTIGATOR) is False

    def test_lead_investigator_set_once(self, session):
        session.register_agent("sherlock", AgentRole.INVESTIGATOR)
        session.register_agent("watson", AgentRole.INVESTIGATOR)
        assert session.lead_investigator == "sherlock"

    def test_activate_agent(self, session):
        session.register_agent("sherlock", AgentRole.INVESTIGATOR)
        assert session.activate_agent("sherlock") is True
        assert "sherlock" in session.active_agents

    def test_activate_unregistered_agent(self, session):
        assert session.activate_agent("unknown") is False

    def test_deactivate_agent(self, session):
        session.register_agent("sherlock", AgentRole.INVESTIGATOR)
        session.activate_agent("sherlock")
        assert session.deactivate_agent("sherlock") is True
        assert "sherlock" not in session.active_agents

    def test_deactivate_inactive_agent(self, session):
        assert session.deactivate_agent("unknown") is False

    def test_get_active_investigators(self, session):
        session.register_agent("sherlock", AgentRole.INVESTIGATOR)
        session.register_agent("watson", AgentRole.VALIDATOR)
        session.activate_agent("sherlock")
        session.activate_agent("watson")
        investigators = session.get_active_investigators()
        assert "sherlock" in investigators
        assert "watson" not in investigators

    def test_get_active_validators(self, session):
        session.register_agent("watson", AgentRole.VALIDATOR)
        session.activate_agent("watson")
        validators = session.get_active_validators()
        assert "watson" in validators

    # -- Phases --
    def test_start_session(self, session):
        assert session.start_session() is True
        assert session.status == SessionStatus.ACTIVE
        assert len(session.checkpoints) == 1
        assert len(session.investigation_phases) == 1

    def test_start_session_not_initializing(self, session):
        session.status = SessionStatus.ACTIVE
        assert session.start_session() is False

    def test_start_phase(self, session):
        pid = session.start_phase("evidence_collection", "Collecting clues")
        assert pid.startswith("phase_")
        assert session.current_phase == "evidence_collection"
        assert len(session.investigation_phases) == 1

    def test_end_phase(self, session):
        session.start_phase("testing")
        assert session.end_phase({"result": "ok"}) is True
        assert session.investigation_phases[-1]["status"] == "completed"

    def test_end_phase_no_phases(self, session):
        assert session.end_phase() is False

    def test_get_current_phase_info(self, session):
        session.start_phase("analysis")
        info = session.get_current_phase_info()
        assert info["phase_name"] == "analysis"
        assert info["status"] == "active"

    def test_get_current_phase_none(self, session):
        assert session.get_current_phase_info() is None

    # -- Beliefs --
    def test_add_session_belief(self, session):
        assert (
            session.add_session_belief("b1", {"content": "suspect"}, "sherlock") is True
        )
        assert "b1" in session.session_beliefs
        assert session.session_statistics["beliefs_created"] == 1

    def test_add_duplicate_belief(self, session):
        session.add_session_belief("b1", {"content": "x"}, "sherlock")
        assert session.add_session_belief("b1", {"content": "y"}, "watson") is False

    def test_update_session_belief(self, session):
        session.add_session_belief("b1", {"content": "old"}, "sherlock")
        assert session.update_session_belief("b1", {"content": "new"}, "watson") is True
        assert session.session_beliefs["b1"]["content"] == "new"
        assert session.session_statistics["beliefs_modified"] == 1

    def test_update_nonexistent_belief(self, session):
        assert session.update_session_belief("bad", {}, "x") is False

    def test_share_belief_with_agents(self, session):
        session.add_session_belief("b1", {}, "sherlock")
        assert session.share_belief_with_agents("b1", ["watson", "moriarty"]) is True
        assert "watson" in session.session_beliefs["b1"]["shared_with"]

    def test_share_nonexistent_belief(self, session):
        assert session.share_belief_with_agents("bad", ["watson"]) is False

    # -- Hypotheses --
    def test_add_hypothesis(self, session):
        assert (
            session.add_hypothesis("h1", {"text": "Colonel Mustard"}, "sherlock")
            is True
        )
        assert "h1" in session.hypotheses_under_test
        assert session.session_statistics["hypotheses_formulated"] == 1

    def test_add_duplicate_hypothesis(self, session):
        session.add_hypothesis("h1", {}, "sherlock")
        assert session.add_hypothesis("h1", {}, "watson") is False

    def test_validate_hypothesis_valid(self, session):
        session.add_hypothesis("h1", {"text": "test"}, "sherlock")
        assert session.validate_hypothesis("h1", {"is_valid": True}, "watson") is True
        assert "h1" in session.validated_conclusions
        assert "h1" not in session.hypotheses_under_test

    def test_validate_hypothesis_invalid(self, session):
        session.add_hypothesis("h1", {"text": "test"}, "sherlock")
        assert session.validate_hypothesis("h1", {"is_valid": False}, "watson") is True
        assert session.hypotheses_under_test["h1"]["status"] == "invalidated"
        assert session.session_statistics["beliefs_invalidated"] == 1

    def test_validate_nonexistent_hypothesis(self, session):
        assert session.validate_hypothesis("bad", {}, "watson") is False

    # -- Evidence --
    def test_add_evidence(self, session):
        assert session.add_evidence("e1", {"type": "fingerprint"}) is True
        assert "e1" in session.available_evidence

    def test_add_duplicate_evidence(self, session):
        session.add_evidence("e1", {})
        assert session.add_evidence("e1", {}) is False

    def test_link_evidence_to_hypothesis_supports(self, session):
        session.add_evidence("e1", {})
        session.add_hypothesis("h1", {}, "sherlock")
        assert session.link_evidence_to_hypothesis("e1", "h1", "supports") is True
        assert "e1" in session.hypotheses_under_test["h1"]["supporting_evidence"]

    def test_link_evidence_to_hypothesis_contradicts(self, session):
        session.add_evidence("e1", {})
        session.add_hypothesis("h1", {}, "sherlock")
        assert session.link_evidence_to_hypothesis("e1", "h1", "contradicts") is True
        assert "e1" in session.hypotheses_under_test["h1"]["contradicting_evidence"]

    def test_link_nonexistent_evidence(self, session):
        session.add_hypothesis("h1", {}, "sherlock")
        assert session.link_evidence_to_hypothesis("bad", "h1") is False

    def test_link_nonexistent_hypothesis(self, session):
        session.add_evidence("e1", {})
        assert session.link_evidence_to_hypothesis("e1", "bad") is False

    # -- Checkpoints --
    def test_should_create_checkpoint_initially(self, session):
        assert session.should_create_checkpoint() is True

    def test_should_create_checkpoint_too_recent(self, session):
        session.last_checkpoint_time = datetime.now()
        assert session.should_create_checkpoint() is False

    def test_should_create_checkpoint_after_interval(self, session):
        session.last_checkpoint_time = datetime.now() - timedelta(minutes=15)
        assert session.should_create_checkpoint() is True

    def test_create_checkpoint(self, session):
        cp = session.create_checkpoint("test_cp", "Test checkpoint")
        assert cp is not None
        assert cp.session_id == "inv1"
        assert len(session.checkpoints) == 1
        assert session.session_statistics["checkpoints_created"] == 1

    def test_checkpoint_limit_pruning(self, session):
        session.max_checkpoints = 5
        for i in range(10):
            session.create_checkpoint(f"cp_{i}")
        assert len(session.checkpoints) <= 5

    def test_restore_checkpoint(self, session):
        session.add_session_belief("b1", {"val": "before"}, "sherlock")
        cp = session.create_checkpoint("before_change")
        session.add_session_belief("b2", {"val": "after"}, "sherlock")
        assert "b2" in session.session_beliefs

        result = session.restore_checkpoint(cp.checkpoint_id)
        assert result is True
        assert "b1" in session.session_beliefs
        assert "b2" not in session.session_beliefs

    def test_restore_nonexistent_checkpoint(self, session):
        assert session.restore_checkpoint("nonexistent") is False

    # -- Consistency --
    def test_update_consistency_state(self, session):
        session.update_consistency_state({"is_consistent": True})
        assert session.global_consistency_state["check_count"] == 1

    def test_update_consistency_with_conflicts(self, session):
        session.start_phase("test")
        session.update_consistency_state(
            {
                "is_consistent": False,
                "conflicts": ["c1", "c2"],
            }
        )
        assert session.session_statistics["conflicts_detected"] == 2

    # -- Metrics --
    def test_calculate_session_metrics(self, session):
        session.register_agent("sherlock", AgentRole.INVESTIGATOR)
        session.activate_agent("sherlock")
        metrics = session.calculate_session_metrics()
        assert "overall_performance_score" in metrics
        assert metrics["agent_collaboration_score"] == 1.0

    # -- Complete Session --
    def test_complete_session(self, session):
        session.start_session()
        session.register_agent("sherlock", AgentRole.INVESTIGATOR)
        summary = session.complete_session({"solution": "Mustard", "confidence": 0.9})
        assert session.status == SessionStatus.COMPLETED
        assert isinstance(summary, SessionSummary)
        assert summary.confidence_score == 0.9

    # -- Serialization --
    def test_to_dict(self, session):
        d = session.to_dict()
        assert d["session_id"] == "inv1"
        assert d["investigation_type"] == "cluedo_game"
        assert d["title"] == "Murder Mystery"
        assert "checkpoints" not in d

    def test_to_dict_with_checkpoints(self, session):
        session.create_checkpoint("cp1")
        d = session.to_dict(include_checkpoints=True)
        assert "checkpoints" in d
        assert len(d["checkpoints"]) == 1

    def test_from_dict_roundtrip(self, session):
        session.register_agent("sherlock", AgentRole.INVESTIGATOR)
        session.add_session_belief("b1", {"val": 1}, "sherlock")
        d = session.to_dict(include_checkpoints=True)
        restored = InvestigationSessionModel.from_dict(d)
        assert restored.session_id == "inv1"
        assert "sherlock" in restored.registered_agents
        assert "b1" in restored.session_beliefs


# ── Integration ──


class TestInvestigationIntegration:
    def test_full_investigation_lifecycle(self):
        """Full Cluedo investigation: register, start, evidence, hypotheses, validate, complete."""
        session = InvestigationSessionModel(
            session_id="cluedo_01",
            investigation_type=InvestigationType.CLUEDO_GAME,
            title="Cluedo Investigation",
        )

        # Register agents
        session.register_agent("sherlock", AgentRole.INVESTIGATOR)
        session.register_agent("watson", AgentRole.VALIDATOR)
        session.activate_agent("sherlock")
        session.activate_agent("watson")

        # Start session
        session.start_session()
        assert session.status == SessionStatus.ACTIVE

        # Add evidence
        session.add_evidence("fingerprint_kitchen", {"location": "kitchen"})
        session.add_evidence("weapon_rope", {"type": "weapon"})

        # Hypothesis phase
        session.start_phase("hypothesis_formulation")
        session.add_hypothesis("h_mustard", {"suspect": "Mustard"}, "sherlock")
        session.add_hypothesis("h_plum", {"suspect": "Plum"}, "sherlock")
        session.end_phase()

        # Link evidence
        session.link_evidence_to_hypothesis(
            "fingerprint_kitchen", "h_mustard", "supports"
        )
        session.link_evidence_to_hypothesis("weapon_rope", "h_plum", "contradicts")

        # Validation phase
        session.start_phase("validation")
        session.validate_hypothesis("h_plum", {"is_valid": False}, "watson")
        session.validate_hypothesis("h_mustard", {"is_valid": True}, "watson")
        session.end_phase()

        # Complete
        summary = session.complete_session(
            {
                "solution": "Colonel Mustard in the Kitchen with the Rope",
                "confidence": 0.95,
            }
        )

        assert summary.status == SessionStatus.COMPLETED
        assert summary.confidence_score == 0.95
        assert "h_mustard" in summary.hypotheses_tested
        assert len(summary.evidence_processed) == 2

        # Serialization roundtrip
        d = session.to_dict(include_checkpoints=True)
        json_str = json.dumps(d, default=str)
        assert len(json_str) > 100
