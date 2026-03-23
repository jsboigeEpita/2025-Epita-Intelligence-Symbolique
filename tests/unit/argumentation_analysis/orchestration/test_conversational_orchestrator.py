"""Integration tests for ConversationalOrchestrator (#227, Epic #208-K).

Tests the conversational orchestration pipeline with mocked LLM:
1. Agent creation with specialized plugins
2. AGENT_PLUGIN_MAP structure and isolation
3. Phase execution with round-robin fallback
4. State enrichment across phases
5. Full run_conversational_analysis pipeline
6. Edge cases (empty text, missing agents, unknown names)
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

from argumentation_analysis.orchestration.conversational_orchestrator import (
    AGENT_PLUGIN_MAP,
    _load_plugin_instance,
    _safe_import,
    create_conversational_agents,
    run_conversational_analysis,
    _run_phase,
)
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState


# ── Fixtures ──


SAMPLE_TEXT = (
    "L'IA est dangereuse car Elon Musk l'a dit. "
    "Tout le monde sait que la technologie detruit les emplois. "
    "Si nous n'interdisons pas l'IA, la civilisation sera detruite."
)


@pytest.fixture
def state():
    return RhetoricalAnalysisState(SAMPLE_TEXT)


@pytest.fixture
def mock_kernel():
    """Create a mock SK kernel with a fake LLM service."""
    kernel = MagicMock()
    mock_service = MagicMock()
    mock_service.service_id = "test_llm"
    kernel.get_service.return_value = mock_service
    return kernel


# ── AGENT_PLUGIN_MAP structure ──


class TestAgentPluginMap:
    def test_all_eight_agents_defined(self):
        expected_agents = {
            "ProjectManager",
            "ExtractAgent",
            "InformalAgent",
            "FormalAgent",
            "QualityAgent",
            "DebateAgent",
            "CounterAgent",
            "GovernanceAgent",
        }
        assert set(AGENT_PLUGIN_MAP.keys()) == expected_agents

    def test_each_entry_has_plugins_and_instructions(self):
        for name, config in AGENT_PLUGIN_MAP.items():
            assert "plugins" in config, f"{name} missing 'plugins' key"
            assert "instructions" in config, f"{name} missing 'instructions' key"
            assert isinstance(config["plugins"], list), f"{name} plugins should be list"
            assert isinstance(
                config["instructions"], str
            ), f"{name} instructions should be str"

    def test_pm_has_no_specialty_plugins(self):
        assert AGENT_PLUGIN_MAP["ProjectManager"]["plugins"] == []

    def test_extract_has_no_specialty_plugins(self):
        assert AGENT_PLUGIN_MAP["ExtractAgent"]["plugins"] == []

    def test_informal_has_fallacy_plugin(self):
        assert "FrenchFallacyPlugin" in AGENT_PLUGIN_MAP["InformalAgent"]["plugins"]

    def test_formal_has_tweety_plugin(self):
        assert "TweetyLogicPlugin" in AGENT_PLUGIN_MAP["FormalAgent"]["plugins"]

    def test_quality_has_scoring_plugin(self):
        assert "QualityScoringPlugin" in AGENT_PLUGIN_MAP["QualityAgent"]["plugins"]

    def test_debate_has_debate_plugin(self):
        assert "DebatePlugin" in AGENT_PLUGIN_MAP["DebateAgent"]["plugins"]

    def test_counter_has_counter_plugin(self):
        assert (
            "CounterArgumentPlugin" in AGENT_PLUGIN_MAP["CounterAgent"]["plugins"]
        )

    def test_governance_has_governance_plugin(self):
        assert "GovernancePlugin" in AGENT_PLUGIN_MAP["GovernanceAgent"]["plugins"]

    def test_instructions_are_in_french(self):
        """All instructions should be in French (contain accented chars or French words)."""
        french_indicators = ["Tu es", "agent", "Quand", "analyse", "Lis"]
        for name, config in AGENT_PLUGIN_MAP.items():
            found = any(ind in config["instructions"] for ind in french_indicators)
            assert found, f"{name} instructions don't appear to be in French"

    def test_no_agent_has_all_plugins(self):
        """No single agent should have more than 2 specialty plugins."""
        for name, config in AGENT_PLUGIN_MAP.items():
            assert (
                len(config["plugins"]) <= 2
            ), f"{name} has {len(config['plugins'])} plugins — too many"

    def test_plugin_isolation_informal_no_tweety(self):
        """InformalAgent should NOT have TweetyLogicPlugin."""
        assert "TweetyLogicPlugin" not in AGENT_PLUGIN_MAP["InformalAgent"]["plugins"]

    def test_plugin_isolation_formal_no_fallacy(self):
        """FormalAgent should NOT have FrenchFallacyPlugin."""
        assert "FrenchFallacyPlugin" not in AGENT_PLUGIN_MAP["FormalAgent"]["plugins"]


# ── Plugin loading ──


class TestPluginLoading:
    def test_safe_import_returns_none_on_failure(self):
        result = _safe_import("nonexistent.module", "FakeClass")
        assert result is None

    def test_load_unknown_plugin_returns_none(self):
        result = _load_plugin_instance("NonexistentPlugin")
        assert result is None

    def test_load_plugin_instance_known_names(self):
        """All plugin names in AGENT_PLUGIN_MAP should be recognized by _load_plugin_instance."""
        all_plugin_names = set()
        for config in AGENT_PLUGIN_MAP.values():
            all_plugin_names.update(config["plugins"])

        for plugin_name in all_plugin_names:
            # We don't need the import to succeed (deps may be missing),
            # but the name should be recognized (not return None due to unknown name)
            # The function logs warnings for import failures, which is fine
            with patch(
                "argumentation_analysis.orchestration.conversational_orchestrator._safe_import",
                return_value=MagicMock(),
            ) as mock_import:
                result = _load_plugin_instance(plugin_name)
                mock_import.assert_called_once()


# ── Agent creation ──


class TestCreateConversationalAgents:
    def test_creates_all_agents_by_default(self, mock_kernel, state):
        """Without agent_names filter, creates all 8 agents."""
        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent"
        ) as MockAgent:
            MockAgent.return_value = MagicMock()
            agents = create_conversational_agents(
                mock_kernel, state, "test_llm"
            )
            assert len(agents) == 8

    def test_creates_subset_of_agents(self, mock_kernel, state):
        """Can create a specific subset of agents."""
        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent"
        ) as MockAgent:
            MockAgent.return_value = MagicMock()
            agents = create_conversational_agents(
                mock_kernel,
                state,
                "test_llm",
                agent_names=["ProjectManager", "ExtractAgent"],
            )
            assert len(agents) == 2

    def test_skips_unknown_agent_names(self, mock_kernel, state):
        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent"
        ) as MockAgent:
            MockAgent.return_value = MagicMock()
            agents = create_conversational_agents(
                mock_kernel,
                state,
                "test_llm",
                agent_names=["ProjectManager", "NonexistentAgent"],
            )
            assert len(agents) == 1

    def test_agent_gets_state_manager_plugin(self, mock_kernel, state):
        """Every agent should receive StateManagerPlugin."""
        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent"
        ) as MockAgent:
            MockAgent.return_value = MagicMock()
            create_conversational_agents(
                mock_kernel,
                state,
                "test_llm",
                agent_names=["ProjectManager"],
            )
            # Check the plugins arg passed to ChatCompletionAgent
            call_kwargs = MockAgent.call_args[1]
            plugins = call_kwargs.get("plugins", [])
            # First plugin should be StateManagerPlugin
            assert len(plugins) >= 1
            assert type(plugins[0]).__name__ == "StateManagerPlugin"

    def test_agent_gets_function_choice_behavior(self, mock_kernel, state):
        """Every agent should have FunctionChoiceBehavior.Auto()."""
        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent"
        ) as MockAgent:
            MockAgent.return_value = MagicMock()
            create_conversational_agents(
                mock_kernel,
                state,
                "test_llm",
                agent_names=["ExtractAgent"],
            )
            call_kwargs = MockAgent.call_args[1]
            fcb = call_kwargs.get("function_choice_behavior")
            assert fcb is not None

    def test_empty_agent_list_returns_empty(self, mock_kernel, state):
        agents = create_conversational_agents(
            mock_kernel, state, "test_llm", agent_names=[]
        )
        assert agents == []


# ── Phase execution ──


class TestRunPhase:
    @pytest.mark.asyncio
    async def test_round_robin_fallback(self):
        """When SK AgentGroupChat is unavailable, uses round-robin."""
        mock_agent1 = MagicMock()
        mock_agent1.name = "Agent1"

        async def fake_invoke(chat_history):
            msg = MagicMock()
            msg.content = "I analyzed the text"
            yield msg

        mock_agent1.invoke = fake_invoke

        mock_agent2 = MagicMock()
        mock_agent2.name = "Agent2"

        async def fake_invoke2(chat_history):
            msg = MagicMock()
            msg.content = "I found fallacies"
            yield msg

        mock_agent2.invoke = fake_invoke2

        # Force SK import to fail → fallback to round-robin
        with patch.dict(
            "sys.modules",
            {"semantic_kernel.agents.group_chat.agent_group_chat": None},
        ):
            messages = await _run_phase(
                [mock_agent1, mock_agent2],
                "Analyze this text",
                max_turns=4,
                phase_name="Test Phase",
            )

        assert len(messages) == 4
        # Round-robin: turns alternate between agents
        agents_used = [m["agent"] for m in messages]
        assert "Agent1" in agents_used
        assert "Agent2" in agents_used

    @pytest.mark.asyncio
    async def test_phase_respects_max_turns(self):
        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"

        async def fake_invoke(chat_history):
            msg = MagicMock()
            msg.content = "response"
            yield msg

        mock_agent.invoke = fake_invoke

        with patch.dict(
            "sys.modules",
            {"semantic_kernel.agents.group_chat.agent_group_chat": None},
        ):
            messages = await _run_phase(
                [mock_agent],
                "test",
                max_turns=3,
                phase_name="Limited",
            )

        assert len(messages) == 3

    @pytest.mark.asyncio
    async def test_phase_handles_agent_error_gracefully(self):
        mock_agent = MagicMock()
        mock_agent.name = "FailingAgent"

        async def failing_invoke(chat_history):
            raise RuntimeError("LLM timeout")
            yield  # noqa: unreachable — makes it an async generator

        mock_agent.invoke = failing_invoke

        with patch.dict(
            "sys.modules",
            {"semantic_kernel.agents.group_chat.agent_group_chat": None},
        ):
            messages = await _run_phase(
                [mock_agent],
                "test",
                max_turns=2,
                phase_name="Error Phase",
            )

        assert len(messages) == 2
        assert all("ERROR" in m["content"] for m in messages)

    @pytest.mark.asyncio
    async def test_phase_captures_agent_content(self):
        mock_agent = MagicMock()
        mock_agent.name = "ContentAgent"

        async def invoke_with_content(chat_history):
            msg = MagicMock()
            msg.content = "J'ai identifie 3 arguments dans le texte"
            yield msg

        mock_agent.invoke = invoke_with_content

        with patch.dict(
            "sys.modules",
            {"semantic_kernel.agents.group_chat.agent_group_chat": None},
        ):
            messages = await _run_phase(
                [mock_agent],
                "test",
                max_turns=1,
                phase_name="Content",
            )

        assert "arguments" in messages[0]["content"].lower()
        assert messages[0]["phase"] == "Content"
        assert messages[0]["turn"] == 1


# ── State enrichment ──


class TestStateEnrichment:
    def test_state_starts_empty(self, state):
        assert state.identified_arguments == {}
        assert state.identified_fallacies == {}
        assert state.belief_sets == {}
        assert state.final_conclusion is None

    def test_state_manager_can_add_arguments(self, state):
        """StateManagerPlugin methods should enrich the shared state."""
        from argumentation_analysis.core.state_manager_plugin import (
            StateManagerPlugin,
        )

        sm = StateManagerPlugin(state)
        result = sm.add_identified_argument("L'IA est dangereuse")
        assert "arg_" in result
        assert len(state.identified_arguments) == 1

    def test_state_manager_can_add_fallacies(self, state):
        from argumentation_analysis.core.state_manager_plugin import (
            StateManagerPlugin,
        )

        sm = StateManagerPlugin(state)
        sm.add_identified_argument("Argument cible")
        result = sm.add_identified_fallacy(
            fallacy_type="appel_autorite",
            justification="Citation d'Elon Musk comme autorite",
            target_argument_id="arg_1",
        )
        assert "fallacy_" in result or "f_" in result.lower() or result
        assert len(state.identified_fallacies) >= 1

    def test_state_manager_set_conclusion(self, state):
        from argumentation_analysis.core.state_manager_plugin import (
            StateManagerPlugin,
        )

        sm = StateManagerPlugin(state)
        sm.set_final_conclusion("Le texte contient 3 sophismes majeurs.")
        assert state.final_conclusion is not None
        assert "sophismes" in state.final_conclusion

    def test_state_snapshot_captures_all_fields(self, state):
        from argumentation_analysis.core.state_manager_plugin import (
            StateManagerPlugin,
        )

        sm = StateManagerPlugin(state)
        sm.add_identified_argument("Premier argument")
        sm.add_identified_argument("Deuxieme argument")
        snapshot = sm.get_current_state_snapshot()
        assert "identified_arguments" in snapshot or "arg" in snapshot.lower()


# ── Full pipeline (mocked LLM) ──


class TestRunConversationalAnalysis:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_mock_llm(self):
        """Test end-to-end pipeline with mocked LLM service."""
        mock_service = MagicMock()
        mock_service.service_id = "conversational_llm"

        mock_kernel = MagicMock()
        mock_kernel.get_service.return_value = mock_service

        # Mock ChatCompletionAgent to return agents with fake invoke
        def make_fake_agent(**kwargs):
            agent = MagicMock()
            agent.name = kwargs.get("name", "MockAgent")

            async def fake_invoke(chat_history):
                msg = MagicMock()
                msg.content = f"[{agent.name}] J'ai analyse le texte."
                yield msg

            agent.invoke = fake_invoke
            return agent

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service

            results = await run_conversational_analysis(
                text=SAMPLE_TEXT,
                max_turns_per_phase=2,
                agent_names=["ProjectManager", "ExtractAgent", "InformalAgent"],
            )

        # Validate result structure
        assert results["mode"] == "conversational"
        assert isinstance(results["phases"], list)
        assert len(results["phases"]) == 3
        assert results["total_messages"] > 0
        assert results["duration_seconds"] > 0
        assert "state_snapshot" in results
        assert "unified_state" in results
        assert isinstance(results["conversation_log"], list)

    @pytest.mark.asyncio
    async def test_pipeline_requires_api_key(self):
        """Should raise RuntimeError if OPENAI_API_KEY is missing."""
        with patch.dict("os.environ", {}, clear=True):
            # Remove all env vars to simulate missing key
            with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
                with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                    await run_conversational_analysis(text="test")

    @pytest.mark.asyncio
    async def test_pipeline_three_phases(self):
        """Pipeline should run exactly 3 macro-phases."""
        mock_service = MagicMock()
        mock_service.service_id = "conversational_llm"
        mock_kernel = MagicMock()
        mock_kernel.get_service.return_value = mock_service

        phase_names_seen = []

        original_run_phase = _run_phase

        async def tracking_run_phase(agents, prompt, max_turns=5, phase_name=""):
            phase_names_seen.append(phase_name)
            return [
                {
                    "phase": phase_name,
                    "turn": 1,
                    "agent": "MockAgent",
                    "content": "test",
                }
            ]

        def make_fake_agent(**kwargs):
            agent = MagicMock()
            agent.name = kwargs.get("name", "Mock")
            return agent

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator._run_phase",
            side_effect=tracking_run_phase,
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service
            results = await run_conversational_analysis(
                text=SAMPLE_TEXT, max_turns_per_phase=2
            )

        assert len(phase_names_seen) == 3
        assert "Extraction" in phase_names_seen[0]
        assert "Formal" in phase_names_seen[1] or "Quality" in phase_names_seen[1]
        assert "Synthesis" in phase_names_seen[2] or "Debate" in phase_names_seen[2]

    @pytest.mark.asyncio
    async def test_pipeline_returns_conversation_log(self):
        """Conversation log should contain entries from all phases."""
        mock_service = MagicMock()
        mock_service.service_id = "conversational_llm"
        mock_kernel = MagicMock()
        mock_kernel.get_service.return_value = mock_service

        def make_fake_agent(**kwargs):
            agent = MagicMock()
            agent.name = kwargs.get("name", "Mock")

            async def fake_invoke(chat_history):
                msg = MagicMock()
                msg.content = f"[{agent.name}] response"
                yield msg

            agent.invoke = fake_invoke
            return agent

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.sk.Kernel",
            return_value=mock_kernel,
        ), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.OpenAIChatCompletion"
        ) as MockLLM, patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent",
            side_effect=make_fake_agent,
        ), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "sk-test-fake-key"}
        ):
            MockLLM.return_value = mock_service
            results = await run_conversational_analysis(
                text=SAMPLE_TEXT,
                max_turns_per_phase=2,
            )

        log = results["conversation_log"]
        phases_in_log = set(m["phase"] for m in log)
        # Should have messages from all 3 phases
        assert len(phases_in_log) == 3


# ── Edge cases ──


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_run_phase_with_empty_agents_list(self):
        """An empty agent list causes ZeroDivisionError in round-robin.

        The caller (run_conversational_analysis) guards against this by
        skipping phases with no matching agents (line 317-319).
        _run_phase itself does NOT guard — it crashes.
        """
        with patch.dict(
            "sys.modules",
            {"semantic_kernel.agents.group_chat.agent_group_chat": None},
        ):
            # round-robin uses agents[turn % len(agents)] → ZeroDivisionError
            with pytest.raises(ZeroDivisionError):
                await _run_phase(
                    [],
                    "test",
                    max_turns=2,
                    phase_name="Empty",
                )

    def test_create_agents_with_all_unknown_names(self, mock_kernel, state):
        """All unknown names should produce an empty list."""
        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent"
        ):
            agents = create_conversational_agents(
                mock_kernel,
                state,
                "test_llm",
                agent_names=["Unknown1", "Unknown2"],
            )
        assert agents == []
