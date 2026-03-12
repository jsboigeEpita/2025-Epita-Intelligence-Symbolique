# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.reporting.enhanced_real_time_trace_analyzer
Covers ConversationMessage, StateSnapshot, EnhancedToolCall,
ProjectManagerPhase, EnhancedRealTimeTraceAnalyzer, decorator, and helpers.
"""

import time
import pytest

from argumentation_analysis.reporting.enhanced_real_time_trace_analyzer import (
    ConversationMessage,
    StateSnapshot,
    EnhancedToolCall,
    ProjectManagerPhase,
    EnhancedRealTimeTraceAnalyzer,
    enhanced_global_trace_analyzer,
    enhanced_tool_call_tracer,
    start_enhanced_pm_capture,
    stop_enhanced_pm_capture,
    start_pm_orchestration_phase,
    capture_shared_state,
    get_enhanced_pm_report,
)


# ============================================================
# ConversationMessage
# ============================================================

class TestConversationMessage:
    def test_basic_fields(self):
        msg = ConversationMessage(agent_name="Agent1", content="Hello", tour_number=1, phase_id="p1")
        assert msg.agent_name == "Agent1"
        assert msg.content == "Hello"
        assert msg.tour_number == 1
        assert msg.phase_id == "p1"

    def test_default_timestamp(self):
        msg = ConversationMessage(agent_name="A", content="c", tour_number=1, phase_id="p")
        assert msg.timestamp > 0

    def test_default_tool_calls_count(self):
        msg = ConversationMessage(agent_name="A", content="c", tour_number=1, phase_id="p")
        assert msg.tool_calls_count == 0

    def test_format_short_content(self):
        msg = ConversationMessage(agent_name="Agent1", content="Short text", tour_number=2, phase_id="p1")
        output = msg.to_enhanced_format()
        assert "Agent1" in output
        assert "Tour 2" in output
        assert "Short text" in output

    def test_format_long_content_truncated(self):
        msg = ConversationMessage(agent_name="A", content="x" * 600, tour_number=1, phase_id="p")
        output = msg.to_enhanced_format()
        assert "..." in output

    def test_format_with_tool_calls(self):
        msg = ConversationMessage(agent_name="A", content="c", tour_number=1, phase_id="p", tool_calls_count=5)
        output = msg.to_enhanced_format()
        assert "5 appels d'outils" in output


# ============================================================
# StateSnapshot
# ============================================================

class TestStateSnapshot:
    def test_basic_fields(self):
        snap = StateSnapshot(phase_id="p1", tour_number=1, agent_active="Agent1",
                             state_variables={"key": "val"}, metadata={"m": 1})
        assert snap.phase_id == "p1"
        assert snap.agent_active == "Agent1"
        assert snap.state_variables == {"key": "val"}

    def test_markdown_format_numeric(self):
        snap = StateSnapshot(phase_id="p1", tour_number=1, agent_active="A",
                             state_variables={"count": 42}, metadata={})
        output = snap.to_markdown_format()
        assert "`count`: 42" in output

    def test_markdown_format_string(self):
        snap = StateSnapshot(phase_id="p1", tour_number=1, agent_active="A",
                             state_variables={"name": "hello"}, metadata={})
        output = snap.to_markdown_format()
        assert '"hello"' in output

    def test_markdown_format_long_string_truncated(self):
        snap = StateSnapshot(phase_id="p1", tour_number=1, agent_active="A",
                             state_variables={"text": "z" * 100}, metadata={})
        output = snap.to_markdown_format()
        assert "..." in output

    def test_markdown_format_list(self):
        snap = StateSnapshot(phase_id="p1", tour_number=1, agent_active="A",
                             state_variables={"items": [1, 2, 3]}, metadata={})
        output = snap.to_markdown_format()
        assert "list(3)" in output

    def test_markdown_format_dict(self):
        snap = StateSnapshot(phase_id="p1", tour_number=1, agent_active="A",
                             state_variables={"config": {"a": 1}}, metadata={})
        output = snap.to_markdown_format()
        assert "dict(1)" in output

    def test_metadata_in_output(self):
        snap = StateSnapshot(phase_id="p1", tour_number=3, agent_active="AgentX",
                             state_variables={}, metadata={"key": "val"})
        output = snap.to_markdown_format()
        assert "Tour**: 3" in output
        assert "AgentX" in output


# ============================================================
# EnhancedToolCall
# ============================================================

class TestEnhancedToolCall:
    def _make_call(self, **overrides):
        defaults = dict(
            agent_name="Agent1", tool_name="search", arguments={"q": "test"},
            result="found", timestamp=1000.0, execution_time_ms=50.0, success=True,
        )
        defaults.update(overrides)
        return EnhancedToolCall(**defaults)

    def test_basic_fields(self):
        call = self._make_call()
        assert call.agent_name == "Agent1"
        assert call.tool_name == "search"
        assert call.success is True

    def test_default_call_id(self):
        call = self._make_call()
        assert call.call_id == ""

    def test_default_error_message(self):
        call = self._make_call()
        assert call.error_message is None

    # --- _truncate_value_smartly ---

    def test_truncate_short_string(self):
        call = self._make_call()
        assert call._truncate_value_smartly("hello") == '"hello"'

    def test_truncate_long_string(self):
        call = self._make_call()
        result = call._truncate_value_smartly("x" * 100)
        assert result.endswith('..."')

    def test_truncate_empty_list(self):
        call = self._make_call()
        assert call._truncate_value_smartly([]) == "[]"

    def test_truncate_short_list(self):
        call = self._make_call()
        assert call._truncate_value_smartly([1, 2]) == "[1, 2]"

    def test_truncate_long_list(self):
        call = self._make_call()
        result = call._truncate_value_smartly(list(range(10)))
        assert "10 éléments" in result

    def test_truncate_small_dict(self):
        call = self._make_call()
        result = call._truncate_value_smartly({"a": 1})
        assert "a" in result

    def test_truncate_large_dict(self):
        call = self._make_call()
        result = call._truncate_value_smartly({f"k{i}": i for i in range(5)})
        assert "5 clés" in result

    def test_truncate_numeric(self):
        call = self._make_call()
        assert call._truncate_value_smartly(42) == "42"

    # --- _format_arguments_elegantly ---

    def test_format_args_empty(self):
        call = self._make_call(arguments={})
        assert call._format_arguments_elegantly() == "{}"

    def test_format_args_nonempty(self):
        call = self._make_call(arguments={"key": "val"})
        result = call._format_arguments_elegantly()
        assert "key:" in result

    # --- _format_result_smartly ---

    def test_format_result_none(self):
        call = self._make_call(result=None)
        assert call._format_result_smartly() == "None"

    def test_format_result_short_string(self):
        call = self._make_call(result="ok")
        assert call._format_result_smartly() == "ok"

    def test_format_result_long_string(self):
        call = self._make_call(result="x" * 200)
        result = call._format_result_smartly()
        assert result.endswith("...")

    def test_format_result_empty_list(self):
        call = self._make_call(result=[])
        assert call._format_result_smartly() == "Liste vide"

    def test_format_result_short_list(self):
        call = self._make_call(result=[1, 2])
        assert call._format_result_smartly() == "[1, 2]"

    def test_format_result_long_list(self):
        call = self._make_call(result=list(range(10)))
        assert "10 éléments" in call._format_result_smartly()

    def test_format_result_small_dict(self):
        call = self._make_call(result={"a": 1})
        assert "a" in call._format_result_smartly()

    def test_format_result_large_dict(self):
        call = self._make_call(result={f"k{i}": i for i in range(5)})
        assert "5 clés" in call._format_result_smartly()

    # --- to_enhanced_conversation_format ---

    def test_conversation_format_contains_tool_name(self):
        call = self._make_call()
        output = call.to_enhanced_conversation_format()
        assert "search" in output

    def test_conversation_format_contains_timing(self):
        call = self._make_call(execution_time_ms=123.4)
        output = call.to_enhanced_conversation_format()
        assert "123.4ms" in output

    def test_conversation_format_empty_args(self):
        call = self._make_call(arguments={})
        output = call.to_enhanced_conversation_format()
        assert "aucun argument" in output


# ============================================================
# ProjectManagerPhase
# ============================================================

class TestProjectManagerPhase:
    def test_init(self):
        phase = ProjectManagerPhase(phase_id="p1", phase_name="Analysis", assigned_agents=["A1", "A2"])
        assert phase.phase_id == "p1"
        assert phase.phase_name == "Analysis"
        assert phase.assigned_agents == ["A1", "A2"]
        assert phase.tool_calls == []
        assert phase.state_snapshots == []
        assert phase.end_time is None

    def test_add_tool_call(self):
        phase = ProjectManagerPhase(phase_id="p1", phase_name="P", assigned_agents=[])
        call = EnhancedToolCall(
            agent_name="A", tool_name="t", arguments={},
            result=None, timestamp=0, execution_time_ms=0, success=True,
        )
        phase.add_tool_call(call)
        assert len(phase.tool_calls) == 1

    def test_add_state_snapshot(self):
        phase = ProjectManagerPhase(phase_id="p1", phase_name="P", assigned_agents=[])
        snap = StateSnapshot(phase_id="p1", tour_number=1, agent_active="A",
                             state_variables={}, metadata={})
        phase.add_state_snapshot(snap)
        assert len(phase.state_snapshots) == 1

    def test_finalize(self):
        phase = ProjectManagerPhase(phase_id="p1", phase_name="P", assigned_agents=[])
        assert phase.end_time is None
        phase.finalize()
        assert phase.end_time is not None

    def test_duration_before_finalize(self):
        phase = ProjectManagerPhase(phase_id="p1", phase_name="P", assigned_agents=[])
        assert phase._get_duration() == 0.0

    def test_duration_after_finalize(self):
        phase = ProjectManagerPhase(phase_id="p1", phase_name="P", assigned_agents=[])
        time.sleep(0.01)
        phase.finalize()
        assert phase._get_duration() > 0

    def test_conversation_format(self):
        phase = ProjectManagerPhase(phase_id="p1", phase_name="Detection", assigned_agents=["Sherlock"])
        output = phase.to_enhanced_conversation_format()
        assert "Detection" in output
        assert "Sherlock" in output


# ============================================================
# EnhancedRealTimeTraceAnalyzer
# ============================================================

class TestEnhancedRealTimeTraceAnalyzer:
    @pytest.fixture
    def analyzer(self):
        a = EnhancedRealTimeTraceAnalyzer()
        yield a
        a.stop_capture()

    def test_init_state(self, analyzer):
        assert analyzer.capture_enabled is False
        assert analyzer.orchestration_phases == []
        assert analyzer.current_phase is None
        assert analyzer.total_tool_calls == 0
        assert analyzer.total_state_snapshots == 0

    def test_start_capture(self, analyzer):
        analyzer.start_capture()
        assert analyzer.capture_enabled is True
        assert analyzer.start_time is not None

    def test_stop_capture(self, analyzer):
        analyzer.start_capture()
        analyzer.stop_capture()
        assert analyzer.capture_enabled is False
        assert analyzer.end_time is not None

    def test_start_phase_disabled(self, analyzer):
        result = analyzer.start_pm_phase("p1", "Phase1", ["A"])
        assert result is None

    def test_start_phase_enabled(self, analyzer):
        analyzer.start_capture()
        phase = analyzer.start_pm_phase("p1", "Phase1", ["A"])
        assert phase is not None
        assert len(analyzer.orchestration_phases) == 1

    def test_multiple_phases(self, analyzer):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "Phase1", ["A"])
        analyzer.start_pm_phase("p2", "Phase2", ["B"])
        assert len(analyzer.orchestration_phases) == 2

    def test_capture_state_disabled(self, analyzer):
        analyzer.capture_state_snapshot("p1", 1, "A", {"key": "val"})
        assert analyzer.total_state_snapshots == 0

    def test_capture_state_enabled(self, analyzer):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "Phase1", ["A"])
        analyzer.capture_state_snapshot("p1", 1, "A", {"key": "val"})
        assert analyzer.total_state_snapshots == 1
        assert len(analyzer.state_evolution) == 1

    def test_record_tool_call_disabled(self, analyzer):
        analyzer.record_enhanced_tool_call("A", "t", {}, None, 0)
        assert analyzer.total_tool_calls == 0

    def test_record_tool_call_enabled(self, analyzer):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "P1", ["A"])
        analyzer.record_enhanced_tool_call("A", "search", {"q": "test"}, "found", 10.0)
        assert analyzer.total_tool_calls == 1
        assert len(analyzer.current_phase.tool_calls) == 1

    def test_capture_conversation_disabled(self, analyzer):
        analyzer.capture_conversation_message("A", "hello", 1)
        assert len(analyzer.conversation_messages) == 0

    def test_capture_conversation_enabled(self, analyzer):
        analyzer.start_capture()
        analyzer.capture_conversation_message("A", "hello", 1, "p1")
        assert len(analyzer.conversation_messages) == 1

    # --- Report ---

    def test_report_empty(self, analyzer):
        report = analyzer.generate_enhanced_pm_orchestration_report()
        assert "Aucune orchestration" in report

    def test_report_with_data(self, analyzer):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "Detection", ["Sherlock"])
        analyzer.record_enhanced_tool_call("Sherlock", "investigate", {"clue": "x"}, "found", 50.0)
        analyzer.capture_state_snapshot("p1", 1, "Sherlock", {"hypothesis": "butler"})
        analyzer.capture_conversation_message("Sherlock", "I found a clue", 1, "p1")
        analyzer.stop_capture()
        report = analyzer.generate_enhanced_pm_orchestration_report()
        assert "ORCHESTRATION" in report
        assert "Detection" in report
        assert "Sherlock" in report

    # --- Duration ---

    def test_duration_before_stop(self, analyzer):
        assert analyzer._get_total_duration_ms() == 0.0

    def test_duration_after_capture(self, analyzer):
        analyzer.start_capture()
        time.sleep(0.01)
        analyzer.stop_capture()
        assert analyzer._get_total_duration_ms() > 0

    # --- Save ---

    def test_save_report(self, analyzer, tmp_path):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "P1", ["A"])
        analyzer.stop_capture()
        filepath = str(tmp_path / "report.md")
        assert analyzer.save_enhanced_report(filepath) is True
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "ORCHESTRATION" in content

    def test_save_report_invalid_path(self, analyzer):
        # Use a truly non-existent path (Windows drive that doesn't exist)
        assert analyzer.save_enhanced_report("Z:\\this_drive_does_not_exist\\path\\report.md") is False


# ============================================================
# enhanced_tool_call_tracer decorator
# ============================================================

class TestEnhancedToolCallTracer:
    def test_decorator_disabled(self):
        @enhanced_tool_call_tracer("Agent", "tool")
        def my_func(x):
            return x * 2

        enhanced_global_trace_analyzer.capture_enabled = False
        assert my_func(5) == 10

    def test_decorator_enabled(self):
        old_enabled = enhanced_global_trace_analyzer.capture_enabled
        old_calls = enhanced_global_trace_analyzer.total_tool_calls
        try:
            enhanced_global_trace_analyzer.start_capture()
            enhanced_global_trace_analyzer.start_pm_phase("p", "P", ["A"])

            @enhanced_tool_call_tracer("Agent", "tool")
            def my_func(x=1):
                return x + 1

            result = my_func(x=3)
            assert result == 4
            assert enhanced_global_trace_analyzer.total_tool_calls > old_calls
        finally:
            enhanced_global_trace_analyzer.stop_capture()
            enhanced_global_trace_analyzer.capture_enabled = old_enabled


# ============================================================
# Module-level helpers
# ============================================================

class TestModuleHelpers:
    def test_start_stop_capture(self):
        start_enhanced_pm_capture()
        assert enhanced_global_trace_analyzer.capture_enabled is True
        stop_enhanced_pm_capture()
        assert enhanced_global_trace_analyzer.capture_enabled is False

    def test_get_report_empty(self):
        enhanced_global_trace_analyzer.orchestration_phases = []
        report = get_enhanced_pm_report()
        assert "Aucune orchestration" in report

    def test_start_phase_helper(self):
        start_enhanced_pm_capture()
        try:
            phase = start_pm_orchestration_phase("p1", "Phase1", ["A"])
            assert phase is not None
        finally:
            stop_enhanced_pm_capture()

    def test_capture_state_helper(self):
        start_enhanced_pm_capture()
        try:
            enhanced_global_trace_analyzer.start_pm_phase("p1", "P", ["A"])
            capture_shared_state("p1", 1, "A", {"k": "v"})
            assert enhanced_global_trace_analyzer.total_state_snapshots >= 1
        finally:
            stop_enhanced_pm_capture()
