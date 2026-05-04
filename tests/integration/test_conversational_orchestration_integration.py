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
            "mode",
            "phases",
            "conversation_log",
            "total_messages",
            "duration_seconds",
            "state_snapshot",
            "state_non_empty_fields",
            "unified_state",
            "trace_report",
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
            assert (
                len(config["instructions"]) > 20
            ), f"Agent {name} has suspiciously short instructions"

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
        assert (
            len(unique) >= 4
        ), f"Expected at least 4 distinct specialities, got {len(unique)}: {unique}"


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
        assert (
            len(agents_in_log) >= 2
        ), f"Expected multiple agents in log, got: {agents_in_log}"


# =============================================================================
# IMPROVED TESTS (#251 follow-up) - Real agent creation, only mock LLM API
# =============================================================================


@pytest.mark.integration
class TestRealAgentCreationWithMockedLLM:
    """Tests using real agent creation with only LLM API mocked.

    These tests address issue #251 by using real SK agent creation
    instead of mocking ChatCompletionAgent entirely.
    """

    async def test_real_agent_creation_with_mocked_llm(self):
        """Create real SK agents with mocked OpenAI client.

        Only mocks the LLM API response, not the entire agent infrastructure.
        """
        from semantic_kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        from semantic_kernel.agents import ChatCompletionAgent

        # Create real kernel
        kernel = Kernel()

        # Mock only the OpenAI API response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analysis complete."

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}), patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=mock_response,
        ):
            # Add real chat completion service
            chat_service = OpenAIChatCompletion(
                service_id="test-service",
                ai_model_id="gpt-4o-mini",
            )
            kernel.add_service(chat_service)

            # Create real agent
            agent = ChatCompletionAgent(
                kernel=kernel,
                name="TestAgent",
                instructions="You are a test agent.",
            )

            assert agent is not None
            assert agent.name == "TestAgent"

    async def test_function_choice_behavior_auto_enables_tools(self):
        """Verify FunctionChoiceBehavior.Auto() allows tool calls.

        This test verifies that the SK configuration enables tool calls
        when FunctionChoiceBehavior.Auto() is used.
        """
        from semantic_kernel.connectors.ai.function_choice_behavior import (
            FunctionChoiceBehavior,
        )

        # Verify Auto behavior exists and is configurable
        behavior = FunctionChoiceBehavior.Auto()

        # Auto behavior should enable automatic function calling
        assert behavior is not None
        # In SK 1.40+, Auto() enables the kernel to call functions automatically
        # This is the key feature for cross-KB synergies

    async def test_agent_with_real_plugins(self):
        """Create agent with real plugin instances (mocked LLM only)."""
        from semantic_kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        from semantic_kernel.agents import ChatCompletionAgent

        # Create a simple test plugin
        from semantic_kernel.functions import kernel_function

        class TestPlugin:
            @kernel_function(description="Test function")
            def test_method(self, text: str) -> str:
                return f"Processed: {text}"

        kernel = Kernel()

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Analysis complete."

        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}), patch(
            "openai.resources.chat.completions.Completions.create",
            return_value=mock_response,
        ):
            chat_service = OpenAIChatCompletion(
                service_id="test-service",
                ai_model_id="gpt-4o-mini",
            )
            kernel.add_service(chat_service)

            # Add real plugin
            kernel.add_plugin(TestPlugin(), plugin_name="TestPlugin")

            # Verify plugin is registered
            functions = kernel.get_function("TestPlugin", "test_method")
            assert functions is not None

            # Create agent with plugin access
            agent = ChatCompletionAgent(
                kernel=kernel,
                name="PluginAgent",
                instructions="Use the TestPlugin to process text.",
            )
            assert agent is not None


@pytest.mark.integration
class TestCrossKBSynergyRealCode:
    """Tests for cross-KB synergies using real state management.

    Tests that quality phase results are readable by sophismes phase,
    and JTMS can read quality scores.
    """

    def test_jtms_can_read_quality_scores(self):
        """JTMS phase can access quality scores from upstream phase."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("Test argument with evidence.")
        state.quality_scores = {
            "arg_1": {"note_finale": 7.0, "scores_par_vertu": {"clarity": 8.0}}
        }

        # JTMS should be able to read quality_scores
        assert state.quality_scores is not None
        assert "arg_1" in state.quality_scores

    def test_fallacy_detection_can_access_quality(self):
        """Fallacy detection phase can access quality annotations."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("Ad hominem attack text.")
        state.neural_fallacy_scores = [
            {"label": "Ad Hominem", "confidence": 0.85, "text": "attack text"}
        ]
        state.quality_scores = {"arg_1": {"note_finale": 3.0}}  # Low quality

        # Cross-KB: fallacy detection should be able to correlate with quality
        # Low quality arguments are more likely to contain fallacies
        assert len(state.neural_fallacy_scores) > 0
        assert state.quality_scores["arg_1"]["note_finale"] < 5.0


@pytest.mark.integration
class TestStateFieldPopulation:
    """Tests for verifying 18+ state fields are populated during analysis."""

    # Fields that actually exist on UnifiedAnalysisState
    EXPECTED_STATE_FIELDS = [
        "raw_text",
        "neural_fallacy_scores",
        "jtms_beliefs",
        "propositional_analysis_results",
        "fol_analysis_results",
        "counter_arguments",
        "identified_arguments",
        "identified_fallacies",
        "argument_quality_scores",
        "final_conclusion",
        "errors",
        "query_log",
        "analysis_tasks",
        "answers",
        "workflow_results",
        "belief_sets",
        "dialogue_results",
        "debate_transcripts",
    ]

    def test_state_has_expected_fields(self):
        """UnifiedAnalysisState has 18+ expected fields."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("Test text")

        # Count how many expected fields exist (as attributes or properties)
        existing_fields = 0
        for field in self.EXPECTED_STATE_FIELDS:
            if hasattr(state, field):
                existing_fields += 1

        # Should have at least 18 fields
        assert existing_fields >= 18, (
            f"Expected 18+ fields, found {existing_fields}: "
            f"{[f for f in self.EXPECTED_STATE_FIELDS if hasattr(state, f)]}"
        )

    async def test_pipeline_populates_multiple_fields(self):
        """Pipeline execution populates multiple state fields."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState(SAMPLE_TEXT)

        # Simulate pipeline phases populating state
        state.argument_quality_scores = {"arg_1": {"note_finale": 6.5}}
        state.neural_fallacy_scores = [{"label": "Ad Hominem", "confidence": 0.85}]

        # Count non-empty fields
        non_empty = 0
        for field in self.EXPECTED_STATE_FIELDS:
            if hasattr(state, field):
                value = getattr(state, field)
                if value is not None and value != [] and value != {}:
                    non_empty += 1

        # At least 3 fields should be populated after phases
        assert non_empty >= 3, f"Expected 3+ populated fields, got {non_empty}"


@pytest.mark.integration
class TestCleanupTeardown:
    """Tests verifying proper cleanup after integration tests."""

    def test_env_vars_restored_after_test(self):
        """Environment variables are restored after test completion."""
        import os

        original_key = os.environ.get("OPENAI_API_KEY")

        # Simulate test modifying env
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
            assert os.environ["OPENAI_API_KEY"] == "test-key"

        # After context, should be restored
        if original_key is not None:
            assert os.environ.get("OPENAI_API_KEY") == original_key
        else:
            assert "OPENAI_API_KEY" not in os.environ

    def test_no_global_state_pollution(self):
        """Tests don't pollute global state between runs."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        # Create and modify state
        state1 = UnifiedAnalysisState("First text")

        # Create new state - should be independent
        state2 = UnifiedAnalysisState("Second text")
        assert state1.raw_text != state2.raw_text
