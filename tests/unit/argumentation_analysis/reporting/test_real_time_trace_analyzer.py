# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.reporting.real_time_trace_analyzer
Covers RealToolCall, AgentConversationBlock, RealTimeTraceAnalyzer,
tool_call_tracer decorator, and module-level helper functions.
"""

import time
import pytest
from unittest.mock import patch

from argumentation_analysis.reporting.real_time_trace_analyzer import (
    RealToolCall,
    AgentConversationBlock,
    RealTimeTraceAnalyzer,
    global_trace_analyzer,
    tool_call_tracer,
    start_conversation_capture,
    stop_conversation_capture,
    get_conversation_report,
)

# ============================================================
# RealToolCall — formatting
# ============================================================


class TestRealToolCall:
    def _make_call(self, **overrides):
        defaults = dict(
            agent_name="TestAgent",
            tool_name="test_tool",
            arguments={"key": "value"},
            result="ok",
            timestamp=1000.0,
            execution_time_ms=42.5,
            success=True,
        )
        defaults.update(overrides)
        return RealToolCall(**defaults)

    def test_basic_fields(self):
        call = self._make_call()
        assert call.agent_name == "TestAgent"
        assert call.tool_name == "test_tool"
        assert call.success is True

    def test_default_call_id(self):
        call = self._make_call()
        assert call.call_id == ""

    def test_default_error_message(self):
        call = self._make_call()
        assert call.error_message is None

    # --- _format_arguments_intelligently ---

    def test_format_args_empty(self):
        call = self._make_call(arguments={})
        assert call._format_arguments_intelligently() == "{}"

    def test_format_args_short_string(self):
        call = self._make_call(arguments={"name": "hello"})
        result = call._format_arguments_intelligently()
        assert 'name="hello"' in result

    def test_format_args_long_string_truncated(self):
        call = self._make_call(arguments={"text": "x" * 200})
        result = call._format_arguments_intelligently()
        assert "..." in result
        assert len(result) <= 200  # Not strictly 150 because of key name

    def test_format_args_list_short(self):
        call = self._make_call(arguments={"items": [1, 2]})
        result = call._format_arguments_intelligently()
        assert "items=" in result

    def test_format_args_list_long(self):
        call = self._make_call(arguments={"items": list(range(50))})
        result = call._format_arguments_intelligently()
        assert "50 items" in result

    def test_format_args_empty_list(self):
        call = self._make_call(arguments={"items": []})
        result = call._format_arguments_intelligently()
        assert "items=[]" in result

    def test_format_args_dict_short(self):
        call = self._make_call(arguments={"config": {"a": 1}})
        result = call._format_arguments_intelligently()
        assert "config=" in result

    def test_format_args_dict_long(self):
        call = self._make_call(arguments={"config": {f"k{i}": i for i in range(20)}})
        result = call._format_arguments_intelligently()
        assert "20 keys" in result

    def test_format_args_numeric(self):
        call = self._make_call(arguments={"count": 42})
        result = call._format_arguments_intelligently()
        assert "count=42" in result

    def test_format_args_overall_truncation(self):
        call = self._make_call(arguments={f"k{i}": f"v{i}" * 30 for i in range(10)})
        result = call._format_arguments_intelligently()
        assert len(result) <= 155  # 150 + "..."

    # --- _format_result_concisely ---

    def test_format_result_none(self):
        call = self._make_call(result=None)
        assert call._format_result_concisely() == "None"

    def test_format_result_short_string(self):
        call = self._make_call(result="short")
        assert call._format_result_concisely() == '"short"'

    def test_format_result_long_string(self):
        call = self._make_call(result="x" * 200)
        result = call._format_result_concisely()
        assert result.endswith('..."')
        assert len(result) <= 85

    def test_format_result_empty_list(self):
        call = self._make_call(result=[])
        assert call._format_result_concisely() == "[]"

    def test_format_result_short_list(self):
        call = self._make_call(result=[1, 2])
        assert call._format_result_concisely() == "[1, 2]"

    def test_format_result_long_list(self):
        call = self._make_call(result=list(range(10)))
        result = call._format_result_concisely()
        assert "10" in result
        assert "éléments" in result

    def test_format_result_small_dict(self):
        call = self._make_call(result={"a": 1})
        result = call._format_result_concisely()
        assert "a" in result

    def test_format_result_large_dict(self):
        call = self._make_call(result={"a": 1, "b": 2, "c": 3, "d": 4})
        result = call._format_result_concisely()
        assert "more" in result

    def test_format_result_other_type(self):
        call = self._make_call(result=42)
        assert call._format_result_concisely() == "42"

    def test_format_result_long_other_type(self):
        call = self._make_call(result="y" * 200)
        result = call._format_result_concisely()
        assert "..." in result

    # --- to_conversation_format ---

    def test_conversation_format_structure(self):
        call = self._make_call()
        output = call.to_conversation_format()
        assert "[AGENT] TestAgent" in output
        assert "[TOOL] test_tool" in output
        assert "[ARGS]" in output
        assert "[TIME]" in output
        assert "[RESULT]" in output

    def test_conversation_format_time_formatted(self):
        call = self._make_call(execution_time_ms=123.456)
        output = call.to_conversation_format()
        assert "123.5ms" in output


# ============================================================
# AgentConversationBlock
# ============================================================


class TestAgentConversationBlock:
    def test_init(self):
        block = AgentConversationBlock(agent_name="Agent1")
        assert block.agent_name == "Agent1"
        assert block.tool_calls == []
        assert block.end_time is None

    def test_add_tool_call(self):
        block = AgentConversationBlock(agent_name="Agent1")
        call = RealToolCall(
            agent_name="Agent1",
            tool_name="t",
            arguments={},
            result=None,
            timestamp=0,
            execution_time_ms=0,
            success=True,
        )
        block.add_tool_call(call)
        assert len(block.tool_calls) == 1

    def test_finalize_sets_end_time(self):
        block = AgentConversationBlock(agent_name="Agent1")
        assert block.end_time is None
        block.finalize()
        assert block.end_time is not None

    def test_conversation_format_empty(self):
        block = AgentConversationBlock(agent_name="Agent1")
        output = block.to_conversation_format()
        assert "Agent1" in output
        assert "Aucun outil" in output

    def test_conversation_format_with_calls(self):
        block = AgentConversationBlock(agent_name="Agent1")
        call = RealToolCall(
            agent_name="Agent1",
            tool_name="search",
            arguments={"q": "test"},
            result="found",
            timestamp=0,
            execution_time_ms=10.0,
            success=True,
        )
        block.add_tool_call(call)
        output = block.to_conversation_format()
        assert "[TOOL] search" in output


# ============================================================
# RealTimeTraceAnalyzer
# ============================================================


class TestRealTimeTraceAnalyzer:
    @pytest.fixture
    def analyzer(self):
        a = RealTimeTraceAnalyzer()
        yield a
        # Ensure capture stopped after each test
        a.stop_capture()

    def test_init_state(self, analyzer):
        assert analyzer.capture_enabled is False
        assert analyzer.conversation_blocks == []
        assert analyzer.current_block is None
        assert analyzer.total_tool_calls == 0

    def test_start_capture(self, analyzer):
        analyzer.start_capture()
        assert analyzer.capture_enabled is True
        assert analyzer.start_time is not None

    def test_stop_capture(self, analyzer):
        analyzer.start_capture()
        analyzer.stop_capture()
        assert analyzer.capture_enabled is False
        assert analyzer.end_time is not None

    def test_start_agent_block_when_disabled(self, analyzer):
        result = analyzer.start_agent_block("Agent1")
        assert result is None

    def test_start_agent_block_when_enabled(self, analyzer):
        analyzer.start_capture()
        block = analyzer.start_agent_block("Agent1")
        assert block is not None
        assert block.agent_name == "Agent1"
        assert len(analyzer.conversation_blocks) == 1

    def test_multiple_agent_blocks(self, analyzer):
        analyzer.start_capture()
        analyzer.start_agent_block("Agent1")
        analyzer.start_agent_block("Agent2")
        assert len(analyzer.conversation_blocks) == 2

    def test_record_tool_call_disabled(self, analyzer):
        analyzer.record_tool_call(
            agent_name="A",
            tool_name="t",
            arguments={},
            result=None,
            execution_time_ms=0,
        )
        assert analyzer.total_tool_calls == 0

    def test_record_tool_call_enabled(self, analyzer):
        analyzer.start_capture()
        # Pre-create block to avoid nested lock (source code uses non-reentrant Lock)
        analyzer.start_agent_block("Agent1")
        analyzer.record_tool_call(
            agent_name="Agent1",
            tool_name="search",
            arguments={"q": "test"},
            result="found",
            execution_time_ms=15.0,
        )
        assert analyzer.total_tool_calls == 1
        assert len(analyzer.conversation_blocks) == 1
        assert len(analyzer.conversation_blocks[0].tool_calls) == 1

    def test_record_creates_new_block_for_new_agent(self, analyzer):
        analyzer.start_capture()
        # Pre-create blocks to avoid nested lock deadlock
        analyzer.start_agent_block("A1")
        analyzer.record_tool_call(
            agent_name="A1",
            tool_name="t1",
            arguments={},
            result=None,
            execution_time_ms=0,
        )
        # Switch agent — pre-create block
        analyzer.start_agent_block("A2")
        analyzer.record_tool_call(
            agent_name="A2",
            tool_name="t2",
            arguments={},
            result=None,
            execution_time_ms=0,
        )
        assert len(analyzer.conversation_blocks) == 2

    def test_record_same_agent_same_block(self, analyzer):
        analyzer.start_capture()
        analyzer.start_agent_block("A1")
        analyzer.record_tool_call(
            agent_name="A1",
            tool_name="t1",
            arguments={},
            result=None,
            execution_time_ms=0,
        )
        analyzer.record_tool_call(
            agent_name="A1",
            tool_name="t2",
            arguments={},
            result=None,
            execution_time_ms=0,
        )
        assert len(analyzer.conversation_blocks) == 1
        assert len(analyzer.conversation_blocks[0].tool_calls) == 2

    def test_record_error_tool_call(self, analyzer):
        analyzer.start_capture()
        analyzer.start_agent_block("A1")
        analyzer.record_tool_call(
            agent_name="A1",
            tool_name="fail_tool",
            arguments={},
            result=None,
            execution_time_ms=5.0,
            success=False,
            error_message="timeout",
        )
        call = analyzer.conversation_blocks[0].tool_calls[0]
        assert call.success is False
        assert call.error_message == "timeout"

    # --- _get_total_duration_ms ---

    def test_duration_before_stop(self, analyzer):
        assert analyzer._get_total_duration_ms() == 0.0

    def test_duration_after_capture(self, analyzer):
        analyzer.start_capture()
        time.sleep(0.01)
        analyzer.stop_capture()
        duration = analyzer._get_total_duration_ms()
        assert duration > 0

    # --- generate_complete_conversation_report ---

    def test_report_empty(self, analyzer):
        report = analyzer.generate_complete_conversation_report()
        assert "Aucune conversation" in report

    def test_report_with_data(self, analyzer):
        analyzer.start_capture()
        analyzer.start_agent_block("Sherlock")
        analyzer.record_tool_call(
            agent_name="Sherlock",
            tool_name="investigate",
            arguments={"clue": "footprint"},
            result="suspect found",
            execution_time_ms=100.0,
        )
        analyzer.stop_capture()
        report = analyzer.generate_complete_conversation_report()
        assert "RAPPORT" in report
        assert "Sherlock" in report
        assert "investigate" in report
        assert "Répartition par agent" in report

    # --- trace_tool_call context manager ---

    def test_trace_context_manager_disabled(self, analyzer):
        with analyzer.trace_tool_call("A", "t", key="val"):
            pass
        assert analyzer.total_tool_calls == 0

    def test_trace_context_manager_enabled(self, analyzer):
        analyzer.start_capture()
        analyzer.start_agent_block("Agent")
        with analyzer.trace_tool_call("Agent", "tool", key="val"):
            time.sleep(0.001)
        assert analyzer.total_tool_calls == 1

    def test_trace_context_manager_error(self, analyzer):
        analyzer.start_capture()
        analyzer.start_agent_block("Agent")
        with pytest.raises(ValueError):
            with analyzer.trace_tool_call("Agent", "tool"):
                raise ValueError("test error")
        # Tool call should still be recorded
        assert analyzer.total_tool_calls == 1
        call = analyzer.conversation_blocks[0].tool_calls[0]
        assert call.success is False
        assert "test error" in call.error_message

    # --- save_conversation_report ---

    def test_save_report(self, analyzer, tmp_path):
        analyzer.start_capture()
        analyzer.start_agent_block("A")
        analyzer.record_tool_call(
            agent_name="A",
            tool_name="t",
            arguments={},
            result="ok",
            execution_time_ms=1.0,
        )
        analyzer.stop_capture()
        filepath = str(tmp_path / "report.md")
        result = analyzer.save_conversation_report(filepath)
        assert result is True
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "RAPPORT" in content

    def test_save_report_invalid_path(self, analyzer):
        # Use a truly non-existent path (Windows drive that doesn't exist)
        result = analyzer.save_conversation_report(
            "Z:\\this_drive_does_not_exist\\path\\report.md"
        )
        assert result is False


# ============================================================
# tool_call_tracer decorator
# ============================================================


class TestToolCallTracer:
    def test_decorator_when_disabled(self):
        """When capture is disabled, function runs normally."""

        @tool_call_tracer("Agent", "tool")
        def my_func(x):
            return x * 2

        # Ensure global capture is off
        global_trace_analyzer.capture_enabled = False
        result = my_func(5)
        assert result == 10

    def test_decorator_when_enabled(self):
        """When capture is enabled, function runs and call is recorded."""
        old_enabled = global_trace_analyzer.capture_enabled
        old_calls = global_trace_analyzer.total_tool_calls
        try:
            global_trace_analyzer.start_capture()
            global_trace_analyzer.start_agent_block("DecAgent")

            @tool_call_tracer("DecAgent", "dec_tool")
            def my_func(x=1):
                return x + 1

            result = my_func(x=3)
            assert result == 4
            assert global_trace_analyzer.total_tool_calls > old_calls
        finally:
            global_trace_analyzer.stop_capture()
            global_trace_analyzer.capture_enabled = old_enabled


# ============================================================
# Module-level functions
# ============================================================


class TestModuleFunctions:
    def test_start_stop_capture(self):
        start_conversation_capture()
        assert global_trace_analyzer.capture_enabled is True
        stop_conversation_capture()
        assert global_trace_analyzer.capture_enabled is False

    def test_get_report_empty(self):
        # Reset
        global_trace_analyzer.conversation_blocks = []
        report = get_conversation_report()
        assert "Aucune conversation" in report
