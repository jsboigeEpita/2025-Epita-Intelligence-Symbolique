# tests/unit/argumentation_analysis/core/communication/test_hierarchical_channel.py
"""Tests for HierarchicalChannel — priority queues, direction stats, clear_queue."""

import pytest
from unittest.mock import MagicMock

from argumentation_analysis.core.communication.hierarchical_channel import (
    HierarchicalChannel,
)
from argumentation_analysis.core.communication.channel_interface import ChannelType
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


# ── Init ──

class TestInit:
    def test_channel_type(self):
        ch = HierarchicalChannel("h1")
        assert ch.type == ChannelType.HIERARCHICAL

    def test_channel_id(self):
        ch = HierarchicalChannel("h1")
        assert ch.id == "h1"

    def test_empty_queues(self):
        ch = HierarchicalChannel("h1")
        assert ch.message_queues == {}

    def test_initial_stats(self):
        ch = HierarchicalChannel("h1")
        assert ch.stats["messages_sent"] == 0
        assert ch.stats["messages_received"] == 0
        assert ch.stats["by_priority"]["normal"] == 0


# ── send_message ──

class TestSendMessage:
    @pytest.fixture
    def ch(self):
        return HierarchicalChannel("h1")

    def test_send_returns_true(self, ch):
        msg = _make_msg()
        assert ch.send_message(msg) is True

    def test_send_increments_stats(self, ch):
        ch.send_message(_make_msg())
        assert ch.stats["messages_sent"] == 1

    def test_send_tracks_priority(self, ch):
        ch.send_message(_make_msg(priority=MessagePriority.HIGH))
        assert ch.stats["by_priority"]["high"] == 1

    def test_send_no_recipient_returns_false(self, ch):
        msg = _make_msg(recipient=None)
        assert ch.send_message(msg) is False

    def test_send_creates_queue_for_recipient(self, ch):
        ch.send_message(_make_msg(recipient="bob"))
        assert "bob" in ch.message_queues

    def test_send_multiple_messages(self, ch):
        for _ in range(5):
            ch.send_message(_make_msg())
        assert ch.stats["messages_sent"] == 5

    def test_send_non_ideal_type_still_succeeds(self, ch):
        msg = _make_msg(msg_type=MessageType.EVENT)
        assert ch.send_message(msg) is True


# ── Direction tracking ──

class TestDirectionStats:
    @pytest.fixture
    def ch(self):
        return HierarchicalChannel("h1")

    def test_strategic_to_tactical(self, ch):
        msg = _make_msg(
            sender_level=AgentLevel.STRATEGIC, recipient="tactical_agent"
        )
        ch.send_message(msg)
        assert ch.stats["by_direction"]["strategic_to_tactical"] == 1

    def test_tactical_to_strategic(self, ch):
        msg = _make_msg(
            sender_level=AgentLevel.TACTICAL, recipient="strategic_agent"
        )
        ch.send_message(msg)
        assert ch.stats["by_direction"]["tactical_to_strategic"] == 1

    def test_tactical_to_operational(self, ch):
        msg = _make_msg(
            sender_level=AgentLevel.TACTICAL, recipient="operational_agent"
        )
        ch.send_message(msg)
        assert ch.stats["by_direction"]["tactical_to_operational"] == 1

    def test_operational_to_tactical(self, ch):
        msg = _make_msg(
            sender_level=AgentLevel.OPERATIONAL, recipient="tactical_agent"
        )
        ch.send_message(msg)
        assert ch.stats["by_direction"]["operational_to_tactical"] == 1

    def test_same_level(self, ch):
        msg = _make_msg(
            sender_level=AgentLevel.OPERATIONAL, recipient="other_operational"
        )
        ch.send_message(msg)
        assert ch.stats["by_direction"]["same_level"] == 1


# ── receive_message ──

class TestReceiveMessage:
    @pytest.fixture
    def ch(self):
        return HierarchicalChannel("h1")

    def test_receive_returns_message(self, ch):
        msg = _make_msg(recipient="bob")
        ch.send_message(msg)
        received = ch.receive_message("bob", timeout=0.1)
        assert received is not None
        assert received.id == msg.id

    def test_receive_increments_stats(self, ch):
        ch.send_message(_make_msg(recipient="bob"))
        ch.receive_message("bob", timeout=0.1)
        assert ch.stats["messages_received"] == 1

    def test_receive_empty_queue_returns_none(self, ch):
        result = ch.receive_message("bob", timeout=0.01)
        assert result is None

    def test_receive_priority_order(self, ch):
        low = _make_msg(recipient="bob", priority=MessagePriority.LOW)
        high = _make_msg(recipient="bob", priority=MessagePriority.HIGH)
        critical = _make_msg(recipient="bob", priority=MessagePriority.CRITICAL)
        # Send in random order
        ch.send_message(low)
        ch.send_message(critical)
        ch.send_message(high)
        # Receive should return critical first, then high, then low
        r1 = ch.receive_message("bob", timeout=0.1)
        r2 = ch.receive_message("bob", timeout=0.1)
        r3 = ch.receive_message("bob", timeout=0.1)
        assert r1.id == critical.id
        assert r2.id == high.id
        assert r3.id == low.id


# ── subscribe / unsubscribe ──

class TestSubscribe:
    @pytest.fixture
    def ch(self):
        return HierarchicalChannel("h1")

    def test_subscribe_returns_id(self, ch):
        sub_id = ch.subscribe("agent_1")
        assert sub_id.startswith("sub-")

    def test_subscribe_adds_subscriber(self, ch):
        ch.subscribe("agent_1")
        assert len(ch.subscribers) == 1

    def test_subscribe_with_filter(self, ch):
        sub_id = ch.subscribe("agent_1", filter_criteria={"sender": "boss"})
        assert ch.subscribers[sub_id]["filter_criteria"]["sender"] == "boss"

    def test_unsubscribe_success(self, ch):
        sub_id = ch.subscribe("agent_1")
        assert ch.unsubscribe(sub_id) is True
        assert len(ch.subscribers) == 0

    def test_unsubscribe_nonexistent(self, ch):
        assert ch.unsubscribe("nonexistent") is False

    def test_subscriber_callback_on_send(self, ch):
        callback = MagicMock()
        ch.subscribe("sub1", callback=callback)
        msg = _make_msg()
        ch.send_message(msg)
        callback.assert_called_once_with(msg)

    def test_subscriber_callback_with_filter_match(self, ch):
        callback = MagicMock()
        ch.subscribe("sub1", callback=callback, filter_criteria={"sender": "agent_1"})
        ch.send_message(_make_msg(sender="agent_1"))
        callback.assert_called_once()

    def test_subscriber_callback_with_filter_no_match(self, ch):
        callback = MagicMock()
        ch.subscribe("sub1", callback=callback, filter_criteria={"sender": "agent_1"})
        ch.send_message(_make_msg(sender="other"))
        callback.assert_not_called()

    def test_subscriber_callback_error_handled(self, ch):
        callback = MagicMock(side_effect=RuntimeError("boom"))
        ch.subscribe("sub1", callback=callback)
        # Should not raise
        assert ch.send_message(_make_msg()) is True


# ── get_pending_messages ──

class TestGetPendingMessages:
    @pytest.fixture
    def ch(self):
        return HierarchicalChannel("h1")

    def test_get_all_pending(self, ch):
        for _ in range(3):
            ch.send_message(_make_msg(recipient="bob"))
        pending = ch.get_pending_messages("bob")
        assert len(pending) == 3

    def test_get_pending_with_limit(self, ch):
        for _ in range(5):
            ch.send_message(_make_msg(recipient="bob"))
        pending = ch.get_pending_messages("bob", max_count=2)
        assert len(pending) == 2

    def test_get_pending_preserves_queue(self, ch):
        for _ in range(3):
            ch.send_message(_make_msg(recipient="bob"))
        ch.get_pending_messages("bob")
        # Messages should still be in the queue (get_pending_messages preserves them)
        assert ch.message_queues["bob"].qsize() == 3

    def test_get_pending_empty(self, ch):
        pending = ch.get_pending_messages("nonexistent")
        assert pending == []


# ── clear_queue ──

class TestClearQueue:
    @pytest.fixture
    def ch(self):
        return HierarchicalChannel("h1")

    def test_clear_returns_count(self, ch):
        for _ in range(3):
            ch.send_message(_make_msg(recipient="bob"))
        count = ch.clear_queue("bob")
        assert count == 3

    def test_clear_empties_queue(self, ch):
        for _ in range(3):
            ch.send_message(_make_msg(recipient="bob"))
        ch.clear_queue("bob")
        assert ch.message_queues["bob"].qsize() == 0

    def test_clear_nonexistent_returns_zero(self, ch):
        assert ch.clear_queue("nobody") == 0


# ── get_channel_info ──

class TestGetChannelInfo:
    def test_channel_info(self):
        ch = HierarchicalChannel("h1")
        ch.subscribe("sub1")
        ch.send_message(_make_msg(recipient="bob"))
        info = ch.get_channel_info()
        assert info["id"] == "h1"
        assert info["type"] == "hierarchical"
        assert info["subscriber_count"] == 1
        assert info["queue_sizes"]["bob"] == 1
        assert info["stats"]["messages_sent"] == 1
