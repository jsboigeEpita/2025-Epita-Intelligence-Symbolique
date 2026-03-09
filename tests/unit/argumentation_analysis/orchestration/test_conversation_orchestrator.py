# tests/unit/argumentation_analysis/orchestration/test_conversation_orchestrator.py
"""Tests for ConversationOrchestrator, ConversationLogger, AnalysisState, SimulatedAgent."""

import pytest
from unittest.mock import patch

from argumentation_analysis.orchestration.conversation_orchestrator import (
    ConversationLogger,
    AnalysisState,
    SimulatedAgent,
    ConversationOrchestrator,
    create_conversation_orchestrator,
    run_mode_micro,
    run_mode_demo,
    run_mode_trace,
    run_mode_enhanced,
)


SAMPLE_TEXT = "Les mesures fermes sont nécessaires pour maintenir l'ordre et la stabilité du pays."


# ── ConversationLogger ──

class TestConversationLogger:
    def test_micro_mode_limits(self):
        cl = ConversationLogger(mode="micro")
        assert cl.max_messages == 8
        assert cl.max_tools == 6
        assert cl.max_states == 3
        assert cl.max_message_len == 150

    def test_demo_mode_limits(self):
        cl = ConversationLogger(mode="demo")
        assert cl.max_messages == 20
        assert cl.max_tools == 15
        assert cl.max_states == 8
        assert cl.max_message_len == 300

    def test_log_agent_message(self):
        cl = ConversationLogger(mode="trace")
        cl.log_agent_message("Sherlock", "Test message", "analysis")
        assert len(cl.messages) == 1
        assert cl.messages[0]["agent"] == "Sherlock"
        assert cl.messages[0]["phase"] == "analysis"

    def test_message_truncation(self):
        cl = ConversationLogger(mode="micro")
        long_msg = "A" * 300
        cl.log_agent_message("Agent", long_msg)
        assert len(cl.messages[0]["message"]) <= 150

    def test_max_messages_enforced(self):
        cl = ConversationLogger(mode="micro")
        for i in range(20):
            cl.log_agent_message("Agent", f"msg {i}")
        assert len(cl.messages) == 8  # micro limit

    def test_log_tool_call(self):
        cl = ConversationLogger(mode="trace")
        cl.log_tool_call("Agent", "detect_fallacy", {"text": "x"}, {"result": True})
        assert len(cl.tool_calls) == 1
        assert cl.tool_calls[0]["tool"] == "detect_fallacy"
        assert cl.tool_calls[0]["success"] is True

    def test_tool_call_truncation(self):
        cl = ConversationLogger(mode="trace")
        long_args = {"text": "X" * 200}
        cl.log_tool_call("Agent", "tool", long_args, "R" * 200)
        assert len(cl.tool_calls[0]["arguments"]) <= 100
        assert len(cl.tool_calls[0]["result"]) <= 150

    def test_max_tools_enforced(self):
        cl = ConversationLogger(mode="micro")
        for i in range(10):
            cl.log_tool_call("Agent", f"tool_{i}", {}, "ok")
        assert len(cl.tool_calls) == 6  # micro limit

    def test_log_state_snapshot(self):
        cl = ConversationLogger(mode="trace")
        cl.log_state_snapshot("init", {"score": 0.5})
        assert len(cl.state_snapshots) == 1
        assert cl.state_snapshots[0]["phase"] == "init"

    def test_max_states_enforced(self):
        cl = ConversationLogger(mode="micro")
        for i in range(10):
            cl.log_state_snapshot(f"phase_{i}", {})
        assert len(cl.state_snapshots) == 3  # micro limit

    def test_timestamp_relative(self):
        cl = ConversationLogger(mode="trace")
        cl.log_agent_message("Agent", "test")
        assert cl.messages[0]["time_ms"] >= 0


# ── AnalysisState ──

class TestAnalysisState:
    def test_initial_state(self):
        state = AnalysisState()
        assert state.score == 0.0
        assert state.agents_active == 0
        assert state.fallacies_detected == 0
        assert state.phase == "initialization"
        assert state.completed is False

    def test_update_from_informal(self):
        state = AnalysisState()
        state.update_from_informal({"fallacies_count": 3, "sophistication_score": 0.8})
        assert state.fallacies_detected == 3
        assert state.score == pytest.approx(0.32)  # 0.8 * 0.4

    def test_update_from_modal(self):
        state = AnalysisState()
        state.update_from_modal({"propositions_count": 5, "consistency": 0.9, "logical_score": 0.7})
        assert state.propositions_found == 5
        assert state.consistency_score == 0.9
        assert state.score == pytest.approx(0.21)  # 0.7 * 0.3

    def test_update_from_synthesis(self):
        state = AnalysisState()
        state.update_from_synthesis({"unified_score": 0.73})
        assert state.completed is True
        assert state.score == pytest.approx(0.219)  # 0.73 * 0.3

    def test_to_dict(self):
        state = AnalysisState()
        state.score = 0.5
        state.fallacies_detected = 2
        d = state.to_dict()
        assert d["score"] == 0.5
        assert d["fallacies_detected"] == 2
        assert "phase" in d

    def test_to_rhetorical_state_completed(self):
        state = AnalysisState()
        state.completed = True
        rs = state.to_rhetorical_state()
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        assert isinstance(rs, RhetoricalAnalysisState)
        assert rs.final_conclusion is not None

    def test_to_rhetorical_state_active(self):
        state = AnalysisState()
        rs = state.to_rhetorical_state()
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        assert isinstance(rs, RhetoricalAnalysisState)
        assert rs.final_conclusion is None

    def test_agent_results_stored(self):
        state = AnalysisState()
        state.update_from_informal({"fallacies_count": 1, "sophistication_score": 0.5})
        assert "informal" in state.agent_results

    def test_cumulative_scoring(self):
        state = AnalysisState()
        state.update_from_informal({"fallacies_count": 2, "sophistication_score": 1.0})
        state.update_from_modal({"propositions_count": 3, "consistency": 0.8, "logical_score": 1.0})
        state.update_from_synthesis({"unified_score": 1.0})
        assert state.score == pytest.approx(1.0)  # 0.4 + 0.3 + 0.3


# ── SimulatedAgent ──

class TestSimulatedAgent:
    def test_informal_agent(self):
        agent = SimulatedAgent("TestAgent", "informal")
        cl = ConversationLogger(mode="trace")
        state = AnalysisState()
        result = agent.analyze(SAMPLE_TEXT, cl, state)
        assert result["fallacies_count"] == 2
        assert state.fallacies_detected == 2
        assert state.agents_active == 1
        assert len(cl.messages) > 0
        assert len(cl.tool_calls) > 0

    def test_fol_logic_agent(self):
        agent = SimulatedAgent("FOLAgent", "fol_logic")
        cl = ConversationLogger(mode="trace")
        state = AnalysisState()
        result = agent.analyze(SAMPLE_TEXT, cl, state)
        assert "formulas_count" in result
        assert state.agents_active == 1

    def test_synthesis_agent(self):
        agent = SimulatedAgent("SynthAgent", "synthesis")
        cl = ConversationLogger(mode="trace")
        state = AnalysisState()
        result = agent.analyze(SAMPLE_TEXT, cl, state)
        assert result["unified_score"] == 0.73
        assert state.completed is True

    def test_unknown_agent_type(self):
        agent = SimulatedAgent("Unknown", "unknown_type")
        cl = ConversationLogger(mode="trace")
        state = AnalysisState()
        result = agent.analyze(SAMPLE_TEXT, cl, state)
        assert "error" in result


# ── ConversationOrchestrator ──

class TestConversationOrchestrator:
    def test_micro_mode_setup(self):
        orch = ConversationOrchestrator(mode="micro")
        assert len(orch.agents) == 2
        assert orch.mode == "micro"

    def test_demo_mode_setup(self):
        orch = ConversationOrchestrator(mode="demo")
        assert len(orch.agents) == 3

    @patch("builtins.print")
    def test_run_orchestration_demo(self, mock_print):
        orch = ConversationOrchestrator(mode="demo")
        report = orch.run_orchestration(SAMPLE_TEXT)
        assert isinstance(report, str)
        assert "TRACE ANALYTIQUE" in report
        assert orch.state.completed is True
        assert orch.state.processing_time > 0

    @patch("builtins.print")
    def test_run_orchestration_micro(self, mock_print):
        orch = ConversationOrchestrator(mode="micro")
        report = orch.run_orchestration(SAMPLE_TEXT)
        assert isinstance(report, str)
        assert len(orch.conv_logger.tool_calls) <= 6

    def test_run_orchestration_trace_no_print(self):
        orch = ConversationOrchestrator(mode="trace")
        report = orch.run_orchestration(SAMPLE_TEXT)
        assert isinstance(report, str)

    @patch("builtins.print")
    def test_generate_report_content(self, mock_print):
        orch = ConversationOrchestrator(mode="demo")
        orch.run_orchestration(SAMPLE_TEXT)
        report = orch.generate_report()
        assert "Score global" in report
        assert "Messages capturés" in report
        assert "Outils utilisés" in report

    @patch("builtins.print")
    def test_get_conversation_state(self, mock_print):
        orch = ConversationOrchestrator(mode="demo")
        orch.run_orchestration(SAMPLE_TEXT)
        state = orch.get_conversation_state()
        assert state["mode"] == "demo"
        assert state["completed"] is True
        assert state["messages_count"] > 0
        assert state["tools_count"] > 0

    @pytest.mark.asyncio
    @patch("builtins.print")
    async def test_run_demo_conversation(self, mock_print):
        orch = ConversationOrchestrator(mode="demo")
        result = await orch.run_demo_conversation(SAMPLE_TEXT)
        assert result["status"] == "success"
        assert "report" in result
        assert result["mode"] == "demo"

    @patch("builtins.print")
    def test_agent_error_handled(self, mock_print):
        orch = ConversationOrchestrator(mode="demo")
        # Replace first agent with one that raises
        class FailingAgent:
            name = "FailAgent"
            agent_type = "informal"
            def analyze(self, text, cl, state):
                raise RuntimeError("Agent failure")
        orch.agents[0] = FailingAgent()
        # Should not raise — errors are caught
        report = orch.run_orchestration(SAMPLE_TEXT)
        assert isinstance(report, str)

    @patch("builtins.print")
    def test_report_contains_text_excerpt(self, mock_print):
        orch = ConversationOrchestrator(mode="demo")
        report = orch.run_orchestration("Short test text.")
        assert "Short test text." in report


# ── Factory and mode functions ──

class TestFactoryAndModes:
    def test_create_conversation_orchestrator(self):
        orch = create_conversation_orchestrator("trace")
        assert isinstance(orch, ConversationOrchestrator)
        assert orch.mode == "trace"

    @patch("builtins.print")
    def test_run_mode_micro(self, mock_print):
        report = run_mode_micro(SAMPLE_TEXT)
        assert isinstance(report, str)

    @patch("builtins.print")
    def test_run_mode_demo(self, mock_print):
        report = run_mode_demo(SAMPLE_TEXT)
        assert isinstance(report, str)

    def test_run_mode_trace(self):
        report = run_mode_trace(SAMPLE_TEXT)
        assert isinstance(report, str)

    @patch("builtins.print")
    def test_run_mode_enhanced(self, mock_print):
        report = run_mode_enhanced(SAMPLE_TEXT)
        assert isinstance(report, str)
