"""Tests for the WebSocket manager.

Validates:
- Connection lifecycle (connect, disconnect, cleanup)
- Message broadcasting to session
- Dead connection handling
- Phase result, debate turn, vote update, JTMS update broadcasts
- Status and error broadcasts
- Singleton manager
- Safe serialization
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.websockets import WebSocketState

from argumentation_analysis.services.websocket_manager import (
    AnalysisWebSocketManager,
    get_websocket_manager,
    _safe_serialize,
)


class FakeWebSocket:
    """Minimal fake WebSocket for testing."""

    def __init__(self, connected=True):
        self.client_state = (
            WebSocketState.CONNECTED if connected else WebSocketState.DISCONNECTED
        )
        self.accepted = False
        self.sent_messages = []
        self.accept = AsyncMock()
        self.send_json = AsyncMock(side_effect=self._record_send)

    async def _record_send(self, msg):
        self.sent_messages.append(msg)


@pytest.fixture
def manager():
    return AnalysisWebSocketManager()


@pytest.fixture
def ws():
    return FakeWebSocket()


# ──── Connection Lifecycle ────


class TestConnectionLifecycle:
    async def test_connect(self, manager, ws):
        await manager.connect("sess-1", ws)
        ws.accept.assert_awaited_once()
        assert manager.get_session_count("sess-1") == 1

    async def test_connect_multiple(self, manager):
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        await manager.connect("sess-1", ws1)
        await manager.connect("sess-1", ws2)
        assert manager.get_session_count("sess-1") == 2

    async def test_disconnect(self, manager, ws):
        await manager.connect("sess-1", ws)
        await manager.disconnect("sess-1", ws)
        assert manager.get_session_count("sess-1") == 0

    async def test_disconnect_last_removes_session(self, manager, ws):
        await manager.connect("sess-1", ws)
        await manager.disconnect("sess-1", ws)
        assert "sess-1" not in manager._connections

    async def test_disconnect_nonexistent(self, manager, ws):
        # Should not raise
        await manager.disconnect("nonexistent", ws)

    async def test_active_sessions(self, manager):
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        await manager.connect("sess-1", ws1)
        await manager.connect("sess-2", ws2)
        sessions = manager.get_active_sessions()
        assert set(sessions) == {"sess-1", "sess-2"}


# ──── Broadcasting ────


class TestBroadcasting:
    async def test_send_to_session(self, manager):
        ws1, ws2 = FakeWebSocket(), FakeWebSocket()
        await manager.connect("sess-1", ws1)
        await manager.connect("sess-1", ws2)

        await manager.broadcast_status("sess-1", "running", "Phase 1")

        assert len(ws1.sent_messages) == 1
        assert ws1.sent_messages[0]["type"] == "status"
        assert ws1.sent_messages[0]["status"] == "running"
        assert len(ws2.sent_messages) == 1

    async def test_send_to_empty_session(self, manager):
        # Should not raise
        await manager.broadcast_status("nonexistent", "ok")

    async def test_dead_connection_cleanup(self, manager):
        ws_alive = FakeWebSocket()
        ws_dead = FakeWebSocket(connected=False)
        await manager.connect("sess-1", ws_alive)
        await manager.connect("sess-1", ws_dead)

        await manager.broadcast_status("sess-1", "test")

        # Dead ws should have been cleaned up
        assert manager.get_session_count("sess-1") == 1

    async def test_send_error_cleanup(self, manager):
        ws = FakeWebSocket()
        ws.send_json = AsyncMock(side_effect=RuntimeError("broken"))
        await manager.connect("sess-1", ws)

        await manager.broadcast_status("sess-1", "test")

        # Should clean up the broken ws
        assert manager.get_session_count("sess-1") == 0


# ──── Broadcast Helpers ────


class TestBroadcastHelpers:
    async def test_phase_result(self, manager, ws):
        await manager.connect("s1", ws)
        await manager.broadcast_phase_result("s1", "extraction", {"score": 42}, 1, 5)

        msg = ws.sent_messages[0]
        assert msg["type"] == "phase_result"
        assert msg["phase"] == "extraction"
        assert msg["phase_index"] == 1
        assert msg["total_phases"] == 5
        assert msg["result"]["score"] == 42
        assert "timestamp" in msg

    async def test_debate_turn(self, manager, ws):
        await manager.connect("s1", ws)
        await manager.broadcast_debate_turn(
            "s1",
            "Socrate",
            "The argument is...",
            {"clarity": 8.5},
            round_num=3,
            argument_type="rebuttal",
        )

        msg = ws.sent_messages[0]
        assert msg["type"] == "debate_turn"
        assert msg["agent"] == "Socrate"
        assert msg["argument"] == "The argument is..."
        assert msg["scores"]["clarity"] == 8.5
        assert msg["round"] == 3
        assert msg["argument_type"] == "rebuttal"

    async def test_vote_update(self, manager, ws):
        await manager.connect("s1", ws)
        await manager.broadcast_vote_update(
            "s1",
            "prop-1",
            "voter-42",
            "pour",
            {"pour": 5, "contre": 2, "abstention": 1},
        )

        msg = ws.sent_messages[0]
        assert msg["type"] == "vote_update"
        assert msg["proposal_id"] == "prop-1"
        assert msg["voter_id"] == "voter-42"
        assert msg["position"] == "pour"
        assert msg["vote_counts"]["pour"] == 5

    async def test_jtms_update(self, manager, ws):
        await manager.connect("s1", ws)
        await manager.broadcast_jtms_update(
            "s1", "belief_A", "IN", "OUT", "Justification withdrawn"
        )

        msg = ws.sent_messages[0]
        assert msg["type"] == "jtms_update"
        assert msg["belief"] == "belief_A"
        assert msg["old_status"] == "IN"
        assert msg["new_status"] == "OUT"
        assert msg["justification"] == "Justification withdrawn"

    async def test_error_broadcast(self, manager, ws):
        await manager.connect("s1", ws)
        await manager.broadcast_error("s1", "Something went wrong")

        msg = ws.sent_messages[0]
        assert msg["type"] == "error"
        assert msg["error"] == "Something went wrong"


# ──── Safe Serialization ────


class TestSafeSerialize:
    def test_primitives(self):
        assert _safe_serialize(None) is None
        assert _safe_serialize(42) == 42
        assert _safe_serialize("hello") == "hello"
        assert _safe_serialize(True) is True

    def test_dict(self):
        assert _safe_serialize({"a": 1}) == {"a": 1}

    def test_list(self):
        assert _safe_serialize([1, 2]) == [1, 2]

    def test_nested(self):
        assert _safe_serialize({"a": [1, {"b": 2}]}) == {"a": [1, {"b": 2}]}

    def test_object_with_dict_method(self):
        obj = MagicMock()
        obj.dict.return_value = {"key": "val"}
        assert _safe_serialize(obj) == {"key": "val"}

    def test_fallback_to_str(self):
        class Custom:
            def __str__(self):
                return "custom_repr"

        # Non-serializable falls back to str()
        result = _safe_serialize(Custom())
        assert "custom_repr" in str(result) or isinstance(result, dict)


# ──── Singleton ────


class TestSingleton:
    def test_get_websocket_manager(self):
        import argumentation_analysis.services.websocket_manager as mod

        old = mod._manager
        mod._manager = None
        try:
            m1 = get_websocket_manager()
            m2 = get_websocket_manager()
            assert m1 is m2
        finally:
            mod._manager = old
