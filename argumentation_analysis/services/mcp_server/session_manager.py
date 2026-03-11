"""In-memory session manager for multi-turn MCP conversations."""

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MCPSessionManager")


@dataclass
class SessionState:
    """State for a single conversation session."""

    session_id: str
    created_at: float
    last_accessed: float
    text: str
    workflow_name: str = "standard"
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    state: Optional[Any] = None
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SessionManager:
    """Manages in-memory conversation sessions with TTL-based expiry."""

    def __init__(self, ttl_seconds: int = 1800, max_sessions: int = 100):
        self._sessions: Dict[str, SessionState] = {}
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions

    def create_session(
        self,
        text: str,
        workflow_name: str = "standard",
        config: Optional[Dict[str, Any]] = None,
    ) -> SessionState:
        """Create a new conversation session."""
        self._cleanup_expired()
        if len(self._sessions) >= self._max_sessions:
            oldest = min(self._sessions.values(), key=lambda s: s.last_accessed)
            del self._sessions[oldest.session_id]
            logger.info("Evicted oldest session %s (max sessions reached)", oldest.session_id)

        session_id = str(uuid.uuid4())
        now = time.time()
        session = SessionState(
            session_id=session_id,
            created_at=now,
            last_accessed=now,
            text=text,
            workflow_name=workflow_name,
            config=config or {},
        )
        self._sessions[session_id] = session
        logger.info("Created session %s (workflow=%s)", session_id, workflow_name)
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve a session by ID, returning None if expired or not found."""
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if (time.time() - session.last_accessed) >= self._ttl:
            del self._sessions[session_id]
            logger.info("Session %s expired", session_id)
            return None
        session.last_accessed = time.time()
        return session

    def update_session(self, session_id: str, round_result: Dict[str, Any]) -> bool:
        """Append a round result to the session history."""
        session = self.get_session(session_id)
        if session is None:
            return False
        session.conversation_history.append(round_result)
        return True

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return self._sessions.pop(session_id, None) is not None

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active (non-expired) sessions."""
        self._cleanup_expired()
        return [
            {
                "session_id": s.session_id,
                "created_at": s.created_at,
                "rounds": len(s.conversation_history),
                "workflow": s.workflow_name,
            }
            for s in self._sessions.values()
        ]

    def _cleanup_expired(self) -> None:
        """Remove expired sessions."""
        now = time.time()
        expired = [
            sid
            for sid, s in self._sessions.items()
            if (now - s.last_accessed) >= self._ttl
        ]
        for sid in expired:
            del self._sessions[sid]
        if expired:
            logger.info("Cleaned up %d expired sessions", len(expired))
