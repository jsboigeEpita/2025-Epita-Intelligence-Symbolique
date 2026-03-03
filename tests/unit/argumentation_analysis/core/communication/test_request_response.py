# tests/unit/argumentation_analysis/core/communication/test_request_response.py
"""Tests for RequestResponseProtocol — sync/async request-response with timeouts."""

import threading
import time
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

from argumentation_analysis.core.communication.request_response import (
    RequestResponseProtocol,
    RequestTimeoutError,
)
from argumentation_analysis.core.communication.message import (
    Message,
    MessageType,
    MessagePriority,
    AgentLevel,
)


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_middleware():
    m = MagicMock()
    m.send_message = MagicMock()
    return m


@pytest.fixture
def protocol(mock_middleware):
    """Fresh RequestResponseProtocol with cleanup."""
    p = RequestResponseProtocol(mock_middleware)
    yield p
    p.shutdown()


def make_response(reply_to, conversation_id=None):
    """Helper: create a response Message with reply_to metadata."""
    metadata = {"reply_to": reply_to}
    if conversation_id:
        metadata["conversation_id"] = conversation_id
    return Message(
        message_type=MessageType.RESPONSE,
        sender="responder",
        sender_level=AgentLevel.OPERATIONAL,
        content={"answer": "yes"},
        metadata=metadata,
    )


# ── __init__ ────────────────────────────────────────────────────────────

class TestRequestResponseInit:
    """Tests for RequestResponseProtocol.__init__."""

    def test_middleware_stored(self, protocol, mock_middleware):
        assert protocol.middleware is mock_middleware

    def test_pending_requests_empty(self, protocol):
        assert protocol.pending_requests == {}

    def test_response_callbacks_empty(self, protocol):
        assert protocol.response_callbacks == {}

    def test_early_responses_empty(self, protocol):
        assert protocol.early_responses == {}
        assert protocol.early_responses_by_conversation == {}

    def test_running_is_true(self, protocol):
        assert protocol.running is True

    def test_timeout_thread_alive(self, protocol):
        assert protocol.timeout_thread.is_alive()

    def test_timeout_thread_is_daemon(self, protocol):
        assert protocol.timeout_thread.daemon is True


# ── handle_response ─────────────────────────────────────────────────────

class TestHandleResponse:
    """Tests for handle_response()."""

    def test_no_reply_to_returns_false(self, protocol):
        msg = Message(
            message_type=MessageType.RESPONSE,
            sender="x",
            sender_level=AgentLevel.OPERATIONAL,
            content={},
            metadata={},
        )
        assert protocol.handle_response(msg) is False

    def test_empty_reply_to_returns_false(self, protocol):
        msg = Message(
            message_type=MessageType.RESPONSE,
            sender="x",
            sender_level=AgentLevel.OPERATIONAL,
            content={},
            metadata={"reply_to": ""},
        )
        assert protocol.handle_response(msg) is False

    def test_matching_pending_request(self, protocol):
        event = threading.Event()
        protocol.pending_requests["req-1"] = {
            "request": MagicMock(),
            "expires_at": datetime.now() + timedelta(seconds=30),
            "response": None,
            "completed": event,
        }
        response = make_response("req-1")
        result = protocol.handle_response(response)
        assert result is True
        assert event.is_set()
        assert protocol.pending_requests["req-1"]["response"] is response

    def test_callback_invoked(self, protocol):
        callback = MagicMock()
        event = threading.Event()
        protocol.pending_requests["req-2"] = {
            "request": MagicMock(),
            "expires_at": datetime.now() + timedelta(seconds=30),
            "response": None,
            "completed": event,
            "callback": callback,
        }
        response = make_response("req-2")
        protocol.handle_response(response)
        callback.assert_called_once_with(response, None)

    def test_callback_exception_handled(self, protocol):
        callback = MagicMock(side_effect=RuntimeError("callback broke"))
        event = threading.Event()
        protocol.pending_requests["req-3"] = {
            "request": MagicMock(),
            "expires_at": datetime.now() + timedelta(seconds=30),
            "response": None,
            "completed": event,
            "callback": callback,
        }
        response = make_response("req-3")
        # Should not raise
        result = protocol.handle_response(response)
        assert result is True

    def test_unknown_request_stored_as_early(self, protocol):
        response = make_response("unknown-req")
        result = protocol.handle_response(response)
        assert result is True
        assert "unknown-req" in protocol.early_responses

    def test_early_response_with_conversation_id(self, protocol):
        response = make_response("unknown-req", conversation_id="conv-123")
        protocol.handle_response(response)
        assert "conv-123" in protocol.early_responses_by_conversation


# ── _handle_timeout ─────────────────────────────────────────────────────

class TestHandleTimeout:
    """Tests for _handle_timeout()."""

    def test_completed_request_ignored(self, protocol):
        event = threading.Event()
        event.set()  # Already completed
        protocol.pending_requests["req-done"] = {
            "request": MagicMock(),
            "expires_at": datetime.now(),
            "response": MagicMock(),
            "completed": event,
        }
        protocol._handle_timeout("req-done")
        # Request should still be there (not deleted)
        assert "req-done" in protocol.pending_requests

    def test_timeout_removes_request(self, protocol):
        event = threading.Event()
        protocol.pending_requests["req-timeout"] = {
            "request": MagicMock(),
            "expires_at": datetime.now() - timedelta(seconds=1),
            "response": None,
            "completed": event,
        }
        protocol._handle_timeout("req-timeout")
        assert "req-timeout" not in protocol.pending_requests
        assert event.is_set()

    def test_timeout_calls_callback_with_error(self, protocol):
        callback = MagicMock()
        event = threading.Event()
        protocol.pending_requests["req-cb"] = {
            "request": MagicMock(),
            "expires_at": datetime.now(),
            "response": None,
            "completed": event,
            "callback": callback,
        }
        protocol._handle_timeout("req-cb")
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] is None  # No response
        assert isinstance(args[1], RequestTimeoutError)

    def test_timeout_nonexistent_request(self, protocol):
        # Should not raise
        protocol._handle_timeout("nonexistent")

    def test_timeout_callback_exception_handled(self, protocol):
        callback = MagicMock(side_effect=RuntimeError("cb fail"))
        event = threading.Event()
        protocol.pending_requests["req-err"] = {
            "request": MagicMock(),
            "expires_at": datetime.now(),
            "response": None,
            "completed": event,
            "callback": callback,
        }
        # Should not raise
        protocol._handle_timeout("req-err")


# ── send_request_async_callback ─────────────────────────────────────────

class TestSendRequestAsyncCallback:
    """Tests for send_request_async_callback()."""

    def test_returns_request_id(self, protocol):
        callback = MagicMock()
        req_id = protocol.send_request_async_callback(
            sender="agent_a",
            sender_level=AgentLevel.TACTICAL,
            recipient="agent_b",
            request_type="query",
            content={"data": "test"},
            callback=callback,
        )
        assert isinstance(req_id, str)
        assert len(req_id) > 0

    def test_registers_pending_request(self, protocol):
        callback = MagicMock()
        req_id = protocol.send_request_async_callback(
            sender="a",
            sender_level=AgentLevel.OPERATIONAL,
            recipient="b",
            request_type="q",
            content={},
            callback=callback,
        )
        assert req_id in protocol.pending_requests
        pending = protocol.pending_requests[req_id]
        assert pending["callback"] is callback
        assert pending["retry_count"] == 0
        assert pending["attempt"] == 0

    def test_sends_via_middleware(self, protocol, mock_middleware):
        protocol.send_request_async_callback(
            sender="a",
            sender_level=AgentLevel.OPERATIONAL,
            recipient="b",
            request_type="q",
            content={},
            callback=MagicMock(),
        )
        mock_middleware.send_message.assert_called_once()
        sent_msg = mock_middleware.send_message.call_args[0][0]
        assert sent_msg.type == MessageType.REQUEST

    def test_custom_timeout(self, protocol):
        req_id = protocol.send_request_async_callback(
            sender="a",
            sender_level=AgentLevel.OPERATIONAL,
            recipient="b",
            request_type="q",
            content={},
            callback=MagicMock(),
            timeout=60.0,
        )
        pending = protocol.pending_requests[req_id]
        # Expires ~60s from now
        assert pending["expires_at"] > datetime.now()

    def test_retry_config(self, protocol):
        req_id = protocol.send_request_async_callback(
            sender="a",
            sender_level=AgentLevel.OPERATIONAL,
            recipient="b",
            request_type="q",
            content={},
            callback=MagicMock(),
            retry_count=3,
            retry_delay=2.0,
        )
        pending = protocol.pending_requests[req_id]
        assert pending["retry_count"] == 3
        assert pending["retry_delay"] == 2.0

    def test_priority_preserved(self, protocol, mock_middleware):
        protocol.send_request_async_callback(
            sender="a",
            sender_level=AgentLevel.OPERATIONAL,
            recipient="b",
            request_type="q",
            content={},
            callback=MagicMock(),
            priority=MessagePriority.CRITICAL,
        )
        sent_msg = mock_middleware.send_message.call_args[0][0]
        assert sent_msg.priority == MessagePriority.CRITICAL


# ── send_request (synchronous, with fast response) ──────────────────────

class TestSendRequest:
    """Tests for send_request() — synchronous version."""

    def test_sends_and_receives_response(self, protocol, mock_middleware):
        """Simulate middleware instantly responding."""
        def side_effect(msg):
            # Simulate instant response via handle_response
            response = make_response(msg.id)
            protocol.handle_response(response)

        mock_middleware.send_message.side_effect = side_effect

        result = protocol.send_request(
            sender="agent_a",
            sender_level=AgentLevel.TACTICAL,
            recipient="agent_b",
            request_type="query",
            content={"q": "test"},
            timeout=5.0,
        )
        assert result is not None
        assert result.content["answer"] == "yes"

    def test_timeout_raises_error(self, protocol):
        with pytest.raises(RequestTimeoutError):
            protocol.send_request(
                sender="a",
                sender_level=AgentLevel.OPERATIONAL,
                recipient="b",
                request_type="q",
                content={},
                timeout=0.2,
                retry_count=0,
            )

    def test_early_response_found(self, protocol, mock_middleware):
        """Pre-store an early response before sending the request."""
        # We can't predict the request ID, so test via handle_response flow
        def side_effect(msg):
            response = make_response(msg.id)
            protocol.handle_response(response)

        mock_middleware.send_message.side_effect = side_effect

        result = protocol.send_request(
            sender="a",
            sender_level=AgentLevel.OPERATIONAL,
            recipient="b",
            request_type="q",
            content={},
            timeout=2.0,
        )
        assert result is not None


# ── send_request_async ──────────────────────────────────────────────────

class TestSendRequestAsync:
    """Tests for send_request_async()."""

    async def test_timeout_raises(self, protocol):
        with pytest.raises(RequestTimeoutError):
            await protocol.send_request_async(
                sender="a",
                sender_level=AgentLevel.OPERATIONAL,
                recipient="b",
                request_type="q",
                content={},
                timeout=0.3,
            )

    async def test_sends_message(self, protocol, mock_middleware):
        # Will timeout but should at least send the message
        try:
            await protocol.send_request_async(
                sender="a",
                sender_level=AgentLevel.OPERATIONAL,
                recipient="b",
                request_type="q",
                content={},
                timeout=0.3,
            )
        except RequestTimeoutError:
            pass
        mock_middleware.send_message.assert_called()


# ── shutdown ────────────────────────────────────────────────────────────

class TestShutdown:
    """Tests for shutdown()."""

    def test_stops_running(self, protocol):
        protocol.shutdown()
        assert protocol.running is False

    def test_clears_pending(self, protocol):
        event = threading.Event()
        protocol.pending_requests["r1"] = {
            "request": MagicMock(),
            "expires_at": datetime.now() + timedelta(seconds=30),
            "response": None,
            "completed": event,
        }
        protocol.shutdown()
        assert protocol.pending_requests == {}

    def test_clears_early_responses(self, protocol):
        protocol.early_responses["e1"] = {"response": MagicMock(), "timestamp": datetime.now()}
        protocol.early_responses_by_conversation["c1"] = {"response": MagicMock(), "timestamp": datetime.now()}
        protocol.shutdown()
        assert protocol.early_responses == {}
        assert protocol.early_responses_by_conversation == {}

    def test_callback_called_on_shutdown(self, protocol):
        callback = MagicMock()
        event = threading.Event()
        protocol.pending_requests["r1"] = {
            "request": MagicMock(),
            "expires_at": datetime.now() + timedelta(seconds=30),
            "response": None,
            "completed": event,
            "callback": callback,
        }
        protocol.shutdown()
        callback.assert_called_once()
        args = callback.call_args[0]
        assert args[0] is None
        assert isinstance(args[1], Exception)

    def test_completed_events_set(self, protocol):
        event = threading.Event()
        protocol.pending_requests["r1"] = {
            "request": MagicMock(),
            "expires_at": datetime.now() + timedelta(seconds=30),
            "response": None,
            "completed": event,
        }
        protocol.shutdown()
        assert event.is_set()

    def test_double_shutdown_safe(self, protocol):
        protocol.shutdown()
        protocol.shutdown()  # Should not raise


# ── RequestTimeoutError ─────────────────────────────────────────────────

class TestRequestTimeoutError:
    """Tests for RequestTimeoutError exception."""

    def test_is_exception(self):
        err = RequestTimeoutError("timed out")
        assert isinstance(err, Exception)

    def test_message(self):
        err = RequestTimeoutError("my message")
        assert str(err) == "my message"
