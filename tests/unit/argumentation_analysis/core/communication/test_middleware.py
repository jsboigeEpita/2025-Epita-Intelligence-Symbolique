# tests/unit/argumentation_analysis/core/communication/test_middleware.py
"""Tests for MessageMiddleware — channel routing, handlers, and statistics."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.message import (
    Message,
    MessageType,
    MessagePriority,
    AgentLevel,
)
from argumentation_analysis.core.communication.channel_interface import ChannelType


def _make_msg(
    msg_type=MessageType.COMMAND,
    sender="agent_1",
    recipient="agent_2",
    channel=None,
    priority=MessagePriority.NORMAL,
    content=None,
    metadata=None,
):
    return Message(
        message_type=msg_type,
        sender=sender,
        sender_level=AgentLevel.STRATEGIC,
        content=content or {},
        recipient=recipient,
        channel=channel,
        priority=priority,
        metadata=metadata,
    )


@pytest.fixture
def middleware():
    return MessageMiddleware()


# ── Init ──


class TestInit:
    def test_default_config(self, middleware):
        assert middleware.config == {}
        assert middleware.channels == {}
        assert middleware.message_handlers == {}
        assert middleware.global_handlers == []

    def test_custom_config(self):
        mw = MessageMiddleware(config={"key": "value"})
        assert mw.config["key"] == "value"

    def test_initial_stats(self, middleware):
        assert middleware.stats["messages_sent"] == 0
        assert middleware.stats["messages_received"] == 0
        assert middleware.stats["errors"] == 0

    def test_protocols_not_initialized(self, middleware):
        assert middleware.request_response is None
        assert middleware.publish_subscribe is None


# ── Channel registration ──


class TestChannelRegistration:
    def test_register_channel(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        middleware.register_channel(channel)
        assert ChannelType.HIERARCHICAL in middleware.channels

    def test_get_channel(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.COLLABORATION
        middleware.register_channel(channel)
        assert middleware.get_channel(ChannelType.COLLABORATION) == channel

    def test_get_channel_not_found(self, middleware):
        assert middleware.get_channel(ChannelType.HIERARCHICAL) is None

    def test_channel_stats_initialized(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.DATA
        middleware.register_channel(channel)
        assert middleware.stats["by_channel"]["data"]["sent"] == 0


# ── Handler registration ──


class TestHandlerRegistration:
    def test_register_message_handler(self, middleware):
        handler = MagicMock()
        middleware.register_message_handler(MessageType.COMMAND, handler)
        assert handler in middleware.message_handlers[MessageType.COMMAND]

    def test_register_multiple_handlers(self, middleware):
        h1, h2 = MagicMock(), MagicMock()
        middleware.register_message_handler(MessageType.COMMAND, h1)
        middleware.register_message_handler(MessageType.COMMAND, h2)
        assert len(middleware.message_handlers[MessageType.COMMAND]) == 2

    def test_register_global_handler(self, middleware):
        handler = MagicMock()
        middleware.register_global_handler(handler)
        assert handler in middleware.global_handlers


# ── determine_channel ──


class TestDetermineChannel:
    def test_explicit_channel(self, middleware):
        msg = _make_msg(channel="hierarchical")
        assert middleware.determine_channel(msg) == ChannelType.HIERARCHICAL

    def test_explicit_invalid_channel_fallback(self, middleware):
        msg = _make_msg(msg_type=MessageType.COMMAND, channel="nonexistent")
        # Falls through to type-based routing
        result = middleware.determine_channel(msg)
        assert result == ChannelType.HIERARCHICAL

    def test_command_routes_to_hierarchical(self, middleware):
        msg = _make_msg(msg_type=MessageType.COMMAND)
        assert middleware.determine_channel(msg) == ChannelType.HIERARCHICAL

    def test_information_analysis_routes_to_data(self, middleware):
        msg = _make_msg(
            msg_type=MessageType.INFORMATION,
            content={"info_type": "analysis_result_detailed"},
        )
        assert middleware.determine_channel(msg) == ChannelType.DATA

    def test_information_generic_routes_to_hierarchical(self, middleware):
        msg = _make_msg(
            msg_type=MessageType.INFORMATION,
            content={"info_type": "status_update"},
        )
        assert middleware.determine_channel(msg) == ChannelType.HIERARCHICAL

    def test_request_assistance_routes_to_collaboration(self, middleware):
        msg = _make_msg(
            msg_type=MessageType.REQUEST,
            content={"request_type": "assistance_needed"},
        )
        assert middleware.determine_channel(msg) == ChannelType.COLLABORATION

    def test_request_generic_routes_to_hierarchical(self, middleware):
        msg = _make_msg(
            msg_type=MessageType.REQUEST,
            content={"request_type": "get_data"},
        )
        assert middleware.determine_channel(msg) == ChannelType.HIERARCHICAL

    def test_response_routes_to_hierarchical(self, middleware):
        msg = _make_msg(msg_type=MessageType.RESPONSE)
        assert middleware.determine_channel(msg) == ChannelType.HIERARCHICAL

    def test_event_routes_to_feedback(self, middleware):
        msg = _make_msg(msg_type=MessageType.EVENT)
        assert middleware.determine_channel(msg) == ChannelType.FEEDBACK

    def test_control_routes_to_system(self, middleware):
        msg = _make_msg(msg_type=MessageType.CONTROL)
        assert middleware.determine_channel(msg) == ChannelType.SYSTEM

    def test_publication_routes_to_data(self, middleware):
        msg = _make_msg(msg_type=MessageType.PUBLICATION)
        assert middleware.determine_channel(msg) == ChannelType.DATA

    def test_subscription_routes_to_system(self, middleware):
        msg = _make_msg(msg_type=MessageType.SUBSCRIPTION)
        assert middleware.determine_channel(msg) == ChannelType.SYSTEM


# ── send_message ──


class TestSendMessage:
    def test_send_success(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        channel.send_message.return_value = True
        middleware.register_channel(channel)

        msg = _make_msg(msg_type=MessageType.COMMAND)
        result = middleware.send_message(msg)
        assert result is True
        assert middleware.stats["messages_sent"] == 1

    def test_send_no_channel(self, middleware):
        msg = _make_msg(msg_type=MessageType.COMMAND)
        result = middleware.send_message(msg)
        assert result is False

    def test_send_updates_type_stats(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        channel.send_message.return_value = True
        middleware.register_channel(channel)

        msg = _make_msg(msg_type=MessageType.COMMAND)
        middleware.send_message(msg)
        assert middleware.stats["by_type"]["command"] == 1

    def test_send_updates_priority_stats(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        channel.send_message.return_value = True
        middleware.register_channel(channel)

        msg = _make_msg(msg_type=MessageType.COMMAND, priority=MessagePriority.HIGH)
        middleware.send_message(msg)
        assert middleware.stats["by_priority"]["high"] == 1

    def test_send_sets_channel_on_message(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        channel.send_message.return_value = True
        middleware.register_channel(channel)

        msg = _make_msg(msg_type=MessageType.COMMAND)
        middleware.send_message(msg)
        assert msg.channel == "hierarchical"


# ── get_statistics ──


class TestGetStatistics:
    def test_returns_copy(self, middleware):
        stats = middleware.get_statistics()
        stats["messages_sent"] = 999
        assert middleware.stats["messages_sent"] == 0  # Original unchanged


# ── get_channel_info ──


class TestGetChannelInfo:
    def test_existing_channel(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        channel.get_channel_info.return_value = {"status": "active"}
        middleware.register_channel(channel)

        info = middleware.get_channel_info(ChannelType.HIERARCHICAL)
        assert info["status"] == "active"

    def test_nonexistent_channel(self, middleware):
        assert middleware.get_channel_info(ChannelType.DATA) is None


# ── _handle_message ──


class TestHandleMessage:
    def test_calls_type_handler(self, middleware):
        handler = MagicMock()
        middleware.register_message_handler(MessageType.COMMAND, handler)
        msg = _make_msg(msg_type=MessageType.COMMAND)
        middleware._handle_message(msg)
        handler.assert_called_once_with(msg)

    def test_calls_global_handler(self, middleware):
        handler = MagicMock()
        middleware.register_global_handler(handler)
        msg = _make_msg(msg_type=MessageType.COMMAND)
        middleware._handle_message(msg)
        handler.assert_called_once_with(msg)

    def test_handler_exception_caught(self, middleware):
        handler = MagicMock(side_effect=RuntimeError("boom"))
        middleware.register_message_handler(MessageType.COMMAND, handler)
        msg = _make_msg(msg_type=MessageType.COMMAND)
        # Should not raise
        middleware._handle_message(msg)

    def test_global_handler_exception_caught(self, middleware):
        handler = MagicMock(side_effect=RuntimeError("boom"))
        middleware.register_global_handler(handler)
        msg = _make_msg(msg_type=MessageType.COMMAND)
        middleware._handle_message(msg)

    def test_response_with_request_response_protocol(self, middleware):
        middleware.request_response = MagicMock()
        middleware.request_response.handle_response.return_value = True
        msg = _make_msg(
            msg_type=MessageType.RESPONSE,
            metadata={"reply_to": "req-123"},
        )
        middleware._handle_message(msg)
        middleware.request_response.handle_response.assert_called()


# ── shutdown ──


class TestShutdown:
    def test_shutdown_with_protocols(self, middleware):
        middleware.request_response = MagicMock()
        middleware.publish_subscribe = MagicMock()
        middleware.shutdown()
        middleware.request_response.shutdown.assert_called_once()
        middleware.publish_subscribe.shutdown.assert_called_once()

    def test_shutdown_without_protocols(self, middleware):
        middleware.shutdown()  # Should not raise


# ── receive_message (CM-1 restore: DRIFT_REGISTER) ──
#
# The pre-reduction suite (b350e539^) covered receive/pending/protocol/async
# paths via a heavyweight in-memory ``MockChannel``. These restore that
# coverage in the current pytest idiom — a ``MagicMock`` channel is the
# unit-equivalent: it isolates the *middleware's* delegation + stats + handler
# logic from any concrete channel implementation.


class TestReceiveMessage:
    def test_receive_from_channel(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        msg = _make_msg(msg_type=MessageType.COMMAND, recipient="agent_2")
        channel.receive_message.return_value = msg
        middleware.register_channel(channel)

        received = middleware.receive_message("agent_2", ChannelType.HIERARCHICAL)
        assert received is msg
        assert middleware.stats["messages_received"] == 1
        assert middleware.stats["by_channel"]["hierarchical"]["received"] == 1

    def test_receive_channel_not_found(self, middleware):
        # channel_type requested but never registered → None, no crash
        assert middleware.receive_message("agent_2", ChannelType.DATA) is None

    def test_receive_returns_none_when_channel_empty(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        channel.receive_message.return_value = None
        middleware.register_channel(channel)

        received = middleware.receive_message("agent_2", ChannelType.HIERARCHICAL)
        assert received is None
        assert middleware.stats["messages_received"] == 0

    def test_receive_invokes_handlers(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        msg = _make_msg(msg_type=MessageType.COMMAND, recipient="agent_2")
        channel.receive_message.return_value = msg
        middleware.register_channel(channel)

        handler = MagicMock()
        middleware.register_message_handler(MessageType.COMMAND, handler)
        middleware.receive_message("agent_2", ChannelType.HIERARCHICAL)
        handler.assert_called_once_with(msg)


# ── get_pending_messages (CM-1 restore) ──


class TestGetPendingMessages:
    def test_pending_from_specific_channel(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        pending = [_make_msg(), _make_msg()]
        channel.get_pending_messages.return_value = pending
        middleware.register_channel(channel)

        result = middleware.get_pending_messages("agent_2", ChannelType.HIERARCHICAL)
        assert result == pending
        channel.get_pending_messages.assert_called_once_with("agent_2", None)

    def test_pending_channel_not_found(self, middleware):
        assert middleware.get_pending_messages("agent_2", ChannelType.DATA) == []

    def test_pending_aggregates_across_channels(self, middleware):
        ch1 = MagicMock()
        ch1.type = ChannelType.HIERARCHICAL
        ch1.get_pending_messages.return_value = [_make_msg()]
        ch2 = MagicMock()
        ch2.type = ChannelType.DATA
        ch2.get_pending_messages.return_value = [_make_msg()]
        middleware.register_channel(ch1)
        middleware.register_channel(ch2)

        result = middleware.get_pending_messages("agent_2")
        assert len(result) == 2


# ── protocol delegation: send_request / publish / subscribe (CM-1 restore) ──


class TestProtocolDelegation:
    def test_send_request_delegates(self, middleware):
        middleware.request_response = MagicMock()
        middleware.request_response.send_request.return_value = {"status": "ok"}

        result = middleware.send_request(
            sender="agent_1",
            sender_level=AgentLevel.STRATEGIC,
            request_type="get_analysis",
            recipient="agent_2",
        )
        middleware.request_response.send_request.assert_called_once()
        assert result == {"status": "ok"}

    def test_send_request_lazy_initializes_protocols(self, middleware):
        # request_response is None → send_request must trigger initialize_protocols
        assert middleware.request_response is None

        def _set_protocol():
            middleware.request_response = MagicMock()

        with patch.object(
            middleware, "initialize_protocols", side_effect=_set_protocol
        ) as mock_init:
            middleware.send_request(sender="a", sender_level=AgentLevel.STRATEGIC)
            mock_init.assert_called_once()

    def test_publish_delegates(self, middleware):
        middleware.publish_subscribe = MagicMock()
        middleware.publish(
            sender="agent_1",
            sender_level=AgentLevel.STRATEGIC,
            topic="analysis_results",
            data={},
        )
        middleware.publish_subscribe.publish.assert_called_once()

    def test_subscribe_delegates(self, middleware):
        middleware.publish_subscribe = MagicMock()
        middleware.subscribe(
            subscriber_id="agent_1",
            topic="analysis_results",
            callback=MagicMock(),
        )
        middleware.publish_subscribe.subscribe.assert_called_once()


# ── async methods: receive_message_async / send_request_async (CM-1 restore) ──
#
# asyncio_mode=auto (pyproject) — plain ``async def`` tests run without a marker.


class TestAsyncMethods:
    async def test_receive_message_async_delegates(self, middleware):
        channel = MagicMock()
        channel.type = ChannelType.HIERARCHICAL
        msg = _make_msg(msg_type=MessageType.COMMAND, recipient="agent_2")
        channel.receive_message.return_value = msg
        middleware.register_channel(channel)

        received = await middleware.receive_message_async(
            "agent_2", ChannelType.HIERARCHICAL
        )
        assert received is msg

    async def test_send_request_async_delegates(self, middleware):
        middleware.request_response = MagicMock()
        middleware.request_response.send_request_async = AsyncMock(
            return_value={"status": "success"}
        )

        result = await middleware.send_request_async(
            sender="agent_1",
            sender_level=AgentLevel.STRATEGIC,
            request_type="get_analysis",
            recipient="agent_2",
        )
        middleware.request_response.send_request_async.assert_awaited_once()
        assert result == {"status": "success"}
