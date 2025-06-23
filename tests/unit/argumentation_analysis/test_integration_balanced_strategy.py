# -*- coding: utf-8 -*-
"""
Tests d'intégration pour la stratégie d'équilibrage de participation des agents.

Ce module contient des tests d'intégration qui vérifient le comportement
de la stratégie d'équilibrage de participation dans différents scénarios
d'analyse argumentative.
"""

import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
import pytest
import logging

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
# Correction de l'importation de AuthorRole suite à la refactorisation de semantic-kernel
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import Agent, AgentGroupChat

# Utiliser la fonction setup_import_paths pour résoudre les problèmes d'imports relatifs
# from tests import setup_import_paths # Commenté pour investigation
# setup_import_paths() # Commenté pour investigation

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import BalancedParticipationStrategy
from argumentation_analysis.orchestration.analysis_runner import AnalysisRunner
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.pl.pl_definitions import setup_pl_kernel
from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel
from argumentation_analysis.agents.core.pm.pm_definitions import setup_pm_kernel
# from tests.async_test_case import AsyncTestCase # Suppression de l'import


class TestBalancedStrategyIntegration: # Suppression de l'héritage AsyncTestCase
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logging.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests d'intégration pour la stratégie d'équilibrage de participation."""

    @pytest.fixture(autouse=True)
    def setup_method(self):
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
        
        self.pm_agent = MagicMock(spec=BaseAgent)
        self.pm_agent.name = "ProjectManagerAgent"
        self.pm_agent.id = "pm_agent_id"
        
        self.pl_agent = MagicMock(spec=BaseAgent)
        self.pl_agent.name = "PropositionalLogicAgent"
        self.pl_agent.id = "pl_agent_id"
        
        self.informal_agent = MagicMock(spec=BaseAgent)
        self.informal_agent.name = "InformalAnalysisAgent"
        self.informal_agent.id = "informal_agent_id"
        
        self.extract_agent = MagicMock(spec=BaseAgent)
        self.extract_agent.name = "ExtractAgent"
        self.extract_agent.id = "extract_agent_id"
        
        self.agents = [self.pm_agent, self.pl_agent, self.informal_agent, self.extract_agent]

    @pytest.mark.asyncio
    async def test_balanced_strategy_integration(self):
        """Teste l'intégration de la stratégie d'équilibrage avec les autres composants."""
        balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )
        
        assert balanced_strategy._analysis_state == self.state
        assert balanced_strategy._default_agent_name == "ProjectManagerAgent"
        assert len(balanced_strategy._agents_map) == 4
        
        history = []
        
        selected_agent = await balanced_strategy.next(self.agents, history)
        assert selected_agent == self.pm_agent
        
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = "assistant"
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Je vais définir les tâches d'analyse."
        history.append(pm_message)
        
        self.state.add_task("Identifier les arguments dans le texte")
        
        selected_agent = await balanced_strategy.next(self.agents, history)
        assert selected_agent != self.pm_agent
        
        agent_message = MagicMock(spec=ChatMessageContent)
        agent_message.role = "assistant"
        agent_message.name = selected_agent.name
        agent_message.content = "Je vais analyser les arguments."
        history.append(agent_message)
        
        assert balanced_strategy._participation_counts["ProjectManagerAgent"] == 1
        assert balanced_strategy._participation_counts[selected_agent.name] == 1
        assert balanced_strategy._total_turns == 2

    @pytest.mark.asyncio
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
        assert selected_agent == self.pl_agent
        
        pl_message = MagicMock(spec=ChatMessageContent)
        pl_message.role = "assistant"
        pl_message.name = "PropositionalLogicAgent"
        pl_message.content = "Je vais formaliser les arguments."
        history.append(pl_message)
        
        self.state.designate_next_agent("InformalAnalysisAgent")
        selected_agent = await balanced_strategy.next(self.agents, history)
        assert selected_agent == self.informal_agent
        
        informal_message = MagicMock(spec=ChatMessageContent)
        informal_message.role = "assistant"
        informal_message.name = "InformalAnalysisAgent"
        informal_message.content = "Je vais identifier les sophismes."
        history.append(informal_message)
        
        selected_agent = await balanced_strategy.next(self.agents, history)
        
        assert balanced_strategy._participation_counts["PropositionalLogicAgent"] == 1
        assert balanced_strategy._participation_counts["InformalAnalysisAgent"] == 1
        assert balanced_strategy._total_turns == 3
        
        assert balanced_strategy._imbalance_budget["ProjectManagerAgent"] >= 0
        assert balanced_strategy._imbalance_budget["ExtractAgent"] >= 0

    @pytest.mark.asyncio
    async def test_balanced_strategy_in_group_chat(self):
        """Teste l'utilisation de la stratégie d'équilibrage dans un AgentGroupChat."""
        balanced_strategy = BalancedParticipationStrategy(
            agents=self.agents,
            state=self.state,
            default_agent_name="ProjectManagerAgent"
        )
        
        history = []
        
        selected_agent = await balanced_strategy.next(self.agents, history)
        assert selected_agent == self.pm_agent
        
        pm_message = MagicMock(spec=ChatMessageContent)
        pm_message.role = "assistant"
        pm_message.name = "ProjectManagerAgent"
        pm_message.content = "Message du PM"
        history.append(pm_message)
        
        selected_agent = await balanced_strategy.next(self.agents, history)
        assert selected_agent != self.pm_agent
        
        agent_message = MagicMock(spec=ChatMessageContent)
        agent_message.role = "assistant"
        agent_message.name = selected_agent.name
        agent_message.content = "Message de l'agent"
        history.append(agent_message)
        
        selected_agent2 = await balanced_strategy.next(self.agents, history)
        assert selected_agent2 != self.pm_agent
        assert selected_agent2 != selected_agent
        
        assert balanced_strategy._participation_counts["ProjectManagerAgent"] == 1
        assert balanced_strategy._participation_counts[selected_agent.name] == 1
        assert balanced_strategy._total_turns == 3




if __name__ == '__main__':
    pytest.main(['-xvs', __file__])


