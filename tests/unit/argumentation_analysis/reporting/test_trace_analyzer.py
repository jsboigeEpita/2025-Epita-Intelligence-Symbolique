# tests/unit/argumentation_analysis/reporting/test_trace_analyzer.py
"""Tests for trace_analyzer dataclasses and utility methods."""

import json
import time
import pytest
from dataclasses import asdict

from argumentation_analysis.reporting.trace_analyzer import (
    ExtractMetadata,
    OrchestrationFlow,
    StateEvolution,
    QueryResults,
    ToolCall,
    AgentStep,
    ConversationCapture,
    InformalExploration,
)

# ── ExtractMetadata ──


class TestExtractMetadata:
    def test_required_fields(self):
        m = ExtractMetadata(
            source_file="test.txt",
            content_length=100,
            content_type="text",
            complexity_level="low",
            analysis_timestamp="2026-01-01",
        )
        assert m.source_file == "test.txt"
        assert m.content_length == 100
        assert m.content_type == "text"
        assert m.complexity_level == "low"

    def test_optional_fields_default_none(self):
        m = ExtractMetadata(
            source_file="f",
            content_length=0,
            content_type="t",
            complexity_level="l",
            analysis_timestamp="ts",
        )
        assert m.encoding_info is None
        assert m.source_origin is None

    def test_optional_fields_set(self):
        m = ExtractMetadata(
            source_file="f",
            content_length=50,
            content_type="html",
            complexity_level="high",
            analysis_timestamp="ts",
            encoding_info="utf-8",
            source_origin="web",
        )
        assert m.encoding_info == "utf-8"
        assert m.source_origin == "web"

    def test_asdict(self):
        m = ExtractMetadata(
            source_file="test.txt",
            content_length=100,
            content_type="text",
            complexity_level="medium",
            analysis_timestamp="2026-01-01",
        )
        d = asdict(m)
        assert d["source_file"] == "test.txt"
        assert d["content_length"] == 100


# ── OrchestrationFlow ──


class TestOrchestrationFlow:
    def test_basic(self):
        flow = OrchestrationFlow(
            agents_called=["agent_1", "agent_2"],
            sequence_order=[("agent_1", "analyze"), ("agent_2", "validate")],
            coordination_messages=["start", "done"],
            total_execution_time=1.5,
            success_status="completed",
        )
        assert len(flow.agents_called) == 2
        assert flow.total_execution_time == 1.5
        assert flow.success_status == "completed"

    def test_empty_flow(self):
        flow = OrchestrationFlow(
            agents_called=[],
            sequence_order=[],
            coordination_messages=[],
            total_execution_time=0.0,
            success_status="empty",
        )
        assert len(flow.agents_called) == 0


# ── StateEvolution ──


class TestStateEvolution:
    def test_basic(self):
        evo = StateEvolution(
            shared_state_changes=[{"key": "val1"}, {"key": "val2"}],
            belief_state_construction=[{"belief": "B1"}],
            progressive_enrichment=["step1", "step2"],
            state_transitions=[("init", "active"), ("active", "done")],
        )
        assert len(evo.shared_state_changes) == 2
        assert len(evo.state_transitions) == 2

    def test_empty_evolution(self):
        evo = StateEvolution(
            shared_state_changes=[],
            belief_state_construction=[],
            progressive_enrichment=[],
            state_transitions=[],
        )
        assert len(evo.progressive_enrichment) == 0


# ── QueryResults ──


class TestQueryResults:
    def test_basic(self):
        qr = QueryResults(
            formalizations=[{"formula": "A -> B"}],
            inference_queries=["query1"],
            validation_results=[{"valid": True}],
            logic_types_used=["FOL", "propositional"],
            knowledge_base_status="loaded",
        )
        assert len(qr.formalizations) == 1
        assert qr.knowledge_base_status == "loaded"
        assert "FOL" in qr.logic_types_used


# ── ToolCall ──


class TestToolCall:
    @pytest.fixture
    def basic_call(self):
        return ToolCall(
            tool_name="analyze_text",
            arguments={"text": "hello world"},
            result={"score": 0.9},
            timestamp=1000.0,
            execution_time_ms=42.5,
            success=True,
        )

    def test_basic_init(self, basic_call):
        assert basic_call.tool_name == "analyze_text"
        assert basic_call.success is True
        assert basic_call.error_message is None

    def test_error_message(self):
        call = ToolCall(
            tool_name="fail",
            arguments={},
            result=None,
            timestamp=1000.0,
            execution_time_ms=5.0,
            success=False,
            error_message="timeout",
        )
        assert call.error_message == "timeout"
        assert call.success is False

    # -- to_compact_string --

    def test_compact_string_success(self, basic_call):
        s = basic_call.to_compact_string()
        assert "✓" in s
        assert "analyze_text" in s
        assert "42.5ms" in s

    def test_compact_string_failure(self):
        call = ToolCall("fail", {}, None, 0, 1.0, False)
        s = call.to_compact_string()
        assert "✗" in s

    def test_compact_string_long_args_truncated(self):
        long_args = {"text": "x" * 200}
        call = ToolCall("tool", long_args, None, 0, 1.0, True)
        s = call.to_compact_string()
        assert "..." in s

    # -- to_conversation_format --

    def test_conversation_format(self, basic_call):
        s = basic_call.to_conversation_format("Sherlock")
        assert "[AGENT] Sherlock" in s
        assert "[TOOL] analyze_text" in s
        assert "[TIME]" in s
        assert "[RESULT]" in s

    def test_conversation_format_default_agent(self, basic_call):
        s = basic_call.to_conversation_format()
        assert "[AGENT] Agent" in s

    # -- _format_arguments_intelligently --

    def test_format_args_empty(self):
        call = ToolCall("t", {}, None, 0, 0, True)
        assert call._format_arguments_intelligently() == "{}"

    def test_format_args_short_string(self):
        call = ToolCall("t", {"key": "short"}, None, 0, 0, True)
        result = call._format_arguments_intelligently()
        assert "key=" in result
        assert "short" in result

    def test_format_args_long_string_truncated(self):
        call = ToolCall("t", {"key": "x" * 200}, None, 0, 0, True)
        result = call._format_arguments_intelligently()
        assert "..." in result

    def test_format_args_long_list(self):
        call = ToolCall("t", {"items": list(range(100))}, None, 0, 0, True)
        result = call._format_arguments_intelligently()
        assert "items" in result

    def test_format_args_long_dict(self):
        call = ToolCall("t", {"data": {str(i): i for i in range(20)}}, None, 0, 0, True)
        result = call._format_arguments_intelligently()
        assert "keys" in result

    def test_format_args_total_truncation(self):
        call = ToolCall(
            "t", {f"key_{i}": f"value_{i}" * 10 for i in range(20)}, None, 0, 0, True
        )
        result = call._format_arguments_intelligently()
        # Very long args string gets truncated to 150 chars
        assert len(result) <= 153  # 150 + "..."

    # -- _format_result_concisely --

    def test_format_result_none(self):
        call = ToolCall("t", {}, None, 0, 0, True)
        assert call._format_result_concisely() == "None"

    def test_format_result_short_string(self):
        call = ToolCall("t", {}, "hello", 0, 0, True)
        assert call._format_result_concisely() == '"hello"'

    def test_format_result_long_string(self):
        call = ToolCall("t", {}, "x" * 100, 0, 0, True)
        result = call._format_result_concisely()
        assert result.endswith('..."')
        assert len(result) < 100

    def test_format_result_empty_list(self):
        call = ToolCall("t", {}, [], 0, 0, True)
        assert call._format_result_concisely() == "[]"

    def test_format_result_short_list(self):
        call = ToolCall("t", {}, [1, 2, 3], 0, 0, True)
        assert call._format_result_concisely() == "[1, 2, 3]"

    def test_format_result_long_list(self):
        call = ToolCall("t", {}, list(range(10)), 0, 0, True)
        result = call._format_result_concisely()
        assert "10 éléments" in result

    def test_format_result_small_dict(self):
        call = ToolCall("t", {}, {"a": 1}, 0, 0, True)
        result = call._format_result_concisely()
        assert "a" in result

    def test_format_result_large_dict(self):
        call = ToolCall("t", {}, {"a": 1, "b": 2, "c": 3, "d": 4}, 0, 0, True)
        result = call._format_result_concisely()
        assert "more" in result

    def test_format_result_integer(self):
        call = ToolCall("t", {}, 42, 0, 0, True)
        assert call._format_result_concisely() == "42"

    def test_format_result_boolean(self):
        call = ToolCall("t", {}, True, 0, 0, True)
        assert call._format_result_concisely() == "True"

    def test_format_result_long_other_type(self):
        call = ToolCall("t", {}, list(range(1000)), 0, 0, True)
        result = call._format_result_concisely()
        # Long list truncated
        assert "1000" in result


# ── AgentStep ──


class TestAgentStep:
    def test_basic_init(self):
        step = AgentStep(agent_name="sherlock")
        assert step.agent_name == "sherlock"
        assert step.tool_calls == []
        assert step.status == "active"
        assert step.end_time is None

    def test_add_tool_call(self):
        step = AgentStep(agent_name="watson")
        call = ToolCall("t", {}, None, 0, 0, True)
        step.add_tool_call(call)
        assert len(step.tool_calls) == 1

    def test_complete(self):
        step = AgentStep(agent_name="agent")
        step.complete()
        assert step.status == "completed"
        assert step.end_time is not None

    def test_complete_with_status(self):
        step = AgentStep(agent_name="agent")
        step.complete(status="failed")
        assert step.status == "failed"

    def test_get_duration_ms_completed(self):
        step = AgentStep(agent_name="agent")
        step.start_time = 1000.0
        step.end_time = 1001.0
        assert step.get_duration_ms() == 1000.0

    def test_get_duration_ms_active(self):
        step = AgentStep(agent_name="agent")
        # Active step returns duration until now
        duration = step.get_duration_ms()
        assert duration >= 0

    def test_to_conversation_format_no_tools(self):
        step = AgentStep(agent_name="sherlock")
        result = step.to_conversation_format()
        assert "[AGENT] sherlock" in result
        assert "Aucun outil utilisé" in result

    def test_to_conversation_format_with_tools(self):
        step = AgentStep(agent_name="watson")
        call = ToolCall("analyze", {"text": "hi"}, "ok", 0, 5.0, True)
        step.add_tool_call(call)
        result = step.to_conversation_format()
        assert "analyze" in result
        assert "[AGENT] watson" in result


# ── ConversationCapture ──


class TestConversationCapture:
    def test_init(self):
        cap = ConversationCapture()
        assert cap.messages == []
        assert cap.tool_calls == []
        assert cap.total_duration_ms == 0.0

    def test_add_message(self):
        cap = ConversationCapture()
        cap.add_message("user", "Hello")
        assert len(cap.messages) == 1
        assert cap.messages[0]["role"] == "user"
        assert cap.messages[0]["content"] == "Hello"
        assert "timestamp" in cap.messages[0]
        assert "relative_time_ms" in cap.messages[0]

    def test_add_message_with_timestamp(self):
        cap = ConversationCapture()
        cap.start_time = 1000.0
        cap.add_message("assistant", "Hi", timestamp=1001.0)
        assert cap.messages[0]["timestamp"] == 1001.0
        assert cap.messages[0]["relative_time_ms"] == 1000.0

    def test_add_tool_call(self):
        cap = ConversationCapture()
        call = ToolCall("t", {}, None, 0, 0, True)
        cap.add_tool_call(call)
        assert len(cap.tool_calls) == 1

    def test_finalize(self):
        cap = ConversationCapture()
        cap.finalize()
        assert cap.total_duration_ms > 0 or cap.total_duration_ms == 0.0

    def test_to_compact_summary(self):
        cap = ConversationCapture()
        cap.add_message("user", "Hello world this is a test message")
        call = ToolCall("analyze", {}, "result", 0, 10.0, True)
        cap.add_tool_call(call)
        cap.finalize()

        summary = cap.to_compact_summary()
        assert summary["total_messages"] == 1
        assert summary["total_tool_calls"] == 1
        assert isinstance(summary["tool_summary"], list)
        assert isinstance(summary["conversation_flow"], list)

    def test_compact_summary_truncates(self):
        cap = ConversationCapture()
        # Add many messages and tool calls
        for i in range(10):
            cap.add_message("user", f"Message {i} with some content")
        for i in range(10):
            cap.add_tool_call(ToolCall(f"tool_{i}", {}, None, 0, 0, True))
        cap.finalize()

        summary = cap.to_compact_summary()
        assert summary["total_messages"] == 10
        assert summary["total_tool_calls"] == 10
        # Only last 5 tool calls in summary
        assert len(summary["tool_summary"]) == 5
        # Only last 3 messages in flow
        assert len(summary["conversation_flow"]) == 3


# ── InformalExploration ──


class TestInformalExploration:
    def test_basic(self):
        exp = InformalExploration(
            taxonomy_path=["general", "specifique"],
            fallacy_detection=[{"type": "ad_hominem", "confidence": 0.8}],
            rhetorical_patterns=["appel_emotion"],
            severity_analysis=[{"severity": "high"}],
        )
        assert len(exp.taxonomy_path) == 2
        assert len(exp.fallacy_detection) == 1

    def test_optional_defaults(self):
        exp = InformalExploration(
            taxonomy_path=[],
            fallacy_detection=[],
            rhetorical_patterns=[],
            severity_analysis=[],
        )
        assert exp.taxonomy_workflow == []
        assert exp.sophism_keys_detected == []
        assert exp.arguments_identified == []
        assert exp.detection_method == ""

    def test_with_optional_fields(self):
        exp = InformalExploration(
            taxonomy_path=["level1"],
            fallacy_detection=[],
            rhetorical_patterns=[],
            severity_analysis=[],
            taxonomy_workflow=[{"step": 1}],
            sophism_keys_detected=[3, 7],
            arguments_identified=["arg1"],
            detection_method="pattern_matching",
        )
        assert exp.taxonomy_workflow[0]["step"] == 1
        assert 3 in exp.sophism_keys_detected
        assert exp.detection_method == "pattern_matching"


# ── Integration: dataclass serialization ──


class TestDataclassSerialization:
    def test_tool_call_roundtrip(self):
        call = ToolCall(
            tool_name="analyze",
            arguments={"text": "test"},
            result={"score": 0.5},
            timestamp=1000.0,
            execution_time_ms=25.0,
            success=True,
        )
        d = asdict(call)
        assert d["tool_name"] == "analyze"
        assert d["success"] is True
        json_str = json.dumps(d)
        restored = json.loads(json_str)
        assert restored["tool_name"] == "analyze"

    def test_extract_metadata_roundtrip(self):
        m = ExtractMetadata(
            source_file="test.txt",
            content_length=500,
            content_type="markdown",
            complexity_level="high",
            analysis_timestamp="2026-01-01T12:00:00",
            encoding_info="utf-8",
        )
        d = asdict(m)
        json_str = json.dumps(d)
        restored = json.loads(json_str)
        assert restored["source_file"] == "test.txt"
        assert restored["encoding_info"] == "utf-8"

    def test_orchestration_flow_serializable(self):
        flow = OrchestrationFlow(
            agents_called=["a", "b"],
            sequence_order=[("a", "init"), ("b", "run")],
            coordination_messages=["msg1"],
            total_execution_time=2.5,
            success_status="ok",
        )
        d = asdict(flow)
        json_str = json.dumps(d)
        assert len(json_str) > 10
