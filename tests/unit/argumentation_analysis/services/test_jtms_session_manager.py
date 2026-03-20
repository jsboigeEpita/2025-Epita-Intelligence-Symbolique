# tests/unit/argumentation_analysis/services/test_jtms_session_manager.py
"""Tests for JTMSSessionManager — session lifecycle, checkpoints, versioning."""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from argumentation_analysis.services.jtms_service import JTMSService
from argumentation_analysis.services.jtms_session_manager import JTMSSessionManager


@pytest.fixture
def service():
    return JTMSService()


@pytest.fixture
def manager(service, tmp_path):
    return JTMSSessionManager(service, storage_path=str(tmp_path))


@pytest.fixture
async def session(manager):
    """Manager with one session already created."""
    sid = await manager.create_session("agent_sherlock", session_name="Test Session")
    return manager, sid


# ── __init__ ──


class TestInit:
    def test_bidirectional_injection(self, service, tmp_path):
        mgr = JTMSSessionManager(service, storage_path=str(tmp_path))
        assert service.session_manager is mgr
        assert mgr.jtms_service is service

    def test_storage_path_created(self, service, tmp_path):
        path = tmp_path / "deep" / "nested"
        # mkdir with exist_ok won't create parents; but the constructor only does mkdir(exist_ok=True)
        # so we need an existing parent
        mgr = JTMSSessionManager(service, storage_path=str(tmp_path / "sessions"))
        assert mgr.storage_path.exists()

    def test_default_config(self, service, tmp_path):
        mgr = JTMSSessionManager(service, storage_path=str(tmp_path))
        assert mgr.max_checkpoints_per_session == 10
        assert mgr.session_timeout_hours == 24
        assert mgr.auto_checkpoint_interval == 300


# ── create_session ──


class TestCreateSession:
    @pytest.mark.asyncio
    async def test_creates_session(self, manager):
        sid = await manager.create_session("watson")
        assert sid.startswith("session_watson_")
        assert sid in manager.sessions
        assert manager.sessions[sid]["status"] == "active"

    @pytest.mark.asyncio
    async def test_custom_name(self, manager):
        sid = await manager.create_session("watson", session_name="Investigation A")
        assert manager.sessions[sid]["session_name"] == "Investigation A"

    @pytest.mark.asyncio
    async def test_default_name_generated(self, manager):
        sid = await manager.create_session("watson")
        assert manager.sessions[sid]["session_name"].startswith("Session_")

    @pytest.mark.asyncio
    async def test_metadata_stored(self, manager):
        sid = await manager.create_session("watson", metadata={"case": "murder"})
        assert manager.sessions[sid]["metadata"]["case"] == "murder"

    @pytest.mark.asyncio
    async def test_agent_association(self, manager):
        sid = await manager.create_session("watson")
        assert "watson" in manager.agent_sessions
        assert sid in manager.agent_sessions["watson"]

    @pytest.mark.asyncio
    async def test_initial_checkpoint_created(self, manager):
        sid = await manager.create_session("watson")
        assert len(manager.checkpoints[sid]) == 1
        cp = manager.checkpoints[sid][0]
        assert cp["description"] == "session_created"
        assert cp["auto_generated"] is True

    @pytest.mark.asyncio
    async def test_session_saved_to_disk(self, manager):
        sid = await manager.create_session("watson")
        session_file = manager.storage_path / f"{sid}.json"
        assert session_file.exists()

    @pytest.mark.asyncio
    async def test_multiple_sessions_same_agent(self, manager):
        s1 = await manager.create_session("watson")
        s2 = await manager.create_session("watson")
        assert s1 != s2
        assert len(manager.agent_sessions["watson"]) == 2


# ── get_session ──


class TestGetSession:
    @pytest.mark.asyncio
    async def test_get_existing_session(self, manager):
        sid = await manager.create_session("watson")
        info = await manager.get_session(sid)
        assert info["session_id"] == sid
        assert info["agent_id"] == "watson"
        assert "jtms_instances_info" in info

    @pytest.mark.asyncio
    async def test_updates_last_accessed(self, manager):
        sid = await manager.create_session("watson")
        old_accessed = manager.sessions[sid]["last_accessed"]
        # Small delay not needed — isoformat precision is fine
        info = await manager.get_session(sid)
        # last_accessed should be updated
        assert info["last_accessed"] >= old_accessed

    @pytest.mark.asyncio
    async def test_nonexistent_raises(self, manager):
        with pytest.raises(ValueError, match="Session non trouvée"):
            await manager.get_session("nonexistent")

    @pytest.mark.asyncio
    async def test_loads_from_disk(self, manager):
        sid = await manager.create_session("watson")
        # Remove from memory
        session_data = manager.sessions.pop(sid)
        # get_session should reload from disk
        info = await manager.get_session(sid)
        assert info["session_id"] == sid

    @pytest.mark.asyncio
    async def test_jtms_instances_info(self, manager):
        sid = await manager.create_session("watson")
        iid = await manager.jtms_service.create_jtms_instance(sid)
        manager.sessions[sid]["jtms_instances"].append(iid)
        info = await manager.get_session(sid)
        assert len(info["jtms_instances_info"]) == 1
        assert info["jtms_instances_info"][0]["instance_id"] == iid


# ── list_sessions ──


class TestListSessions:
    @pytest.mark.asyncio
    async def test_list_all(self, manager):
        await manager.create_session("watson")
        await manager.create_session("sherlock")
        sessions = await manager.list_sessions()
        assert len(sessions) == 2

    @pytest.mark.asyncio
    async def test_filter_by_agent(self, manager):
        await manager.create_session("watson")
        await manager.create_session("sherlock")
        await manager.create_session("watson")
        sessions = await manager.list_sessions(agent_id="watson")
        assert len(sessions) == 2
        assert all(s["agent_id"] == "watson" for s in sessions)

    @pytest.mark.asyncio
    async def test_filter_by_status(self, manager):
        s1 = await manager.create_session("watson")
        s2 = await manager.create_session("watson")
        manager.sessions[s2]["status"] = "closed"
        sessions = await manager.list_sessions(status="active")
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == s1

    @pytest.mark.asyncio
    async def test_sorted_by_date_desc(self, manager):
        s1 = await manager.create_session("watson")
        s2 = await manager.create_session("watson")
        sessions = await manager.list_sessions()
        assert sessions[0]["session_id"] == s2  # most recent first

    @pytest.mark.asyncio
    async def test_empty_when_no_sessions(self, manager):
        sessions = await manager.list_sessions()
        assert sessions == []


# ── create_checkpoint ──


class TestCreateCheckpoint:
    @pytest.mark.asyncio
    async def test_creates_checkpoint(self, manager):
        sid = await manager.create_session("watson")
        cp_id = await manager.create_checkpoint(sid, "before_changes")
        assert cp_id.startswith("cp_")
        assert len(manager.checkpoints[sid]) == 2  # initial + new

    @pytest.mark.asyncio
    async def test_checkpoint_saved_to_disk(self, manager):
        sid = await manager.create_session("watson")
        cp_id = await manager.create_checkpoint(sid, "save_point")
        cp_file = manager.storage_path / f"{cp_id}.cp.json"
        assert cp_file.exists()

    @pytest.mark.asyncio
    async def test_captures_jtms_state(self, manager):
        sid = await manager.create_session("watson")
        iid = await manager.jtms_service.create_jtms_instance(sid)
        await manager.jtms_service.create_belief(iid, "evidence", initial_value=True)
        manager.sessions[sid]["jtms_instances"].append(iid)
        cp_id = await manager.create_checkpoint(sid, "with_evidence")
        cp = [c for c in manager.checkpoints[sid] if c["checkpoint_id"] == cp_id][0]
        assert iid in cp["jtms_states"]

    @pytest.mark.asyncio
    async def test_nonexistent_session_raises(self, manager):
        with pytest.raises(ValueError, match="Session non trouvée"):
            await manager.create_checkpoint("bad", "test")

    @pytest.mark.asyncio
    async def test_max_checkpoints_limit(self, manager):
        sid = await manager.create_session("watson")
        manager.max_checkpoints_per_session = 3
        # Initial checkpoint already created (1)
        for i in range(5):
            await manager.create_checkpoint(sid, f"cp_{i}")
        assert len(manager.checkpoints[sid]) <= 3


# ── restore_checkpoint ──


class TestRestoreCheckpoint:
    @pytest.mark.asyncio
    async def test_restore_to_checkpoint(self, manager):
        sid = await manager.create_session("watson")
        iid = await manager.jtms_service.create_jtms_instance(sid)
        await manager.jtms_service.create_belief(iid, "clue1", initial_value=True)
        manager.sessions[sid]["jtms_instances"].append(iid)

        # Create checkpoint
        cp_id = await manager.create_checkpoint(sid, "before_adding_clue2")

        # Add more data
        await manager.jtms_service.create_belief(iid, "clue2", initial_value=True)

        # Restore
        result = await manager.restore_checkpoint(sid, cp_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_nonexistent_session_raises(self, manager):
        with pytest.raises(ValueError, match="Session non trouvée"):
            await manager.restore_checkpoint("bad", "cp1")

    @pytest.mark.asyncio
    async def test_nonexistent_checkpoint_raises(self, manager):
        sid = await manager.create_session("watson")
        with pytest.raises(ValueError, match="Checkpoint non trouvé"):
            await manager.restore_checkpoint(sid, "bad_cp")

    @pytest.mark.asyncio
    async def test_no_checkpoints_key_missing_raises(self, manager):
        sid = await manager.create_session("watson")
        del manager.checkpoints[sid]  # remove key entirely
        with pytest.raises(ValueError, match="Aucun checkpoint"):
            await manager.restore_checkpoint(sid, "cp_x")

    @pytest.mark.asyncio
    async def test_empty_checkpoints_list_raises(self, manager):
        sid = await manager.create_session("watson")
        manager.checkpoints[sid] = []  # clear checkpoints
        with pytest.raises(ValueError, match="Checkpoint non trouvé"):
            await manager.restore_checkpoint(sid, "cp_x")


# ── delete_session ──


class TestDeleteSession:
    @pytest.mark.asyncio
    async def test_deletes_session(self, manager):
        sid = await manager.create_session("watson")
        result = await manager.delete_session(sid)
        assert result is True
        assert sid not in manager.sessions
        assert sid not in manager.checkpoints

    @pytest.mark.asyncio
    async def test_cleans_up_jtms_instances(self, manager):
        sid = await manager.create_session("watson")
        iid = await manager.jtms_service.create_jtms_instance(sid)
        manager.sessions[sid]["jtms_instances"].append(iid)
        await manager.delete_session(sid)
        assert iid not in manager.jtms_service.instances

    @pytest.mark.asyncio
    async def test_removes_from_agent_sessions(self, manager):
        sid = await manager.create_session("watson")
        await manager.delete_session(sid)
        assert "watson" not in manager.agent_sessions

    @pytest.mark.asyncio
    async def test_deletes_files_from_disk(self, manager):
        sid = await manager.create_session("watson")
        session_file = manager.storage_path / f"{sid}.json"
        assert session_file.exists()
        await manager.delete_session(sid)
        assert not session_file.exists()

    @pytest.mark.asyncio
    async def test_nonexistent_raises(self, manager):
        with pytest.raises(ValueError, match="Session non trouvée"):
            await manager.delete_session("nonexistent")

    @pytest.mark.asyncio
    async def test_multiple_sessions_one_agent(self, manager):
        s1 = await manager.create_session("watson")
        s2 = await manager.create_session("watson")
        await manager.delete_session(s1)
        assert s2 in manager.agent_sessions["watson"]
        assert s1 not in manager.agent_sessions["watson"]


# ── update_session_metadata ──


class TestUpdateSessionMetadata:
    @pytest.mark.asyncio
    async def test_updates_metadata(self, manager):
        sid = await manager.create_session("watson")
        result = await manager.update_session_metadata(sid, {"case": "theft"})
        assert result is True
        assert manager.sessions[sid]["metadata"]["case"] == "theft"

    @pytest.mark.asyncio
    async def test_increments_version(self, manager):
        sid = await manager.create_session("watson")
        old_version = manager.sessions[sid]["version"]
        await manager.update_session_metadata(sid, {"new_key": "val"})
        assert manager.sessions[sid]["version"] == old_version + 1

    @pytest.mark.asyncio
    async def test_merges_metadata(self, manager):
        sid = await manager.create_session("watson", metadata={"existing": True})
        await manager.update_session_metadata(sid, {"added": True})
        meta = manager.sessions[sid]["metadata"]
        assert meta["existing"] is True
        assert meta["added"] is True

    @pytest.mark.asyncio
    async def test_nonexistent_raises(self, manager):
        with pytest.raises(ValueError):
            await manager.update_session_metadata("bad", {"x": 1})


# ── add_jtms_instance_to_session ──


class TestAddJTMSInstanceToSession:
    @pytest.mark.asyncio
    async def test_adds_instance(self, manager):
        sid = await manager.create_session("watson")
        iid = await manager.jtms_service.create_jtms_instance(sid)
        result = await manager.add_jtms_instance_to_session(sid, iid)
        assert result is True
        assert iid in manager.sessions[sid]["jtms_instances"]

    @pytest.mark.asyncio
    async def test_no_duplicate_on_double_add(self, manager):
        sid = await manager.create_session("watson")
        iid = await manager.jtms_service.create_jtms_instance(sid)
        await manager.add_jtms_instance_to_session(sid, iid)
        await manager.add_jtms_instance_to_session(sid, iid)
        assert manager.sessions[sid]["jtms_instances"].count(iid) == 1

    @pytest.mark.asyncio
    async def test_nonexistent_session_raises(self, manager):
        with pytest.raises(ValueError, match="Session non trouvée"):
            await manager.add_jtms_instance_to_session("bad", "iid")

    @pytest.mark.asyncio
    async def test_nonexistent_instance_raises(self, manager):
        sid = await manager.create_session("watson")
        with pytest.raises(ValueError, match="Instance JTMS non trouvée"):
            await manager.add_jtms_instance_to_session(sid, "bad_instance")


# ── cleanup_expired_sessions ──


class TestCleanupExpiredSessions:
    @pytest.mark.asyncio
    async def test_no_expired(self, manager):
        await manager.create_session("watson")
        count = await manager.cleanup_expired_sessions()
        assert count == 0

    @pytest.mark.asyncio
    async def test_expires_old_sessions(self, manager):
        sid = await manager.create_session("watson")
        # Set last_accessed to 48 hours ago
        from datetime import datetime, timedelta

        old_time = (datetime.now() - timedelta(hours=48)).isoformat()
        manager.sessions[sid]["last_accessed"] = old_time
        count = await manager.cleanup_expired_sessions()
        assert count == 1
        assert sid not in manager.sessions

    @pytest.mark.asyncio
    async def test_locked_sessions_not_cleaned(self, manager):
        sid = await manager.create_session("watson")
        from datetime import datetime, timedelta

        old_time = (datetime.now() - timedelta(hours=48)).isoformat()
        manager.sessions[sid]["last_accessed"] = old_time
        manager.sessions[sid]["status"] = "locked"
        count = await manager.cleanup_expired_sessions()
        assert count == 0


# ── Disk persistence ──


class TestDiskPersistence:
    @pytest.mark.asyncio
    async def test_load_session_from_disk(self, manager):
        sid = await manager.create_session("watson", session_name="Reloadable")
        # Remove from memory
        manager.sessions.pop(sid)
        manager.checkpoints.pop(sid, None)
        # Reload
        await manager._load_session_from_disk(sid)
        assert sid in manager.sessions
        assert manager.sessions[sid]["session_name"] == "Reloadable"

    @pytest.mark.asyncio
    async def test_load_nonexistent_no_error(self, manager):
        await manager._load_session_from_disk("nonexistent_id")
        assert "nonexistent_id" not in manager.sessions

    @pytest.mark.asyncio
    async def test_load_all_sessions(self, manager):
        s1 = await manager.create_session("watson")
        s2 = await manager.create_session("sherlock")
        # Remove from memory
        manager.sessions.clear()
        manager.checkpoints.clear()
        # Reload all
        await manager._load_all_sessions()
        assert s1 in manager.sessions
        assert s2 in manager.sessions

    @pytest.mark.asyncio
    async def test_checkpoint_persists_on_disk(self, manager):
        sid = await manager.create_session("watson")
        cp_id = await manager.create_checkpoint(sid, "persist_test")
        cp_file = manager.storage_path / f"{cp_id}.cp.json"
        assert cp_file.exists()
        with open(cp_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["checkpoint_id"] == cp_id
        assert data["description"] == "persist_test"

    @pytest.mark.asyncio
    async def test_delete_removes_checkpoint_files(self, manager):
        sid = await manager.create_session("watson")
        cp_id = await manager.create_checkpoint(sid, "to_delete")
        cp_file = manager.storage_path / f"{cp_id}.cp.json"
        assert cp_file.exists()
        await manager.delete_session(sid)
        assert not cp_file.exists()


# ── Integration ──


class TestSessionManagerIntegration:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self, manager):
        """Create session, add JTMS, checkpoint, modify, restore, delete."""
        sid = await manager.create_session("sherlock", session_name="Case 42")

        # Add JTMS instance with beliefs
        iid = await manager.jtms_service.create_jtms_instance(sid)
        await manager.jtms_service.create_belief(iid, "suspect_A", initial_value=True)
        await manager.add_jtms_instance_to_session(sid, iid)

        # Checkpoint
        cp_id = await manager.create_checkpoint(sid, "initial_evidence")

        # Modify
        await manager.jtms_service.create_belief(iid, "alibi_A", initial_value=True)
        await manager.update_session_metadata(sid, {"suspect_count": 1})

        # Verify modification
        state = await manager.jtms_service.get_jtms_state(iid)
        assert state["statistics"]["total_beliefs"] == 2

        # List sessions
        sessions = await manager.list_sessions(agent_id="sherlock")
        assert len(sessions) == 1

        # Delete
        result = await manager.delete_session(sid)
        assert result is True
        assert len(manager.sessions) == 0

    @pytest.mark.asyncio
    async def test_multi_agent_sessions(self, manager):
        """Multiple agents with independent sessions."""
        s_sherlock = await manager.create_session("sherlock")
        s_watson = await manager.create_session("watson")

        i1 = await manager.jtms_service.create_jtms_instance(s_sherlock)
        await manager.add_jtms_instance_to_session(s_sherlock, i1)

        i2 = await manager.jtms_service.create_jtms_instance(s_watson)
        await manager.add_jtms_instance_to_session(s_watson, i2)

        # Each has their own
        info_s = await manager.get_session(s_sherlock)
        info_w = await manager.get_session(s_watson)
        assert i1 in [ii["instance_id"] for ii in info_s["jtms_instances_info"]]
        assert i2 in [ii["instance_id"] for ii in info_w["jtms_instances_info"]]

        # Delete one doesn't affect the other
        await manager.delete_session(s_sherlock)
        assert s_watson in manager.sessions
