# tests/unit/argumentation_analysis/core/communication/test_channel_interface.py
"""Tests for ChannelType, Channel.matches_filter, LocalChannel, and exception classes."""

import pytest
from unittest.mock import MagicMock

from argumentation_analysis.core.communication.channel_interface import (
    ChannelType,
    Channel,
    LocalChannel,
    ChannelException,
    ChannelFullException,
    ChannelTimeoutException,
    ChannelClosedException,
    InvalidMessageException,
    UnauthorizedAccessException,
)
from argumentation_analysis.core.communication.message import (
    Message,
    MessageType,
    MessagePriority,
    AgentLevel,
)


def _make_msg(
    msg_type=MessageType.COMMAND,
    sender="agent_1",
    recipient="agent_2",
    priority=MessagePriority.NORMAL,
    sender_level=AgentLevel.OPERATIONAL,
    content=None,
):
    return Message(
        message_type=msg_type,
        sender=sender,
        sender_level=sender_level,
        content=content or {},
        recipient=recipient,
        priority=priority,
    )


# ── ChannelType ──

class TestChannelType:
    def test_all_values(self):
        assert ChannelType.HIERARCHICAL.value == "hierarchical"
        assert ChannelType.COLLABORATION.value == "collaboration"
        assert ChannelType.DATA.value == "data"
        assert ChannelType.NEGOTIATION.value == "negotiation"
        assert ChannelType.FEEDBACK.value == "feedback"
        assert ChannelType.SYSTEM.value == "system"
        assert ChannelType.LOCAL.value == "local"

    def test_count(self):
        assert len(ChannelType) == 7


# ── Exception hierarchy ──

class TestExceptions:
    def test_channel_exception_is_exception(self):
        assert issubclass(ChannelException, Exception)

    def test_channel_full_inherits(self):
        assert issubclass(ChannelFullException, ChannelException)

    def test_channel_timeout_inherits(self):
        assert issubclass(ChannelTimeoutException, ChannelException)

    def test_channel_closed_inherits(self):
        assert issubclass(ChannelClosedException, ChannelException)

    def test_invalid_message_inherits(self):
        assert issubclass(InvalidMessageException, ChannelException)

    def test_unauthorized_inherits(self):
        assert issubclass(UnauthorizedAccessException, ChannelException)

    def test_can_raise_and_catch(self):
        with pytest.raises(ChannelException):
            raise ChannelFullException("queue full")


# ── matches_filter ──

class TestMatchesFilter:
    @pytest.fixture
    def channel(self):
        return LocalChannel("test_ch")

    def test_empty_filter_matches_all(self, channel):
        msg = _make_msg()
        assert channel.matches_filter(msg, {}) is True

    def test_none_filter_matches_all(self, channel):
        msg = _make_msg()
        assert channel.matches_filter(msg, None) is True

    def test_message_type_single_match(self, channel):
        msg = _make_msg(msg_type=MessageType.COMMAND)
        assert channel.matches_filter(msg, {"message_type": "command"}) is True

    def test_message_type_single_no_match(self, channel):
        msg = _make_msg(msg_type=MessageType.COMMAND)
        assert channel.matches_filter(msg, {"message_type": "event"}) is False

    def test_message_type_list_match(self, channel):
        msg = _make_msg(msg_type=MessageType.EVENT)
        assert channel.matches_filter(msg, {"message_type": ["command", "event"]}) is True

    def test_message_type_list_no_match(self, channel):
        msg = _make_msg(msg_type=MessageType.RESPONSE)
        assert channel.matches_filter(msg, {"message_type": ["command", "event"]}) is False

    def test_sender_single_match(self, channel):
        msg = _make_msg(sender="sherlock")
        assert channel.matches_filter(msg, {"sender": "sherlock"}) is True

    def test_sender_single_no_match(self, channel):
        msg = _make_msg(sender="sherlock")
        assert channel.matches_filter(msg, {"sender": "watson"}) is False

    def test_sender_list_match(self, channel):
        msg = _make_msg(sender="watson")
        assert channel.matches_filter(msg, {"sender": ["sherlock", "watson"]}) is True

    def test_sender_list_no_match(self, channel):
        msg = _make_msg(sender="moriarty")
        assert channel.matches_filter(msg, {"sender": ["sherlock", "watson"]}) is False

    def test_priority_single_match(self, channel):
        msg = _make_msg(priority=MessagePriority.HIGH)
        assert channel.matches_filter(msg, {"priority": "high"}) is True

    def test_priority_single_no_match(self, channel):
        msg = _make_msg(priority=MessagePriority.LOW)
        assert channel.matches_filter(msg, {"priority": "high"}) is False

    def test_priority_list_match(self, channel):
        msg = _make_msg(priority=MessagePriority.CRITICAL)
        assert channel.matches_filter(msg, {"priority": ["high", "critical"]}) is True

    def test_sender_level_single_match(self, channel):
        msg = _make_msg(sender_level=AgentLevel.STRATEGIC)
        assert channel.matches_filter(msg, {"sender_level": "strategic"}) is True

    def test_sender_level_single_no_match(self, channel):
        msg = _make_msg(sender_level=AgentLevel.OPERATIONAL)
        assert channel.matches_filter(msg, {"sender_level": "strategic"}) is False

    def test_sender_level_list_match(self, channel):
        msg = _make_msg(sender_level=AgentLevel.TACTICAL)
        assert channel.matches_filter(msg, {"sender_level": ["tactical", "strategic"]}) is True

    def test_content_filter_match(self, channel):
        msg = _make_msg(content={"info_type": "result", "value": 42})
        assert channel.matches_filter(msg, {"content": {"info_type": "result"}}) is True

    def test_content_filter_no_match(self, channel):
        msg = _make_msg(content={"info_type": "status"})
        assert channel.matches_filter(msg, {"content": {"info_type": "result"}}) is False

    def test_content_filter_missing_key(self, channel):
        msg = _make_msg(content={"other": "val"})
        assert channel.matches_filter(msg, {"content": {"info_type": "result"}}) is False

    def test_multiple_criteria_all_match(self, channel):
        msg = _make_msg(
            msg_type=MessageType.COMMAND,
            sender="sherlock",
            priority=MessagePriority.HIGH,
        )
        f = {"message_type": "command", "sender": "sherlock", "priority": "high"}
        assert channel.matches_filter(msg, f) is True

    def test_multiple_criteria_one_fails(self, channel):
        msg = _make_msg(
            msg_type=MessageType.COMMAND,
            sender="watson",
            priority=MessagePriority.HIGH,
        )
        f = {"message_type": "command", "sender": "sherlock", "priority": "high"}
        assert channel.matches_filter(msg, f) is False


# ── LocalChannel ──

class TestLocalChannel:
    @pytest.fixture
    def ch(self):
        return LocalChannel("local_1")

    def test_init(self, ch):
        assert ch.id == "local_1"
        assert ch.type == ChannelType.LOCAL
        assert ch.config == {}
        assert ch._message_queue == []
        assert ch.subscribers == {}

    def test_init_with_config(self):
        ch = LocalChannel("ch", config={"buffer_size": 100})
        assert ch.config["buffer_size"] == 100

    # -- send_message --

    def test_send_message(self, ch):
        msg = _make_msg()
        result = ch.send_message(msg)
        assert result is True
        assert len(ch._message_queue) == 1

    def test_send_notifies_subscriber(self, ch):
        callback = MagicMock()
        ch.subscribe("sub1", callback=callback)
        msg = _make_msg()
        ch.send_message(msg)
        callback.assert_called_once_with(msg)

    def test_send_notifies_matching_subscriber(self, ch):
        callback = MagicMock()
        ch.subscribe("sub1", callback=callback, filter_criteria={"sender": "sherlock"})
        msg = _make_msg(sender="sherlock")
        ch.send_message(msg)
        callback.assert_called_once()

    def test_send_skips_non_matching_subscriber(self, ch):
        callback = MagicMock()
        ch.subscribe("sub1", callback=callback, filter_criteria={"sender": "sherlock"})
        msg = _make_msg(sender="watson")
        ch.send_message(msg)
        callback.assert_not_called()

    def test_send_callback_error_handled(self, ch):
        callback = MagicMock(side_effect=RuntimeError("boom"))
        ch.subscribe("sub1", callback=callback)
        msg = _make_msg()
        result = ch.send_message(msg)
        assert result is True  # Doesn't raise

    # -- receive_message --

    def test_receive_message(self, ch):
        msg = _make_msg(recipient="agent_2")
        ch.send_message(msg)
        received = ch.receive_message("agent_2")
        assert received is not None
        assert received.id == msg.id
        assert len(ch._message_queue) == 0  # Removed from queue

    def test_receive_message_wildcard(self, ch):
        msg = _make_msg(recipient="anyone")
        ch.send_message(msg)
        received = ch.receive_message("*")
        assert received is not None

    def test_receive_message_no_match(self, ch):
        msg = _make_msg(recipient="agent_2")
        ch.send_message(msg)
        received = ch.receive_message("agent_3")
        assert received is None

    def test_receive_message_empty_queue(self, ch):
        assert ch.receive_message("agent_1") is None

    # -- subscribe / unsubscribe --

    def test_subscribe(self, ch):
        sub_id = ch.subscribe("sub1")
        assert sub_id.startswith("local_1_sub1_")
        assert len(ch.subscribers) == 1

    def test_subscribe_with_filter(self, ch):
        sub_id = ch.subscribe("sub1", filter_criteria={"sender": "sherlock"})
        assert ch.subscribers[sub_id]["filter"]["sender"] == "sherlock"

    def test_unsubscribe(self, ch):
        sub_id = ch.subscribe("sub1")
        assert ch.unsubscribe(sub_id) is True
        assert len(ch.subscribers) == 0

    def test_unsubscribe_nonexistent(self, ch):
        assert ch.unsubscribe("nonexistent") is False

    # -- get_pending_messages --

    def test_get_pending_messages(self, ch):
        for i in range(5):
            ch.send_message(_make_msg(recipient="agent_2"))
        pending = ch.get_pending_messages("agent_2")
        assert len(pending) == 5
        assert len(ch._message_queue) == 0

    def test_get_pending_messages_with_limit(self, ch):
        for i in range(5):
            ch.send_message(_make_msg(recipient="agent_2"))
        pending = ch.get_pending_messages("agent_2", max_count=3)
        assert len(pending) == 3
        assert len(ch._message_queue) == 2  # 2 remaining

    def test_get_pending_messages_wildcard(self, ch):
        ch.send_message(_make_msg(recipient="a"))
        ch.send_message(_make_msg(recipient="b"))
        pending = ch.get_pending_messages("*")
        assert len(pending) == 2

    def test_get_pending_messages_no_match(self, ch):
        ch.send_message(_make_msg(recipient="agent_2"))
        pending = ch.get_pending_messages("agent_3")
        assert len(pending) == 0
        assert len(ch._message_queue) == 1  # Still in queue

    # -- get_channel_info --

    def test_get_channel_info(self, ch):
        ch.subscribe("sub1")
        ch.send_message(_make_msg())
        info = ch.get_channel_info()
        assert info["id"] == "local_1"
        assert info["type"] == "local"
        assert info["subscriber_count"] == 1
        assert info["pending_message_count"] == 1
