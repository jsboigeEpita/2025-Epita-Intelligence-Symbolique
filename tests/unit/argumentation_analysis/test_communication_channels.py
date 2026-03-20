# -*- coding: utf-8 -*-
"""
Unit tests for the communication system channels and middleware.

Tests cover:
- Message creation, serialization, ordering
- HierarchicalChannel: send/receive, priority ordering, subscriptions
- CollaborationChannel: groups, direct/group messaging
- DataChannel: storage, versioning, compression
- MessageMiddleware: routing, handler registration, statistics
- PublishSubscribeProtocol: topics, subscriptions, TTL
"""

import json
import time
import threading
import pytest
from unittest.mock import MagicMock

from argumentation_analysis.core.communication.message import (
    Message,
    MessageType,
    MessagePriority,
    AgentLevel,
    CommandMessage,
    InformationMessage,
    RequestMessage,
    EventMessage,
)
from argumentation_analysis.core.communication.channel_interface import (
    Channel,
    ChannelType,
    ChannelException,
    ChannelFullException,
    ChannelTimeoutException,
)
from argumentation_analysis.core.communication.hierarchical_channel import (
    HierarchicalChannel,
)
from argumentation_analysis.core.communication.collaboration_channel import (
    CollaborationChannel,
    CollaborationGroup,
)
from argumentation_analysis.core.communication.data_channel import (
    DataChannel,
    DataStore,
)
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.pub_sub import (
    Topic,
    PublishSubscribeProtocol,
)

# ===========================================================================
# Message Tests
# ===========================================================================


class TestMessage:
    """Unit tests for Message and specialized message classes."""

    def test_message_creation(self):
        msg = Message(
            message_type=MessageType.INFORMATION,
            sender="agent-1",
            sender_level=AgentLevel.TACTICAL,
            content={"key": "value"},
        )
        assert msg.sender == "agent-1"
        assert msg.type == MessageType.INFORMATION
        assert msg.sender_level == AgentLevel.TACTICAL
        assert msg.content == {"key": "value"}
        assert msg.id is not None
        assert msg.timestamp is not None

    def test_message_serialization_roundtrip(self):
        msg = Message(
            message_type=MessageType.COMMAND,
            sender="agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command": "analyze"},
            recipient="agent-2",
            priority=MessagePriority.HIGH,
        )
        data = msg.to_dict()
        restored = Message.from_dict(data)
        assert restored.id == msg.id
        assert restored.sender == msg.sender
        assert restored.content == msg.content
        assert restored.recipient == msg.recipient

    def test_message_priority_ordering(self):
        """Critical messages should sort before low-priority ones."""
        critical = Message(
            MessageType.COMMAND,
            "a",
            AgentLevel.STRATEGIC,
            {},
            priority=MessagePriority.CRITICAL,
        )
        time.sleep(0.001)  # ensure different timestamps
        low = Message(
            MessageType.INFORMATION,
            "b",
            AgentLevel.OPERATIONAL,
            {},
            priority=MessagePriority.LOW,
        )
        assert critical < low  # critical should come first in sorted order

    def test_message_response_creation(self):
        original = Message(
            MessageType.REQUEST,
            "agent-1",
            AgentLevel.TACTICAL,
            {"request_type": "help"},
            recipient="agent-2",
        )
        response = original.create_response(content={"answer": "done"})
        assert response.recipient == "agent-1"
        assert response.type == MessageType.RESPONSE
        assert response.metadata.get("reply_to") == original.id

    def test_message_acknowledgement(self):
        msg = Message(
            MessageType.COMMAND,
            "agent-1",
            AgentLevel.STRATEGIC,
            {"action": "start"},
            recipient="agent-2",
        )
        ack = msg.create_acknowledgement()
        assert ack.type == MessageType.RESPONSE  # ACK is a RESPONSE type
        assert ack.metadata.get("reply_to") == msg.id

    def test_command_message(self):
        cmd = CommandMessage(
            sender="strategic-1",
            sender_level=AgentLevel.STRATEGIC,
            command_type="analyze",
            parameters={"text_id": "t1"},
            recipient="tactical-1",
        )
        assert cmd.type == MessageType.COMMAND
        assert cmd.content["command_type"] == "analyze"
        assert cmd.priority == MessagePriority.HIGH

    def test_information_message(self):
        info = InformationMessage(
            sender="tactical-1",
            sender_level=AgentLevel.TACTICAL,
            info_type="status_update",
            data={"progress": 50},
        )
        assert info.type == MessageType.INFORMATION
        assert info.content["info_type"] == "status_update"

    def test_request_message(self):
        req = RequestMessage(
            sender="tactical-1",
            sender_level=AgentLevel.TACTICAL,
            request_type="guidance",
            description="Need help",
            context={"task": "analysis"},
            recipient="strategic-1",
        )
        assert req.type == MessageType.REQUEST
        assert req.content["request_type"] == "guidance"

    def test_event_message(self):
        evt = EventMessage(
            sender="system",
            sender_level=AgentLevel.SYSTEM,
            event_type="resource_low",
            description="CPU at 95%",
            details={"cpu": 95},
        )
        assert evt.type == MessageType.EVENT
        assert evt.priority == MessagePriority.HIGH


# ===========================================================================
# HierarchicalChannel Tests
# ===========================================================================


class TestHierarchicalChannel:
    """Unit tests for HierarchicalChannel."""

    @pytest.fixture
    def channel(self):
        return HierarchicalChannel("test-hierarchical")

    def test_send_and_receive(self, channel):
        msg = Message(
            MessageType.COMMAND,
            "strategic-1",
            AgentLevel.STRATEGIC,
            {"action": "analyze"},
            recipient="tactical-1",
        )
        assert channel.send_message(msg) is True

        received = channel.receive_message("tactical-1", timeout=1.0)
        assert received is not None
        assert received.id == msg.id

    def test_receive_returns_none_on_timeout(self, channel):
        result = channel.receive_message("nobody", timeout=0.1)
        assert result is None

    def test_priority_ordering(self, channel):
        """Higher priority messages should be received first."""
        low = Message(
            MessageType.INFORMATION,
            "a",
            AgentLevel.TACTICAL,
            {"p": "low"},
            recipient="agent-1",
            priority=MessagePriority.LOW,
        )
        high = Message(
            MessageType.COMMAND,
            "a",
            AgentLevel.STRATEGIC,
            {"p": "high"},
            recipient="agent-1",
            priority=MessagePriority.HIGH,
        )
        channel.send_message(low)
        channel.send_message(high)

        first = channel.receive_message("agent-1", timeout=1.0)
        assert first.content["p"] == "high"

    def test_get_pending_messages(self, channel):
        for i in range(5):
            msg = Message(
                MessageType.INFORMATION,
                "sender",
                AgentLevel.TACTICAL,
                {"i": i},
                recipient="agent-1",
            )
            channel.send_message(msg)

        pending = channel.get_pending_messages("agent-1", max_count=3)
        assert len(pending) == 3

    def test_subscribe_and_callback(self, channel):
        callback = MagicMock()
        sub_id = channel.subscribe("agent-1", callback=callback)
        assert sub_id is not None

        msg = Message(
            MessageType.INFORMATION,
            "sender",
            AgentLevel.TACTICAL,
            {"data": "test"},
            recipient="agent-1",
        )
        channel.send_message(msg)

        # Give callback time to fire
        time.sleep(0.1)
        callback.assert_called_once()

    def test_unsubscribe(self, channel):
        sub_id = channel.subscribe("agent-1")
        assert channel.unsubscribe(sub_id) is True

    def test_channel_info(self, channel):
        info = channel.get_channel_info()
        assert info["id"] == "test-hierarchical"
        assert info["type"] == ChannelType.HIERARCHICAL.value

    def test_clear_queue(self, channel):
        for i in range(3):
            msg = Message(
                MessageType.INFORMATION,
                "s",
                AgentLevel.TACTICAL,
                {},
                recipient="agent-1",
            )
            channel.send_message(msg)

        cleared = channel.clear_queue("agent-1")
        assert cleared == 3
        assert channel.receive_message("agent-1", timeout=0.1) is None


# ===========================================================================
# CollaborationChannel Tests
# ===========================================================================


class TestCollaborationChannel:
    """Unit tests for CollaborationChannel and CollaborationGroup."""

    @pytest.fixture
    def channel(self):
        return CollaborationChannel("test-collab")

    def test_group_creation(self):
        group = CollaborationGroup("g1", name="Analysts", members=["a1", "a2"])
        assert group.id == "g1"
        assert group.name == "Analysts"
        assert "a1" in group.members
        assert group.get_member_count() == 2

    def test_group_add_remove_member(self):
        group = CollaborationGroup("g1")
        assert group.add_member("agent-1") is True
        assert group.add_member("agent-1") is False  # already member
        assert group.get_member_count() == 1
        assert group.remove_member("agent-1") is True
        assert group.get_member_count() == 0

    def test_create_group_via_channel(self, channel):
        group_id = channel.create_group(name="Team A", members=["a1", "a2"])
        assert group_id is not None
        groups = channel.get_groups()
        assert group_id in groups

    def test_send_direct_message(self, channel):
        msg = Message(
            MessageType.INFORMATION,
            "agent-1",
            AgentLevel.TACTICAL,
            {"info": "hello"},
            recipient="agent-2",
        )
        assert channel.send_message(msg) is True

        received = channel.receive_message("agent-2", timeout=1.0)
        assert received is not None
        assert received.content["info"] == "hello"

    def test_group_messaging(self, channel):
        group_id = channel.create_group(name="Team", members=["a1", "a2", "a3"])
        msg = Message(
            MessageType.INFORMATION,
            "a1",
            AgentLevel.TACTICAL,
            {"info": "group msg"},
            metadata={"group_id": group_id},  # routing via metadata
        )
        channel.send_message(msg)

        messages = channel.get_group_messages(group_id, count=10)
        assert len(messages) >= 1

    def test_delete_group(self, channel):
        group_id = channel.create_group(name="Temp")
        assert channel.delete_group(group_id) is True
        assert channel.get_group_info(group_id) is None

    def test_agent_groups(self, channel):
        g1 = channel.create_group(members=["agent-1", "agent-2"])
        g2 = channel.create_group(members=["agent-1", "agent-3"])
        groups = channel.get_agent_groups("agent-1")
        assert len(groups) == 2

    def test_channel_info(self, channel):
        info = channel.get_channel_info()
        assert info["type"] == ChannelType.COLLABORATION.value


# ===========================================================================
# DataChannel Tests
# ===========================================================================


class TestDataStore:
    """Unit tests for DataStore."""

    @pytest.fixture
    def store(self):
        return DataStore("test-store")

    def test_store_and_retrieve(self, store):
        version_id = store.store_data("d1", {"key": "value"}, compress=False)
        assert version_id is not None

        data, metadata = store.get_data("d1", version_id)
        assert data == {"key": "value"}

    def test_versioning(self, store):
        v1 = store.store_data("d1", {"version": 1}, compress=False)
        v2 = store.store_data("d1", {"version": 2}, compress=False)
        assert v1 != v2

        versions = store.get_versions("d1")
        assert len(versions) == 2

        data_v1, _ = store.get_data("d1", v1)
        data_v2, _ = store.get_data("d1", v2)
        assert data_v1["version"] == 1
        assert data_v2["version"] == 2

    def test_latest_version(self, store):
        store.store_data("d1", {"v": 1}, compress=False)
        store.store_data("d1", {"v": 2}, compress=False)

        data, _ = store.get_data("d1")  # no version = latest
        assert data["v"] == 2

    def test_delete_data(self, store):
        v1 = store.store_data("d1", {"data": "x"}, compress=False)
        assert store.delete_data("d1", v1) is True
        assert store.get_versions("d1") == []

    def test_data_info(self, store):
        store.store_data(
            "d1", {"data": "x"}, metadata={"owner": "agent-1"}, compress=False
        )
        info = store.get_data_info("d1")
        assert info is not None
        assert info["metadata"]["owner"] == "agent-1"


class TestDataChannel:
    """Unit tests for DataChannel."""

    @pytest.fixture
    def channel(self, tmp_path):
        return DataChannel(str(tmp_path))

    def test_store_and_get_data(self, channel):
        version_id = channel.store_data("d1", {"key": "value"}, compress=False)
        data, metadata = channel.get_data("d1", version_id)
        assert data == {"key": "value"}

    def test_send_message_with_data(self, channel):
        msg = Message(
            MessageType.INFORMATION,
            "agent-1",
            AgentLevel.TACTICAL,
            {"data_id": "d1", "info": "dataset ready"},
            recipient="agent-2",
        )
        assert channel.send_message(msg) is True

        received = channel.receive_message("agent-2", timeout=1.0)
        assert received is not None

    def test_channel_info(self, channel):
        info = channel.get_channel_info()
        assert info["type"] == ChannelType.DATA.value


# ===========================================================================
# Middleware Tests
# ===========================================================================


class TestMessageMiddleware:
    """Unit tests for MessageMiddleware."""

    @pytest.fixture
    def middleware(self):
        mw = MessageMiddleware()
        mw.register_channel(HierarchicalChannel("hier"))
        mw.register_channel(CollaborationChannel("collab"))
        return mw

    def test_register_channel(self, middleware):
        ch = middleware.get_channel(ChannelType.HIERARCHICAL)
        assert ch is not None

    def test_determine_channel_command(self, middleware):
        msg = Message(
            MessageType.COMMAND,
            "s",
            AgentLevel.STRATEGIC,
            {},
            recipient="t",
        )
        ch_type = middleware.determine_channel(msg)
        assert ch_type == ChannelType.HIERARCHICAL

    def test_determine_channel_information(self, middleware):
        msg = Message(
            MessageType.INFORMATION,
            "s",
            AgentLevel.TACTICAL,
            {},
            recipient="t",
        )
        ch_type = middleware.determine_channel(msg)
        # Information typically routes to hierarchical
        assert ch_type in (ChannelType.HIERARCHICAL, ChannelType.COLLABORATION)

    def test_send_and_receive_via_middleware(self, middleware):
        msg = CommandMessage(
            "strategic-1",
            AgentLevel.STRATEGIC,
            "analyze",
            {"text": "hello"},
            "tactical-1",
        )
        assert middleware.send_message(msg) is True

        received = middleware.receive_message(
            "tactical-1",
            channel_type=ChannelType.HIERARCHICAL,
            timeout=1.0,
        )
        assert received is not None
        assert received.id == msg.id

    def test_message_handler_registration(self, middleware):
        """Handlers fire when messages are received (not sent)."""
        handler = MagicMock()
        middleware.register_message_handler(MessageType.COMMAND, handler)

        msg = CommandMessage(
            "strategic-1",
            AgentLevel.STRATEGIC,
            "test",
            {},
            "tactical-1",
        )
        middleware.send_message(msg)

        # Handlers are triggered on receive_message, not send_message
        middleware.receive_message(
            "tactical-1",
            channel_type=ChannelType.HIERARCHICAL,
            timeout=1.0,
        )
        handler.assert_called_once()

    def test_global_handler(self, middleware):
        """Global handlers fire when messages are received."""
        handler = MagicMock()
        middleware.register_global_handler(handler)

        msg = Message(
            MessageType.INFORMATION,
            "s",
            AgentLevel.TACTICAL,
            {},
            recipient="r",
        )
        middleware.send_message(msg)

        # Trigger handlers by receiving the message
        middleware.receive_message(
            "r",
            channel_type=ChannelType.HIERARCHICAL,
            timeout=1.0,
        )
        handler.assert_called_once()

    def test_statistics(self, middleware):
        msg = Message(
            MessageType.COMMAND,
            "s",
            AgentLevel.STRATEGIC,
            {},
            recipient="r",
        )
        middleware.send_message(msg)
        stats = middleware.get_statistics()
        assert stats["messages_sent"] >= 1

    def test_get_pending_messages(self, middleware):
        for i in range(3):
            msg = Message(
                MessageType.INFORMATION,
                "s",
                AgentLevel.TACTICAL,
                {"i": i},
                recipient="agent-1",
            )
            middleware.send_message(msg)

        pending = middleware.get_pending_messages(
            "agent-1",
            channel_type=ChannelType.HIERARCHICAL,
        )
        assert len(pending) >= 1

    def test_shutdown(self, middleware):
        middleware.initialize_protocols()
        middleware.shutdown()  # should not raise


# ===========================================================================
# PubSub Tests
# ===========================================================================


class TestTopic:
    """Unit tests for Topic."""

    def test_create_topic(self):
        topic = Topic("events.system", description="System events")
        assert topic.id == "events.system"
        assert topic.get_subscriber_count() == 0
        assert topic.get_message_count() == 0

    def test_subscribe_and_publish(self):
        topic = Topic("test-topic")
        callback = MagicMock()
        sub_id = topic.add_subscriber("agent-1", callback=callback)
        assert sub_id is not None

        msg = Message(
            MessageType.PUBLICATION,
            "system",
            AgentLevel.SYSTEM,
            {"event": "update"},
        )
        notified = topic.publish_message(msg)
        assert "agent-1" in notified
        callback.assert_called_once()

    def test_unsubscribe(self):
        topic = Topic("test-topic")
        sub_id = topic.add_subscriber("agent-1")
        assert topic.get_subscriber_count() == 1
        assert topic.remove_subscriber(sub_id) is True
        assert topic.get_subscriber_count() == 0

    def test_recent_messages(self):
        topic = Topic("test-topic")
        for i in range(5):
            msg = Message(
                MessageType.PUBLICATION,
                "system",
                AgentLevel.SYSTEM,
                {"i": i},
            )
            topic.publish_message(msg)

        recent = topic.get_recent_messages(count=3)
        assert len(recent) == 3

    def test_publish_notifies_all_subscribers(self):
        """All subscribers receive published messages."""
        topic = Topic("test-topic")
        cb1 = MagicMock()
        cb2 = MagicMock()
        topic.add_subscriber("agent-1", callback=cb1)
        topic.add_subscriber("agent-2", callback=cb2)

        msg = Message(MessageType.PUBLICATION, "s", AgentLevel.SYSTEM, {"data": 1})
        topic.publish_message(msg)

        cb1.assert_called_once()
        cb2.assert_called_once()

    def test_topic_info(self):
        topic = Topic("test-topic", description="Test")
        topic.add_subscriber("a1")
        info = topic.get_topic_info()
        assert info["id"] == "test-topic"
        assert info["subscriber_count"] == 1


class TestPublishSubscribeProtocol:
    """Unit tests for PublishSubscribeProtocol."""

    @pytest.fixture
    def protocol(self):
        middleware = MagicMock()
        proto = PublishSubscribeProtocol(middleware)
        return proto

    def test_create_topic(self, protocol):
        topic = protocol.create_topic("events.system", description="System events")
        assert topic is not None
        assert "events.system" in protocol.get_topics()

    def test_publish_to_topic(self, protocol):
        protocol.create_topic("test-topic")
        callback = MagicMock()
        protocol.subscribe("test-topic", "agent-1", callback=callback)

        notified = protocol.publish(
            "test-topic",
            "system",
            AgentLevel.SYSTEM,
            content={"event": "update"},
        )
        assert len(notified) >= 1
        callback.assert_called_once()

    def test_unsubscribe(self, protocol):
        protocol.create_topic("test-topic")
        sub_id = protocol.subscribe("test-topic", "agent-1")
        assert protocol.unsubscribe("test-topic", sub_id) is True

    def test_delete_topic(self, protocol):
        protocol.create_topic("temp-topic")
        assert protocol.delete_topic("temp-topic") is True
        assert "temp-topic" not in protocol.get_topics()

    def test_get_topic_info(self, protocol):
        protocol.create_topic("test-topic", description="Test")
        info = protocol.get_topic_info("test-topic")
        assert info is not None
        assert info["id"] == "test-topic"

    def test_shutdown(self, protocol):
        protocol.shutdown()  # should not raise
