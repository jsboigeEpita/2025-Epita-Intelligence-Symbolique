"""#2344: a defect on the receive side raises instead of looking like a timeout.

Measured before the change (on #2589's head, which only repaired the send side):

- ``MessageMiddleware.receive_message`` on a channel that raises returned
  ``None``, the value of a timeout; the only difference was ``errors=1``.
- ``get_pending_messages`` returned ``[]`` on any exception, the value of an
  empty queue.
- the hierarchical and data channels caught every exception of their own
  ``receive_message`` into ``None``.
- a data-channel message whose payload, stored apart, could not be read back
  was delivered anyway, with ``data`` set to ``None`` and marked read: the
  payload was lost and the recipient could not tell.

A timeout, an empty queue and a missing channel keep their values.
"""

import pytest

from argumentation_analysis.core.communication.channel_interface import ChannelType
from argumentation_analysis.core.communication.data_channel import DataChannel
from argumentation_analysis.core.communication.hierarchical_channel import (
    HierarchicalChannel,
)
from argumentation_analysis.core.communication.message import (
    AgentLevel,
    Message,
    MessageType,
)
from argumentation_analysis.core.communication.middleware import (
    MessageMiddleware,
    create_default_middleware,
)


def _msg(message_type=MessageType.COMMAND, recipient="tactical-1", content=None):
    return Message(
        message_type=message_type,
        sender="strategic-1",
        sender_level=AgentLevel.STRATEGIC,
        content={"task": "t-1"} if content is None else content,
        recipient=recipient,
    )


def _raising_middleware():
    mw = create_default_middleware()
    channel = mw.get_channel(ChannelType.HIERARCHICAL)

    def broken(*args, **kwargs):
        raise RuntimeError("queue backend down")

    channel.receive_message = broken
    channel.get_pending_messages = broken
    return mw


def _data_message_with_lost_payload():
    """A message whose large payload was stored apart, then lost from the store."""
    channel = DataChannel("data_main")
    payload = {"rows": ["x" * 100] * 200}  # above max_inline_data_size
    assert channel.send_message(
        _msg(MessageType.PUBLICATION, content={"data": payload})
    )
    entry = channel.message_queues["tactical-1"][0]
    data_id = entry["message"].content["data_reference"]["data_id"]
    assert channel.data_store.delete_data(data_id)
    return channel, entry


# --- The middleware -------------------------------------------------------------


def test_a_channel_defect_on_receive_raises_and_is_counted():
    mw = _raising_middleware()

    with pytest.raises(RuntimeError, match="queue backend down"):
        mw.receive_message("tactical-1", ChannelType.HIERARCHICAL, 0.1)

    assert mw.stats["errors"] == 1
    assert mw.stats["messages_received"] == 0


def test_a_channel_defect_on_pending_raises():
    mw = _raising_middleware()

    with pytest.raises(RuntimeError, match="queue backend down"):
        mw.get_pending_messages("tactical-1", ChannelType.HIERARCHICAL)


def test_a_missing_channel_on_receive_is_counted():
    mw = MessageMiddleware()

    assert mw.receive_message("tactical-1", ChannelType.HIERARCHICAL, 0.1) is None
    assert mw.stats["errors"] == 1


# --- The channels ---------------------------------------------------------------


def test_the_hierarchical_channel_raises_its_receive_defect():
    channel = HierarchicalChannel("hierarchical_main")
    assert channel.send_message(_msg())

    with pytest.raises(TypeError):
        channel.receive_message("tactical-1", timeout="soon")


def test_a_lost_payload_raises_and_the_message_stays_unread():
    channel, entry = _data_message_with_lost_payload()

    with pytest.raises(KeyError):
        channel.receive_message("tactical-1")

    assert entry["read"] is False
    assert channel.stats["messages_received"] == 0


def test_a_lost_payload_is_not_listed_without_its_data():
    channel, _ = _data_message_with_lost_payload()

    with pytest.raises(KeyError):
        channel.get_pending_messages("tactical-1")


# --- Controls: the values callers rely on ------------------------------------------


def test_a_timeout_is_still_none_and_not_an_error():
    mw = create_default_middleware()

    assert mw.receive_message("tactical-1", ChannelType.HIERARCHICAL, 0.05) is None
    assert mw.stats["errors"] == 0


def test_an_empty_queue_is_still_an_empty_list():
    mw = create_default_middleware()

    assert mw.get_pending_messages("tactical-1", ChannelType.HIERARCHICAL) == []


def test_a_stored_payload_comes_back_whole():
    channel = DataChannel("data_main")
    payload = {"rows": ["x" * 100] * 200}
    assert channel.send_message(
        _msg(MessageType.PUBLICATION, content={"data": payload})
    )

    received = channel.receive_message("tactical-1")

    assert received.content["data"] == payload
    assert "data_reference" not in received.content
