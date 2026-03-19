# tests/unit/argumentation_analysis/core/communication/test_message.py
"""Tests for Message data structures and specialized message subclasses."""

import pytest
from datetime import datetime

from argumentation_analysis.core.communication.message import (
    MessageType,
    MessagePriority,
    AgentLevel,
    Message,
    CommandMessage,
    InformationMessage,
    RequestMessage,
    EventMessage,
)

# ── Enums ──


class TestMessageType:
    def test_all_values(self):
        assert MessageType.COMMAND.value == "command"
        assert MessageType.INFORMATION.value == "information"
        assert MessageType.REQUEST.value == "request"
        assert MessageType.RESPONSE.value == "response"
        assert MessageType.EVENT.value == "event"
        assert MessageType.CONTROL.value == "control"
        assert MessageType.PUBLICATION.value == "publication"
        assert MessageType.SUBSCRIPTION.value == "subscription"

    def test_count(self):
        assert len(MessageType) == 8


class TestMessagePriority:
    def test_all_values(self):
        assert MessagePriority.LOW.value == "low"
        assert MessagePriority.NORMAL.value == "normal"
        assert MessagePriority.HIGH.value == "high"
        assert MessagePriority.CRITICAL.value == "critical"

    def test_count(self):
        assert len(MessagePriority) == 4


class TestAgentLevel:
    def test_all_values(self):
        assert AgentLevel.STRATEGIC.value == "strategic"
        assert AgentLevel.TACTICAL.value == "tactical"
        assert AgentLevel.OPERATIONAL.value == "operational"
        assert AgentLevel.SYSTEM.value == "system"

    def test_count(self):
        assert len(AgentLevel) == 4


# ── Message ──


class TestMessage:
    @pytest.fixture
    def basic_msg(self):
        return Message(
            message_type=MessageType.COMMAND,
            sender="agent_1",
            sender_level=AgentLevel.STRATEGIC,
            content={"action": "analyze"},
            recipient="agent_2",
        )

    def test_auto_id(self, basic_msg):
        assert basic_msg.id.startswith("command-")

    def test_explicit_id(self):
        msg = Message(
            message_type=MessageType.COMMAND,
            sender="a",
            sender_level=AgentLevel.OPERATIONAL,
            content={},
            message_id="custom-id",
        )
        assert msg.id == "custom-id"

    def test_auto_timestamp(self, basic_msg):
        assert isinstance(basic_msg.timestamp, datetime)

    def test_explicit_timestamp(self):
        ts = datetime(2026, 1, 1, 12, 0)
        msg = Message(
            message_type=MessageType.INFORMATION,
            sender="a",
            sender_level=AgentLevel.TACTICAL,
            content={},
            timestamp=ts,
        )
        assert msg.timestamp == ts

    def test_default_priority(self, basic_msg):
        # Default is NORMAL
        assert basic_msg.priority == MessagePriority.NORMAL

    def test_custom_priority(self):
        msg = Message(
            message_type=MessageType.EVENT,
            sender="a",
            sender_level=AgentLevel.SYSTEM,
            content={},
            priority=MessagePriority.CRITICAL,
        )
        assert msg.priority == MessagePriority.CRITICAL

    def test_metadata_default_empty(self):
        msg = Message(
            message_type=MessageType.INFORMATION,
            sender="a",
            sender_level=AgentLevel.OPERATIONAL,
            content={},
        )
        assert msg.metadata == {}

    def test_recipient_default_none(self):
        msg = Message(
            message_type=MessageType.EVENT,
            sender="a",
            sender_level=AgentLevel.OPERATIONAL,
            content={},
        )
        assert msg.recipient is None

    # -- Equality --
    def test_eq_same(self, basic_msg):
        assert basic_msg == basic_msg

    def test_eq_not_message(self, basic_msg):
        assert basic_msg != "not a message"

    def test_eq_different_id(self):
        ts = datetime(2026, 1, 1)
        m1 = Message(
            MessageType.COMMAND,
            "a",
            AgentLevel.SYSTEM,
            {},
            message_id="id1",
            timestamp=ts,
        )
        m2 = Message(
            MessageType.COMMAND,
            "a",
            AgentLevel.SYSTEM,
            {},
            message_id="id2",
            timestamp=ts,
        )
        assert m1 != m2

    # -- Ordering --
    def test_lt_higher_priority_first(self):
        ts = datetime(2026, 1, 1)
        m_high = Message(
            MessageType.COMMAND,
            "a",
            AgentLevel.SYSTEM,
            {},
            priority=MessagePriority.HIGH,
            message_id="h",
            timestamp=ts,
        )
        m_low = Message(
            MessageType.COMMAND,
            "a",
            AgentLevel.SYSTEM,
            {},
            priority=MessagePriority.LOW,
            message_id="l",
            timestamp=ts,
        )
        assert m_high < m_low  # Higher priority is "less" (comes first)

    def test_lt_same_priority_older_first(self):
        m_old = Message(
            MessageType.COMMAND,
            "a",
            AgentLevel.SYSTEM,
            {},
            priority=MessagePriority.NORMAL,
            message_id="o",
            timestamp=datetime(2026, 1, 1),
        )
        m_new = Message(
            MessageType.COMMAND,
            "a",
            AgentLevel.SYSTEM,
            {},
            priority=MessagePriority.NORMAL,
            message_id="n",
            timestamp=datetime(2026, 1, 2),
        )
        assert m_old < m_new  # Older timestamp comes first

    def test_lt_not_message(self, basic_msg):
        assert basic_msg.__lt__("not a message") == NotImplemented

    # -- Serialization --
    def test_to_dict(self, basic_msg):
        d = basic_msg.to_dict()
        assert d["sender"] == "agent_1"
        assert d["sender_level"] == "strategic"
        assert d["type"] == "command"
        assert d["recipient"] == "agent_2"
        assert d["priority"] == "normal"
        assert d["content"] == {"action": "analyze"}
        assert "id" in d
        assert "timestamp" in d

    def test_from_dict_roundtrip(self, basic_msg):
        d = basic_msg.to_dict()
        restored = Message.from_dict(d)
        assert restored.id == basic_msg.id
        assert restored.sender == basic_msg.sender
        assert restored.sender_level == basic_msg.sender_level
        assert restored.type == basic_msg.type
        assert restored.content == basic_msg.content

    # -- is_response_to --
    def test_is_response_to_true(self):
        msg = Message(
            MessageType.RESPONSE,
            "b",
            AgentLevel.OPERATIONAL,
            {},
            metadata={"reply_to": "req-123"},
        )
        assert msg.is_response_to("req-123") is True

    def test_is_response_to_wrong_id(self):
        msg = Message(
            MessageType.RESPONSE,
            "b",
            AgentLevel.OPERATIONAL,
            {},
            metadata={"reply_to": "req-123"},
        )
        assert msg.is_response_to("req-456") is False

    def test_is_response_to_not_response_type(self):
        msg = Message(
            MessageType.COMMAND,
            "b",
            AgentLevel.OPERATIONAL,
            {},
            metadata={"reply_to": "req-123"},
        )
        assert msg.is_response_to("req-123") is False

    # -- requires_acknowledgement --
    def test_requires_ack_true(self):
        msg = Message(
            MessageType.COMMAND,
            "a",
            AgentLevel.STRATEGIC,
            {},
            metadata={"requires_ack": True},
        )
        assert msg.requires_acknowledgement() is True

    def test_requires_ack_false_default(self, basic_msg):
        assert basic_msg.requires_acknowledgement() is False

    # -- create_response --
    def test_create_response(self, basic_msg):
        response = basic_msg.create_response({"result": "ok"})
        assert response.type == MessageType.RESPONSE
        assert response.sender == basic_msg.recipient
        assert response.recipient == basic_msg.sender
        assert response.metadata["reply_to"] == basic_msg.id
        assert response.priority == basic_msg.priority

    def test_create_response_custom_priority(self, basic_msg):
        response = basic_msg.create_response(
            {"result": "urgent"},
            priority=MessagePriority.CRITICAL,
        )
        assert response.priority == MessagePriority.CRITICAL

    def test_create_response_custom_sender_level(self, basic_msg):
        response = basic_msg.create_response(
            {"result": "ok"},
            sender_level=AgentLevel.TACTICAL,
        )
        assert response.sender_level == AgentLevel.TACTICAL

    # -- create_acknowledgement --
    def test_create_acknowledgement(self, basic_msg):
        ack = basic_msg.create_acknowledgement()
        assert ack.type == MessageType.RESPONSE
        assert ack.content["status"] == "acknowledged"
        assert ack.content["message_id"] == basic_msg.id
        assert ack.metadata["reply_to"] == basic_msg.id
        assert ack.metadata["acknowledgement"] is True


# ── CommandMessage ──


class TestCommandMessage:
    def test_basic(self):
        msg = CommandMessage(
            sender="strategic_agent",
            sender_level=AgentLevel.STRATEGIC,
            command_type="execute_analysis",
            parameters={"text": "sample"},
            recipient="operational_agent",
        )
        assert msg.type == MessageType.COMMAND
        assert msg.content["command_type"] == "execute_analysis"
        assert msg.content["parameters"]["text"] == "sample"
        assert msg.priority == MessagePriority.HIGH  # default for command

    def test_with_constraints(self):
        msg = CommandMessage(
            sender="s",
            sender_level=AgentLevel.STRATEGIC,
            command_type="analyze",
            parameters={},
            recipient="r",
            constraints={"timeout": 30},
        )
        assert msg.content["constraints"]["timeout"] == 30

    def test_requires_ack_default_true(self):
        msg = CommandMessage(
            sender="s",
            sender_level=AgentLevel.STRATEGIC,
            command_type="test",
            parameters={},
            recipient="r",
        )
        assert msg.requires_acknowledgement() is True

    def test_requires_ack_false(self):
        msg = CommandMessage(
            sender="s",
            sender_level=AgentLevel.STRATEGIC,
            command_type="test",
            parameters={},
            recipient="r",
            requires_ack=False,
        )
        assert msg.requires_acknowledgement() is False


# ── InformationMessage ──


class TestInformationMessage:
    def test_basic(self):
        msg = InformationMessage(
            sender="op_agent",
            sender_level=AgentLevel.OPERATIONAL,
            info_type="analysis_result",
            data={"score": 0.9},
        )
        assert msg.type == MessageType.INFORMATION
        assert msg.content["info_type"] == "analysis_result"
        assert msg.priority == MessagePriority.NORMAL

    def test_broadcast_by_default(self):
        msg = InformationMessage(
            sender="op",
            sender_level=AgentLevel.OPERATIONAL,
            info_type="status",
            data={},
        )
        assert msg.recipient is None

    def test_with_recipient(self):
        msg = InformationMessage(
            sender="op",
            sender_level=AgentLevel.OPERATIONAL,
            info_type="status",
            data={},
            recipient="tactical_agent",
        )
        assert msg.recipient == "tactical_agent"


# ── RequestMessage ──


class TestRequestMessage:
    def test_basic(self):
        msg = RequestMessage(
            sender="tactical",
            sender_level=AgentLevel.TACTICAL,
            request_type="get_analysis",
            description="Analyze this text",
            context={"text": "sample"},
            recipient="operational",
        )
        assert msg.type == MessageType.REQUEST
        assert msg.content["request_type"] == "get_analysis"
        assert msg.content["description"] == "Analyze this text"
        assert msg.content["context"]["text"] == "sample"

    def test_with_response_format(self):
        msg = RequestMessage(
            sender="t",
            sender_level=AgentLevel.TACTICAL,
            request_type="get",
            description="desc",
            context={},
            recipient="o",
            response_format="json",
        )
        assert msg.content["response_format"] == "json"

    def test_with_timeout(self):
        msg = RequestMessage(
            sender="t",
            sender_level=AgentLevel.TACTICAL,
            request_type="get",
            description="desc",
            context={},
            recipient="o",
            timeout=30,
        )
        assert msg.content["timeout"] == 30

    def test_no_response_format_when_omitted(self):
        msg = RequestMessage(
            sender="t",
            sender_level=AgentLevel.TACTICAL,
            request_type="get",
            description="desc",
            context={},
            recipient="o",
        )
        assert "response_format" not in msg.content


# ── EventMessage ──


class TestEventMessage:
    def test_basic(self):
        msg = EventMessage(
            sender="system",
            sender_level=AgentLevel.SYSTEM,
            event_type="resource_warning",
            description="Memory high",
            details={"memory_percent": 95},
        )
        assert msg.type == MessageType.EVENT
        assert msg.content["event_type"] == "resource_warning"
        assert msg.priority == MessagePriority.HIGH  # default for events
        assert msg.recipient is None  # events are broadcast

    def test_with_recommended_action(self):
        msg = EventMessage(
            sender="sys",
            sender_level=AgentLevel.SYSTEM,
            event_type="error",
            description="Service down",
            details={"service": "llm"},
            recommended_action="Restart the service",
        )
        assert msg.content["recommended_action"] == "Restart the service"

    def test_no_recommended_action(self):
        msg = EventMessage(
            sender="sys",
            sender_level=AgentLevel.SYSTEM,
            event_type="info",
            description="All good",
            details={},
        )
        assert "recommended_action" not in msg.content


# ── Message sorting ──


class TestMessageSorting:
    def test_sort_by_priority(self):
        ts = datetime(2026, 1, 1)
        msgs = [
            Message(
                MessageType.COMMAND,
                "a",
                AgentLevel.SYSTEM,
                {},
                priority=MessagePriority.LOW,
                message_id="low",
                timestamp=ts,
            ),
            Message(
                MessageType.COMMAND,
                "a",
                AgentLevel.SYSTEM,
                {},
                priority=MessagePriority.CRITICAL,
                message_id="crit",
                timestamp=ts,
            ),
            Message(
                MessageType.COMMAND,
                "a",
                AgentLevel.SYSTEM,
                {},
                priority=MessagePriority.NORMAL,
                message_id="norm",
                timestamp=ts,
            ),
        ]
        sorted_msgs = sorted(msgs)
        assert sorted_msgs[0].id == "crit"
        assert sorted_msgs[1].id == "norm"
        assert sorted_msgs[2].id == "low"

    def test_sort_same_priority_by_timestamp(self):
        msgs = [
            Message(
                MessageType.COMMAND,
                "a",
                AgentLevel.SYSTEM,
                {},
                priority=MessagePriority.NORMAL,
                message_id="new",
                timestamp=datetime(2026, 1, 2),
            ),
            Message(
                MessageType.COMMAND,
                "a",
                AgentLevel.SYSTEM,
                {},
                priority=MessagePriority.NORMAL,
                message_id="old",
                timestamp=datetime(2026, 1, 1),
            ),
        ]
        sorted_msgs = sorted(msgs)
        assert sorted_msgs[0].id == "old"
        assert sorted_msgs[1].id == "new"
