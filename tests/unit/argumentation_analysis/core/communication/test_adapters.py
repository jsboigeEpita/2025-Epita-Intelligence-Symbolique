# tests/unit/argumentation_analysis/core/communication/test_adapters.py
"""Tests for StrategicAdapter and TacticalAdapter — hierarchical communication adapters."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from argumentation_analysis.core.communication.strategic_adapter import StrategicAdapter
from argumentation_analysis.core.communication.tactical_adapter import TacticalAdapter
from argumentation_analysis.core.communication.message import (
    Message,
    MessageType,
    MessagePriority,
    AgentLevel,
)
from argumentation_analysis.core.communication.channel_interface import ChannelType
from argumentation_analysis.paths import DATA_DIR


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_middleware():
    m = MagicMock()
    m.send_message.return_value = True
    m.publish.return_value = ["agent_1", "agent_2"]
    m.receive_message.return_value = None
    return m


@pytest.fixture
def strategic(mock_middleware):
    return StrategicAdapter("strategic_01", mock_middleware)


@pytest.fixture
def tactical(mock_middleware):
    return TacticalAdapter("tactical_01", mock_middleware)


def make_directive_message(sender="strategic_01", command_type="analyze_text"):
    """Create a mock directive message from a strategic agent."""
    msg = Message(
        message_type=MessageType.COMMAND,
        sender=sender,
        sender_level=AgentLevel.STRATEGIC,
        content={"command_type": command_type, "parameters": {"text": "sample"}},
        recipient="tactical_01",
        channel=ChannelType.HIERARCHICAL.value,
        priority=MessagePriority.HIGH,
        metadata={"requires_ack": True},
    )
    return msg


def make_report_message(sender="tactical_01", report_type="status_update"):
    """Create a mock report message from a tactical agent."""
    return Message(
        message_type=MessageType.INFORMATION,
        sender=sender,
        sender_level=AgentLevel.TACTICAL,
        content={
            "info_type": "report",
            "report_type": report_type,
            "data": {"status": "complete"},
        },
        recipient="strategic_01",
        channel=ChannelType.HIERARCHICAL.value,
    )


def make_task_result_message(sender="operational_01"):
    """Create a mock task result message from an operational agent."""
    return Message(
        message_type=MessageType.INFORMATION,
        sender=sender,
        sender_level=AgentLevel.OPERATIONAL,
        content={
            "info_type": "task_result",
            "data": {"result": "found fallacy"},
        },
        recipient="tactical_01",
        channel=ChannelType.HIERARCHICAL.value,
    )


# ══════════════════════════════════════════════════════════════════════════
# StrategicAdapter Tests
# ══════════════════════════════════════════════════════════════════════════

class TestStrategicAdapterInit:
    """Tests for StrategicAdapter.__init__."""

    def test_agent_id_stored(self, strategic):
        assert strategic.agent_id == "strategic_01"

    def test_middleware_stored(self, strategic, mock_middleware):
        assert strategic.middleware is mock_middleware


class TestIssueDirective:
    """Tests for StrategicAdapter.issue_directive()."""

    def test_returns_message_id(self, strategic):
        msg_id = strategic.issue_directive("analyze_text", {"text": "sample"})
        assert isinstance(msg_id, str)
        assert len(msg_id) > 0

    def test_sends_via_middleware(self, strategic, mock_middleware):
        strategic.issue_directive("analyze_text", {"text": "sample"})
        mock_middleware.send_message.assert_called_once()

    def test_message_is_command_type(self, strategic, mock_middleware):
        strategic.issue_directive("analyze_text", {"text": "x"})
        sent = mock_middleware.send_message.call_args[0][0]
        assert sent.type == MessageType.COMMAND
        assert sent.sender_level == AgentLevel.STRATEGIC

    def test_recipient_set(self, strategic, mock_middleware):
        strategic.issue_directive("analyze", {"t": "x"}, recipient_id="tactical_02")
        sent = mock_middleware.send_message.call_args[0][0]
        assert sent.recipient == "tactical_02"

    def test_no_recipient_broadcasts(self, strategic, mock_middleware):
        strategic.issue_directive("analyze", {"t": "x"})
        sent = mock_middleware.send_message.call_args[0][0]
        assert sent.recipient is None

    def test_priority_set(self, strategic, mock_middleware):
        strategic.issue_directive("a", {}, priority=MessagePriority.CRITICAL)
        sent = mock_middleware.send_message.call_args[0][0]
        assert sent.priority == MessagePriority.CRITICAL

    def test_requires_ack_metadata(self, strategic, mock_middleware):
        strategic.issue_directive("a", {}, requires_ack=True)
        sent = mock_middleware.send_message.call_args[0][0]
        assert sent.metadata["requires_ack"] is True

    def test_custom_metadata_merged(self, strategic, mock_middleware):
        strategic.issue_directive("a", {}, metadata={"custom_key": "value"})
        sent = mock_middleware.send_message.call_args[0][0]
        assert sent.metadata["custom_key"] == "value"

    def test_send_failure_still_returns_id(self, strategic, mock_middleware):
        mock_middleware.send_message.return_value = False
        msg_id = strategic.issue_directive("a", {})
        assert isinstance(msg_id, str)


class TestBroadcastObjective:
    """Tests for StrategicAdapter.broadcast_objective()."""

    def test_returns_message_id(self, strategic):
        msg_id = strategic.broadcast_objective("global_strategy", {"plan": "full"})
        assert isinstance(msg_id, str)

    def test_publishes_via_middleware(self, strategic, mock_middleware):
        strategic.broadcast_objective("perf_target", {"target": 95})
        mock_middleware.publish.assert_called_once()
        call_kwargs = mock_middleware.publish.call_args
        assert "objectives.perf_target" in str(call_kwargs)


class TestReceiveReport:
    """Tests for StrategicAdapter.receive_report()."""

    def test_timeout_returns_none(self, strategic, mock_middleware):
        mock_middleware.receive_message.return_value = None
        result = strategic.receive_report(timeout=0.1)
        assert result is None

    def test_receives_matching_report(self, strategic, mock_middleware):
        report = make_report_message()
        mock_middleware.receive_message.return_value = report
        result = strategic.receive_report(timeout=0.1)
        assert result is report

    def test_ignores_non_report(self, strategic, mock_middleware):
        # First call returns non-report, subsequent calls return None (timeout)
        non_report = Message(
            message_type=MessageType.COMMAND,
            sender="tactical_01",
            sender_level=AgentLevel.TACTICAL,
            content={"info_type": "not_report"},
            recipient="strategic_01",
        )
        call_count = [0]
        def receive_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return non_report
            return None
        mock_middleware.receive_message.side_effect = receive_side_effect
        result = strategic.receive_report(timeout=0.2)
        assert result is None

    def test_filter_criteria_match(self, strategic, mock_middleware):
        report = make_report_message(report_type="analysis_done")
        mock_middleware.receive_message.return_value = report
        result = strategic.receive_report(
            timeout=0.1,
            filter_criteria={"status": "complete"},
        )
        assert result is report

    def test_filter_criteria_no_match(self, strategic, mock_middleware):
        report = make_report_message()
        call_count = [0]
        def receive_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return report
            return None
        mock_middleware.receive_message.side_effect = receive_side_effect
        result = strategic.receive_report(
            timeout=0.2,
            filter_criteria={"status": "wrong_value"},
        )
        assert result is None


class TestRequestTacticalInfo:
    """Tests for StrategicAdapter.request_tactical_info()."""

    def test_returns_data_on_success(self, strategic, mock_middleware):
        response = MagicMock()
        response.content = {DATA_DIR: {"status": "ok"}}
        mock_middleware.send_request.return_value = response
        result = strategic.request_tactical_info("status", {}, "tactical_01")
        assert result == {"status": "ok"}

    def test_returns_none_on_timeout(self, strategic, mock_middleware):
        mock_middleware.send_request.return_value = None
        result = strategic.request_tactical_info("status", {}, "tactical_01")
        assert result is None

    def test_returns_none_on_error(self, strategic, mock_middleware):
        mock_middleware.send_request.side_effect = RuntimeError("conn error")
        result = strategic.request_tactical_info("status", {}, "tactical_01")
        assert result is None


class TestRequestTacticalInfoAsync:
    """Tests for StrategicAdapter.request_tactical_info_async()."""

    async def test_returns_data(self, strategic, mock_middleware):
        response = MagicMock()
        response.content = {DATA_DIR: {"val": 42}}
        mock_middleware.send_request_async = AsyncMock(return_value=response)
        result = await strategic.request_tactical_info_async("q", {}, "t01")
        assert result == {"val": 42}

    async def test_timeout_returns_none(self, strategic, mock_middleware):
        mock_middleware.send_request_async = AsyncMock(return_value=None)
        result = await strategic.request_tactical_info_async("q", {}, "t01")
        assert result is None

    async def test_error_returns_none(self, strategic, mock_middleware):
        mock_middleware.send_request_async = AsyncMock(side_effect=Exception("fail"))
        result = await strategic.request_tactical_info_async("q", {}, "t01")
        assert result is None


class TestCollaborateWithStrategic:
    """Tests for StrategicAdapter.collaborate_with_strategic()."""

    def test_creates_new_group(self, strategic, mock_middleware):
        collab_channel = MagicMock()
        collab_channel.create_group.return_value = "grp-001"
        mock_middleware.get_channel.return_value = collab_channel

        msg_id = strategic.collaborate_with_strategic(
            "joint_planning", {"plan": "x"}, ["strategic_02"]
        )
        assert isinstance(msg_id, str)
        collab_channel.create_group.assert_called_once()

    def test_uses_existing_group(self, strategic, mock_middleware):
        collab_channel = MagicMock()
        mock_middleware.get_channel.return_value = collab_channel

        strategic.collaborate_with_strategic(
            "resource_sharing", {"res": "y"}, ["s02"], group_id="grp-existing"
        )
        collab_channel.add_group_member.assert_called_once_with("grp-existing", "s02")


# ══════════════════════════════════════════════════════════════════════════
# TacticalAdapter Tests
# ══════════════════════════════════════════════════════════════════════════

class TestTacticalAdapterInit:
    """Tests for TacticalAdapter.__init__."""

    def test_agent_id(self, tactical):
        assert tactical.agent_id == "tactical_01"

    def test_middleware(self, tactical, mock_middleware):
        assert tactical.middleware is mock_middleware


class TestReceiveDirective:
    """Tests for TacticalAdapter.receive_directive()."""

    def test_timeout_returns_none(self, tactical, mock_middleware):
        mock_middleware.receive_message.return_value = None
        result = tactical.receive_directive(timeout=0.1)
        assert result is None

    def test_receives_directive(self, tactical, mock_middleware):
        directive = make_directive_message()
        mock_middleware.receive_message.return_value = directive
        result = tactical.receive_directive(timeout=0.1)
        assert result is directive

    def test_non_directive_ignored(self, tactical, mock_middleware):
        info_msg = Message(
            message_type=MessageType.INFORMATION,
            sender="strategic_01",
            sender_level=AgentLevel.STRATEGIC,
            content={},
        )
        mock_middleware.receive_message.return_value = info_msg
        result = tactical.receive_directive(timeout=0.1)
        assert result is None

    def test_non_strategic_sender_ignored(self, tactical, mock_middleware):
        cmd = Message(
            message_type=MessageType.COMMAND,
            sender="tactical_02",
            sender_level=AgentLevel.TACTICAL,  # Not STRATEGIC
            content={},
        )
        mock_middleware.receive_message.return_value = cmd
        result = tactical.receive_directive(timeout=0.1)
        assert result is None

    def test_filter_criteria_match(self, tactical, mock_middleware):
        directive = make_directive_message(command_type="detect_fallacies")
        mock_middleware.receive_message.return_value = directive
        result = tactical.receive_directive(
            timeout=0.1,
            filter_criteria={"command_type": "detect_fallacies"},
        )
        assert result is directive

    def test_filter_criteria_no_match(self, tactical, mock_middleware):
        directive = make_directive_message(command_type="analyze_text")
        mock_middleware.receive_message.return_value = directive
        result = tactical.receive_directive(
            timeout=0.1,
            filter_criteria={"command_type": "wrong_command"},
        )
        assert result is None

    def test_filter_list_match(self, tactical, mock_middleware):
        directive = make_directive_message(command_type="analyze_text")
        mock_middleware.receive_message.return_value = directive
        result = tactical.receive_directive(
            timeout=0.1,
            filter_criteria={"command_type": ["analyze_text", "detect_fallacies"]},
        )
        assert result is directive

    def test_sends_ack_when_required(self, tactical, mock_middleware):
        directive = make_directive_message()
        mock_middleware.receive_message.return_value = directive
        tactical.receive_directive(timeout=0.1)
        # Ack should be sent
        assert mock_middleware.send_message.called


class TestAssignTask:
    """Tests for TacticalAdapter.assign_task()."""

    def test_returns_message_id(self, tactical):
        msg_id = tactical.assign_task(
            "detect_fallacies", {"text": "sample"}, "operational_01"
        )
        assert isinstance(msg_id, str)

    def test_sends_via_middleware(self, tactical, mock_middleware):
        tactical.assign_task("analyze", {"t": "x"}, "op_01")
        mock_middleware.send_message.assert_called_once()

    def test_message_content(self, tactical, mock_middleware):
        tactical.assign_task("detect", {"t": "x"}, "op_01", constraints={"max_time": 30})
        sent = mock_middleware.send_message.call_args[0][0]
        assert sent.content["command_type"] == "detect"
        assert sent.content["constraints"] == {"max_time": 30}

    def test_sender_level_tactical(self, tactical, mock_middleware):
        tactical.assign_task("t", {}, "op_01")
        sent = mock_middleware.send_message.call_args[0][0]
        assert sent.sender_level == AgentLevel.TACTICAL

    def test_send_failure(self, tactical, mock_middleware):
        mock_middleware.send_message.return_value = False
        msg_id = tactical.assign_task("t", {}, "op_01")
        assert isinstance(msg_id, str)  # Still returns ID


class TestSendReport:
    """Tests for TacticalAdapter.send_report()."""

    def test_returns_message_id(self, tactical):
        msg_id = tactical.send_report("status_update", {"done": True}, "strategic_01")
        assert isinstance(msg_id, str)

    def test_report_content(self, tactical, mock_middleware):
        tactical.send_report("analysis_complete", {"score": 0.9}, "s01")
        sent = mock_middleware.send_message.call_args[0][0]
        assert sent.content["info_type"] == "report"
        assert sent.content["report_type"] == "analysis_complete"
        assert sent.content["data"]["score"] == 0.9


class TestReceiveTaskResult:
    """Tests for TacticalAdapter.receive_task_result()."""

    def test_timeout_returns_none(self, tactical, mock_middleware):
        mock_middleware.receive_message.return_value = None
        result = tactical.receive_task_result(timeout=0.1)
        assert result is None

    def test_receives_task_result(self, tactical, mock_middleware):
        task_result = make_task_result_message()
        mock_middleware.receive_message.return_value = task_result
        result = tactical.receive_task_result(timeout=0.1)
        assert result is task_result

    def test_ignores_non_operational(self, tactical, mock_middleware):
        wrong = Message(
            message_type=MessageType.INFORMATION,
            sender="tactical_02",
            sender_level=AgentLevel.TACTICAL,  # Not OPERATIONAL
            content={"info_type": "task_result"},
            recipient="tactical_01",
        )
        call_count = [0]
        def receive_side_effect(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return wrong
            return None
        mock_middleware.receive_message.side_effect = receive_side_effect
        result = tactical.receive_task_result(timeout=0.2)
        assert result is None


class TestRequestStrategicGuidance:
    """Tests for TacticalAdapter.request_strategic_guidance()."""

    def test_returns_data(self, tactical, mock_middleware):
        response = MagicMock()
        response.content = {DATA_DIR: {"guidance": "proceed"}}
        mock_middleware.send_request.return_value = response
        result = tactical.request_strategic_guidance("clarification", {}, "s01")
        assert result == {"guidance": "proceed"}

    def test_timeout_returns_none(self, tactical, mock_middleware):
        mock_middleware.send_request.return_value = None
        result = tactical.request_strategic_guidance("q", {}, "s01")
        assert result is None

    def test_error_returns_none(self, tactical, mock_middleware):
        mock_middleware.send_request.side_effect = Exception("err")
        result = tactical.request_strategic_guidance("q", {}, "s01")
        assert result is None


class TestRequestStrategicGuidanceAsync:
    """Tests for TacticalAdapter.request_strategic_guidance_async()."""

    async def test_returns_data(self, tactical, mock_middleware):
        response = MagicMock()
        response.content = {DATA_DIR: {"advice": "go"}}
        mock_middleware.send_request_async = AsyncMock(return_value=response)
        result = await tactical.request_strategic_guidance_async("q", {}, "s01")
        assert result == {"advice": "go"}

    async def test_error_returns_none(self, tactical, mock_middleware):
        mock_middleware.send_request_async = AsyncMock(side_effect=Exception("boom"))
        result = await tactical.request_strategic_guidance_async("q", {}, "s01")
        assert result is None


class TestCollaborateWithTactical:
    """Tests for TacticalAdapter.collaborate_with_tactical()."""

    def test_creates_group(self, tactical, mock_middleware):
        collab = MagicMock()
        collab.create_group.return_value = "grp-tact"
        mock_middleware.get_channel.return_value = collab

        msg_id = tactical.collaborate_with_tactical(
            "task_coordination", {"data": "x"}, ["tactical_02"]
        )
        assert isinstance(msg_id, str)
        collab.create_group.assert_called_once()

    def test_adds_members_to_existing_group(self, tactical, mock_middleware):
        collab = MagicMock()
        mock_middleware.get_channel.return_value = collab

        tactical.collaborate_with_tactical(
            "resource_sharing", {}, ["t02", "t03"], group_id="grp-existing"
        )
        assert collab.add_group_member.call_count == 2
