# tests/unit/argumentation_analysis/orchestration/test_cluedo_extended_orchestrator.py
"""Tests for CluedoExtendedOrchestrator, AgentGroupChat, and utility functions."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from datetime import datetime

from semantic_kernel.contents.chat_message_content import ChatMessageContent


# ============================================================================
# AgentGroupChat Tests
# ============================================================================

class TestAgentGroupChatInit:
    """Tests for AgentGroupChat initialization."""

    def test_init_default_empty_agents(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        chat = AgentGroupChat()
        assert chat.agents == []
        assert chat.selection_strategy is None
        assert chat.termination_strategy is None

    def test_init_with_agents(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        agents = [MagicMock(), MagicMock()]
        chat = AgentGroupChat(agents=agents)
        assert len(chat.agents) == 2

    def test_init_with_strategies(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        sel = MagicMock()
        term = MagicMock()
        chat = AgentGroupChat(
            agents=[MagicMock()],
            selection_strategy=sel,
            termination_strategy=term,
        )
        assert chat.selection_strategy is sel
        assert chat.termination_strategy is term

    def test_init_none_agents_becomes_empty_list(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        chat = AgentGroupChat(agents=None)
        assert chat.agents == []


class TestAgentGroupChatInvoke:
    """Tests for AgentGroupChat.invoke()."""

    async def test_invoke_empty_agents_returns_empty_list(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        chat = AgentGroupChat(agents=[])
        result = await chat.invoke("hello")
        assert result == []

    async def test_invoke_with_callable_agent(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        agent = MagicMock()
        agent.invoke.return_value = "response1"
        chat = AgentGroupChat(agents=[agent])
        result = await chat.invoke("hello")
        assert "response1" in result

    async def test_invoke_with_async_agent(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        agent = MagicMock()
        agent.invoke = AsyncMock(return_value="async_response")
        chat = AgentGroupChat(agents=[agent])
        result = await chat.invoke("hello")
        assert "async_response" in result

    async def test_invoke_agent_without_invoke_method(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        agent = MagicMock(spec=[])  # No invoke method
        chat = AgentGroupChat(agents=[agent])
        result = await chat.invoke("hello")
        # Should return fallback message since no agent could respond
        assert len(result) == 1
        assert "AgentGroupChat" in result[0]

    async def test_invoke_agent_raises_exception(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        agent = MagicMock()
        agent.invoke.side_effect = RuntimeError("Agent error")
        chat = AgentGroupChat(agents=[agent])
        result = await chat.invoke("hello")
        # Exception is silently caught, returns fallback
        assert len(result) == 1
        assert "AgentGroupChat" in result[0]

    async def test_invoke_multiple_agents(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        agent1 = MagicMock()
        agent1.invoke.return_value = "resp1"
        agent2 = MagicMock()
        agent2.invoke.return_value = "resp2"
        chat = AgentGroupChat(agents=[agent1, agent2])
        result = await chat.invoke("hello")
        assert len(result) == 2

    async def test_invoke_none_input(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import AgentGroupChat
        agent = MagicMock()
        agent.invoke.return_value = "response"
        chat = AgentGroupChat(agents=[agent])
        result = await chat.invoke(None)
        assert "response" in result


# ============================================================================
# CluedoExtendedOrchestrator Tests
# ============================================================================

class TestCluedoExtendedOrchestratorInit:
    """Tests for CluedoExtendedOrchestrator initialization."""

    def test_init_default_values(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        kernel = MagicMock()
        settings = MagicMock()
        orch = CluedoExtendedOrchestrator(kernel=kernel, settings=settings)
        assert orch.kernel is kernel
        assert orch.settings is settings
        assert orch.max_turns == 15
        assert orch.max_cycles == 5
        assert orch.oracle_strategy == "balanced"
        assert orch.adaptive_selection is False
        assert orch.oracle_state is None
        assert orch.sherlock_agent is None
        assert orch.watson_agent is None
        assert orch.moriarty_agent is None

    def test_init_custom_values(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        kernel = MagicMock()
        settings = MagicMock()
        orch = CluedoExtendedOrchestrator(
            kernel=kernel,
            settings=settings,
            max_turns=30,
            max_cycles=10,
            oracle_strategy="cooperative",
            adaptive_selection=True,
        )
        assert orch.max_turns == 30
        assert orch.max_cycles == 10
        assert orch.oracle_strategy == "cooperative"
        assert orch.adaptive_selection is True

    def test_init_execution_metrics_empty(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        kernel = MagicMock()
        settings = MagicMock()
        orch = CluedoExtendedOrchestrator(kernel=kernel, settings=settings)
        assert orch.execution_metrics == {}
        assert orch.start_time is None
        assert orch.end_time is None


class TestCluedoExtendedOrchestratorConsolidate:
    """Tests for consolidate_agent_response()."""

    def _make_orchestrator(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        return CluedoExtendedOrchestrator(kernel=MagicMock(), settings=MagicMock())

    def test_consolidate_string_response(self):
        orch = self._make_orchestrator()
        result = orch.consolidate_agent_response("Hello world", "Sherlock")
        assert isinstance(result, ChatMessageContent)
        assert result.content == "Hello world"
        assert result.name == "Sherlock"

    def test_consolidate_none_response(self):
        orch = self._make_orchestrator()
        result = orch.consolidate_agent_response(None, "Watson")
        assert isinstance(result, ChatMessageContent)
        assert result.content == ""

    def test_consolidate_chat_message_content(self):
        orch = self._make_orchestrator()
        msg = ChatMessageContent(role="assistant", content="test content", name="agent")
        result = orch.consolidate_agent_response(msg, "Moriarty")
        assert result.content == "test content"
        assert result.name == "Moriarty"

    def test_consolidate_list_of_chat_messages(self):
        orch = self._make_orchestrator()
        msgs = [
            ChatMessageContent(role="assistant", content="part1"),
            ChatMessageContent(role="assistant", content="part2"),
        ]
        result = orch.consolidate_agent_response(msgs, "Sherlock")
        assert "part1" in result.content
        assert "part2" in result.content

    def test_consolidate_empty_list(self):
        orch = self._make_orchestrator()
        result = orch.consolidate_agent_response([], "Watson")
        assert result.content == ""

    def test_consolidate_integer_response(self):
        orch = self._make_orchestrator()
        result = orch.consolidate_agent_response(42, "Agent")
        assert result.content == "42"


class TestCluedoExtendedOrchestratorDetectMessageType:
    """Tests for _detect_message_type()."""

    def _make_orchestrator(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        return CluedoExtendedOrchestrator(kernel=MagicMock(), settings=MagicMock())

    def test_detect_revelation(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("Je révèle la carte du Colonel") == "revelation"

    def test_detect_revelation_carte(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("J'ai une carte importante") == "revelation"

    def test_detect_suggestion(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("Je suggère que le suspect est...") == "suggestion"

    def test_detect_suggestion_propose(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("Je propose une hypothèse avec l'arme") == "suggestion"

    def test_detect_analysis(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("Mon analyse montre que...") == "analysis"

    def test_detect_analysis_deduction(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("Ma déduction logique est la suivante") == "analysis"

    def test_detect_analysis_donc(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("Donc nous pouvons conclure") == "analysis"

    def test_detect_reaction(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("C'est brillant Watson!") == "reaction"

    def test_detect_reaction_aha(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("Aha! Exactement ce que je pensais") == "reaction"

    def test_detect_generic_message(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("Bonjour tout le monde") == "message"

    def test_detect_empty_message(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("") == "message"

    def test_detect_case_insensitive(self):
        orch = self._make_orchestrator()
        assert orch._detect_message_type("JE RÉVÈLE MA CARTE") == "revelation"


class TestCluedoExtendedOrchestratorExtractSuggestion:
    """Tests for _extract_cluedo_suggestion()."""

    def _make_orchestrator(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        return CluedoExtendedOrchestrator(kernel=MagicMock(), settings=MagicMock())

    def test_no_suggestion_keywords(self):
        orch = self._make_orchestrator()
        result = orch._extract_cluedo_suggestion("Bonjour tout le monde")
        assert result is None

    def test_suggestion_with_two_elements(self):
        orch = self._make_orchestrator()
        result = orch._extract_cluedo_suggestion(
            "Je suggère Colonel Moutarde avec le Poignard"
        )
        assert result is not None
        assert result["suspect"] == "Colonel Moutarde"
        assert result["arme"] == "Poignard"

    def test_suggestion_with_all_three_elements(self):
        orch = self._make_orchestrator()
        result = orch._extract_cluedo_suggestion(
            "Je propose Colonel Moutarde avec le Revolver dans le Salon"
        )
        assert result is not None
        assert result["suspect"] == "Colonel Moutarde"
        assert result["arme"] == "Revolver"
        assert result["lieu"] == "Salon"

    def test_suggestion_only_one_element_returns_none(self):
        orch = self._make_orchestrator()
        result = orch._extract_cluedo_suggestion(
            "Je suggère Colonel Moutarde seulement"
        )
        assert result is None

    def test_suggestion_keyword_accuse(self):
        orch = self._make_orchestrator()
        result = orch._extract_cluedo_suggestion(
            "J'accuse Professeur Violet dans la Cuisine"
        )
        assert result is not None
        assert result["suspect"] == "Professeur Violet"
        assert result["lieu"] == "Cuisine"

    def test_suggestion_keyword_pense_que(self):
        orch = self._make_orchestrator()
        result = orch._extract_cluedo_suggestion(
            "Je pense que c'est le Chandelier dans le Bureau"
        )
        assert result is not None
        assert result["arme"] == "Chandelier"
        assert result["lieu"] == "Bureau"

    def test_suggestion_indetermine_for_missing(self):
        orch = self._make_orchestrator()
        result = orch._extract_cluedo_suggestion(
            "Je propose le Poignard dans la Cuisine"
        )
        assert result is not None
        assert result["suspect"] == "Indéterminé"
        assert result["arme"] == "Poignard"
        assert result["lieu"] == "Cuisine"

    def test_suggestion_case_insensitive(self):
        orch = self._make_orchestrator()
        result = orch._extract_cluedo_suggestion(
            "je suggère colonel moutarde avec le poignard"
        )
        assert result is not None


class TestCluedoExtendedOrchestratorEvaluateSolution:
    """Tests for _evaluate_solution_success()."""

    def _make_orchestrator_with_state(self, proposed=None, correct=None, is_proposed=False):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        orch = CluedoExtendedOrchestrator(kernel=MagicMock(), settings=MagicMock())
        orch.oracle_state = MagicMock()
        orch.oracle_state.is_solution_proposed = is_proposed
        orch.oracle_state.final_solution = proposed
        orch.oracle_state.get_solution_secrete.return_value = correct
        return orch

    def test_no_solution_proposed(self):
        orch = self._make_orchestrator_with_state(
            correct={"suspect": "A", "arme": "B", "lieu": "C"}
        )
        result = orch._evaluate_solution_success()
        assert result["success"] is False
        assert "Aucune solution" in result["reason"]

    def test_correct_solution(self):
        solution = {"suspect": "A", "arme": "B", "lieu": "C"}
        orch = self._make_orchestrator_with_state(
            proposed=solution, correct=solution, is_proposed=True
        )
        result = orch._evaluate_solution_success()
        assert result["success"] is True
        assert "correcte" in result["reason"]

    def test_incorrect_solution(self):
        orch = self._make_orchestrator_with_state(
            proposed={"suspect": "X", "arme": "Y", "lieu": "Z"},
            correct={"suspect": "A", "arme": "B", "lieu": "C"},
            is_proposed=True,
        )
        result = orch._evaluate_solution_success()
        assert result["success"] is False
        assert "incorrecte" in result["reason"]

    def test_partial_match_tracking(self):
        orch = self._make_orchestrator_with_state(
            proposed={"suspect": "A", "arme": "Y", "lieu": "C"},
            correct={"suspect": "A", "arme": "B", "lieu": "C"},
            is_proposed=True,
        )
        result = orch._evaluate_solution_success()
        assert result["partial_matches"]["suspect"] is True
        assert result["partial_matches"]["arme"] is False
        assert result["partial_matches"]["lieu"] is True


class TestCluedoExtendedOrchestratorPerformanceMetrics:
    """Tests for _calculate_performance_metrics()."""

    def _make_orchestrator(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        return CluedoExtendedOrchestrator(kernel=MagicMock(), settings=MagicMock())

    def test_performance_metrics_basic(self):
        orch = self._make_orchestrator()
        oracle_stats = {
            "agent_interactions": {"total_turns": 10},
            "workflow_metrics": {"oracle_interactions": 3, "cards_revealed": 2},
            "recent_revelations": [{"card": "A"}],
        }
        result = orch._calculate_performance_metrics(oracle_stats, execution_time=60.0)
        assert "efficiency" in result
        assert "collaboration" in result
        assert "comparison_2vs3_agents" in result

    def test_performance_metrics_zero_execution_time(self):
        orch = self._make_orchestrator()
        oracle_stats = {
            "agent_interactions": {"total_turns": 5},
            "workflow_metrics": {"oracle_interactions": 1, "cards_revealed": 0},
            "recent_revelations": [],
        }
        result = orch._calculate_performance_metrics(oracle_stats, execution_time=0.0)
        assert result["efficiency"]["turns_per_minute"] == 0

    def test_performance_metrics_empty_stats(self):
        orch = self._make_orchestrator()
        oracle_stats = {
            "agent_interactions": {},
            "workflow_metrics": {},
            "recent_revelations": [],
        }
        result = orch._calculate_performance_metrics(oracle_stats, execution_time=30.0)
        assert result["efficiency"]["turns_per_minute"] == 0

    def test_agent_balance_no_turns(self):
        orch = self._make_orchestrator()
        result = orch._calculate_agent_balance({"total_turns": 0})
        assert result["sherlock"] == 0.0
        assert result["watson"] == 0.0
        assert result["moriarty"] == 0.0

    def test_agent_balance_with_turns(self):
        orch = self._make_orchestrator()
        result = orch._calculate_agent_balance({"total_turns": 9})
        assert result["expected_turns_per_agent"] == 3.0
        assert result["balance_score"] == 1.0


class TestCluedoExtendedOrchestratorDetectEmotionalReactions:
    """Tests for _detect_emotional_reactions()."""

    def _make_orchestrator(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        return CluedoExtendedOrchestrator(kernel=MagicMock(), settings=MagicMock())

    def test_returns_empty_list(self):
        orch = self._make_orchestrator()
        result = orch._detect_emotional_reactions("Sherlock", "some content", [])
        assert result == []


class TestCluedoExtendedOrchestratorExecuteWorkflow:
    """Tests for execute_workflow() error handling."""

    async def test_execute_without_setup_raises(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        orch = CluedoExtendedOrchestrator(kernel=MagicMock(), settings=MagicMock())
        with pytest.raises(ValueError, match="Workflow non configuré"):
            await orch.execute_workflow()

    async def test_execute_sets_start_time(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        orch = CluedoExtendedOrchestrator(kernel=MagicMock(), settings=MagicMock())
        orch.orchestration = MagicMock()
        orch.oracle_state = MagicMock()
        orch.oracle_state.is_solution_proposed = False
        orch.oracle_state.final_solution = None
        orch.oracle_state.get_solution_secrete.return_value = {}
        orch.oracle_state.is_game_solvable_by_elimination.return_value = False
        orch.oracle_state.get_oracle_statistics.return_value = {
            "agent_interactions": {"total_turns": 0},
            "workflow_metrics": {"oracle_interactions": 0, "cards_revealed": 0},
            "recent_revelations": [],
        }
        orch.oracle_state.get_fluidity_metrics.return_value = {}
        orch.sherlock_agent = MagicMock()
        orch.sherlock_agent.name = "Sherlock"

        # Make termination strategy immediately terminate
        orch.termination_strategy = MagicMock()
        orch.termination_strategy.should_terminate = AsyncMock(return_value=True)
        orch.selection_strategy = MagicMock()

        result = await orch.execute_workflow()
        assert orch.start_time is not None
        assert orch.end_time is not None
        assert "workflow_info" in result


class TestAnalyzeContextualElements:
    """Tests for _analyze_contextual_elements()."""

    def _make_orchestrator_with_state(self):
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
        orch = CluedoExtendedOrchestrator(kernel=MagicMock(), settings=MagicMock())
        orch.oracle_state = MagicMock()
        return orch

    def test_detects_suite_a_reference(self):
        orch = self._make_orchestrator_with_state()
        history = [MagicMock(), MagicMock()]
        orch._analyze_contextual_elements("Sherlock", "Suite à votre remarque...", history)
        orch.oracle_state.record_contextual_reference.assert_called_once()
        call_args = orch.oracle_state.record_contextual_reference.call_args
        assert call_args.kwargs["reference_type"] == "building_on"

    def test_detects_en_reaction_a(self):
        orch = self._make_orchestrator_with_state()
        history = [MagicMock(), MagicMock()]
        orch._analyze_contextual_elements("Watson", "En réaction à cela", history)
        orch.oracle_state.record_contextual_reference.assert_called_once()
        call_args = orch.oracle_state.record_contextual_reference.call_args
        assert call_args.kwargs["reference_type"] == "reacting_to"

    def test_no_reference_in_content(self):
        orch = self._make_orchestrator_with_state()
        history = [MagicMock(), MagicMock()]
        orch._analyze_contextual_elements("Sherlock", "Bonjour", history)
        orch.oracle_state.record_contextual_reference.assert_not_called()

    def test_no_reference_with_empty_history(self):
        orch = self._make_orchestrator_with_state()
        # With only 1 message in history, no reference is recorded
        history = [MagicMock()]
        orch._analyze_contextual_elements("Sherlock", "Suite à votre remarque", history)
        # The code checks `len(history) > 1` before recording
        orch.oracle_state.record_contextual_reference.assert_not_called()
