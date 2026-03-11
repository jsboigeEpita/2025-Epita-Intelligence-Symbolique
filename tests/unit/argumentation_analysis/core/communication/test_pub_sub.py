# tests/unit/argumentation_analysis/core/communication/test_pub_sub.py
"""Tests for Topic and PublishSubscribeProtocol — pub/sub messaging."""

import pytest
from unittest.mock import MagicMock

from argumentation_analysis.core.communication.pub_sub import (
    Topic,
    PublishSubscribeProtocol,
)
from argumentation_analysis.core.communication.message import (
    Message,
    MessageType,
    MessagePriority,
    AgentLevel,
)


def _make_msg(
    msg_type=MessageType.PUBLICATION,
    sender="agent_1",
    recipient=None,
    priority=MessagePriority.NORMAL,
    sender_level=AgentLevel.OPERATIONAL,
    content=None,
    metadata=None,
):
    return Message(
        message_type=msg_type,
        sender=sender,
        sender_level=sender_level,
        content=content or {},
        recipient=recipient,
        priority=priority,
        metadata=metadata or {},
    )


# ── Topic ──

class TestTopicInit:
    def test_defaults(self):
        t = Topic("t1")
        assert t.id == "t1"
        assert t.description is None
        assert t.ttl is None
        assert len(t.subscribers) == 0
        assert len(t.messages) == 0
        assert t.max_history == 100

    def test_with_description_and_ttl(self):
        t = Topic("t1", description="Events", ttl=300)
        assert t.description == "Events"
        assert t.ttl == 300


class TestTopicSubscribers:
    @pytest.fixture
    def topic(self):
        return Topic("t1")

    def test_add_subscriber(self, topic):
        sub_id = topic.add_subscriber("agent_1")
        assert sub_id.startswith("sub-")
        assert len(topic.subscribers) == 1

    def test_add_subscriber_with_callback(self, topic):
        cb = MagicMock()
        sub_id = topic.add_subscriber("agent_1", callback=cb)
        assert topic.subscribers[sub_id]["callback"] is cb

    def test_add_subscriber_with_filter(self, topic):
        sub_id = topic.add_subscriber("agent_1", filter_criteria={"sender": "boss"})
        assert topic.subscribers[sub_id]["filter_criteria"]["sender"] == "boss"

    def test_remove_subscriber(self, topic):
        sub_id = topic.add_subscriber("agent_1")
        assert topic.remove_subscriber(sub_id) is True
        assert len(topic.subscribers) == 0

    def test_remove_subscriber_nonexistent(self, topic):
        assert topic.remove_subscriber("nope") is False

    def test_get_subscriber_count(self, topic):
        topic.add_subscriber("a")
        topic.add_subscriber("b")
        assert topic.get_subscriber_count() == 2


class TestTopicPublish:
    @pytest.fixture
    def topic(self):
        return Topic("t1")

    def test_publish_returns_recipients(self, topic):
        topic.add_subscriber("agent_1")
        topic.add_subscriber("agent_2")
        msg = _make_msg()
        recipients = topic.publish_message(msg)
        assert set(recipients) == {"agent_1", "agent_2"}

    def test_publish_adds_to_history(self, topic):
        topic.publish_message(_make_msg())
        assert topic.get_message_count() == 1

    def test_publish_calls_callback(self, topic):
        cb = MagicMock()
        topic.add_subscriber("agent_1", callback=cb)
        msg = _make_msg()
        topic.publish_message(msg)
        cb.assert_called_once_with(msg)

    def test_publish_callback_error_handled(self, topic):
        cb = MagicMock(side_effect=RuntimeError("boom"))
        topic.add_subscriber("agent_1", callback=cb)
        # Should not raise
        recipients = topic.publish_message(_make_msg())
        assert recipients == ["agent_1"]

    def test_publish_with_filter_match(self, topic):
        cb = MagicMock()
        topic.add_subscriber("agent_1", callback=cb, filter_criteria={"sender": "agent_1"})
        topic.publish_message(_make_msg(sender="agent_1"))
        cb.assert_called_once()

    def test_publish_with_filter_no_match(self, topic):
        cb = MagicMock()
        topic.add_subscriber("agent_1", callback=cb, filter_criteria={"sender": "other"})
        topic.publish_message(_make_msg(sender="agent_1"))
        cb.assert_not_called()

    def test_history_capped_at_max(self, topic):
        topic.max_history = 5
        for i in range(10):
            topic.publish_message(_make_msg(sender=f"agent_{i}"))
        assert topic.get_message_count() == 5

    def test_no_subscribers_empty_recipients(self, topic):
        recipients = topic.publish_message(_make_msg())
        assert recipients == []


class TestTopicFilter:
    @pytest.fixture
    def topic(self):
        return Topic("t1")

    def test_no_filter_matches(self, topic):
        assert topic._matches_filter(_make_msg(), None) is True
        assert topic._matches_filter(_make_msg(), {}) is True

    def test_sender_filter_match(self, topic):
        assert topic._matches_filter(
            _make_msg(sender="alice"), {"sender": "alice"}
        ) is True

    def test_sender_filter_no_match(self, topic):
        assert topic._matches_filter(
            _make_msg(sender="alice"), {"sender": "bob"}
        ) is False

    def test_sender_filter_list_match(self, topic):
        assert topic._matches_filter(
            _make_msg(sender="alice"), {"sender": ["alice", "bob"]}
        ) is True

    def test_sender_filter_list_no_match(self, topic):
        assert topic._matches_filter(
            _make_msg(sender="charlie"), {"sender": ["alice", "bob"]}
        ) is False

    def test_priority_filter_match(self, topic):
        assert topic._matches_filter(
            _make_msg(priority=MessagePriority.HIGH), {"priority": "high"}
        ) is True

    def test_priority_filter_no_match(self, topic):
        assert topic._matches_filter(
            _make_msg(priority=MessagePriority.LOW), {"priority": "high"}
        ) is False

    def test_priority_filter_list(self, topic):
        assert topic._matches_filter(
            _make_msg(priority=MessagePriority.CRITICAL), {"priority": ["high", "critical"]}
        ) is True

    def test_sender_level_filter_match(self, topic):
        assert topic._matches_filter(
            _make_msg(sender_level=AgentLevel.STRATEGIC), {"sender_level": "strategic"}
        ) is True

    def test_sender_level_filter_no_match(self, topic):
        assert topic._matches_filter(
            _make_msg(sender_level=AgentLevel.TACTICAL), {"sender_level": "strategic"}
        ) is False

    def test_content_filter_match(self, topic):
        msg = _make_msg(content={"info_type": "result", "value": 42})
        assert topic._matches_filter(msg, {"content": {"info_type": "result"}}) is True

    def test_content_filter_no_match(self, topic):
        msg = _make_msg(content={"info_type": "status"})
        assert topic._matches_filter(msg, {"content": {"info_type": "result"}}) is False

    def test_content_filter_missing_key(self, topic):
        msg = _make_msg(content={"other": "val"})
        assert topic._matches_filter(msg, {"content": {"info_type": "result"}}) is False

    def test_content_filter_list_value(self, topic):
        msg = _make_msg(content={"info_type": "result"})
        assert topic._matches_filter(
            msg, {"content": {"info_type": ["result", "status"]}}
        ) is True


class TestTopicRecentMessages:
    @pytest.fixture
    def topic(self):
        t = Topic("t1")
        for i in range(5):
            t.publish_message(_make_msg(sender=f"agent_{i}"))
        return t

    def test_get_all_recent(self, topic):
        msgs = topic.get_recent_messages()
        assert len(msgs) == 5

    def test_get_recent_with_count(self, topic):
        msgs = topic.get_recent_messages(count=3)
        assert len(msgs) == 3
        assert msgs[0].sender == "agent_2"  # Last 3

    def test_get_recent_with_filter(self, topic):
        msgs = topic.get_recent_messages(filter_criteria={"sender": "agent_0"})
        assert len(msgs) == 1
        assert msgs[0].sender == "agent_0"

    def test_get_recent_with_count_and_filter(self, topic):
        msgs = topic.get_recent_messages(count=1, filter_criteria={"sender": "agent_0"})
        assert len(msgs) == 1


class TestTopicInfo:
    def test_topic_info_empty(self):
        t = Topic("t1", description="My topic", ttl=60)
        info = t.get_topic_info()
        assert info["id"] == "t1"
        assert info["description"] == "My topic"
        assert info["ttl"] == 60
        assert info["subscriber_count"] == 0
        assert info["message_count"] == 0
        assert info["created_at"] is None
        assert info["last_message_at"] is None

    def test_topic_info_with_messages(self):
        t = Topic("t1")
        t.publish_message(_make_msg())
        info = t.get_topic_info()
        assert info["message_count"] == 1
        assert info["created_at"] is not None
        assert info["last_message_at"] is not None


# ── PublishSubscribeProtocol ──

class TestProtocolInit:
    def test_init(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        assert proto.middleware is mw
        assert len(proto.topics) == 0
        proto.shutdown()

    def test_create_topic(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        topic = proto.create_topic("t1", description="Test")
        assert topic.id == "t1"
        assert topic.description == "Test"
        proto.shutdown()

    def test_create_topic_duplicate_returns_existing(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        t1 = proto.create_topic("t1")
        t2 = proto.create_topic("t1")
        assert t1 is t2
        proto.shutdown()

    def test_get_topic(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        proto.create_topic("t1")
        assert proto.get_topic("t1") is not None
        assert proto.get_topic("nope") is None
        proto.shutdown()

    def test_delete_topic(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        proto.create_topic("t1")
        assert proto.delete_topic("t1") is True
        assert proto.get_topic("t1") is None
        proto.shutdown()

    def test_delete_topic_nonexistent(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        assert proto.delete_topic("nope") is False
        proto.shutdown()

    def test_get_topics(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        proto.create_topic("t1")
        proto.create_topic("t2")
        assert set(proto.get_topics()) == {"t1", "t2"}
        proto.shutdown()


class TestProtocolPublish:
    def test_publish_creates_topic(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        proto.publish("t1", "sender", AgentLevel.OPERATIONAL, {"data": "test"})
        assert "t1" in proto.topics
        mw.send_message.assert_called_once()
        proto.shutdown()

    def test_publish_returns_recipients(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        proto.subscribe("t1", "agent_1")
        recipients = proto.publish("t1", "sender", AgentLevel.OPERATIONAL, {"data": "test"})
        assert "agent_1" in recipients
        proto.shutdown()

    def test_subscribe_to_topic(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        sub_id = proto.subscribe("t1", "agent_1")
        assert sub_id.startswith("sub-")
        # subscribe also sends a subscription message
        mw.send_message.assert_called_once()
        proto.shutdown()

    def test_unsubscribe(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        sub_id = proto.subscribe("t1", "agent_1")
        assert proto.unsubscribe("t1", sub_id) is True
        proto.shutdown()

    def test_unsubscribe_nonexistent_topic(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        assert proto.unsubscribe("nope", "sub-123") is False
        proto.shutdown()

    def test_get_topic_info(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        proto.create_topic("t1", description="Test")
        info = proto.get_topic_info("t1")
        assert info["id"] == "t1"
        assert info["description"] == "Test"
        proto.shutdown()

    def test_get_topic_info_nonexistent(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        assert proto.get_topic_info("nope") is None
        proto.shutdown()


class TestProtocolShutdown:
    def test_shutdown(self):
        mw = MagicMock()
        proto = PublishSubscribeProtocol(mw)
        proto.shutdown()
        assert proto.running is False
