# tests/unit/argumentation_analysis/api/test_jtms_models.py
"""Tests for JTMS API Pydantic models — requests, responses, validation."""

import pytest
from pydantic import ValidationError

from argumentation_analysis.api.jtms_models import (
    BeliefInfo,
    JustificationInfo,
    CreateBeliefRequest,
    AddJustificationRequest,
    SetBeliefValidityRequest,
    QueryBeliefsRequest,
    ExplainBeliefRequest,
    GetJTMSStateRequest,
    CreateSessionRequest,
    CreateCheckpointRequest,
    RestoreCheckpointRequest,
    UpdateSessionMetadataRequest,
    JTMSResponse,
    CreateBeliefResponse,
    AddJustificationResponse,
    ExplainBeliefResponse,
    QueryBeliefsResponse,
    JTMSStatistics,
    SessionInfo,
    GetJTMSStateResponse,
    SetBeliefValidityResponse,
    CreateSessionResponse,
    SessionListResponse,
    CheckpointInfo,
    CreateCheckpointResponse,
    RestoreCheckpointResponse,
    JTMSError,
    ExportJTMSRequest,
    ImportJTMSRequest,
    ExportJTMSResponse,
    ImportJTMSResponse,
    PluginStatusResponse,
)


# ── BeliefInfo ──

class TestBeliefInfo:
    def test_required_fields(self):
        b = BeliefInfo(name="A")
        assert b.name == "A"

    def test_defaults(self):
        b = BeliefInfo(name="A")
        assert b.valid is None
        assert b.non_monotonic is False
        assert b.justifications_count == 0
        assert b.implications_count == 0

    def test_all_fields(self):
        b = BeliefInfo(
            name="B", valid=True, non_monotonic=True,
            justifications_count=3, implications_count=2,
        )
        assert b.valid is True
        assert b.non_monotonic is True
        assert b.justifications_count == 3

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            BeliefInfo()


# ── JustificationInfo ──

class TestJustificationInfo:
    def test_required_conclusion(self):
        j = JustificationInfo(conclusion="C")
        assert j.conclusion == "C"
        assert j.in_beliefs == []
        assert j.out_beliefs == []
        assert j.is_valid is None

    def test_all_fields(self):
        j = JustificationInfo(
            in_beliefs=["A", "B"], out_beliefs=["D"],
            conclusion="C", is_valid=True,
        )
        assert len(j.in_beliefs) == 2
        assert j.is_valid is True


# ── CreateBeliefRequest ──

class TestCreateBeliefRequest:
    def test_required_name(self):
        r = CreateBeliefRequest(belief_name="X")
        assert r.belief_name == "X"

    def test_defaults(self):
        r = CreateBeliefRequest(belief_name="X")
        assert r.initial_value == "unknown"
        assert r.session_id is None
        assert r.instance_id is None
        assert r.agent_id == "api_client"

    def test_custom(self):
        r = CreateBeliefRequest(
            belief_name="Y", initial_value="true",
            session_id="s1", instance_id="i1", agent_id="agent1",
        )
        assert r.initial_value == "true"
        assert r.session_id == "s1"

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            CreateBeliefRequest()


# ── AddJustificationRequest ──

class TestAddJustificationRequest:
    def test_minimal(self):
        r = AddJustificationRequest(conclusion="C")
        assert r.conclusion == "C"
        assert r.in_beliefs == []
        assert r.out_beliefs == []

    def test_full(self):
        r = AddJustificationRequest(
            in_beliefs=["A"], out_beliefs=["B"], conclusion="C",
            session_id="s1", agent_id="ag",
        )
        assert r.in_beliefs == ["A"]


# ── SetBeliefValidityRequest ──

class TestSetBeliefValidityRequest:
    def test_required(self):
        r = SetBeliefValidityRequest(belief_name="A", validity=True)
        assert r.belief_name == "A"
        assert r.validity is True

    def test_missing_raises(self):
        with pytest.raises(ValidationError):
            SetBeliefValidityRequest(belief_name="A")


# ── QueryBeliefsRequest ──

class TestQueryBeliefsRequest:
    def test_defaults(self):
        r = QueryBeliefsRequest()
        assert r.filter_status == "all"
        assert r.agent_id == "api_client"


# ── ExplainBeliefRequest ──

class TestExplainBeliefRequest:
    def test_required(self):
        r = ExplainBeliefRequest(belief_name="X")
        assert r.belief_name == "X"


# ── GetJTMSStateRequest ──

class TestGetJTMSStateRequest:
    def test_defaults(self):
        r = GetJTMSStateRequest()
        assert r.include_graph is True
        assert r.include_statistics is True


# ── Session Requests ──

class TestSessionRequests:
    def test_create_session(self):
        r = CreateSessionRequest(agent_id="a1")
        assert r.agent_id == "a1"
        assert r.session_name is None

    def test_create_checkpoint(self):
        r = CreateCheckpointRequest(session_id="s1")
        assert r.session_id == "s1"
        assert r.description is None

    def test_restore_checkpoint(self):
        r = RestoreCheckpointRequest(session_id="s1", checkpoint_id="c1")
        assert r.session_id == "s1"
        assert r.checkpoint_id == "c1"

    def test_update_metadata(self):
        r = UpdateSessionMetadataRequest(
            session_id="s1", metadata={"key": "value"}
        )
        assert r.metadata["key"] == "value"


# ── JTMSResponse ──

class TestJTMSResponse:
    def test_base_response(self):
        r = JTMSResponse(
            status="success", operation="create_belief",
            agent_id="a1", timestamp="2026-01-01",
        )
        assert r.status == "success"
        assert r.session_id is None

    def test_create_belief_response(self):
        belief = BeliefInfo(name="A", valid=True)
        r = CreateBeliefResponse(
            status="success", operation="create_belief",
            agent_id="a1", timestamp="2026-01-01", belief=belief,
        )
        assert r.belief.name == "A"

    def test_add_justification_response(self):
        j = JustificationInfo(conclusion="C")
        r = AddJustificationResponse(
            status="success", operation="add_justification",
            agent_id="a1", timestamp="2026-01-01",
            justification=j, conclusion_status=True,
        )
        assert r.conclusion_status is True

    def test_explain_belief_response(self):
        r = ExplainBeliefResponse(
            status="success", operation="explain",
            agent_id="a1", timestamp="2026-01-01",
            belief_name="X", current_status=True,
            explanation_text="Supported by A",
        )
        assert r.belief_name == "X"
        assert r.justifications == []

    def test_query_beliefs_response(self):
        r = QueryBeliefsResponse(
            status="success", operation="query",
            agent_id="a1", timestamp="2026-01-01",
            total_beliefs=5, filtered_count=3,
            beliefs=[BeliefInfo(name="A"), BeliefInfo(name="B")],
        )
        assert r.total_beliefs == 5
        assert len(r.beliefs) == 2


# ── JTMSStatistics ──

class TestJTMSStatistics:
    def test_defaults(self):
        s = JTMSStatistics()
        assert s.total_beliefs == 0
        assert s.valid_beliefs == 0
        assert s.unknown_beliefs == 0
        assert s.non_monotonic_beliefs == 0

    def test_custom(self):
        s = JTMSStatistics(
            total_beliefs=10, valid_beliefs=5, invalid_beliefs=2,
            unknown_beliefs=3, non_monotonic_beliefs=1,
            total_justifications=7,
        )
        assert s.total_beliefs == 10
        assert s.total_justifications == 7


# ── SessionInfo ──

class TestSessionInfo:
    def test_all_fields(self):
        s = SessionInfo(
            session_id="s1", agent_id="a1", session_name="Test Session",
            created_at="2026-01-01", last_accessed="2026-01-02",
            checkpoint_count=3,
        )
        assert s.session_id == "s1"
        assert s.checkpoint_count == 3


# ── GetJTMSStateResponse ──

class TestGetJTMSStateResponse:
    def test_minimal(self):
        r = GetJTMSStateResponse(
            status="success", operation="get_state",
            agent_id="a1", timestamp="2026-01-01",
        )
        assert r.beliefs == {}
        assert r.justifications_graph is None
        assert r.statistics is None

    def test_with_stats(self):
        stats = JTMSStatistics(total_beliefs=5)
        r = GetJTMSStateResponse(
            status="success", operation="get_state",
            agent_id="a1", timestamp="2026-01-01",
            statistics=stats,
        )
        assert r.statistics.total_beliefs == 5


# ── SetBeliefValidityResponse ──

class TestSetBeliefValidityResponse:
    def test_all_fields(self):
        r = SetBeliefValidityResponse(
            status="success", operation="set_validity",
            agent_id="a1", timestamp="2026-01-01",
            belief_name="A", old_value=None, new_value=True,
            propagation_occurred=True,
        )
        assert r.belief_name == "A"
        assert r.old_value is None
        assert r.new_value is True


# ── Session Responses ──

class TestSessionResponses:
    def test_create_session_response(self):
        r = CreateSessionResponse(
            session_id="s1", agent_id="a1",
            session_name="Test", created_at="2026-01-01",
        )
        assert r.status == "success"

    def test_session_list_response(self):
        r = SessionListResponse(total_count=0)
        assert r.sessions == []
        assert r.agent_filter is None

    def test_checkpoint_info(self):
        c = CheckpointInfo(
            checkpoint_id="c1", session_id="s1",
            created_at="2026-01-01", description="Before change",
        )
        assert c.auto_generated is False
        assert c.session_version == 1

    def test_create_checkpoint_response(self):
        r = CreateCheckpointResponse(
            checkpoint_id="c1", session_id="s1",
            description="Test", created_at="2026-01-01",
        )
        assert r.status == "success"

    def test_restore_checkpoint_response(self):
        r = RestoreCheckpointResponse(
            session_id="s1", checkpoint_id="c1",
            restored_at="2026-01-01",
        )
        assert r.instances_restored == 0


# ── JTMSError ──

class TestJTMSError:
    def test_required(self):
        e = JTMSError(
            error_type="validation", error_message="Invalid input",
            timestamp="2026-01-01",
        )
        assert e.error_type == "validation"
        assert e.error_details is None

    def test_with_details(self):
        e = JTMSError(
            error_type="not_found", error_message="Belief not found",
            error_details={"belief_name": "X"},
            operation="explain", session_id="s1",
            timestamp="2026-01-01",
        )
        assert e.error_details["belief_name"] == "X"


# ── Import/Export ──

class TestImportExport:
    def test_export_request_defaults(self):
        r = ExportJTMSRequest()
        assert r.format == "json"
        assert r.agent_id == "api_client"

    def test_import_request(self):
        r = ImportJTMSRequest(
            session_id="s1", state_data='{"beliefs": []}',
        )
        assert r.format == "json"

    def test_export_response(self):
        r = ExportJTMSResponse(
            instance_id="i1", format="json",
            exported_data='{}', export_timestamp="2026-01-01",
        )
        assert r.status == "success"

    def test_import_response(self):
        r = ImportJTMSResponse(
            session_id="s1", new_instance_id="i2",
            format="json", beliefs_imported=5,
            justifications_imported=3, import_timestamp="2026-01-01",
        )
        assert r.beliefs_imported == 5


# ── PluginStatusResponse ──

class TestPluginStatusResponse:
    def test_all_fields(self):
        r = PluginStatusResponse(
            plugin_name="JTMSPlugin",
            semantic_kernel_available=True,
            functions_count=5,
            functions=["create_belief", "add_justification", "query", "explain", "export"],
            jtms_service_active=True,
            session_manager_active=True,
        )
        assert r.plugin_name == "JTMSPlugin"
        assert len(r.functions) == 5
        assert r.default_session_id is None


# ── Serialization ──

class TestSerialization:
    def test_belief_info_dict(self):
        b = BeliefInfo(name="A", valid=True)
        d = b.model_dump()
        assert d["name"] == "A"
        assert d["valid"] is True

    def test_response_json(self):
        r = JTMSResponse(
            status="success", operation="test",
            agent_id="a1", timestamp="2026-01-01",
        )
        j = r.model_dump_json()
        assert "success" in j

    def test_statistics_dict(self):
        s = JTMSStatistics(total_beliefs=10, valid_beliefs=5)
        d = s.model_dump()
        assert d["total_beliefs"] == 10
        assert d["valid_beliefs"] == 5
