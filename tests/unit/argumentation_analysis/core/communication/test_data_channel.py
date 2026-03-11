# tests/unit/argumentation_analysis/core/communication/test_data_channel.py
"""Tests for DataStore and DataChannel — versioned storage, compression, data transfer."""

import pytest
from unittest.mock import MagicMock

from argumentation_analysis.core.communication.data_channel import (
    DataStore,
    DataChannel,
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


# ── DataStore ──

class TestDataStoreInit:
    def test_init(self):
        ds = DataStore("store1")
        assert ds.id == "store1"
        assert ds.config == {}
        assert ds.data_items == {}

    def test_init_with_config(self):
        ds = DataStore("store1", config={"max_size": 1024})
        assert ds.config["max_size"] == 1024


class TestDataStoreOperations:
    @pytest.fixture
    def ds(self):
        return DataStore("store1")

    def test_store_data_returns_version_id(self, ds):
        vid = ds.store_data("item1", {"key": "value"})
        assert vid.startswith("v-")

    def test_store_data_small_no_compression(self, ds):
        vid = ds.store_data("item1", {"k": "v"}, compress=True)
        item_key = f"item1:{vid}"
        assert ds.data_items[item_key]["is_compressed"] is False

    def test_store_data_large_gets_compressed(self, ds):
        large_data = {"key": "x" * 2000}
        vid = ds.store_data("item1", large_data, compress=True)
        item_key = f"item1:{vid}"
        assert ds.data_items[item_key]["is_compressed"] is True

    def test_store_data_no_compress(self, ds):
        large_data = {"key": "x" * 2000}
        vid = ds.store_data("item1", large_data, compress=False)
        item_key = f"item1:{vid}"
        assert ds.data_items[item_key]["is_compressed"] is False

    def test_store_with_metadata(self, ds):
        vid = ds.store_data("item1", {"k": "v"}, metadata={"author": "test"})
        item_key = f"item1:{vid}"
        assert ds.data_items[item_key]["metadata"]["author"] == "test"

    def test_get_data_roundtrip(self, ds):
        original = {"key": "value", "count": 42}
        vid = ds.store_data("item1", original)
        data, meta = ds.get_data("item1", vid)
        assert data == original

    def test_get_data_latest_version(self, ds):
        ds.store_data("item1", {"v": 1})
        ds.store_data("item1", {"v": 2})
        data, _ = ds.get_data("item1")
        assert data["v"] == 2

    def test_get_data_specific_version(self, ds):
        v1 = ds.store_data("item1", {"v": 1})
        ds.store_data("item1", {"v": 2})
        data, _ = ds.get_data("item1", v1)
        assert data["v"] == 1

    def test_get_data_nonexistent_raises(self, ds):
        with pytest.raises(KeyError):
            ds.get_data("nonexistent")

    def test_get_data_bad_version_raises(self, ds):
        ds.store_data("item1", {"v": 1})
        with pytest.raises(KeyError):
            ds.get_data("item1", "v-nonexistent")

    def test_get_data_compressed_roundtrip(self, ds):
        large = {"data": "x" * 2000}
        vid = ds.store_data("item1", large, compress=True)
        recovered, _ = ds.get_data("item1", vid)
        assert recovered == large

    def test_delete_all_versions(self, ds):
        ds.store_data("item1", {"v": 1})
        ds.store_data("item1", {"v": 2})
        assert ds.delete_data("item1") is True
        with pytest.raises(KeyError):
            ds.get_data("item1")

    def test_delete_specific_version(self, ds):
        v1 = ds.store_data("item1", {"v": 1})
        v2 = ds.store_data("item1", {"v": 2})
        assert ds.delete_data("item1", v1) is True
        data, _ = ds.get_data("item1")
        assert data["v"] == 2

    def test_delete_nonexistent(self, ds):
        assert ds.delete_data("nonexistent") is False

    def test_delete_nonexistent_version(self, ds):
        ds.store_data("item1", {"v": 1})
        assert ds.delete_data("item1", "v-nope") is False

    def test_delete_last_version_removes_item(self, ds):
        vid = ds.store_data("item1", {"v": 1})
        ds.delete_data("item1", vid)
        assert ds.get_versions("item1") == []

    def test_get_versions(self, ds):
        v1 = ds.store_data("item1", {"v": 1})
        v2 = ds.store_data("item1", {"v": 2})
        versions = ds.get_versions("item1")
        assert versions == [v1, v2]

    def test_get_versions_nonexistent(self, ds):
        assert ds.get_versions("nonexistent") == []

    def test_get_data_info(self, ds):
        vid = ds.store_data("item1", {"k": "v"}, metadata={"author": "test"})
        info = ds.get_data_info("item1", vid)
        assert info["id"] == "item1"
        assert info["version_id"] == vid
        assert info["metadata"]["author"] == "test"
        assert "content" not in info  # Content stripped from info

    def test_get_data_info_latest(self, ds):
        ds.store_data("item1", {"v": 1})
        v2 = ds.store_data("item1", {"v": 2})
        info = ds.get_data_info("item1")
        assert info["version_id"] == v2

    def test_get_data_info_nonexistent(self, ds):
        assert ds.get_data_info("nonexistent") is None


# ── DataChannel ──

class TestDataChannelInit:
    def test_channel_type(self):
        ch = DataChannel("d1")
        assert ch.type == ChannelType.DATA

    def test_channel_id(self):
        ch = DataChannel("d1")
        assert ch.id == "d1"

    def test_initial_stats(self):
        ch = DataChannel("d1")
        assert ch.stats["messages_sent"] == 0
        assert ch.stats["data_items_stored"] == 0

    def test_config_defaults(self):
        ch = DataChannel("d1")
        assert ch.compression_threshold == 1024
        assert ch.max_inline_data_size == 10240

    def test_custom_config(self):
        ch = DataChannel("d1", config={"compression_threshold": 512, "max_inline_data_size": 4096})
        assert ch.compression_threshold == 512
        assert ch.max_inline_data_size == 4096


class TestDataChannelSend:
    @pytest.fixture
    def ch(self):
        return DataChannel("d1")

    def test_send_small_message(self, ch):
        msg = _make_msg(content={"info": "small data"})
        assert ch.send_message(msg) is True
        assert ch.stats["messages_sent"] == 1

    def test_send_no_recipient(self, ch):
        msg = _make_msg(recipient=None, content={"info": "data"})
        assert ch.send_message(msg) is False

    def test_send_tracks_stats(self, ch):
        ch.send_message(_make_msg(content={"info": "data"}))
        ch.send_message(_make_msg(content={"info": "more data"}))
        assert ch.stats["messages_sent"] == 2


class TestDataChannelReceive:
    @pytest.fixture
    def ch(self):
        return DataChannel("d1")

    def test_receive_message(self, ch):
        msg = _make_msg(recipient="bob", content={"info": "data"})
        ch.send_message(msg)
        received = ch.receive_message("bob")
        assert received is not None
        assert received.id == msg.id

    def test_receive_marks_as_read(self, ch):
        ch.send_message(_make_msg(recipient="bob"))
        ch.receive_message("bob")
        assert ch.receive_message("bob") is None

    def test_receive_empty(self, ch):
        assert ch.receive_message("bob") is None


class TestDataChannelDataOps:
    @pytest.fixture
    def ch(self):
        return DataChannel("d1")

    def test_store_data(self, ch):
        vid = ch.store_data("item1", {"key": "value"})
        assert vid.startswith("v-")
        assert ch.stats["data_items_stored"] == 1

    def test_get_data(self, ch):
        ch.store_data("item1", {"key": "value"})
        data, meta = ch.get_data("item1")
        assert data == {"key": "value"}
        assert ch.stats["data_items_retrieved"] == 1

    def test_delete_data(self, ch):
        ch.store_data("item1", {"key": "value"})
        assert ch.delete_data("item1") is True

    def test_get_data_info(self, ch):
        vid = ch.store_data("item1", {"key": "value"}, metadata={"author": "test"})
        info = ch.get_data_info("item1", vid)
        assert info["metadata"]["author"] == "test"


class TestDataChannelSubscribe:
    @pytest.fixture
    def ch(self):
        return DataChannel("d1")

    def test_subscribe(self, ch):
        sub_id = ch.subscribe("sub1")
        assert sub_id.startswith("sub-")
        assert len(ch.subscribers) == 1

    def test_unsubscribe(self, ch):
        sub_id = ch.subscribe("sub1")
        assert ch.unsubscribe(sub_id) is True
        assert len(ch.subscribers) == 0

    def test_unsubscribe_nonexistent(self, ch):
        assert ch.unsubscribe("nope") is False

    def test_subscriber_notified(self, ch):
        callback = MagicMock()
        ch.subscribe("sub1", callback=callback)
        ch.send_message(_make_msg())
        callback.assert_called_once()


class TestDataChannelPending:
    @pytest.fixture
    def ch(self):
        return DataChannel("d1")

    def test_pending_messages(self, ch):
        for _ in range(3):
            ch.send_message(_make_msg(recipient="bob"))
        pending = ch.get_pending_messages("bob")
        assert len(pending) == 3

    def test_pending_with_limit(self, ch):
        for _ in range(5):
            ch.send_message(_make_msg(recipient="bob"))
        pending = ch.get_pending_messages("bob", max_count=2)
        assert len(pending) == 2


class TestDataChannelInfo:
    def test_channel_info(self):
        ch = DataChannel("d1")
        ch.subscribe("sub1")
        info = ch.get_channel_info()
        assert info["id"] == "d1"
        assert info["type"] == "data"
        assert info["subscriber_count"] == 1
        assert "compression_threshold" in info
        assert "max_inline_data_size" in info
