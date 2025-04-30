"""
Tests unitaires pour le module strategies.
"""

import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from semantic_kernel.agents import Agent
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from core.strategies import SimpleTerminationStrategy, DelegatingSelectionStrategy
from core.shared_state import RhetoricalAnalysisState
from tests.async_test_case import AsyncTestCase


class TestSimpleTerminationStrategy(AsyncTestCase):
    """Tests pour la classe SimpleTerminationStrategy."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.state = RhetoricalAnalysisState("Texte de test pour l'analyse rhétorique.")
        self.strategy = SimpleTerminationStrategy(self.state, max_steps=5)
        self.agent = MagicMock(spec=Agent)
        self.history = []

    async def test_initialization(self):
        """Teste l'initialisation correcte de la stratégie."""
        self.assertEqual(self.strategy._state, self.state)
        self.assertEqual(self.strategy._max_steps, 5)
        self.assertEqual(self.strategy._step_count, 0)
        self.assertIsNotNone(self.strategy._instance_id)
        self.assertIsNotNone(self.strategy._logger)

    async def test_should_terminate_max_steps(self):
        """Teste la terminaison basée sur le nombre maximum d'étapes."""
        # Simuler 5 appels (le max configuré)
        for _ in range(5):
            result = await self.strategy.should_terminate(self.agent, self.history)
            self.assertFalse(result)
        
        # Le 6ème appel devrait retourner True (max atteint)
        result = await self.strategy.should_terminate(self.agent, self.history)
        self.assertTrue(result)

    async def test_should_terminate_conclusion(self):
        """Teste la terminaison basée sur la présence d'une conclusion."""
        # Sans conclusion, ne devrait pas terminer
        result = await self.strategy.should_terminate(self.agent, self.history)
        self.assertFalse(result)
        
        # Avec une conclusion, devrait terminer
        self.state.set_conclusion("Conclusion finale de test.")
        result = await self.strategy.should_terminate(self.agent, self.history)
        self.assertTrue(result)

    async def test_reset(self):
        """Teste la réinitialisation de la stratégie."""
        # Simuler quelques appels
        for _ in range(3):
            await self.strategy.should_terminate(self.agent, self.history)
        
        # Vérifier que le compteur a été incrémenté
        self.assertEqual(self.strategy._step_count, 3)
        
        # Réinitialiser
        await self.strategy.reset()
        
        # Vérifier que le compteur a été réinitialisé
        self.assertEqual(self.strategy._step_count, 0)


class TestDelegatingSelectionStrategy(AsyncTestCase):
    """Tests pour la classe DelegatingSelectionStrategy."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.state = RhetoricalAnalysisState("Texte de test pour l'analyse rhétorique.")
        
        # Créer des agents mock
        self.pm_agent = MagicMock(spec=Agent)
        self.pm_agent.name = "ProjectManagerAgent"
        
        self.pl_agent = MagicMock(spec=Agent)
        self.pl_agent.name = "PropositionalLogicAgent"
        
        self.informal_agent = MagicMock(spec=Agent)
        self.informal_agent.name = "InformalAnalysisAgent"
        
        self.agents = [self.pm_agent, self.pl_agent, self.informal_agent]
        
        # Créer la stratégie
        self.strategy = DelegatingSelectionStrategy(self.agents, self.state)
        
        # Historique vide
        self.empty_history = []

    async def test_initialization(self):
        """Teste l'initialisation correcte de la stratégie."""
        self.assertEqual(self.strategy._analysis_state, self.state)
        self.assertEqual(self.strategy._default_agent_name, "ProjectManagerAgent")
        self.assertEqual(len(self.strategy._agents_map), 3)
        self.assertIn("ProjectManagerAgent", self.strategy._agents_map)
        self.assertIn("PropositionalLogicAgent", self.strategy._agents_map)
        self.assertIn("InformalAnalysisAgent", self.strategy._agents_map)

    async def test_next_with_empty_history(self):
        """Teste la sélection avec un historique vide."""
        # Sans désignation, devrait retourner l'agent par défaut (PM)
        selected_agent = await self.strategy.next(self.agents, self.empty_history)
        self.assertEqual(selected_agent, self.pm_agent)

    async def test_next_with_designation(self):
        """Teste la sélection avec une désignation explicite."""
        # Désigner explicitement l'agent PL
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        # Devrait sélectionner l'agent PL
        selected_agent = await self.strategy.next(self.agents, self.empty_history)
        self.assertEqual(selected_agent, self.pl_agent)
        
        # La désignation devrait avoir été consommée
        self.assertIsNone(self.state._next_agent_designated)

    async def test_next_with_invalid_designation(self):
        """Teste la sélection avec une désignation invalide."""
        # Désigner un agent qui n'existe pas
        self.state.designate_next_agent("NonExistentAgent")
        
        # Devrait retourner l'agent par défaut (PM)
        selected_agent = await self.strategy.next(self.agents, self.empty_history)
        self.assertEqual(selected_agent, self.pm_agent)
        
        # La désignation devrait avoir été consommée
        self.assertIsNone(self.state._next_agent_designated)

    async def test_next_after_user_message(self):
        """Teste la sélection après un message utilisateur."""
        # Créer un message utilisateur
        user_message = MagicMock(spec=ChatMessageContent)
        user_message.role = AuthorRole.USER
        user_message.name = "User"
        
        history = [user_message]
        
        # Devrait sélectionner l'agent par défaut (PM)
        selected_agent = await self.strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pm_agent)

    async def test_next_after_assistant_message(self):
        """Teste la sélection après un message assistant."""
        # Créer un message assistant (non PM)
        assistant_message = MagicMock(spec=ChatMessageContent)
        assistant_message.role = AuthorRole.ASSISTANT
        assistant_message.name = "InformalAnalysisAgent"
        
        history = [assistant_message]
        
        # Devrait retourner au PM
        selected_agent = await self.strategy.next(self.agents, history)
        self.assertEqual(selected_agent, self.pm_agent)

    async def test_reset(self):
        """Teste la réinitialisation de la stratégie."""
        # Désigner un agent
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        # Réinitialiser
        await self.strategy.reset()
        
        # La désignation devrait avoir été consommée
        self.assertIsNone(self.state._next_agent_designated)


if __name__ == '__main__':
    unittest.main()