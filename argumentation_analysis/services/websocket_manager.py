"""WebSocket manager for real-time streaming of analysis, debate, and deliberation events.

Provides:
- AnalysisWebSocketManager: manages per-session WebSocket connections
- Broadcast helpers for phase results, debate turns, vote updates, JTMS changes
- Connection lifecycle (connect, disconnect, cleanup)
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set

from starlette.websockets import WebSocket, WebSocketState

logger = logging.getLogger(__name__)


class AnalysisWebSocketManager:
    """Manages WebSocket connections grouped by session ID.

    Each session can have multiple connected clients (e.g., multiple browser tabs).
    Messages are JSON-serialized and broadcast to all clients in a session.
    """

    def __init__(self):
        # session_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept a WebSocket connection and register it under a session."""
        await websocket.accept()
        async with self._lock:
            if session_id not in self._connections:
                self._connections[session_id] = set()
            self._connections[session_id].add(websocket)
        logger.info(f"WS connected: session={session_id}, total={len(self._connections.get(session_id, set()))}")

    async def disconnect(self, session_id: str, websocket: WebSocket):
        """Remove a WebSocket from a session."""
        async with self._lock:
            conns = self._connections.get(session_id)
            if conns:
                conns.discard(websocket)
                if not conns:
                    del self._connections[session_id]
        logger.info(f"WS disconnected: session={session_id}")

    async def _send_to_session(self, session_id: str, message: Dict[str, Any]):
        """Send a JSON message to all connections in a session."""
        conns = self._connections.get(session_id, set()).copy()
        dead = []
        for ws in conns:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(message)
                else:
                    dead.append(ws)
            except Exception as e:
                logger.warning(f"WS send error: {e}")
                dead.append(ws)
        # Cleanup dead connections
        if dead:
            async with self._lock:
                s = self._connections.get(session_id)
                if s:
                    for ws in dead:
                        s.discard(ws)

    def get_session_count(self, session_id: str) -> int:
        """Return the number of active connections for a session."""
        return len(self._connections.get(session_id, set()))

    def get_active_sessions(self) -> List[str]:
        """Return list of session IDs with active connections."""
        return list(self._connections.keys())

    # ── Broadcast Helpers ──

    async def broadcast_phase_result(
        self,
        session_id: str,
        phase_name: str,
        result: Any,
        phase_index: int = 0,
        total_phases: int = 0,
    ):
        """Broadcast a workflow phase completion event."""
        await self._send_to_session(session_id, {
            "type": "phase_result",
            "phase": phase_name,
            "phase_index": phase_index,
            "total_phases": total_phases,
            "result": _safe_serialize(result),
            "timestamp": time.time(),
        })

    async def broadcast_debate_turn(
        self,
        session_id: str,
        agent: str,
        argument: str,
        scores: Optional[Dict[str, float]] = None,
        round_num: int = 0,
        argument_type: str = "claim",
    ):
        """Broadcast a debate turn event."""
        await self._send_to_session(session_id, {
            "type": "debate_turn",
            "agent": agent,
            "argument": argument,
            "argument_type": argument_type,
            "scores": scores or {},
            "round": round_num,
            "timestamp": time.time(),
        })

    async def broadcast_vote_update(
        self,
        session_id: str,
        proposal_id: str,
        voter_id: str,
        position: str,
        vote_counts: Optional[Dict[str, int]] = None,
    ):
        """Broadcast a vote update event."""
        await self._send_to_session(session_id, {
            "type": "vote_update",
            "proposal_id": proposal_id,
            "voter_id": voter_id,
            "position": position,
            "vote_counts": vote_counts or {},
            "timestamp": time.time(),
        })

    async def broadcast_jtms_update(
        self,
        session_id: str,
        belief_name: str,
        old_status: str,
        new_status: str,
        justification: Optional[str] = None,
    ):
        """Broadcast a JTMS belief status change event."""
        await self._send_to_session(session_id, {
            "type": "jtms_update",
            "belief": belief_name,
            "old_status": old_status,
            "new_status": new_status,
            "justification": justification,
            "timestamp": time.time(),
        })

    async def broadcast_status(self, session_id: str, status: str, detail: str = ""):
        """Broadcast a generic status message."""
        await self._send_to_session(session_id, {
            "type": "status",
            "status": status,
            "detail": detail,
            "timestamp": time.time(),
        })

    async def broadcast_error(self, session_id: str, error: str):
        """Broadcast an error message."""
        await self._send_to_session(session_id, {
            "type": "error",
            "error": error,
            "timestamp": time.time(),
        })


def _safe_serialize(obj: Any) -> Any:
    """Convert an object to JSON-safe form."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _safe_serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(v) for v in obj]
    if hasattr(obj, "dict"):
        try:
            return obj.dict()
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return {k: _safe_serialize(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
    return str(obj)


# ── Singleton ──

_manager: Optional[AnalysisWebSocketManager] = None


def get_websocket_manager() -> AnalysisWebSocketManager:
    """Get or create the global WebSocket manager."""
    global _manager
    if _manager is None:
        _manager = AnalysisWebSocketManager()
    return _manager
