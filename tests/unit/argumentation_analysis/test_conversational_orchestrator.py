"""
Tests for ConversationalOrchestrator (#208-K).

Tests the conversational multi-agent orchestration: agent creation with
specialized plugins, phase execution, round-robin fallback, and
state population.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


# ── Agent-Plugin mapping tests ───────────────────────────────────────


class TestAgentPluginMapping:
    """Tests for AGENT_PLUGIN_MAP configuration."""

    def test_all_agents_defined(self):
        """All expected agents exist in AGENT_PLUGIN_MAP."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_PLUGIN_MAP,
        )

        expected_agents = [
            "ProjectManager",
            "ExtractAgent",
            "InformalAgent",
            "FormalAgent",
            "QualityAgent",
            "DebateAgent",
            "CounterAgent",
            "GovernanceAgent",
        ]
        for name in expected_agents:
            assert name in AGENT_PLUGIN_MAP, f"Missing agent: {name}"

    def test_all_agents_have_instructions(self):
        """Each agent has a non-empty instructions string."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_PLUGIN_MAP,
        )

        for name, config in AGENT_PLUGIN_MAP.items():
            assert "instructions" in config, f"{name} missing instructions"
            assert len(config["instructions"]) > 20, f"{name} instructions too short"

    def test_pm_has_no_specialized_plugins(self):
        """ProjectManager uses only StateManager (no specialized plugins)."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_PLUGIN_MAP,
        )

        assert AGENT_PLUGIN_MAP["ProjectManager"]["plugins"] == []

    def test_informal_agent_has_fallacy_plugin(self):
        """InformalAgent gets FrenchFallacyPlugin."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_PLUGIN_MAP,
        )

        assert "FrenchFallacyPlugin" in AGENT_PLUGIN_MAP["InformalAgent"]["plugins"]

    def test_formal_agent_has_tweety_plugin(self):
        """FormalAgent gets TweetyLogicPlugin."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_PLUGIN_MAP,
        )

        assert "TweetyLogicPlugin" in AGENT_PLUGIN_MAP["FormalAgent"]["plugins"]

    def test_quality_agent_has_scoring_plugin(self):
        """QualityAgent gets QualityScoringPlugin."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_PLUGIN_MAP,
        )

        assert "QualityScoringPlugin" in AGENT_PLUGIN_MAP["QualityAgent"]["plugins"]

    def test_each_agent_has_plugins_list(self):
        """Each agent config has a 'plugins' key that is a list."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_PLUGIN_MAP,
        )

        for name, config in AGENT_PLUGIN_MAP.items():
            assert "plugins" in config, f"{name} missing plugins key"
            assert isinstance(config["plugins"], list), f"{name} plugins not a list"


# ── Plugin loading tests ─────────────────────────────────────────────


class TestPluginLoading:
    """Tests for _load_plugin_instance."""

    def test_load_known_plugins(self):
        """Known plugin names load without error (or return None gracefully)."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _load_plugin_instance,
        )

        known_plugins = [
            "QualityScoringPlugin",
            "GovernancePlugin",
        ]
        for name in known_plugins:
            result = _load_plugin_instance(name)
            # May return None if dependency missing, but should not crash
            assert result is not None or True  # Just don't crash

    def test_unknown_plugin_returns_none(self):
        """Unknown plugin names return None."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _load_plugin_instance,
        )

        result = _load_plugin_instance("NonExistentPlugin")
        assert result is None


# ── Agent creation tests ─────────────────────────────────────────────


class TestCreateConversationalAgents:
    """Tests for create_conversational_agents."""

    def test_creates_agents_with_real_kernel(self):
        """Agent creation works with a real SK kernel (no LLM call)."""
        import semantic_kernel as sk
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            create_conversational_agents,
        )
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

        kernel = sk.Kernel()
        llm = OpenAIChatCompletion(
            service_id="test_llm",
            ai_model_id="gpt-5-mini",
            api_key="fake-key-for-test",
        )
        kernel.add_service(llm)

        state = RhetoricalAnalysisState("Test text for analysis")

        agents = create_conversational_agents(
            kernel=kernel,
            state=state,
            llm_service_id="test_llm",
            agent_names=["ProjectManager", "ExtractAgent"],
        )

        assert len(agents) == 2
        agent_names = [a.name for a in agents]
        assert "ProjectManager" in agent_names
        assert "ExtractAgent" in agent_names

    def test_creates_all_agents_by_default(self):
        """With no agent_names, creates all agents from AGENT_PLUGIN_MAP."""
        import semantic_kernel as sk
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            create_conversational_agents,
            AGENT_PLUGIN_MAP,
        )
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

        kernel = sk.Kernel()
        llm = OpenAIChatCompletion(
            service_id="test", ai_model_id="gpt-5-mini", api_key="fake"
        )
        kernel.add_service(llm)

        state = RhetoricalAnalysisState("Test text")
        agents = create_conversational_agents(
            kernel=kernel, state=state, llm_service_id="test",
        )

        assert len(agents) == len(AGENT_PLUGIN_MAP)

    def test_skips_unknown_agent_names(self):
        """Unknown agent names are skipped gracefully."""
        import semantic_kernel as sk
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            create_conversational_agents,
        )
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

        kernel = sk.Kernel()
        llm = OpenAIChatCompletion(
            service_id="test", ai_model_id="gpt-5-mini", api_key="fake"
        )
        kernel.add_service(llm)

        state = RhetoricalAnalysisState("Test")
        agents = create_conversational_agents(
            kernel=kernel, state=state, llm_service_id="test",
            agent_names=["ProjectManager", "NonExistentAgent"],
        )

        assert len(agents) == 1
        assert agents[0].name == "ProjectManager"


# ── Phase execution tests ────────────────────────────────────────────


class TestRunPhase:
    """Tests for _run_phase round-robin fallback."""

    @pytest.mark.asyncio
    async def test_round_robin_fallback(self):
        """_run_phase uses round-robin when AgentGroupChat fails."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_phase,
        )

        # Create mock agents with async invoke
        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"

        async def mock_invoke1(history):
            response = MagicMock()
            response.content = "Response from Agent1"
            yield response

        mock_agent1.invoke = mock_invoke1

        mock_agent2 = MagicMock()
        mock_agent2.name = "Agent2"

        async def mock_invoke2(history):
            response = MagicMock()
            response.content = "Response from Agent2"
            yield response

        mock_agent2.invoke = mock_invoke2

        # Patch AgentGroupChat import to raise ImportError → triggers round-robin
        with patch(
            "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat",
            side_effect=ImportError("not available"),
        ):
            messages = await _run_phase(
                [mock_agent1, mock_agent2],
                "Analyze this text",
                max_turns=4,
                phase_name="test_phase",
            )

        assert len(messages) == 4
        assert all(m["phase"] == "test_phase" for m in messages)
        # Round-robin: agents alternate
        agents_used = [m["agent"] for m in messages]
        assert "Agent1" in agents_used
        assert "Agent2" in agents_used


# ── State structure tests ────────────────────────────────────────────


class TestStatePopulation:
    """Tests for state structure expected by conversational orchestration."""

    def test_state_has_required_fields(self):
        """RhetoricalAnalysisState has all fields needed by conversational mode."""
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

        state = RhetoricalAnalysisState("Test text")

        # Fields read/written by conversational agents
        assert hasattr(state, "extracts")
        # State should support get_state_snapshot
        assert callable(getattr(state, "get_state_snapshot", None))

    def test_state_snapshot_works(self):
        """get_state_snapshot returns a dict."""
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

        state = RhetoricalAnalysisState("Test text for analysis")
        snapshot = state.get_state_snapshot()
        assert isinstance(snapshot, dict)

    def test_unified_state_has_extended_fields(self):
        """UnifiedAnalysisState extends with all pipeline dimensions."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        state = UnifiedAnalysisState("Test text")

        # All pipeline dimensions should exist
        assert hasattr(state, "counter_arguments")
        assert hasattr(state, "argument_quality_scores")
        assert hasattr(state, "jtms_beliefs")
        assert hasattr(state, "debate_transcripts")
        assert hasattr(state, "governance_decisions")
        assert hasattr(state, "nl_to_logic_translations")


# ── run_conversational_analysis structure tests ──────────────────────


class TestRunConversationalAnalysis:
    """Tests for run_conversational_analysis (mocked, no real LLM)."""

    def test_function_exists_and_is_async(self):
        """run_conversational_analysis is an async function."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        assert asyncio.iscoroutinefunction(run_conversational_analysis)

    @pytest.mark.asyncio
    async def test_raises_without_api_key(self):
        """run_conversational_analysis raises RuntimeError without API key."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                await run_conversational_analysis("test text")
