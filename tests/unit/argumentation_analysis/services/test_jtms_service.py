# tests/unit/argumentation_analysis/services/test_jtms_service.py
"""Tests for JTMSService — high-level JTMS management with sessions."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.services.jtms_service import JTMSService


@pytest.fixture
def service():
    return JTMSService()


@pytest.fixture
async def service_with_instance(service):
    """Service with one instance already created."""
    instance_id = await service.create_jtms_instance("test_session")
    return service, instance_id


# ── __init__ ──

class TestInit:
    def test_initial_state(self, service):
        assert service.instances == {}
        assert service.metadata == {}
        assert service.session_manager is None


# ── create_jtms_instance ──

class TestCreateJTMSInstance:
    @pytest.mark.asyncio
    async def test_creates_instance(self, service):
        iid = await service.create_jtms_instance("s1")
        assert iid.startswith("jtms_s1_")
        assert iid in service.instances
        assert iid in service.metadata

    @pytest.mark.asyncio
    async def test_metadata_populated(self, service):
        iid = await service.create_jtms_instance("s1", strict_mode=True)
        meta = service.metadata[iid]
        assert meta["session_id"] == "s1"
        assert meta["strict_mode"] is True
        assert meta["beliefs_count"] == 0
        assert meta["justifications_count"] == 0
        assert "created_at" in meta

    @pytest.mark.asyncio
    async def test_multiple_instances_independent(self, service):
        id1 = await service.create_jtms_instance("s1")
        id2 = await service.create_jtms_instance("s1")
        assert id1 != id2
        assert len(service.instances) == 2


# ── create_belief ──

class TestCreateBelief:
    @pytest.mark.asyncio
    async def test_creates_belief(self, service):
        iid = await service.create_jtms_instance("s1")
        result = await service.create_belief(iid, "rain")
        assert result["name"] == "rain"
        assert result["justifications_count"] == 0

    @pytest.mark.asyncio
    async def test_with_initial_value_true(self, service):
        iid = await service.create_jtms_instance("s1")
        result = await service.create_belief(iid, "sun", initial_value=True)
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_with_initial_value_false(self, service):
        iid = await service.create_jtms_instance("s1")
        result = await service.create_belief(iid, "snow", initial_value=False)
        assert result["valid"] is False

    @pytest.mark.asyncio
    async def test_without_initial_value(self, service):
        iid = await service.create_jtms_instance("s1")
        result = await service.create_belief(iid, "wind")
        assert result["valid"] is None

    @pytest.mark.asyncio
    async def test_updates_metadata_count(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "a")
        await service.create_belief(iid, "b")
        assert service.metadata[iid]["beliefs_count"] == 2

    @pytest.mark.asyncio
    async def test_invalid_instance_raises(self, service):
        with pytest.raises(ValueError, match="non trouvée"):
            await service.create_belief("bad_id", "x")


# ── add_justification ──

class TestAddJustification:
    @pytest.mark.asyncio
    async def test_adds_justification(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "rain")
        await service.create_belief(iid, "wet", initial_value=False)
        result = await service.add_justification(iid, ["rain"], [], "wet")
        assert result["conclusion"] == "wet"
        assert result["in_beliefs"] == ["rain"]
        assert result["out_beliefs"] == []

    @pytest.mark.asyncio
    async def test_propagation_with_valid_premises(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "A", initial_value=True)
        await service.create_belief(iid, "B")
        result = await service.add_justification(iid, ["A"], [], "B")
        # A is valid, so B should be propagated to valid
        assert result["conclusion_status"] is True

    @pytest.mark.asyncio
    async def test_with_out_beliefs(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "bird", initial_value=True)
        await service.create_belief(iid, "abnormal")
        await service.create_belief(iid, "flies")
        result = await service.add_justification(iid, ["bird"], ["abnormal"], "flies")
        assert result["conclusion"] == "flies"
        # bird=True, abnormal=None (not valid) → flies should be valid
        assert result["conclusion_status"] is True

    @pytest.mark.asyncio
    async def test_updates_metadata(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "X", initial_value=True)
        await service.create_belief(iid, "Y")
        await service.add_justification(iid, ["X"], [], "Y")
        assert service.metadata[iid]["justifications_count"] >= 1

    @pytest.mark.asyncio
    async def test_invalid_instance_raises(self, service):
        with pytest.raises(ValueError, match="non trouvée"):
            await service.add_justification("bad", ["a"], [], "b")


# ── explain_belief ──

class TestExplainBelief:
    @pytest.mark.asyncio
    async def test_explains_belief_no_justifications(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "lonely")
        result = await service.explain_belief(iid, "lonely")
        assert result["belief_name"] == "lonely"
        assert result["justifications"] == []
        assert "explanation_text" in result

    @pytest.mark.asyncio
    async def test_explains_belief_with_justification(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "A", initial_value=True)
        await service.create_belief(iid, "B")
        await service.add_justification(iid, ["A"], [], "B")
        result = await service.explain_belief(iid, "B")
        assert len(result["justifications"]) >= 1
        assert result["current_status"] is True

    @pytest.mark.asyncio
    async def test_invalid_instance_raises(self, service):
        with pytest.raises(ValueError, match="Instance JTMS non trouvée"):
            await service.explain_belief("bad", "x")

    @pytest.mark.asyncio
    async def test_invalid_belief_raises(self, service):
        iid = await service.create_jtms_instance("s1")
        with pytest.raises(ValueError, match="Croyance non trouvée"):
            await service.explain_belief(iid, "nonexistent")


# ── query_beliefs ──

class TestQueryBeliefs:
    @pytest.mark.asyncio
    async def test_query_all(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "A", initial_value=True)
        await service.create_belief(iid, "B", initial_value=False)
        await service.create_belief(iid, "C")
        result = await service.query_beliefs(iid)
        assert result["total_beliefs"] == 3
        assert result["filtered_count"] == 3
        assert result["filter_applied"] is None

    @pytest.mark.asyncio
    async def test_filter_valid(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "A", initial_value=True)
        await service.create_belief(iid, "B", initial_value=False)
        result = await service.query_beliefs(iid, filter_status="valid")
        assert result["filtered_count"] == 1
        assert result["beliefs"][0]["name"] == "A"

    @pytest.mark.asyncio
    async def test_filter_invalid(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "A", initial_value=True)
        await service.create_belief(iid, "B", initial_value=False)
        result = await service.query_beliefs(iid, filter_status="invalid")
        assert result["filtered_count"] == 1
        assert result["beliefs"][0]["name"] == "B"

    @pytest.mark.asyncio
    async def test_filter_unknown(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "mystery")
        result = await service.query_beliefs(iid, filter_status="unknown")
        assert result["filtered_count"] == 1

    @pytest.mark.asyncio
    async def test_filter_non_monotonic(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "X", initial_value=True)
        result = await service.query_beliefs(iid, filter_status="non_monotonic")
        # no non-monotonic beliefs expected
        assert result["filtered_count"] == 0

    @pytest.mark.asyncio
    async def test_invalid_instance_raises(self, service):
        with pytest.raises(ValueError):
            await service.query_beliefs("bad")


# ── get_jtms_state ──

class TestGetJTMSState:
    @pytest.mark.asyncio
    async def test_empty_state(self, service):
        iid = await service.create_jtms_instance("s1")
        state = await service.get_jtms_state(iid)
        assert state["instance_id"] == iid
        assert state["beliefs"] == {}
        assert state["statistics"]["total_beliefs"] == 0

    @pytest.mark.asyncio
    async def test_state_with_beliefs(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "P", initial_value=True)
        await service.create_belief(iid, "Q")
        await service.add_justification(iid, ["P"], [], "Q")
        state = await service.get_jtms_state(iid)
        assert state["statistics"]["total_beliefs"] == 2
        assert state["statistics"]["valid_beliefs"] == 2
        assert len(state["justifications_graph"]) >= 1

    @pytest.mark.asyncio
    async def test_statistics_breakdown(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "A", initial_value=True)
        await service.create_belief(iid, "B", initial_value=False)
        await service.create_belief(iid, "C")
        state = await service.get_jtms_state(iid)
        stats = state["statistics"]
        assert stats["valid_beliefs"] == 1
        assert stats["invalid_beliefs"] == 1
        assert stats["unknown_beliefs"] == 1

    @pytest.mark.asyncio
    async def test_invalid_instance_raises(self, service):
        with pytest.raises(ValueError):
            await service.get_jtms_state("bad")


# ── set_belief_validity ──

class TestSetBeliefValidity:
    @pytest.mark.asyncio
    async def test_changes_validity(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "X")
        result = await service.set_belief_validity(iid, "X", True)
        assert result["old_value"] is None
        assert result["new_value"] is True
        assert result["propagation_occurred"] is True

    @pytest.mark.asyncio
    async def test_invalid_instance_raises(self, service):
        with pytest.raises(ValueError, match="Instance"):
            await service.set_belief_validity("bad", "X", True)

    @pytest.mark.asyncio
    async def test_invalid_belief_raises(self, service):
        iid = await service.create_jtms_instance("s1")
        with pytest.raises(ValueError, match="Croyance"):
            await service.set_belief_validity(iid, "nonexistent", True)


# ── remove_belief ──

class TestRemoveBelief:
    @pytest.mark.asyncio
    async def test_removes_belief(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "temp")
        result = await service.remove_belief(iid, "temp")
        assert result["removed"] is True
        assert result["remaining_beliefs"] == 0

    @pytest.mark.asyncio
    async def test_metadata_updated(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "a")
        await service.create_belief(iid, "b")
        await service.remove_belief(iid, "a")
        assert service.metadata[iid]["beliefs_count"] == 1

    @pytest.mark.asyncio
    async def test_invalid_instance_raises(self, service):
        with pytest.raises(ValueError, match="Instance"):
            await service.remove_belief("bad", "x")

    @pytest.mark.asyncio
    async def test_nonexistent_belief_raises(self, service):
        iid = await service.create_jtms_instance("s1")
        with pytest.raises(ValueError, match="Croyance"):
            await service.remove_belief(iid, "ghost")


# ── export_jtms_state ──

class TestExportJTMSState:
    @pytest.mark.asyncio
    async def test_export_json(self, service):
        iid = await service.create_jtms_instance("s1")
        await service.create_belief(iid, "A", initial_value=True)
        exported = await service.export_jtms_state(iid, format="json")
        data = json.loads(exported)
        assert data["instance_id"] == iid
        assert "A" in data["beliefs"]

    @pytest.mark.asyncio
    async def test_export_graphml_not_implemented(self, service):
        iid = await service.create_jtms_instance("s1")
        with pytest.raises(NotImplementedError):
            await service.export_jtms_state(iid, format="graphml")

    @pytest.mark.asyncio
    async def test_export_dot_not_implemented(self, service):
        iid = await service.create_jtms_instance("s1")
        with pytest.raises(NotImplementedError):
            await service.export_jtms_state(iid, format="dot")

    @pytest.mark.asyncio
    async def test_export_unknown_format_raises(self, service):
        iid = await service.create_jtms_instance("s1")
        with pytest.raises(ValueError, match="Format non supporté"):
            await service.export_jtms_state(iid, format="xml")


# ── import_jtms_state ──

class TestImportJTMSState:
    @pytest.mark.asyncio
    async def test_roundtrip_export_import(self, service):
        # Create and populate
        iid1 = await service.create_jtms_instance("s1")
        await service.create_belief(iid1, "P", initial_value=True)
        await service.create_belief(iid1, "Q")
        await service.add_justification(iid1, ["P"], [], "Q")

        # Export
        exported = await service.export_jtms_state(iid1)

        # Import into new session
        iid2 = await service.import_jtms_state("s2", exported)
        assert iid2 != iid1
        assert iid2 in service.instances

        # Verify imported state
        state = await service.get_jtms_state(iid2)
        assert "P" in state["beliefs"]
        assert "Q" in state["beliefs"]

    @pytest.mark.asyncio
    async def test_import_invalid_json_raises(self, service):
        with pytest.raises(ValueError, match="JSON invalides"):
            await service.import_jtms_state("s1", "not json {{{")

    @pytest.mark.asyncio
    async def test_import_unsupported_format_raises(self, service):
        with pytest.raises(ValueError, match="Format d'import"):
            await service.import_jtms_state("s1", "{}", format="xml")

    @pytest.mark.asyncio
    async def test_import_empty_state(self, service):
        data = json.dumps({"beliefs": {}})
        iid = await service.import_jtms_state("s1", data)
        state = await service.get_jtms_state(iid)
        assert state["statistics"]["total_beliefs"] == 0


# ── get_instance_ids ──

class TestGetInstanceIds:
    @pytest.mark.asyncio
    async def test_no_instances(self, service):
        ids = await service.get_instance_ids()
        assert ids == []

    @pytest.mark.asyncio
    async def test_all_instances(self, service):
        await service.create_jtms_instance("s1")
        await service.create_jtms_instance("s2")
        ids = await service.get_instance_ids()
        assert len(ids) == 2

    @pytest.mark.asyncio
    async def test_filter_by_session(self, service):
        await service.create_jtms_instance("s1")
        await service.create_jtms_instance("s2")
        await service.create_jtms_instance("s1")
        ids = await service.get_instance_ids(session_id="s1")
        assert len(ids) == 2


# ── cleanup_instance ──

class TestCleanupInstance:
    @pytest.mark.asyncio
    async def test_cleanup_existing(self, service):
        iid = await service.create_jtms_instance("s1")
        result = await service.cleanup_instance(iid)
        assert result is True
        assert iid not in service.instances
        assert iid not in service.metadata

    @pytest.mark.asyncio
    async def test_cleanup_nonexistent(self, service):
        result = await service.cleanup_instance("nonexistent")
        assert result is True


# ── Integration ──

class TestJTMSServiceIntegration:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, service):
        """End-to-end: create instance, add beliefs+justifications, query, remove, cleanup."""
        iid = await service.create_jtms_instance("integration", strict_mode=False)

        await service.create_belief(iid, "premise1", initial_value=True)
        await service.create_belief(iid, "premise2", initial_value=True)
        await service.create_belief(iid, "conclusion")

        await service.add_justification(iid, ["premise1", "premise2"], [], "conclusion")

        result = await service.query_beliefs(iid, filter_status="valid")
        assert result["filtered_count"] == 3  # all valid after propagation

        explanation = await service.explain_belief(iid, "conclusion")
        assert explanation["current_status"] is True
        assert len(explanation["justifications"]) >= 1

        await service.remove_belief(iid, "premise1")
        state = await service.get_jtms_state(iid)
        assert state["statistics"]["total_beliefs"] == 2

        await service.cleanup_instance(iid)
        assert len(service.instances) == 0

    @pytest.mark.asyncio
    async def test_non_monotonic_reasoning(self, service):
        """Default reasoning with out-beliefs."""
        iid = await service.create_jtms_instance("nm")
        await service.create_belief(iid, "bird", initial_value=True)
        await service.create_belief(iid, "abnormal")
        await service.create_belief(iid, "flies")

        # Default: birds fly unless abnormal
        await service.add_justification(iid, ["bird"], ["abnormal"], "flies")

        q = await service.query_beliefs(iid, filter_status="valid")
        valid_names = [b["name"] for b in q["beliefs"]]
        assert "flies" in valid_names

        # Now abnormal becomes valid → flies should retract
        await service.set_belief_validity(iid, "abnormal", True)
        q2 = await service.query_beliefs(iid, filter_status="valid")
        valid_names2 = [b["name"] for b in q2["beliefs"]]
        assert "flies" not in valid_names2
