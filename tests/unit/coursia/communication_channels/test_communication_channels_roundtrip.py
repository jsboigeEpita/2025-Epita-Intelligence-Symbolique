"""Round-trip guard for the communication-channels CoursIA notebook (#1961 Phase 3).

Every value the notebook displays comes from
``docs/coursia_contrib/communication_channels_examples.json`` — the single
source of truth shared by the notebook and this guard. This test replays each
case against the real engine of ``argumentation_analysis/core/communication/``:
message ordering and defaults, the strict channel filter (#2161) next to the
permissive topic filter, the middleware routing table and its measured
collaboration trap, hierarchical priority queues, the drain-vs-preserve split
of ``get_pending_messages``, collaboration groups, the data channel's
claim-check, pub/sub fan-out, and request/response correlation. Structural
claims the notebook teaches are pinned, and the committed notebook must ship
with executed outputs.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pytest

from argumentation_analysis.core.communication.channel_interface import (
    Channel,
    ChannelType,
    LocalChannel,
)
from argumentation_analysis.core.communication.collaboration_channel import (
    CollaborationChannel,
)
from argumentation_analysis.core.communication.data_channel import DataChannel
from argumentation_analysis.core.communication.hierarchical_channel import (
    HierarchicalChannel,
)
from argumentation_analysis.core.communication.message import (
    AgentLevel,
    CommandMessage,
    EventMessage,
    InformationMessage,
    Message,
    MessagePriority,
    MessageType,
)
from argumentation_analysis.core.communication.middleware import (
    MessageMiddleware,
    create_default_middleware,
)
from argumentation_analysis.core.communication.pub_sub import (
    PublishSubscribeProtocol,
    Topic,
)
from argumentation_analysis.core.communication.request_response import (
    RequestResponseProtocol,
    RequestTimeoutError,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
EXAMPLES_PATH = (
    REPO_ROOT / "docs" / "coursia_contrib" / "communication_channels_examples.json"
)
NOTEBOOK_PATH = REPO_ROOT / "docs" / "coursia_contrib" / "communication_channels.ipynb"

T0 = datetime(2026, 1, 1, 12, 0, 0)


@pytest.fixture(autouse=True)
def _stop_leaked_protocol_threads():
    """Stop the daemon threads the threaded protocols spawn (#1341 hygiene)."""
    yield
    PublishSubscribeProtocol.shutdown_all()
    RequestResponseProtocol.shutdown_all()


def _load_examples() -> dict[str, Any]:
    with open(EXAMPLES_PATH, encoding="utf-8") as fh:
        data: dict[str, Any] = json.load(fh)
    return data


def msg(
    mtype: MessageType = MessageType.INFORMATION,
    sender: str = "agent-a",
    level: AgentLevel = AgentLevel.TACTICAL,
    priority: MessagePriority = MessagePriority.NORMAL,
    content: Optional[dict[str, Any]] = None,
    recipient: Optional[str] = None,
    channel: Optional[str] = None,
    ts: Optional[datetime] = None,
    metadata: Optional[dict[str, Any]] = None,
    mid: Optional[str] = None,
) -> Message:
    return Message(
        message_type=mtype,
        sender=sender,
        sender_level=level,
        content=content or {},
        recipient=recipient,
        channel=channel,
        priority=priority,
        metadata=metadata,
        message_id=mid,
        timestamp=ts or T0,
    )


CRITERIA: dict[str, dict[str, Any]] = {
    "scalar_type_match": {"message_type": "command"},
    "scalar_type_no_match": {"message_type": "event"},
    "list_type": {"message_type": ["command", "request"]},
    "enum_member_is_not_a_string": {"message_type": MessageType.COMMAND},
    "content_subkey": {"content": {"command_type": "execute_analysis"}},
    "content_subkey_no_match": {"content": {"command_type": "allocate_resources"}},
    "unknown_key_raises": {"destinataire": "tactical-1"},
    "sender_and_priority_combined": {"sender": "agent-a", "priority": "normal"},
}

TOPIC_CRITERIA: dict[str, dict[str, Any]] = {
    "topic_has_no_message_type_key": {"message_type": "command"},
    "topic_silently_ignores_unknown_keys": {"nimporte": "quoi"},
    "topic_sender_still_honored": {"sender": "agent-b"},
}


def test_inventory_pins() -> None:
    inv = _load_examples()["inventory"]
    assert len(MessageType) == 8
    assert len(MessagePriority) == 4
    assert len(AgentLevel) == 4
    assert len(ChannelType) == 7
    assert inv["message_types"] == [t.value for t in MessageType]
    assert sorted(Channel.__abstractmethods__) == [
        "get_channel_info",
        "get_pending_messages",
        "receive_message",
        "send_message",
        "subscribe",
        "unsubscribe",
    ]
    assert (
        sorted(Channel.FILTER_KEYS)
        == inv["filter_keys"]
        == [
            "content",
            "message_type",
            "priority",
            "sender",
            "sender_level",
        ]
    )


def test_message_semantics_round_trip() -> None:
    cases = {c["scenario"]: c for c in _load_examples()["message_cases"]}

    assert msg(MessageType.COMMAND).id.split("-")[0] == cases["id_prefix"]["expected"]

    msgs = [
        msg(priority=MessagePriority.LOW, ts=T0),
        msg(priority=MessagePriority.NORMAL, ts=T0 + timedelta(seconds=10)),
        msg(priority=MessagePriority.HIGH, ts=T0 + timedelta(seconds=20)),
        msg(priority=MessagePriority.CRITICAL, ts=T0 + timedelta(seconds=30)),
    ]
    order = cases["priority_order_inverted_timestamps"]["expected"]
    assert (
        [m.priority.value for m in sorted(msgs)]
        == order
        == [
            "critical",
            "high",
            "normal",
            "low",
        ]
    )

    tie = [
        msg(priority=MessagePriority.NORMAL, ts=T0 + timedelta(seconds=5)),
        msg(priority=MessagePriority.NORMAL, ts=T0),
    ]
    got = [m.timestamp.isoformat() for m in sorted(tie)]
    assert got == cases["equal_priority_oldest_first"]["expected"]
    assert got[0] == T0.isoformat()

    rt = msg(
        MessageType.REQUEST,
        sender="agent-a",
        level=AgentLevel.STRATEGIC,
        priority=MessagePriority.HIGH,
        content={"request_type": "get_analysis"},
        recipient="agent-b",
        channel="hierarchical",
        metadata={"conversation_id": "conv-test"},
        ts=T0 + timedelta(microseconds=123456),
    )
    rebuilt = Message.from_dict(rt.to_dict())
    round_case = cases["dict_round_trip_equal_and_correlated"]
    assert (rebuilt == rt) is round_case["expected_equal"] is True
    assert rebuilt.is_response_to("nope") is round_case["expected_reply_correlation"]

    req = msg(
        MessageType.REQUEST,
        sender="strategic-1",
        level=AgentLevel.STRATEGIC,
        content={"request_type": "get_status"},
        recipient="tactical-1",
        mid="request-demo",
    )
    resp = req.create_response({"status": "ok"})
    rev = cases["create_response_reversal"]
    assert resp.sender == rev["expected_sender"] == "tactical-1"
    assert resp.recipient == rev["expected_recipient"] == "strategic-1"
    assert resp.type.value == rev["expected_type"] == "response"
    assert resp.metadata["reply_to"] == rev["expected_reply_to"] == "request-demo"
    assert resp.is_response_to(req.id) is rev["expected_is_response_to"] is True

    cmd = CommandMessage(
        sender="strategic-1",
        sender_level=AgentLevel.STRATEGIC,
        command_type="execute_analysis",
        parameters={"depth": 2},
        recipient="operational-1",
        timestamp=T0,
    )
    evt = EventMessage(
        sender="tactical-1",
        sender_level=AgentLevel.TACTICAL,
        event_type="resource_warning",
        description="cpu",
        details={},
        timestamp=T0,
    )
    info = InformationMessage(
        sender="tactical-1",
        sender_level=AgentLevel.TACTICAL,
        info_type="status_update",
        data={"progress": 0.5},
        timestamp=T0,
    )
    spec = cases["specialised_defaults"]
    assert cmd.priority.value == spec["command_priority"] == "high"
    assert cmd.requires_acknowledgement() is spec["command_requires_ack"] is True
    assert sorted(cmd.content.keys()) == spec["command_content_keys"]
    assert evt.recipient == spec["event_recipient"] is None
    assert evt.priority.value == spec["event_priority"] == "high"
    assert info.recipient == spec["info_recipient"] is None


@pytest.mark.parametrize("case", _load_examples()["filter_cases"])
def test_channel_filter_round_trip(case: dict[str, Any]) -> None:
    probe = msg(MessageType.COMMAND, content={"command_type": "execute_analysis"})
    local = LocalChannel("guard")
    if "raises" in case:
        assert case["raises"] == "ValueError"
        with pytest.raises(ValueError):
            local.matches_filter(probe, CRITERIA[case["name"]])
    else:
        assert local.matches_filter(probe, CRITERIA[case["name"]]) == case["expected"]


@pytest.mark.parametrize("case", _load_examples()["topic_filter_cases"])
def test_topic_filter_round_trip(case: dict[str, Any]) -> None:
    topic = Topic("guard")
    probe = msg(MessageType.EVENT, sender="agent-a")
    assert (
        topic._matches_filter(probe, TOPIC_CRITERIA[case["name"]]) == case["expected"]
    )


@pytest.mark.parametrize("case", _load_examples()["routing_cases"])
def test_routing_table_round_trip(case: dict[str, Any]) -> None:
    bare = MessageMiddleware()
    content: dict[str, Any] = {}
    if case["info_type"]:
        content["info_type"] = case["info_type"]
    if case["request_type"]:
        content["request_type"] = case["request_type"]
    m = msg(
        MessageType(case["message_type"]),
        content=content,
        channel=case["explicit_channel"],
    )
    assert bare.determine_channel(m).value == case["expected"]


def test_middleware_wiring_and_collaboration_trap() -> None:
    cases = {c["name"]: c for c in _load_examples()["middleware_cases"]}

    bare = MessageMiddleware()
    assert (
        bare.send_message(msg(MessageType.COMMAND, recipient="tactical-1"))
        is cases["bare_middleware_is_a_silent_bus"]["expected"]
    )
    assert not bare.channels

    mw = create_default_middleware()
    ids = sorted(c.id for c in mw.channels.values())
    assert (
        ids
        == cases["default_registers_exactly_two_channels"]["expected"]
        == [
            "data_main",
            "hierarchical_main",
        ]
    )

    def assistance() -> Message:
        return msg(
            MessageType.REQUEST,
            sender="tactical-1",
            level=AgentLevel.TACTICAL,
            content={"request_type": "assistance"},
            recipient="tactical-2",
        )

    assert mw.send_message(assistance()) is (
        cases["assistance_routes_to_unregistered_collaboration"]["expected"]
    )
    mw.register_channel(CollaborationChannel(channel_id="collaboration_main"))
    assert mw.send_message(assistance()) is (
        cases["registering_collaboration_fixes_it"]["expected"]
    )


def test_adapter_junction_per_level() -> None:
    from argumentation_analysis.core.communication.operational_adapter import (
        OperationalAdapter,
    )
    from argumentation_analysis.core.communication.tactical_adapter import (
        TacticalAdapter,
    )

    mw = MessageMiddleware()
    assert isinstance(
        mw.get_adapter("tactical-1", AgentLevel.TACTICAL), TacticalAdapter
    )
    assert isinstance(
        mw.get_adapter("operational-1", AgentLevel.OPERATIONAL), OperationalAdapter
    )
    assert mw.get_adapter("strategic-1", AgentLevel.STRATEGIC) is None


def test_hierarchical_channel_round_trip() -> None:
    cases = {c["name"]: c for c in _load_examples()["hierarchical_cases"]}

    hc = HierarchicalChannel("guard")
    assert (
        hc.send_message(msg(MessageType.COMMAND, recipient=None))
        is cases["recipient_required"]["expected"]
    )

    for pr, off in [
        (MessagePriority.NORMAL, 0),
        (MessagePriority.CRITICAL, 5),
        (MessagePriority.LOW, 10),
    ]:
        hc.send_message(
            msg(
                MessageType.COMMAND,
                sender="strategic-1",
                level=AgentLevel.STRATEGIC,
                priority=pr,
                content={"command_type": "execute_analysis"},
                recipient="tactical-1",
                ts=T0 + timedelta(seconds=off),
            )
        )
    order = [
        hc.receive_message("tactical-1", timeout=1.0).priority.value for _ in range(3)
    ]
    assert (
        order
        == cases["priority_queue_critical_first"]["expected"]
        == [
            "critical",
            "normal",
            "low",
        ]
    )

    hc2 = HierarchicalChannel("guard2")
    for i in range(3):
        hc2.send_message(
            msg(
                MessageType.INFORMATION,
                recipient="tactical-1",
                ts=T0 + timedelta(seconds=i),
            )
        )
    pend = [len(hc2.get_pending_messages("tactical-1")) for _ in range(2)]
    pend.append(hc2.clear_queue("tactical-1"))
    pend.append(len(hc2.get_pending_messages("tactical-1")))
    assert pend == cases["pending_is_non_destructive"]["expected"] == [3, 3, 3, 0]

    hc3 = HierarchicalChannel("guard3")
    hc3.send_message(
        msg(
            MessageType.COMMAND,
            sender="strategic-1",
            level=AgentLevel.STRATEGIC,
            recipient="tactical-9",
        )
    )
    hc3.send_message(
        msg(
            MessageType.INFORMATION,
            sender="operational-1",
            level=AgentLevel.OPERATIONAL,
            recipient="tactical-9",
        )
    )
    hc3.send_message(
        msg(
            MessageType.INFORMATION,
            sender="tactical-1",
            level=AgentLevel.TACTICAL,
            recipient="tactical-2",
        )
    )
    assert (
        hc3.stats["by_direction"]
        == cases["direction_stats_keyed_on_recipient_prefix"]["expected"]
    )


def test_pending_semantics_local_drains_hierarchical_preserves() -> None:
    case = _load_examples()["pending_semantics_cases"][0]

    lc = LocalChannel("guard")
    for i in range(2):
        lc.send_message(
            msg(
                MessageType.INFORMATION,
                recipient="tactical-1",
                ts=T0 + timedelta(seconds=i),
            )
        )
    local_counts = [len(lc.get_pending_messages("tactical-1")) for _ in range(2)]
    assert local_counts == case["local"] == [2, 0]

    hc = HierarchicalChannel("guard")
    for i in range(3):
        hc.send_message(
            msg(
                MessageType.INFORMATION,
                recipient="tactical-1",
                ts=T0 + timedelta(seconds=i),
            )
        )
    hier_counts = [len(hc.get_pending_messages("tactical-1")) for _ in range(2)]
    assert hier_counts == case["hierarchical"] == [3, 3]


def test_collaboration_round_trip() -> None:
    cases = {c["name"]: c for c in _load_examples()["collaboration_cases"]}

    cc = CollaborationChannel("guard")
    cc.create_group(group_id="cellule-alpha", members=["sherlock", "watson"])
    outsider = msg(
        MessageType.INFORMATION,
        sender="moriarty",
        level=AgentLevel.OPERATIONAL,
        content={"info_type": "status_update"},
        metadata={"group_id": "cellule-alpha"},
    )
    member = msg(
        MessageType.INFORMATION,
        sender="sherlock",
        level=AgentLevel.OPERATIONAL,
        content={"info_type": "clue_found"},
        metadata={"group_id": "cellule-alpha"},
        mid="info-clue-0001",
    )
    c0 = cases["group_membership_enforced_on_send"]
    assert cc.send_message(outsider) is c0["outsider_send"] is False
    assert cc.send_message(member) is c0["member_send"] is True
    assert len(cc.get_group_messages("cellule-alpha")) == c0["history_len"] == 1

    c1 = cases["group_history_is_a_shared_log"]
    r1, r2 = cc.receive_message("watson"), cc.receive_message("watson")
    assert (r1.id if r1 else None) == c1["watson_first_read"] == "info-clue-0001"
    assert (r2.id if r2 else None) == c1["watson_second_read"] == "info-clue-0001"
    assert cc.receive_message("sherlock") is None

    c2 = cases["direct_messages_are_read_once"]
    direct = msg(
        MessageType.INFORMATION,
        sender="mycroft",
        level=AgentLevel.STRATEGIC,
        content={"info_type": "directive"},
        recipient="lestrade",
        mid="info-direct-0001",
    )
    assert cc.send_message(direct) is True
    d1, d2 = cc.receive_message("lestrade"), cc.receive_message("lestrade")
    assert (d1.id if d1 else None) == c2["first"] == "info-direct-0001"
    assert d2 is c2["second"] is None


def test_data_channel_claim_check_and_versioning() -> None:
    cases = {c["name"]: c for c in _load_examples()["data_cases"]}

    dc = DataChannel("guard")
    payload = {"paragraphs": ["analyse " * 40] * 60}
    assert (
        dc.max_inline_data_size
        == _load_examples()["inventory"]["max_inline_data_size"]
        == 10240
    )

    big = msg(
        MessageType.INFORMATION,
        sender="tactical-1",
        level=AgentLevel.TACTICAL,
        content={"info_type": "analysis_result", "data": payload},
        recipient="strategic-1",
    )
    dc.send_message(big)
    in_flight = dc.message_queues["strategic-1"][0]["message"].content
    c0 = cases["claim_check_in_flight"]
    assert in_flight.get("data") is c0["inline_none"] is None
    assert (in_flight.get("data_reference") is not None) is c0["reference_present"]

    received = dc.receive_message("strategic-1")
    c1 = cases["transparent_rehydration"]
    assert (received.content["data"] == payload) is c1["equal"] is True
    assert ("data_reference" not in received.content) is c1["reference_gone"] is True

    import time as _time

    dc.store_data("corpus-notes", {"revision": 1}, metadata={"stage": "extraction"})
    _time.sleep(0.01)
    dc.store_data("corpus-notes", {"revision": 2}, metadata={"stage": "synthesis"})
    versions = dc.data_store.get_versions("corpus-notes")
    latest, latest_meta = dc.get_data("corpus-notes")
    pinned, _ = dc.get_data("corpus-notes", versions[0])
    c2 = cases["versioning_latest_vs_pinned"]
    assert len(versions) == c2["versions_count"] == 2
    assert latest["revision"] == c2["latest_revision"] == 2
    assert pinned["revision"] == c2["pinned_revision"] == 1
    assert latest_meta["stage"] == c2["latest_stage"] == "synthesis"


def test_pubsub_round_trip() -> None:
    cases = {c["name"]: c for c in _load_examples()["pubsub_cases"]}
    mw = create_default_middleware()
    ps = PublishSubscribeProtocol(mw)
    try:
        received: list[str] = []
        ps.subscribe(
            topic_id="analyses",
            subscriber_id="veille-1",
            callback=lambda m: received.append(m.id),
        )
        broadcasts: list[str] = []
        mw.register_global_handler(lambda m: broadcasts.append(m.id))

        recipients = ps.publish(
            topic_id="analyses",
            sender="tactical-1",
            sender_level=AgentLevel.TACTICAL,
            content={"info_type": "analysis_result"},
        )
        c0 = cases["publish_returns_recipients"]
        assert recipients == c0["expected"] == ["veille-1"]
        assert len(received) == c0["callback_hits"] == 1

        before = len(broadcasts)
        ps.subscribe(topic_id="analyses", subscriber_id="veille-2")
        c2 = cases["subscribe_emits_nothing"]
        assert (len(broadcasts) - before) == c2["expected"] == 0

        for i in range(3):
            ps.publish(
                topic_id="analyses",
                sender="tactical-1",
                sender_level=AgentLevel.TACTICAL,
                content={"info_type": "analysis_result", "seq": i},
            )
        c1 = cases["broadcast_fans_out_to_global_listener"]
        assert (len(broadcasts) >= 4) is c1["expected"] is True

        late = ps.get_topic("analyses").get_recent_messages(2)
        c3 = cases["late_subscriber_reads_history"]
        assert [m.content.get("seq") for m in late] == c3["expected"] == [1, 2]
    finally:
        ps.shutdown()


def test_request_response_round_trip() -> None:
    cases = {c["name"]: c for c in _load_examples()["request_response_cases"]}
    mw = create_default_middleware()
    rr = RequestResponseProtocol(mw)
    try:
        c0 = cases["unanswered_request_raises_timeout"]
        with pytest.raises(RequestTimeoutError):
            rr.send_request(
                sender="strategic-1",
                sender_level=AgentLevel.STRATEGIC,
                recipient="personne",
                request_type="get_analysis",
                content={},
                timeout=0.3,
            )
        assert c0["expected"] == "RequestTimeoutError"

        rid = rr.send_request_async_callback(
            sender="strategic-1",
            sender_level=AgentLevel.STRATEGIC,
            recipient="tactical-1",
            request_type="get_status",
            content={},
            callback=lambda r, e: None,
            timeout=30,
        )
        answer = msg(
            MessageType.RESPONSE,
            sender="tactical-1",
            level=AgentLevel.TACTICAL,
            content={"status": "ok"},
            recipient="strategic-1",
            metadata={"reply_to": rid, "conversation_id": "conv-x"},
        )
        c1 = cases["reply_to_correlation"]
        assert rr.handle_response(answer) is c1["correlated"] is True
        assert rr.pending_requests[rid]["completed"].is_set() is c1["completed"] is True
        assert rr.pending_requests[rid]["response"].content["status"] == c1["stored"]

        orphan = msg(
            MessageType.RESPONSE,
            sender="tactical-2",
            level=AgentLevel.TACTICAL,
            content={"status": "ko"},
            recipient="strategic-1",
            metadata={"reply_to": "request-inconnu"},
        )
        c2 = cases["orphan_response_parked_as_early"]
        assert rr.handle_response(orphan) is c2["handled"] is True
        assert len(rr.early_responses) == c2["early_count"] == 1
    finally:
        rr.shutdown()


def test_committed_notebook_carries_executed_outputs() -> None:
    with open(NOTEBOOK_PATH, encoding="utf-8") as fh:
        nb = json.load(fh)
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert code_cells, "notebook has code cells"
    for cell in code_cells:
        assert cell.get("outputs"), "every code cell ships an executed output"
        assert cell.get("execution_count") is not None
