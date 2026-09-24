"""#2344: a send that did not deliver is never counted or logged as sent, and a
defect in the send path raises instead of becoming ``False``.

Measured on ``main`` ``3087aa3b0`` before the change:

- a message the channel refused returned ``False`` but was counted in
  ``messages_sent`` and logged ``Message sent``;
- a missing channel returned ``False`` without counting an error;
- a routing defect surfaced as ``UnboundLocalError`` on ``channel_type``, from
  the middleware's own ``except`` block, instead of the routing error;
- an exception from the channel returned ``False``, and the only trace was
  ``stats["errors"]``;
- the three channels caught every exception of their own send into ``False``,
  once after the message was already in the recipient's queue.

The channels here are the real ones ``create_default_middleware`` wires, except
where a test needs a channel that raises.
"""

import logging
from unittest.mock import MagicMock

import pytest

from argumentation_analysis.core.communication.channel_interface import ChannelType
from argumentation_analysis.core.communication.collaboration_channel import (
    CollaborationChannel,
)
from argumentation_analysis.core.communication.data_channel import DataChannel
from argumentation_analysis.core.communication.hierarchical_channel import (
    HierarchicalChannel,
)
from argumentation_analysis.core.communication.message import (
    AgentLevel,
    Message,
    MessagePriority,
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


def _middleware_logs(caplog):
    return [
        (r.levelno, r.getMessage())
        for r in caplog.records
        if r.name == "MessageMiddleware"
    ]


# --- A send that did not deliver --------------------------------------------


def test_a_refused_message_is_not_counted_as_sent(caplog):
    mw = create_default_middleware()
    caplog.set_level(logging.INFO, logger="MessageMiddleware")

    msg = _msg(recipient=None)
    assert mw.send_message(msg) is False

    assert mw.stats["messages_sent"] == 0
    assert mw.stats["by_channel"]["hierarchical"]["sent"] == 0
    assert mw.stats["by_type"] == {}
    assert mw.stats["errors"] == 1
    assert mw.stats["by_channel"]["hierarchical"]["errors"] == 1
    logs = _middleware_logs(caplog)
    assert (
        logging.WARNING,
        f"Message refused: {msg.id} by channel hierarchical",
    ) in logs
    assert not any(text.startswith("Message sent") for _, text in logs)


def test_a_missing_channel_is_counted_as_a_failure(caplog):
    mw = MessageMiddleware()
    caplog.set_level(logging.INFO, logger="MessageMiddleware")

    assert mw.send_message(_msg()) is False

    assert mw.stats["messages_sent"] == 0
    assert mw.stats["errors"] == 1
    # The #1471 guard counts this marker; it stays an ERROR.
    assert (logging.ERROR, "Channel not found: hierarchical") in _middleware_logs(
        caplog
    )


# --- A defect in the send path ------------------------------------------------


def test_a_routing_defect_raises_the_routing_error():
    mw = create_default_middleware()
    msg = _msg(message_type=MessageType.INFORMATION)
    msg.content = None  # determine_channel reads content["info_type"]

    with pytest.raises(AttributeError, match="'NoneType' object has no attribute"):
        mw.send_message(msg)

    assert mw.stats["errors"] == 1
    assert mw.stats["messages_sent"] == 0


def test_a_channel_exception_propagates_and_is_counted():
    mw = MessageMiddleware()
    channel = MagicMock()
    channel.type = ChannelType.HIERARCHICAL
    channel.send_message.side_effect = RuntimeError("queue backend down")
    mw.register_channel(channel)

    with pytest.raises(RuntimeError, match="queue backend down"):
        mw.send_message(_msg())

    assert mw.stats["errors"] == 1
    assert mw.stats["by_channel"]["hierarchical"]["errors"] == 1
    assert mw.stats["messages_sent"] == 0


def test_a_message_already_queued_is_not_reported_as_refused():
    # The hierarchical channel queued the message, then failed on its own
    # statistics: it used to answer False for a message the recipient receives.
    mw = create_default_middleware()
    msg = _msg()
    msg.priority = "high"  # not a MessagePriority: breaks the stats update

    with pytest.raises(AttributeError, match="'str' object has no attribute 'value'"):
        mw.send_message(msg)

    assert mw.stats["messages_sent"] == 0
    assert mw.stats["errors"] == 1


def _hierarchical_defect():
    msg = _msg()
    msg.priority = "high"
    return HierarchicalChannel("hierarchical_main"), msg


def _data_defect():
    msg = _msg(message_type=MessageType.PUBLICATION)
    msg.content = None
    return DataChannel("data_main"), msg


def _collaboration_defect():
    msg = _msg(message_type=MessageType.REQUEST)
    msg.metadata = None
    return CollaborationChannel("collaboration_main"), msg


@pytest.mark.parametrize(
    "make", [_hierarchical_defect, _data_defect, _collaboration_defect]
)
def test_each_channel_raises_its_send_defect(make):
    channel, msg = make()
    with pytest.raises(AttributeError):
        channel.send_message(msg)


# --- Controls: what callers rely on -------------------------------------------


def test_a_delivered_message_is_counted_once_and_received(caplog):
    mw = create_default_middleware()
    caplog.set_level(logging.INFO, logger="MessageMiddleware")

    msg = _msg()
    assert mw.send_message(msg) is True

    assert mw.stats["messages_sent"] == 1
    assert mw.stats["by_channel"]["hierarchical"]["sent"] == 1
    assert mw.stats["by_type"] == {"command": 1}
    assert mw.stats["by_priority"] == {MessagePriority.NORMAL.value: 1}
    assert mw.stats["errors"] == 0
    assert (logging.INFO, f"Message sent: {msg.id} via hierarchical") in (
        _middleware_logs(caplog)
    )
    received = mw.receive_message("tactical-1", ChannelType.HIERARCHICAL, 0.1)
    assert received is not None and received.id == msg.id


@pytest.mark.parametrize(
    "channel", [HierarchicalChannel("h"), DataChannel("d"), CollaborationChannel("c")]
)
def test_a_message_without_recipient_is_still_a_refusal(channel):
    assert channel.send_message(_msg(recipient=None)) is False
