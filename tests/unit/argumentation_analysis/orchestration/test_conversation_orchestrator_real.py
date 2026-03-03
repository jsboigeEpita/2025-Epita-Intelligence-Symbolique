# -*- coding: utf-8 -*-
"""
Tests for ConversationOrchestrator with mode='real' (LLM-backed agents).

Covers: real mode setup, fallback behavior, async orchestration with mocked
real agents, result adaptation, factory with kernel parameter.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.orchestration.conversation_orchestrator import (
    ConversationOrchestrator,
    AnalysisState,
    create_conversation_orchestrator,
)


# ============================================================
# Real mode setup & fallback
# ============================================================


class TestRealModeSetup:
    def test_real_mode_without_kernel_falls_back_to_demo(self):
        """No kernel => fallback to demo mode with simulated agents."""
        orch = ConversationOrchestrator(mode="real")
        assert orch.mode == "demo"
        assert len(orch.agents) == 3

    def test_real_mode_with_empty_kernel_services_falls_back(self):
        """Kernel with empty services => fallback to demo."""
        kernel = MagicMock()
        kernel.services = {}
        orch = ConversationOrchestrator(mode="real", kernel=kernel)
        assert orch.mode == "demo"

    def test_real_mode_kernel_has_llm_check(self):
        """_kernel_has_llm returns True when services exist."""
        orch = ConversationOrchestrator(mode="demo")
        assert orch._kernel_has_llm() is False

        orch.kernel = MagicMock()
        orch.kernel.services = {"default": MagicMock()}
        assert orch._kernel_has_llm() is True

    def test_demo_mode_unchanged_with_kernel(self):
        """Demo mode works exactly as before even when kernel is provided."""
        kernel = MagicMock()
        kernel.services = {"default": MagicMock()}
        orch = ConversationOrchestrator(mode="demo", kernel=kernel)
        assert orch.mode == "demo"
        assert len(orch.agents) == 3
        assert orch.kernel is kernel

    def test_micro_mode_unchanged(self):
        """Micro mode still creates 2 simulated agents."""
        orch = ConversationOrchestrator(mode="micro")
        assert len(orch.agents) == 2
        assert orch.mode == "micro"

    def test_kernel_stored_on_instance(self):
        """Kernel is stored as instance attribute."""
        kernel = MagicMock()
        orch = ConversationOrchestrator(mode="demo", kernel=kernel)
        assert orch.kernel is kernel

    def test_real_agents_dict_empty_for_demo(self):
        """Demo mode has empty _real_agents dict."""
        orch = ConversationOrchestrator(mode="demo")
        assert orch._real_agents == {}


# ============================================================
# Result adaptation
# ============================================================


class TestResultAdaptation:
    @pytest.fixture
    def orch(self):
        return ConversationOrchestrator(mode="demo")

    def test_adapt_informal_result(self, orch):
        result = orch._adapt_real_result("informal", {
            "fallacies": [
                {"fallacy_type": "ad_hominem", "confidence": 0.9},
                {"fallacy_type": "false_cause", "confidence": 0.7},
            ],
        })
        assert result["fallacies_count"] == 2
        assert result["sophistication_score"] > 0
        assert "ad_hominem" in result["main_issues"]

    def test_adapt_informal_empty(self, orch):
        result = orch._adapt_real_result("informal", {"fallacies": []})
        assert result["fallacies_count"] == 0
        assert result["sophistication_score"] == 0.3  # baseline

    def test_adapt_fol_result(self, orch):
        result = orch._adapt_real_result("fol_logic", {
            "formulas": ["forall X: (P(X) => Q(X))"],
            "consistency_check": True,
            "confidence_score": 0.8,
        })
        assert result["formulas_count"] == 1
        assert result["logical_score"] == 0.8
        assert result["consistency"] == 1.0

    def test_adapt_synthesis_result(self, orch):
        result = orch._adapt_real_result("synthesis", {
            "confidence_level": 0.65,
            "overall_validity": True,
            "executive_summary": "Good argument",
        })
        assert result["unified_score"] == 0.65
        assert result["recommendation"] == "Good argument"

    def test_adapt_unknown_agent_returns_raw(self, orch):
        result = orch._adapt_real_result("unknown", {"key": "value"})
        assert result == {"key": "value"}

    def test_adapt_non_dict_result(self, orch):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"field": 42}
        result = orch._adapt_real_result("synthesis", mock_result)
        assert result["unified_score"] == 0.5  # default

    def test_adapt_string_result(self, orch):
        result = orch._adapt_real_result("informal", "not a dict")
        # String gets wrapped as {"raw": "not a dict"} then adapted
        assert result["fallacies_count"] == 0
        assert "raw_result" in result


# ============================================================
# Async orchestration with mocked agents
# ============================================================


class TestRealModeExecution:
    @pytest.fixture
    def mock_informal(self):
        agent = AsyncMock()
        agent.name = "InformalAnalysisAgent"
        agent.perform_complete_analysis = AsyncMock(return_value={
            "fallacies": [
                {"fallacy_type": "ad_hominem", "confidence": 0.9},
            ],
            "categories": {"RELEVANCE": ["ad_hominem"]},
        })
        return agent

    @pytest.fixture
    def mock_synthesis(self):
        agent = AsyncMock()
        agent.name = "SynthesisAgent"
        report = MagicMock()
        report.model_dump.return_value = {
            "confidence_level": 0.7,
            "overall_validity": True,
            "executive_summary": "Test summary",
        }
        agent.synthesize_analysis = AsyncMock(return_value=report)
        return agent

    @pytest.fixture
    def orch_real(self, mock_informal, mock_synthesis):
        """Orchestrator in forced real mode with mocked agents."""
        orch = ConversationOrchestrator(mode="demo")
        orch.mode = "real"
        orch._real_agents = {
            "informal": mock_informal,
            "synthesis": mock_synthesis,
        }
        return orch

    @pytest.mark.asyncio
    async def test_run_orchestration_async_basic(self, orch_real):
        report = await orch_real.run_orchestration_async("Test text for analysis.")
        assert isinstance(report, str)
        assert orch_real.state.completed
        assert orch_real.state.agents_active >= 1

    @pytest.mark.asyncio
    async def test_run_orchestration_async_calls_agents(
        self, orch_real, mock_informal, mock_synthesis
    ):
        await orch_real.run_orchestration_async("Test text.")
        mock_informal.perform_complete_analysis.assert_called_once_with("Test text.")
        mock_synthesis.synthesize_analysis.assert_called_once_with("Test text.")

    @pytest.mark.asyncio
    async def test_run_orchestration_async_state_updates(self, orch_real):
        await orch_real.run_orchestration_async("Test text.")
        assert orch_real.state.fallacies_detected >= 1
        assert orch_real.state.score > 0
        assert orch_real.state.completed

    @pytest.mark.asyncio
    async def test_non_real_mode_delegates_to_sync(self):
        orch = ConversationOrchestrator(mode="demo")
        report = await orch.run_orchestration_async("Test text.")
        assert isinstance(report, str)
        assert "TRACE ANALYTIQUE" in report

    @pytest.mark.asyncio
    async def test_agent_failure_does_not_crash(self):
        orch = ConversationOrchestrator(mode="demo")
        orch.mode = "real"
        failing_agent = AsyncMock()
        failing_agent.name = "FailAgent"
        failing_agent.perform_complete_analysis = AsyncMock(
            side_effect=RuntimeError("LLM down")
        )
        orch._real_agents = {"informal": failing_agent}

        report = await orch.run_orchestration_async("Test text.")
        assert isinstance(report, str)
        assert orch.state.phase == "completed"

    @pytest.mark.asyncio
    async def test_agent_timeout_handled(self):
        orch = ConversationOrchestrator(mode="demo")
        orch.mode = "real"

        async def slow_agent(text):
            await asyncio.sleep(10)
            return {}

        slow = MagicMock()
        slow.name = "SlowAgent"
        slow.perform_complete_analysis = slow_agent
        orch._real_agents = {"informal": slow}

        report = await orch.run_orchestration_async("Test text.")
        assert isinstance(report, str)

    @pytest.mark.asyncio
    async def test_run_demo_conversation_real_mode(self, orch_real):
        result = await orch_real.run_demo_conversation("Test text")
        assert result["status"] == "success"
        assert result["mode"] == "real"

    @pytest.mark.asyncio
    async def test_run_conversation_alias(self, orch_real):
        result = await orch_real.run_conversation("Test text")
        assert result["status"] == "success"


# ============================================================
# Factory with kernel
# ============================================================


class TestFactoryWithKernel:
    def test_create_with_kernel(self):
        kernel = MagicMock()
        orch = create_conversation_orchestrator("demo", kernel=kernel)
        assert orch.kernel is kernel
        assert orch.mode == "demo"

    def test_create_without_kernel(self):
        orch = create_conversation_orchestrator("demo")
        assert orch.kernel is None
        assert orch.mode == "demo"


# ============================================================
# Invoke real agent dispatching
# ============================================================


class TestInvokeRealAgent:
    @pytest.mark.asyncio
    async def test_invoke_informal_perform_complete(self):
        orch = ConversationOrchestrator(mode="demo")
        agent = AsyncMock()
        agent.perform_complete_analysis = AsyncMock(return_value={"fallacies": []})
        result = await orch._invoke_real_agent("informal", agent, "text")
        assert result == {"fallacies": []}

    @pytest.mark.asyncio
    async def test_invoke_informal_analyze_text_fallback(self):
        orch = ConversationOrchestrator(mode="demo")
        agent = MagicMock(spec=[])  # no perform_complete_analysis
        agent.analyze_text = AsyncMock(return_value={"fallacies": []})
        result = await orch._invoke_real_agent("informal", agent, "text")
        assert result == {"fallacies": []}

    @pytest.mark.asyncio
    async def test_invoke_synthesis(self):
        orch = ConversationOrchestrator(mode="demo")
        report = MagicMock()
        report.model_dump.return_value = {"confidence_level": 0.8}
        agent = AsyncMock()
        agent.synthesize_analysis = AsyncMock(return_value=report)
        result = await orch._invoke_real_agent("synthesis", agent, "text")
        assert result == {"confidence_level": 0.8}

    @pytest.mark.asyncio
    async def test_invoke_unknown_raises(self):
        orch = ConversationOrchestrator(mode="demo")
        with pytest.raises(ValueError, match="Unknown agent key"):
            await orch._invoke_real_agent("unknown", MagicMock(), "text")
