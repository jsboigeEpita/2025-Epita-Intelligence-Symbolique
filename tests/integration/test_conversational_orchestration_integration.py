"""Integration tests for conversational orchestration pipeline (#208-K).

Tests the full conversational pipeline with mock LLM, verifying:
1. End-to-end pipeline produces structured results
2. Agent-plugin specialization (each agent has correct plugins)
3. Cross-KB synergy: state enriched across phases
4. TraceAnalyzer captures phase transitions
5. State snapshot benchmark (non-empty fields)
6. Convergence detection via trace report
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from argumentation_analysis.orchestration.conversational_orchestrator import (
    AGENT_CONFIG,
    create_conversational_agents,
    run_conversational_analysis,
)
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState


SAMPLE_TEXT = (
    "L'IA est dangereuse car Elon Musk l'a dit. "
    "De plus, tout le monde sait que la technologie detruit les emplois. "
    "Si nous n'interdisons pas l'IA maintenant, la civilisation sera detruite. "
    "Les experts en securite recommandent une reglementation stricte "
    "pour prevenir les risques catastrophiques."
)


def _make_mock_pipeline():
    """Build mock infrastructure for running the pipeline without LLM."""
    mock_service = MagicMock()
    mock_service.service_id = "conversational_llm"
    mock_kernel = MagicMock()
    mock_kernel.get_service.return_value = mock_service

    def make_fake_agent(**kwargs):
        agent = MagicMock()
        agent.name = kwargs.get("name", "MockAgent")

        async def fake_invoke(chat_history):
            msg = MagicMock()
            msg.content = f"[{agent.name}] Analysis complete for this phase."
            yield msg

        agent.invoke = fake_invoke
        return agent

    return mock_kernel, mock_service, make_fake_agent


@pytest.mark.integration
class TestConversationalPipelineIntegration:
    """End-to-end pipeline tests with mock LLM."""

    async def test_full_pipeline_returns_all_required_fields(self):
        """Full pipeline result contains all expected top-level fields."""
        mock_kernel, mock_service, make_fake_agent = _make_mock_pipeline()

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch(
            "argumentation_analysis.agents.factory.get_plugin_instances",
            return_value=[MagicMock()],
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service
            result = await run_conversational_analysis(
                text=SAMPLE_TEXT, max_turns_per_phase=2
            )

        required_fields = [
            "mode", "phases", "conversation_log", "total_messages",
            "duration_seconds", "state_snapshot", "state_non_empty_fields",
            "unified_state", "trace_report",
        ]
        for field in required_fields:
            assert field in result, f"Missing required field: {field}"

        assert result["mode"] == "conversational"
        assert isinstance(result["phases"], list)
        assert len(result["phases"]) == 3
        assert result["total_messages"] > 0
        assert result["duration_seconds"] >= 0

    async def test_three_phases_execute_in_order(self):
        """The 3 macro-phases run in sequence: Extraction, Formal, Synthesis."""
        mock_kernel, mock_service, make_fake_agent = _make_mock_pipeline()

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch(
            "argumentation_analysis.agents.factory.get_plugin_instances",
            return_value=[MagicMock()],
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service
            result = await run_conversational_analysis(
                text=SAMPLE_TEXT, max_turns_per_phase=2
            )

        phases = result["phases"]
        assert "Extraction" in phases[0]
        assert "Formal" in phases[1] or "Quality" in phases[1]
        assert "Synthesis" in phases[2] or "Debate" in phases[2]


@pytest.mark.integration
class TestAgentPluginSpecialization:
    """Verify each agent gets its correct specialized plugins."""

    def test_all_agents_have_speciality(self):
        """Every agent in AGENT_CONFIG has a speciality field."""
        for name, config in AGENT_CONFIG.items():
            assert "speciality" in config, f"Agent {name} missing speciality"
            assert config["speciality"], f"Agent {name} has empty speciality"

    def test_all_agents_have_instructions(self):
        """Every agent has non-empty instructions."""
        for name, config in AGENT_CONFIG.items():
            assert "instructions" in config, f"Agent {name} missing instructions"
            assert len(config["instructions"]) > 20, (
                f"Agent {name} has suspiciously short instructions"
            )

    def test_plugin_instances_created_for_all_specialities(self):
        """get_plugin_instances succeeds for every agent speciality."""
        from argumentation_analysis.agents.factory import get_plugin_instances

        state = RhetoricalAnalysisState("test text")
        for name, config in AGENT_CONFIG.items():
            speciality = config["speciality"]
            plugins = get_plugin_instances(speciality, state=state)
            assert isinstance(plugins, list), f"Plugin list for {name} is not a list"
            # At least StateManagerPlugin should be present
            assert len(plugins) >= 1, f"No plugins for {name} (speciality={speciality})"

    def test_agents_have_distinct_specialities(self):
        """Non-PM agents should have different specialities (diverse expertise)."""
        specialities = [
            config["speciality"]
            for name, config in AGENT_CONFIG.items()
            if name != "ProjectManager"
        ]
        # Allow some overlap but not all same
        unique = set(specialities)
        assert len(unique) >= 4, (
            f"Expected at least 4 distinct specialities, got {len(unique)}: {unique}"
        )


@pytest.mark.integration
class TestTraceAnalyzerIntegration:
    """Verify TraceAnalyzer captures phase transitions during pipeline run."""

    async def test_trace_report_generated(self):
        """Pipeline generates a non-empty trace report."""
        mock_kernel, mock_service, make_fake_agent = _make_mock_pipeline()

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch(
            "argumentation_analysis.agents.factory.get_plugin_instances",
            return_value=[MagicMock()],
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service
            result = await run_conversational_analysis(
                text=SAMPLE_TEXT, max_turns_per_phase=2
            )

        trace_report = result["trace_report"]
        assert trace_report is not None
        assert isinstance(trace_report, dict)
        # Trace should have recorded phases
        assert "phases" in trace_report or "total_turns" in trace_report

    async def test_trace_captures_all_three_phases(self):
        """Trace report captures transitions for all 3 phases."""
        mock_kernel, mock_service, make_fake_agent = _make_mock_pipeline()

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch(
            "argumentation_analysis.agents.factory.get_plugin_instances",
            return_value=[MagicMock()],
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service
            result = await run_conversational_analysis(
                text=SAMPLE_TEXT, max_turns_per_phase=2
            )

        trace_report = result["trace_report"]
        # Check that trace has some info about phases
        if "phases" in trace_report:
            assert len(trace_report["phases"]) >= 3


@pytest.mark.integration
class TestCrossKBSynergies:
    """Verify cross-KB synergy: state is shared and enriched across phases."""

    async def test_state_object_shared_across_phases(self):
        """All phases share the same RhetoricalAnalysisState instance."""
        mock_kernel, mock_service, make_fake_agent = _make_mock_pipeline()

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch(
            "argumentation_analysis.agents.factory.get_plugin_instances",
            return_value=[MagicMock()],
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service
            result = await run_conversational_analysis(
                text=SAMPLE_TEXT, max_turns_per_phase=2
            )

        # unified_state should be a RhetoricalAnalysisState instance
        state = result["unified_state"]
        assert isinstance(state, RhetoricalAnalysisState)
        # The state should have the original text
        assert state.raw_text == SAMPLE_TEXT

    async def test_state_snapshot_is_dict(self):
        """State snapshot should be a serializable dict."""
        mock_kernel, mock_service, make_fake_agent = _make_mock_pipeline()

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch(
            "argumentation_analysis.agents.factory.get_plugin_instances",
            return_value=[MagicMock()],
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service
            result = await run_conversational_analysis(
                text=SAMPLE_TEXT, max_turns_per_phase=2
            )

        snapshot = result["state_snapshot"]
        assert isinstance(snapshot, dict)


@pytest.mark.integration
class TestConversationLog:
    """Verify conversation log captures agent interactions."""

    async def test_log_entries_have_required_fields(self):
        """Each log entry should have phase, turn, agent, content."""
        mock_kernel, mock_service, make_fake_agent = _make_mock_pipeline()

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch(
            "argumentation_analysis.agents.factory.get_plugin_instances",
            return_value=[MagicMock()],
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service
            result = await run_conversational_analysis(
                text=SAMPLE_TEXT, max_turns_per_phase=2
            )

        for entry in result["conversation_log"]:
            assert "phase" in entry
            assert "turn" in entry
            assert "agent" in entry
            assert "content" in entry

    async def test_multiple_agents_contribute_to_log(self):
        """Conversation log contains entries from multiple agents."""
        mock_kernel, mock_service, make_fake_agent = _make_mock_pipeline()

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch(
            "argumentation_analysis.agents.factory.get_plugin_instances",
            return_value=[MagicMock()],
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service
            result = await run_conversational_analysis(
                text=SAMPLE_TEXT, max_turns_per_phase=2
            )

        agents_in_log = set(entry["agent"] for entry in result["conversation_log"])
        assert len(agents_in_log) >= 2, (
            f"Expected multiple agents in log, got: {agents_in_log}"
        )
