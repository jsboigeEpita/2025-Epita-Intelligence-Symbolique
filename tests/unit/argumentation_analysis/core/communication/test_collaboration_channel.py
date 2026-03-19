# tests/unit/argumentation_analysis/core/communication/test_collaboration_channel.py
"""Tests for CollaborationGroup and CollaborationChannel — groups, direct messages."""

import pytest
from unittest.mock import MagicMock

from argumentation_analysis.core.communication.collaboration_channel import (
    CollaborationGroup,
    CollaborationChannel,
)
from argumentation_analysis.core.communication.channel_interface import ChannelType
from argumentation_analysis.core.communication.message import (
    Message,
    MessageType,
    MessagePriority,
    AgentLevel,
)


def _make_msg(
    msg_type=MessageType.INFORMATION,
    sender="agent_1",
    recipient="agent_2",
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


# ── CollaborationGroup ──


class TestCollaborationGroup:
    def test_init_defaults(self):
        g = CollaborationGroup("g1")
        assert g.id == "g1"
        assert g.name == "Group-g1"
        assert g.description is None
        assert len(g.members) == 0
        assert len(g.messages) == 0

    def test_init_with_name_and_members(self):
        g = CollaborationGroup("g1", name="Team", members=["a", "b"])
        assert g.name == "Team"
        assert g.members == {"a", "b"}

    def test_add_member(self):
        g = CollaborationGroup("g1")
        assert g.add_member("alice") is True
        assert "alice" in g.members

    def test_add_member_duplicate(self):
        g = CollaborationGroup("g1", members=["alice"])
        assert g.add_member("alice") is False

    def test_remove_member(self):
        g = CollaborationGroup("g1", members=["alice"])
        assert g.remove_member("alice") is True
        assert "alice" not in g.members

    def test_remove_member_not_present(self):
        g = CollaborationGroup("g1")
        assert g.remove_member("alice") is False

    def test_add_message(self):
        g = CollaborationGroup("g1")
        msg = _make_msg()
        g.add_message(msg)
        assert len(g.messages) == 1

    def test_get_messages_all(self):
        g = CollaborationGroup("g1")
        for i in range(5):
            g.add_message(_make_msg(sender=f"agent_{i}"))
        msgs = g.get_messages()
        assert len(msgs) == 5

    def test_get_messages_with_count(self):
        g = CollaborationGroup("g1")
        for i in range(5):
            g.add_message(_make_msg(sender=f"agent_{i}"))
        msgs = g.get_messages(count=3)
        assert len(msgs) == 3
        # Should be the last 3
        assert msgs[0].sender == "agent_2"

    def test_get_member_count(self):
        g = CollaborationGroup("g1", members=["a", "b", "c"])
        assert g.get_member_count() == 3

    def test_get_group_info(self):
        g = CollaborationGroup(
            "g1", name="Team", description="Test group", members=["a"]
        )
        g.add_message(_make_msg())
        info = g.get_group_info()
        assert info["id"] == "g1"
        assert info["name"] == "Team"
        assert info["description"] == "Test group"
        assert info["member_count"] == 1
        assert info["message_count"] == 1
        assert "created_at" in info


# ── CollaborationChannel Init ──


class TestCollaborationChannelInit:
    def test_channel_type(self):
        ch = CollaborationChannel("c1")
        assert ch.type == ChannelType.COLLABORATION

    def test_channel_id(self):
        ch = CollaborationChannel("c1")
        assert ch.id == "c1"

    def test_initial_stats(self):
        ch = CollaborationChannel("c1")
        assert ch.stats["messages_sent"] == 0
        assert ch.stats["direct_messages"] == 0
        assert ch.stats["group_messages"] == 0

    def test_no_groups_initially(self):
        ch = CollaborationChannel("c1")
        assert len(ch.groups) == 0


# ── Direct messages ──


class TestDirectMessages:
    @pytest.fixture
    def ch(self):
        return CollaborationChannel("c1")

    def test_send_direct_message(self, ch):
        msg = _make_msg(recipient="bob")
        assert ch.send_message(msg) is True
        assert ch.stats["direct_messages"] == 1

    def test_send_direct_no_recipient(self, ch):
        msg = _make_msg(recipient=None)
        assert ch.send_message(msg) is False

    def test_receive_direct_message(self, ch):
        msg = _make_msg(recipient="bob")
        ch.send_message(msg)
        received = ch.receive_message("bob")
        assert received is not None
        assert received.id == msg.id

    def test_receive_marks_as_read(self, ch):
        ch.send_message(_make_msg(recipient="bob"))
        ch.receive_message("bob")
        # Second receive should return None (message already read)
        assert ch.receive_message("bob") is None

    def test_receive_no_messages(self, ch):
        assert ch.receive_message("bob") is None

    def test_send_tracks_agent_level(self, ch):
        ch.send_message(_make_msg(sender_level=AgentLevel.TACTICAL))
        assert ch.stats["by_agent_level"]["tactical"] == 1

    def test_pending_direct_messages(self, ch):
        for i in range(3):
            ch.send_message(_make_msg(recipient="bob"))
        pending = ch.get_pending_messages("bob")
        assert len(pending) == 3

    def test_pending_with_limit(self, ch):
        for i in range(5):
            ch.send_message(_make_msg(recipient="bob"))
        pending = ch.get_pending_messages("bob", max_count=2)
        assert len(pending) == 2


# ── Group operations ──


class TestGroupOperations:
    @pytest.fixture
    def ch(self):
        return CollaborationChannel("c1")

    def test_create_group(self, ch):
        gid = ch.create_group("g1", name="Team", members=["alice", "bob"])
        assert gid == "g1"
        assert "g1" in ch.groups

    def test_create_group_auto_id(self, ch):
        gid = ch.create_group()
        assert gid.startswith("group-")

    def test_create_group_duplicate(self, ch):
        ch.create_group("g1")
        gid = ch.create_group("g1")
        assert gid == "g1"  # Returns existing

    def test_delete_group(self, ch):
        ch.create_group("g1")
        assert ch.delete_group("g1") is True
        assert "g1" not in ch.groups

    def test_delete_group_nonexistent(self, ch):
        assert ch.delete_group("nope") is False

    def test_add_group_member(self, ch):
        ch.create_group("g1")
        assert ch.add_group_member("g1", "alice") is True

    def test_add_group_member_nonexistent_group(self, ch):
        assert ch.add_group_member("nope", "alice") is False

    def test_add_group_member_duplicate(self, ch):
        ch.create_group("g1", members=["alice"])
        assert ch.add_group_member("g1", "alice") is False

    def test_remove_group_member(self, ch):
        ch.create_group("g1", members=["alice"])
        assert ch.remove_group_member("g1", "alice") is True

    def test_remove_group_member_nonexistent_group(self, ch):
        assert ch.remove_group_member("nope", "alice") is False

    def test_remove_group_member_not_in_group(self, ch):
        ch.create_group("g1")
        assert ch.remove_group_member("g1", "alice") is False

    def test_get_groups(self, ch):
        ch.create_group("g1")
        ch.create_group("g2")
        assert set(ch.get_groups()) == {"g1", "g2"}

    def test_get_agent_groups(self, ch):
        ch.create_group("g1", members=["alice"])
        ch.create_group("g2", members=["bob"])
        ch.create_group("g3", members=["alice", "bob"])
        assert set(ch.get_agent_groups("alice")) == {"g1", "g3"}

    def test_get_group_info(self, ch):
        ch.create_group("g1", name="Team", description="Desc", members=["alice"])
        info = ch.get_group_info("g1")
        assert info["id"] == "g1"
        assert info["name"] == "Team"
        assert info["member_count"] == 1

    def test_get_group_info_nonexistent(self, ch):
        assert ch.get_group_info("nope") is None

    def test_get_group_messages(self, ch):
        ch.create_group("g1", members=["alice"])
        msg = _make_msg(sender="alice", metadata={"group_id": "g1"})
        ch.send_message(msg)
        msgs = ch.get_group_messages("g1")
        assert len(msgs) == 1

    def test_get_group_messages_nonexistent(self, ch):
        assert ch.get_group_messages("nope") == []


# ── Group messaging ──


class TestGroupMessaging:
    @pytest.fixture
    def ch(self):
        ch = CollaborationChannel("c1")
        ch.create_group("g1", members=["alice", "bob"])
        return ch

    def test_send_group_message(self, ch):
        msg = _make_msg(sender="alice", metadata={"group_id": "g1"})
        assert ch.send_message(msg) is True
        assert ch.stats["group_messages"] == 1

    def test_send_group_message_nonexistent_group(self, ch):
        msg = _make_msg(sender="alice", metadata={"group_id": "nope"})
        assert ch.send_message(msg) is False

    def test_send_group_message_non_member(self, ch):
        msg = _make_msg(sender="charlie", metadata={"group_id": "g1"})
        assert ch.send_message(msg) is False

    def test_receive_group_message(self, ch):
        msg = _make_msg(sender="alice", metadata={"group_id": "g1"})
        ch.send_message(msg)
        received = ch.receive_message("bob")
        assert received is not None
        assert received.sender == "alice"

    def test_receive_group_skips_own_messages(self, ch):
        msg = _make_msg(sender="alice", metadata={"group_id": "g1"})
        ch.send_message(msg)
        # Alice sent the message, should not receive her own
        received = ch.receive_message("alice")
        assert received is None

    def test_pending_includes_group_messages(self, ch):
        msg = _make_msg(sender="alice", metadata={"group_id": "g1"})
        ch.send_message(msg)
        pending = ch.get_pending_messages("bob")
        assert len(pending) == 1


# ── Subscribe / Unsubscribe ──


class TestSubscription:
    @pytest.fixture
    def ch(self):
        return CollaborationChannel("c1")

    def test_subscribe(self, ch):
        sub_id = ch.subscribe("agent_1")
        assert sub_id.startswith("sub-")
        assert len(ch.subscribers) == 1

    def test_unsubscribe(self, ch):
        sub_id = ch.subscribe("agent_1")
        assert ch.unsubscribe(sub_id) is True
        assert len(ch.subscribers) == 0

    def test_unsubscribe_nonexistent(self, ch):
        assert ch.unsubscribe("nope") is False

    def test_subscriber_notified_on_direct(self, ch):
        callback = MagicMock()
        ch.subscribe("sub1", callback=callback)
        ch.send_message(_make_msg(recipient="bob"))
        callback.assert_called_once()

    def test_subscriber_callback_error_handled(self, ch):
        callback = MagicMock(side_effect=RuntimeError("boom"))
        ch.subscribe("sub1", callback=callback)
        assert ch.send_message(_make_msg(recipient="bob")) is True


# ── get_channel_info ──


class TestGetChannelInfo:
    def test_channel_info(self):
        ch = CollaborationChannel("c1")
        ch.create_group("g1")
        ch.subscribe("sub1")
        info = ch.get_channel_info()
        assert info["id"] == "c1"
        assert info["type"] == "collaboration"
        assert info["group_count"] == 1
        assert info["subscriber_count"] == 1
