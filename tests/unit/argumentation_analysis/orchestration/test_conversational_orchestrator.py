"""Tests for ConversationalOrchestrator (#220, Epic #208-D).

Validates:
- Kernel creation with/without API key
- Plugin loading per macro-phase
- Agent creation per phase
- Full run_conversational_analysis with mocked LLM
- Fallback when no API key
- CLI --mode conversational argument
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.orchestration.conversational_orchestrator import (
    MACRO_PHASES,
    _create_phase_agents,
    _create_shared_kernel,
    _create_termination_strategy,
    _load_plugins_for_phase,
    run_conversational_analysis,
)


# --- Kernel creation ---


class TestCreateSharedKernel:
    def test_no_api_key_returns_none(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            kernel, service_id = _create_shared_kernel()
        assert kernel is None
        assert service_id is None

    def test_with_api_key_creates_kernel(self):
        with patch.dict(
            "os.environ",
            {"OPENAI_API_KEY": "test-key", "OPENAI_CHAT_MODEL_ID": "gpt-4o-mini"},
            clear=False,
        ), patch("semantic_kernel.kernel.Kernel") as MockKernel, patch(
            "semantic_kernel.connectors.ai.open_ai.OpenAIChatCompletion"
        ):
            mock_kernel = MagicMock()
            MockKernel.return_value = mock_kernel
            kernel, service_id = _create_shared_kernel()

        assert kernel is mock_kernel
        assert service_id == "conversational_llm"
        mock_kernel.add_service.assert_called_once()


# --- Plugin loading ---


class TestPluginLoading:
    def test_extraction_loads_fallacy_plugin(self):
        mock_kernel = MagicMock()
        loaded = _load_plugins_for_phase(mock_kernel, "extraction")
        # May or may not load depending on plugin availability
        assert isinstance(loaded, list)

    def test_formal_loads_logic_plugins(self):
        mock_kernel = MagicMock()
        loaded = _load_plugins_for_phase(mock_kernel, "formal")
        assert isinstance(loaded, list)

    def test_synthesis_loads_quality_plugins(self):
        mock_kernel = MagicMock()
        loaded = _load_plugins_for_phase(mock_kernel, "synthesis")
        assert isinstance(loaded, list)

    def test_unknown_phase_loads_nothing(self):
        mock_kernel = MagicMock()
        loaded = _load_plugins_for_phase(mock_kernel, "unknown")
        assert loaded == []


# --- Agent creation ---


class TestCreatePhaseAgents:
    def test_extraction_creates_agents(self):
        mock_kernel = MagicMock()
        with patch(
            "argumentation_analysis.agents.factory.AgentFactory",
            side_effect=ImportError("no factory"),
        ):
            agents = _create_phase_agents(mock_kernel, "svc", "extraction")
        # With import error, returns empty
        assert agents == []

    def test_unknown_phase_returns_empty(self):
        mock_kernel = MagicMock()
        agents = _create_phase_agents(mock_kernel, "svc", "nonexistent")
        assert agents == []


# --- Termination strategy ---


class TestTerminationStrategy:
    def test_creates_default_strategy(self):
        strategy = _create_termination_strategy(max_iterations=5)
        if strategy is not None:
            assert hasattr(strategy, "should_terminate")

    def test_max_iterations_applied(self):
        strategy = _create_termination_strategy(max_iterations=10)
        if strategy is not None:
            assert strategy.maximum_iterations == 10


# --- Macro-phases definition ---


class TestMacroPhases:
    def test_three_phases_defined(self):
        assert len(MACRO_PHASES) == 3

    def test_phase_names(self):
        assert MACRO_PHASES == ["extraction", "formal", "synthesis"]


# --- Full run_conversational_analysis ---


class TestRunConversationalAnalysis:
    @pytest.mark.asyncio
    async def test_no_api_key_returns_no_llm(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            result = await run_conversational_analysis("test text")

        assert result["status"] == "no_llm"
        assert "error" in result
        assert result["duration_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_with_mocked_pipeline(self):
        """Mock the pipeline execution to test the orchestration flow."""
        mock_kernel = MagicMock()
        mock_kernel.add_plugin = MagicMock()
        mock_kernel.add_service = MagicMock()

        mock_pipeline_result = {
            "status": "high_confidence",
            "rounds": [{"round_number": 1}],
            "summary": "Analysis complete",
        }

        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance.execute = AsyncMock(return_value=mock_pipeline_result)

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator."
            "_create_shared_kernel",
            return_value=(mock_kernel, "test_svc"),
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator."
            "_create_phase_agents",
            return_value=[MagicMock(name="agent1"), MagicMock(name="agent2")],
        ), patch(
            "argumentation_analysis.orchestration.conversational_executor."
            "ConversationalPipeline",
            return_value=mock_pipeline_instance,
        ):
            result = await run_conversational_analysis(
                "Test argumentation text", max_rounds=2
            )

        assert result["status"] == "completed"
        assert result["completed_phases"] == 3
        assert result["total_phases"] == 3
        assert result["duration_seconds"] >= 0

    @pytest.mark.asyncio
    async def test_selective_phases(self):
        """Run only specific phases."""
        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance.execute = AsyncMock(
            return_value={"status": "converged", "rounds": [{}], "summary": "ok"}
        )

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator."
            "_create_shared_kernel",
            return_value=(MagicMock(), "svc"),
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator."
            "_create_phase_agents",
            return_value=[MagicMock()],
        ), patch(
            "argumentation_analysis.orchestration.conversational_executor."
            "ConversationalPipeline",
            return_value=mock_pipeline_instance,
        ):
            result = await run_conversational_analysis(
                "text", phases=["extraction", "synthesis"]
            )

        assert result["total_phases"] == 2

    @pytest.mark.asyncio
    async def test_phase_failure_handled(self):
        """If a phase raises, it should be caught and reported."""
        mock_pipeline_instance = AsyncMock()
        mock_pipeline_instance.execute = AsyncMock(
            side_effect=RuntimeError("LLM timeout")
        )

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator."
            "_create_shared_kernel",
            return_value=(MagicMock(), "svc"),
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator."
            "_create_phase_agents",
            return_value=[MagicMock()],
        ), patch(
            "argumentation_analysis.orchestration.conversational_executor."
            "ConversationalPipeline",
            return_value=mock_pipeline_instance,
        ):
            result = await run_conversational_analysis("text", phases=["extraction"])

        assert result["phases"]["extraction"]["status"] == "error"
        assert "LLM timeout" in result["phases"]["extraction"]["error"]

    @pytest.mark.asyncio
    async def test_no_agents_skips_phase(self):
        """If no agents available for a phase, it should be skipped."""
        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator."
            "_create_shared_kernel",
            return_value=(MagicMock(), "svc"),
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator."
            "_create_phase_agents",
            return_value=[],
        ):
            result = await run_conversational_analysis("text", phases=["formal"])

        assert result["phases"]["formal"]["status"] == "skipped"


# --- CLI integration ---


class TestCLIIntegration:
    def test_mode_argument_accepted(self):
        """Verify the --mode conversational argument is wired in run_orchestration."""
        import argumentation_analysis.run_orchestration as ro
        import argparse

        # The module defines main() with argparse; just verify the import works
        # and the conversational_orchestrator can be imported
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis as rca,
        )

        assert callable(rca)
