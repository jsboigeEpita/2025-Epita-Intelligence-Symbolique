# tests/unit/argumentation_analysis/reporting/test_enhanced_trace_analyzer.py
"""Tests for EnhancedRealTimeTraceAnalyzer dataclasses and orchestration capture."""

import time
import pytest
from unittest.mock import patch

from argumentation_analysis.reporting.enhanced_real_time_trace_analyzer import (
    ConversationMessage,
    StateSnapshot,
    EnhancedToolCall,
    ProjectManagerPhase,
    EnhancedRealTimeTraceAnalyzer,
)


# ── ConversationMessage ──

class TestConversationMessage:
    def test_init(self):
        msg = ConversationMessage(
            agent_name="AgentA", content="Hello", tour_number=1, phase_id="p1"
        )
        assert msg.agent_name == "AgentA"
        assert msg.content == "Hello"
        assert msg.tour_number == 1
        assert msg.phase_id == "p1"
        assert msg.tool_calls_count == 0

    def test_timestamp_auto(self):
        before = time.time()
        msg = ConversationMessage(
            agent_name="A", content="c", tour_number=1, phase_id="p"
        )
        after = time.time()
        assert before <= msg.timestamp <= after

    def test_to_enhanced_format(self):
        msg = ConversationMessage(
            agent_name="Watson", content="Analysis result", tour_number=3, phase_id="p1"
        )
        result = msg.to_enhanced_format()
        assert "Watson" in result
        assert "Tour 3" in result
        assert "Analysis result" in result

    def test_to_enhanced_format_long_content(self):
        msg = ConversationMessage(
            agent_name="A", content="x" * 600, tour_number=1, phase_id="p"
        )
        result = msg.to_enhanced_format()
        assert "..." in result
        assert len(result) < 700

    def test_to_enhanced_format_with_tool_calls(self):
        msg = ConversationMessage(
            agent_name="A", content="c", tour_number=1, phase_id="p",
            tool_calls_count=5,
        )
        result = msg.to_enhanced_format()
        assert "5 appels d'outils" in result


# ── StateSnapshot ──

class TestStateSnapshot:
    def test_init(self):
        snap = StateSnapshot(
            phase_id="p1", tour_number=2, agent_active="AgentB",
            state_variables={"key": "val"}, metadata={"m": 1},
        )
        assert snap.phase_id == "p1"
        assert snap.tour_number == 2
        assert snap.agent_active == "AgentB"
        assert snap.state_variables == {"key": "val"}

    def test_to_markdown_int(self):
        snap = StateSnapshot(
            phase_id="p1", tour_number=1, agent_active="A",
            state_variables={"count": 42}, metadata={},
        )
        result = snap.to_markdown_format()
        assert "`count`" in result
        assert "42" in result

    def test_to_markdown_string(self):
        snap = StateSnapshot(
            phase_id="p1", tour_number=1, agent_active="A",
            state_variables={"name": "hello world"}, metadata={},
        )
        result = snap.to_markdown_format()
        assert '"hello world"' in result

    def test_to_markdown_long_string(self):
        snap = StateSnapshot(
            phase_id="p1", tour_number=1, agent_active="A",
            state_variables={"text": "a" * 100}, metadata={},
        )
        result = snap.to_markdown_format()
        assert "..." in result

    def test_to_markdown_list(self):
        snap = StateSnapshot(
            phase_id="p1", tour_number=1, agent_active="A",
            state_variables={"items": [1, 2, 3]}, metadata={},
        )
        result = snap.to_markdown_format()
        assert "list(3)" in result

    def test_to_markdown_dict(self):
        snap = StateSnapshot(
            phase_id="p1", tour_number=1, agent_active="A",
            state_variables={"data": {"a": 1}}, metadata={},
        )
        result = snap.to_markdown_format()
        assert "dict(1)" in result

    def test_to_markdown_other_type(self):
        snap = StateSnapshot(
            phase_id="p1", tour_number=1, agent_active="A",
            state_variables={"obj": object()}, metadata={},
        )
        result = snap.to_markdown_format()
        assert "object" in result

    def test_to_markdown_metadata_section(self):
        snap = StateSnapshot(
            phase_id="analysis", tour_number=3, agent_active="Watson",
            state_variables={}, metadata={"key": "val"},
        )
        result = snap.to_markdown_format()
        assert "Tour" in result and "3" in result
        assert "Watson" in result
        assert "analysis" in result


# ── EnhancedToolCall ──

class TestEnhancedToolCall:
    @pytest.fixture
    def tool_call(self):
        return EnhancedToolCall(
            agent_name="Sherlock",
            tool_name="analyze_text",
            arguments={"text": "sample"},
            result="Analysis complete",
            timestamp=time.time(),
            execution_time_ms=150.5,
            success=True,
        )

    def test_init(self, tool_call):
        assert tool_call.agent_name == "Sherlock"
        assert tool_call.tool_name == "analyze_text"
        assert tool_call.success is True
        assert tool_call.error_message is None

    def test_to_enhanced_format(self, tool_call):
        result = tool_call.to_enhanced_conversation_format()
        assert "analyze_text" in result
        assert "150.5ms" in result
        assert "Analysis complete" in result

    def test_to_enhanced_format_no_args(self):
        tc = EnhancedToolCall(
            agent_name="A", tool_name="t", arguments={},
            result=None, timestamp=0, execution_time_ms=10, success=True,
        )
        result = tc.to_enhanced_conversation_format()
        assert "aucun argument" in result

    def test_truncate_value_short_string(self, tool_call):
        assert tool_call._truncate_value_smartly("hello") == '"hello"'

    def test_truncate_value_long_string(self, tool_call):
        result = tool_call._truncate_value_smartly("x" * 100)
        assert result.endswith('..."')
        assert len(result) < 100

    def test_truncate_value_empty_list(self, tool_call):
        assert tool_call._truncate_value_smartly([]) == "[]"

    def test_truncate_value_short_list(self, tool_call):
        result = tool_call._truncate_value_smartly([1, 2])
        assert "[1, 2]" in result

    def test_truncate_value_long_list(self, tool_call):
        result = tool_call._truncate_value_smartly([1, 2, 3, 4, 5])
        assert "5 éléments" in result

    def test_truncate_value_small_dict(self, tool_call):
        result = tool_call._truncate_value_smartly({"a": 1})
        assert "a" in result

    def test_truncate_value_large_dict(self, tool_call):
        result = tool_call._truncate_value_smartly({"a": 1, "b": 2, "c": 3})
        assert "3 clés" in result

    def test_truncate_value_other(self, tool_call):
        assert tool_call._truncate_value_smartly(42) == "42"

    def test_format_result_none(self, tool_call):
        tool_call.result = None
        assert tool_call._format_result_smartly() == "None"

    def test_format_result_short_string(self, tool_call):
        tool_call.result = "short"
        assert tool_call._format_result_smartly() == "short"

    def test_format_result_long_string(self, tool_call):
        tool_call.result = "x" * 200
        result = tool_call._format_result_smartly()
        assert result.endswith("...")

    def test_format_result_empty_list(self, tool_call):
        tool_call.result = []
        assert tool_call._format_result_smartly() == "Liste vide"

    def test_format_result_short_list(self, tool_call):
        tool_call.result = [1, 2]
        result = tool_call._format_result_smartly()
        assert "[1, 2]" in result

    def test_format_result_long_list(self, tool_call):
        tool_call.result = list(range(10))
        result = tool_call._format_result_smartly()
        assert "10 éléments" in result

    def test_format_result_small_dict(self, tool_call):
        tool_call.result = {"a": 1}
        result = tool_call._format_result_smartly()
        assert "a" in result

    def test_format_result_large_dict(self, tool_call):
        tool_call.result = {f"k{i}": i for i in range(5)}
        result = tool_call._format_result_smartly()
        assert "5 clés" in result

    def test_format_arguments_no_args(self, tool_call):
        tool_call.arguments = {}
        assert tool_call._format_arguments_elegantly() == "{}"

    def test_format_arguments_with_args(self, tool_call):
        result = tool_call._format_arguments_elegantly()
        assert "text:" in result


# ── ProjectManagerPhase ──

class TestProjectManagerPhase:
    def test_init(self):
        phase = ProjectManagerPhase(
            phase_id="p1", phase_name="Analysis", assigned_agents=["A", "B"]
        )
        assert phase.phase_id == "p1"
        assert phase.phase_name == "Analysis"
        assert phase.assigned_agents == ["A", "B"]
        assert phase.success is True
        assert phase.end_time is None

    def test_add_state_snapshot(self):
        phase = ProjectManagerPhase(
            phase_id="p1", phase_name="Test", assigned_agents=[]
        )
        snap = StateSnapshot(
            phase_id="p1", tour_number=1, agent_active="A",
            state_variables={}, metadata={},
        )
        phase.add_state_snapshot(snap)
        assert len(phase.state_snapshots) == 1

    def test_add_tool_call(self):
        phase = ProjectManagerPhase(
            phase_id="p1", phase_name="Test", assigned_agents=[]
        )
        tc = EnhancedToolCall(
            agent_name="A", tool_name="t", arguments={},
            result=None, timestamp=0, execution_time_ms=10, success=True,
        )
        phase.add_tool_call(tc)
        assert len(phase.tool_calls) == 1

    def test_finalize(self):
        phase = ProjectManagerPhase(
            phase_id="p1", phase_name="Test", assigned_agents=[]
        )
        assert phase.end_time is None
        phase.finalize()
        assert phase.end_time is not None

    def test_get_duration_not_finalized(self):
        phase = ProjectManagerPhase(
            phase_id="p1", phase_name="Test", assigned_agents=[]
        )
        assert phase._get_duration() == 0.0

    def test_get_duration_finalized(self):
        phase = ProjectManagerPhase(
            phase_id="p1", phase_name="Test", assigned_agents=[]
        )
        phase.start_time = 100.0
        phase.end_time = 100.5
        assert phase._get_duration() == pytest.approx(500.0, abs=1)

    def test_to_enhanced_format(self):
        phase = ProjectManagerPhase(
            phase_id="p1", phase_name="Analysis Phase",
            assigned_agents=["Sherlock", "Watson"],
        )
        result = phase.to_enhanced_conversation_format()
        assert "Analysis Phase" in result
        assert "Sherlock" in result
        assert "Watson" in result


# ── EnhancedRealTimeTraceAnalyzer ──

class TestEnhancedRealTimeTraceAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return EnhancedRealTimeTraceAnalyzer()

    def test_init(self, analyzer):
        assert analyzer.capture_enabled is False
        assert analyzer.orchestration_phases == []
        assert analyzer.current_phase is None
        assert analyzer.total_tool_calls == 0
        assert analyzer.total_state_snapshots == 0

    def test_start_capture(self, analyzer):
        analyzer.start_capture()
        assert analyzer.capture_enabled is True
        assert analyzer.start_time is not None
        assert analyzer.orchestration_metadata["pm_active"] is True

    def test_stop_capture(self, analyzer):
        analyzer.start_capture()
        analyzer.stop_capture()
        assert analyzer.capture_enabled is False
        assert analyzer.end_time is not None

    def test_stop_capture_finalizes_phase(self, analyzer):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "Phase 1", ["A"])
        assert analyzer.current_phase.end_time is None
        analyzer.stop_capture()
        assert analyzer.current_phase.end_time is not None

    def test_start_pm_phase_disabled(self, analyzer):
        result = analyzer.start_pm_phase("p1", "Phase 1", ["A"])
        assert result is None

    def test_start_pm_phase_enabled(self, analyzer):
        analyzer.start_capture()
        phase = analyzer.start_pm_phase("p1", "Phase 1", ["A", "B"])
        assert phase is not None
        assert phase.phase_id == "p1"
        assert len(analyzer.orchestration_phases) == 1
        assert analyzer.current_phase is phase

    def test_start_second_phase_finalizes_first(self, analyzer):
        analyzer.start_capture()
        p1 = analyzer.start_pm_phase("p1", "Phase 1", ["A"])
        p2 = analyzer.start_pm_phase("p2", "Phase 2", ["B"])
        assert p1.end_time is not None
        assert analyzer.current_phase is p2
        assert len(analyzer.orchestration_phases) == 2

    def test_capture_state_snapshot_disabled(self, analyzer):
        analyzer.capture_state_snapshot("p1", 1, "A", {"key": "val"})
        assert analyzer.total_state_snapshots == 0

    def test_capture_state_snapshot_enabled(self, analyzer):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "Phase 1", ["A"])
        analyzer.capture_state_snapshot("p1", 1, "A", {"key": "val"})
        assert analyzer.total_state_snapshots == 1
        assert len(analyzer.state_evolution) == 1
        assert len(analyzer.current_phase.state_snapshots) == 1

    def test_capture_state_snapshot_different_phase(self, analyzer):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "Phase 1", ["A"])
        analyzer.capture_state_snapshot("p2", 1, "A", {"key": "val"})
        assert analyzer.total_state_snapshots == 1
        assert len(analyzer.state_evolution) == 1
        assert len(analyzer.current_phase.state_snapshots) == 0  # Different phase

    def test_record_tool_call_disabled(self, analyzer):
        analyzer.record_enhanced_tool_call("A", "tool", {}, None, 10.0)
        assert analyzer.total_tool_calls == 0

    def test_record_tool_call_enabled(self, analyzer):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "Phase 1", ["A"])
        analyzer.record_enhanced_tool_call("A", "analyze", {"text": "t"}, "result", 50.0)
        assert analyzer.total_tool_calls == 1
        assert len(analyzer.current_phase.tool_calls) == 1

    def test_record_tool_call_no_phase(self, analyzer):
        analyzer.start_capture()
        analyzer.record_enhanced_tool_call("A", "tool", {}, None, 10.0)
        assert analyzer.total_tool_calls == 1

    def test_capture_conversation_disabled(self, analyzer):
        analyzer.capture_conversation_message("A", "hello", 1)
        assert len(analyzer.conversation_messages) == 0

    def test_capture_conversation_enabled(self, analyzer):
        analyzer.start_capture()
        analyzer.capture_conversation_message("A", "hello", 1, "p1")
        assert len(analyzer.conversation_messages) == 1
        assert analyzer.conversation_messages[0].agent_name == "A"

    def test_generate_report_empty(self, analyzer):
        result = analyzer.generate_enhanced_pm_orchestration_report()
        assert "Aucune orchestration" in result

    def test_generate_report_with_data(self, analyzer):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "Rhetoric Analysis", ["Sherlock", "Watson"])
        analyzer.capture_state_snapshot("p1", 1, "Sherlock", {"findings": 3})
        analyzer.record_enhanced_tool_call("Sherlock", "detect", {}, "found 2", 100.0)
        analyzer.capture_conversation_message("Sherlock", "I found 2 fallacies", 1, "p1")
        analyzer.stop_capture()

        report = analyzer.generate_enhanced_pm_orchestration_report()
        assert "Rhetoric Analysis" in report
        assert "Sherlock" in report
        assert "Watson" in report
        assert "Phase" in report

    def test_get_total_duration(self, analyzer):
        assert analyzer._get_total_duration_ms() == 0.0
        analyzer.start_time = 100.0
        analyzer.end_time = 100.5
        assert analyzer._get_total_duration_ms() == pytest.approx(500.0, abs=1)

    def test_save_report(self, analyzer, tmp_path):
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "Test", ["A"])
        analyzer.stop_capture()
        filepath = str(tmp_path / "report.md")
        result = analyzer.save_enhanced_report(filepath)
        assert result is True
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Test" in content

    def test_save_report_bad_path(self, analyzer):
        """Test que save_enhanced_report retourne False si l'écriture échoue."""
        analyzer.start_capture()
        analyzer.start_pm_phase("p1", "Test", ["A"])
        analyzer.stop_capture()
        with patch("builtins.open", side_effect=PermissionError("Cannot write to path")):
            result = analyzer.save_enhanced_report("/nonexistent/path/report.md")
        assert result is False

    def test_metadata_updates(self, analyzer):
        analyzer.start_capture()
        assert analyzer.orchestration_metadata["pm_active"] is True
        analyzer.start_pm_phase("p1", "Phase 1", ["A"])
        assert analyzer.orchestration_metadata["multi_turn_coordination"] is True
        analyzer.stop_capture()
        assert analyzer.orchestration_metadata["total_phases"] == 1

    def test_full_workflow(self, analyzer):
        """Integration test: full capture workflow."""
        analyzer.start_capture()

        # Phase 1
        analyzer.start_pm_phase("extraction", "Extraction Phase", ["FactExtractor"])
        analyzer.capture_state_snapshot("extraction", 1, "FactExtractor", {"facts": 0})
        analyzer.record_enhanced_tool_call(
            "FactExtractor", "extract_facts", {"text": "sample"},
            ["fact1", "fact2"], 200.0
        )
        analyzer.capture_conversation_message(
            "FactExtractor", "Extracted 2 facts", 1, "extraction"
        )
        analyzer.capture_state_snapshot("extraction", 2, "FactExtractor", {"facts": 2})

        # Phase 2
        analyzer.start_pm_phase("analysis", "Analysis Phase", ["Sherlock", "Watson"])
        analyzer.record_enhanced_tool_call(
            "Sherlock", "analyze", {"facts": 2}, {"fallacies": 1}, 300.0
        )

        analyzer.stop_capture()

        assert len(analyzer.orchestration_phases) == 2
        assert analyzer.total_tool_calls == 2
        assert analyzer.total_state_snapshots == 2
        assert len(analyzer.conversation_messages) == 1

        report = analyzer.generate_enhanced_pm_orchestration_report()
        assert "Extraction Phase" in report
        assert "Analysis Phase" in report
        assert "FactExtractor" in report
