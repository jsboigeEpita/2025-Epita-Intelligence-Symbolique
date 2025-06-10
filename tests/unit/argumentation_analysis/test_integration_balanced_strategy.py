# -*- coding: utf-8 -*-
"""
Tests d'intégration pour la stratégie d'équilibrage de participation des agents.

Ce module contient des tests d'intégration qui vérifient le comportement
de la stratégie d'équilibrage de participation dans différents scénarios
d'analyse argumentative.
"""

import unittest
import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
try:
    from semantic_kernel.contents import AuthorRole
except ImportError:
    # Fallback pour versions récentes de Semantic Kernel
    from semantic_kernel.contents.chat_message_content import AuthorRole
from semantic_kernel.agents import Agent, AgentGroupChat

# Utiliser la fonction setup_import_paths pour résoudre les problèmes d'imports relatifs
# from tests import setup_import_paths # Commenté pour investigation
# setup_import_paths() # Commenté pour investigation

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import BalancedParticipationStrategy
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel
from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
# from tests.async_test_case import AsyncTestCase # Suppression de l'import


class TestBalancedStrategyIntegration: # Suppression de l'héritage AsyncTestCase
    """Tests d'intégration pour la stratégie d'équilibrage de participation."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.test_text = """
        La Terre est plate car l'horizon semble plat quand on regarde au loin.
        De plus, si la Terre était ronde, les gens à l'autre bout tomberaient.
        Certains scientifiques affirment que la Terre est ronde, mais ils sont payés par la NASA.
        """
        
        self.state = RhetoricalAnalysisState(self.test_text)
        
        self.llm_service = MagicMock()
        self.llm_service.service_id = "test_service"
        
        self.kernel = sk.Kernel()
        
        self.state_manager = StateManagerPlugin(self.state)
        self.kernel.add_plugin(self.state_manager, "StateManager")
        
        self.pm_agent = MagicMock(spec=Agent)
        self.pm_agent.name = "ProjectManagerAgent"
        self.pm_agent.id = "pm_agent_id"
        
        self.pl_agent = MagicMock(spec=Agent)
        self.pl_agent.name = "PropositionalLogicAgent"
        self.pl_agent.id = "pl_agent_id"
        
        self.informal_agent = MagicMock(spec=Agent)
        self.informal_agent.name = "InformalAnalysisAgent"
        self.informal_agent.id = "informal_agent_id"
        
        self.extract_agent = MagicMock(spec=Agent)
        self.extract_agent.name = "ExtractAgent"
        self.extract_agent.id = "extract_agent_id"
        
        self.agents = [self.pm_agent, self.pl_agent, self.informal_agent, self.extract_agent]

    async def test_balanced_strategy_integration(self):
        """Teste l'intégration de la stratégie d'équilibrage avec les autres composants."""
        balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )
        
        self.assertEqual(balanced_strategy._analysis_state, self.state)
        self.assertEqual(balanced_strategy._default_agent_name, "ProjectManagerAgent")
        self.assertEqual(len(balanced_strategy._agents_map), 4)
        
        history = []
        
        selected_agent = await balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pm_agent)
        
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = AuthorRole.ASSISTANT
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Je vais définir les tâches d'analyse."
        history.append(pm_message)
        
        self.state.add_task("Identifier les arguments dans le texte")
        
        selected_agent = await balanced_strategy.next(self.agents, history)
        self.assertNotEqual(selected_agent, self.pm_agent)
        
        agent_message = MagicMock(spec=ChatMessageContent)
        agent_message.role = AuthorRole.ASSISTANT
        agent_message.name = selected_agent.name
        agent_message.content = "Je vais analyser les arguments."
        history.append(agent_message)
        
        self.assertEqual(balanced_strategy._participation_counts["ProjectManagerAgent"], 1)
        self.assertEqual(balanced_strategy._participation_counts[selected_agent.name], 1)
        self.assertEqual(balanced_strategy._total_turns, 2)

    async def test_balanced_strategy_with_designations(self):
        """Teste l'interaction entre la stratégie d'équilibrage et les désignations explicites."""
        balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )
        
        history = []
        
        self.state.designate_next_agent("PropositionalLogicAgent")
        selected_agent = await balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pl_agent)
        
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = AuthorRole.ASSISTANT
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "Je vais formaliser les arguments."
        history.append(pl_message)
        
        self.state.designate_next_agent("InformalAnalysisAgent")
        selected_agent = await balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.informal_agent)
        
        informal_message = MagicMock(spec=ChatMessageContent)
        informal_message.role = AuthorRole.ASSISTANT
        informal_message.name = "InformalAnalysisAgent"
        informal_message.content = "Je vais identifier les sophismes."
        history.append(informal_message)
        
        selected_agent = await balanced_strategy.next(self.agents, history)
        
        self.assertEqual(balanced_strategy._participation_counts["PropositionalLogicAgent"], 1)
        self.assertEqual(balanced_strategy._participation_counts["InformalAnalysisAgent"], 1)
        self.assertEqual(balanced_strategy._total_turns, 3)
        
        self.assertGreaterEqual(balanced_strategy._imbalance_budget["ProjectManagerAgent"], 0)
        self.assertGreaterEqual(balanced_strategy._imbalance_budget["ExtractAgent"], 0)

    async def test_balanced_strategy_in_group_chat(self):
        """Teste l'utilisation de la stratégie d'équilibrage dans un AgentGroupChat."""
        balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )
        
        history = []
        
        selected_agent = await balanced_strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pm_agent)
        
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = AuthorRole.ASSISTANT
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Message du PM"
        history.append(pm_message)
        
        selected_agent = await balanced_strategy.next(self.agents, history)
        self.assertNotEqual(selected_agent, self.pm_agent)
        
        agent_message = MagicMock(spec=ChatMessageContent)
        agent_message.role = AuthorRole.ASSISTANT
        agent_message.name = selected_agent.name
        agent_message.content = "Message de l'agent"
        history.append(agent_message)
        
        selected_agent2 = await balanced_strategy.next(self.agents, history)
        self.assertNotEqual(selected_agent2, self.pm_agent)
        self.assertNotEqual(selected_agent2, selected_agent)
        
        self.assertEqual(balanced_strategy._participation_counts["ProjectManagerAgent"], 1)
        self.assertEqual(balanced_strategy._participation_counts[selected_agent.name], 1)
        self.assertEqual(balanced_strategy._total_turns, 3)


class TestBalancedStrategyEndToEnd: # Suppression de l'héritage AsyncTestCase
    """Tests d'intégration end-to-end pour la stratégie d'équilibrage."""

    @patch('argumentation_analysis.orchestration.analysis_runner.BalancedParticipationStrategy') # Corrigé le chemin du mock
    @patch('argumentation_analysis.orchestration.analysis_runner.AgentGroupChat') # Corrigé le chemin du mock
    async def test_balanced_strategy_in_analysis_runner(self, mock_agent_group_chat, mock_balanced_strategy):
        """Teste l'utilisation de la stratégie d'équilibrage dans le runner d'analyse."""
        mock_strategy_instance = MagicMock()
        mock_balanced_strategy.return_value = mock_strategy_instance
        
        mock_extract_kernel = MagicMock()
        mock_extract_agent = MagicMock()
        mock_extract_agent.id = "extract_agent_id"
        
        mock_group_chat_instance = MagicMock()
        mock_agent_group_chat.return_value = mock_group_chat_instance
        
        async def mock_invoke():
            message1 = MagicMock()
            message1.name = "ProjectManagerAgent"
            message1.role = AuthorRole.ASSISTANT
            message1.content = "Message du PM"
            yield message1
            
            message2 = MagicMock()
            message2.name = "InformalAnalysisAgent"
            message2.role = AuthorRole.ASSISTANT
            message2.content = "Message de l'agent informel"
            yield message2
        
        mock_group_chat_instance.invoke = mock_invoke
        mock_group_chat_instance.history = MagicMock()
        mock_group_chat_instance.history.add_user_message = MagicMock()
        mock_group_chat_instance.history.messages = []
        
        llm_service_mock = MagicMock()
        llm_service_mock.service_id = "test_service"
        
        with patch('argumentation_analysis.orchestration.analysis_runner.RhetoricalAnalysisState'), \
             patch('argumentation_analysis.orchestration.analysis_runner.StateManagerPlugin'), \
             patch('argumentation_analysis.orchestration.analysis_runner.sk.Kernel'), \
             patch('argumentation_analysis.orchestration.analysis_runner.setup_pm_kernel'), \
             patch('argumentation_analysis.orchestration.analysis_runner.setup_informal_kernel'), \
             patch('argumentation_analysis.orchestration.analysis_runner.setup_pl_kernel'), \
             patch('argumentation_analysis.orchestration.analysis_runner.setup_extract_agent', return_value=(mock_extract_kernel, mock_extract_agent)), \
             patch('argumentation_analysis.orchestration.analysis_runner.ChatCompletionAgent'), \
             patch('argumentation_analysis.orchestration.analysis_runner.SimpleTerminationStrategy'):
            
            await run_analysis_conversation("Texte de test", llm_service_mock)
        
        mock_balanced_strategy.assert_called_once()
        mock_agent_group_chat.assert_called_once()


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])