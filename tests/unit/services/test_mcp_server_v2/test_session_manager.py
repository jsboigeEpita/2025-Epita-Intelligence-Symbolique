"""Tests for the MCP session manager."""

import time
import pytest
from unittest.mock import patch

from argumentation_analysis.services.mcp_server.session_manager import (
    SessionManager,
    SessionState,
)


class TestSessionState:
    """Tests for the SessionState dataclass."""

    def test_creation_defaults(self):
        now = time.time()
        state = SessionState(
            session_id="test-id",
            created_at=now,
            last_accessed=now,
            text="Hello world",
        )
        assert state.session_id == "test-id"
        assert state.text == "Hello world"
        assert state.workflow_name == "standard"
        assert state.conversation_history == []
        assert state.state is None
        assert state.config == {}
        assert state.metadata == {}

    def test_creation_custom(self):
        now = time.time()
        state = SessionState(
            session_id="custom",
            created_at=now,
            last_accessed=now,
            text="Test",
            workflow_name="full",
            config={"max_rounds": 5},
        )
        assert state.workflow_name == "full"
        assert state.config["max_rounds"] == 5


class TestSessionManager:
    """Tests for the SessionManager class."""

    def test_create_session(self):
        sm = SessionManager()
        session = sm.create_session("Test text")
        assert session.text == "Test text"
        assert session.workflow_name == "standard"
        assert len(session.session_id) > 0

    def test_create_session_with_params(self):
        sm = SessionManager()
        session = sm.create_session(
            "Test",
            workflow_name="full",
            config={"max_rounds": 5},
        )
        assert session.workflow_name == "full"
        assert session.config["max_rounds"] == 5

    def test_get_session_valid(self):
        sm = SessionManager()
        session = sm.create_session("Test")
        retrieved = sm.get_session(session.session_id)
        assert retrieved is not None
        assert retrieved.session_id == session.session_id

    def test_get_session_not_found(self):
        sm = SessionManager()
        assert sm.get_session("nonexistent-id") is None

    def test_get_session_expired(self):
        sm = SessionManager(ttl_seconds=1)
        session = sm.create_session("Test")
        # Manually expire
        session.last_accessed = time.time() - 2
        result = sm.get_session(session.session_id)
        assert result is None

    def test_update_session(self):
        sm = SessionManager()
        session = sm.create_session("Test")
        result = sm.update_session(session.session_id, {"round": 1, "status": "ok"})
        assert result is True
        retrieved = sm.get_session(session.session_id)
        assert len(retrieved.conversation_history) == 1
        assert retrieved.conversation_history[0]["round"] == 1

    def test_update_nonexistent_session(self):
        sm = SessionManager()
        result = sm.update_session("nonexistent", {"round": 1})
        assert result is False

    def test_delete_session(self):
        sm = SessionManager()
        session = sm.create_session("Test")
        assert sm.delete_session(session.session_id) is True
        assert sm.get_session(session.session_id) is None

    def test_delete_nonexistent_session(self):
        sm = SessionManager()
        assert sm.delete_session("nonexistent") is False

    def test_list_sessions(self):
        sm = SessionManager()
        sm.create_session("Test 1")
        sm.create_session("Test 2", workflow_name="full")
        sessions = sm.list_sessions()
        assert len(sessions) == 2
        workflows = {s["workflow"] for s in sessions}
        assert "standard" in workflows
        assert "full" in workflows

    def test_list_sessions_excludes_expired(self):
        sm = SessionManager(ttl_seconds=1)
        s1 = sm.create_session("Fresh")
        s2 = sm.create_session("Old")
        s2.last_accessed = time.time() - 2
        sessions = sm.list_sessions()
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == s1.session_id

    def test_max_sessions_eviction(self):
        sm = SessionManager(max_sessions=2)
        s1 = sm.create_session("First")
        s2 = sm.create_session("Second")
        s3 = sm.create_session("Third")
        sessions = sm.list_sessions()
        assert len(sessions) == 2
        session_ids = {s["session_id"] for s in sessions}
        assert s1.session_id not in session_ids
        assert s2.session_id in session_ids
        assert s3.session_id in session_ids

    def test_cleanup_expired(self):
        sm = SessionManager(ttl_seconds=1)
        sm.create_session("Test 1")
        sm.create_session("Test 2")
        # Expire all
        for s in sm._sessions.values():
            s.last_accessed = time.time() - 2
        sm._cleanup_expired()
        assert len(sm._sessions) == 0
