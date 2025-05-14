"""
Tests unitaires pour le module strategies.
"""

import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from semantic_kernel.agents import Agent
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from argumentiation_analysis.core.strategies import SimpleTerminationStrategy, DelegatingSelectionStrategy, BalancedParticipationStrategy
from argumentiation_analysis.core.shared_state import RhetoricalAnalysisState
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


class TestBalancedParticipationStrategy(AsyncTestCase):
    """Tests pour la classe BalancedParticipationStrategy."""

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
        
        # Créer la stratégie avec configuration par défaut
        self.strategy = BalancedParticipationStrategy(self.agents, self.state)
        
        # Historique vide
        self.empty_history = []

    async def test_initialization_default(self):
        """Teste l'initialisation correcte de la stratégie avec configuration par défaut."""
        self.assertEqual(self.strategy._analysis_state, self.state)
        self.assertEqual(self.strategy._default_agent_name, "ProjectManagerAgent")
        self.assertEqual(len(self.strategy._agents_map), 3)
        self.assertIn("ProjectManagerAgent", self.strategy._agents_map)
        self.assertIn("PropositionalLogicAgent", self.strategy._agents_map)
        self.assertIn("InformalAnalysisAgent", self.strategy._agents_map)
        
        # Vérifier que les compteurs sont initialisés à zéro
        self.assertEqual(self.strategy._total_turns, 0)
        for agent_name in self.strategy._participation_counts:
            self.assertEqual(self.strategy._participation_counts[agent_name], 0)
            self.assertEqual(self.strategy._last_selected[agent_name], 0)
            self.assertEqual(self.strategy._imbalance_budget[agent_name], 0.0)
        
        # Vérifier la distribution des participations cibles (PM devrait avoir une part plus importante)
        self.assertGreater(self.strategy._target_participation["ProjectManagerAgent"],
                          self.strategy._target_participation["PropositionalLogicAgent"])
        self.assertGreater(self.strategy._target_participation["ProjectManagerAgent"],
                          self.strategy._target_participation["InformalAnalysisAgent"])
        
        # Vérifier que la somme des participations cibles est égale à 1.0
        total_participation = sum(self.strategy._target_participation.values())
        self.assertAlmostEqual(total_participation, 1.0)

    async def test_initialization_custom(self):
        """Teste l'initialisation avec une configuration personnalisée."""
        # Définir des participations cibles personnalisées
        custom_targets = {
            "ProjectManagerAgent": 0.5,
            "PropositionalLogicAgent": 0.3,
            "InformalAnalysisAgent": 0.2
        }
        
        # Créer une stratégie avec configuration personnalisée
        custom_strategy = BalancedParticipationStrategy(
            self.agents,
            self.state,
            default_agent_name="PropositionalLogicAgent",
            target_participation=custom_targets
        )
        
        # Vérifier la configuration
        self.assertEqual(custom_strategy._default_agent_name, "PropositionalLogicAgent")
        self.assertEqual(custom_strategy._target_participation["ProjectManagerAgent"], 0.5)
        self.assertEqual(custom_strategy._target_participation["PropositionalLogicAgent"], 0.3)
        self.assertEqual(custom_strategy._target_participation["InformalAnalysisAgent"], 0.2)

    async def test_next_with_designation(self):
        """Teste que la stratégie respecte les désignations explicites."""
        # Désigner explicitement l'agent PL
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        # Devrait sélectionner l'agent PL
        selected_agent = await self.strategy.next(self.agents, self.empty_history)
        self.assertEqual(selected_agent, self.pl_agent)
        
        # La désignation devrait avoir été consommée
        self.assertIsNone(self.state._next_agent_designated)
        
        # Vérifier que les compteurs ont été mis à jour
        self.assertEqual(self.strategy._participation_counts["PropositionalLogicAgent"], 1)
        self.assertEqual(self.strategy._total_turns, 1)

    async def test_next_with_invalid_designation(self):
        """Teste la sélection avec une désignation invalide."""
        # Désigner un agent qui n'existe pas
        self.state.designate_next_agent("NonExistentAgent")
        
        # Devrait retourner l'agent par défaut (PM)
        selected_agent = await self.strategy.next(self.agents, self.empty_history)
        self.assertEqual(selected_agent, self.pm_agent)
        
        # La désignation devrait avoir été consommée
        self.assertIsNone(self.state._next_agent_designated)
        
        # Vérifier que les compteurs ont été mis à jour pour l'agent par défaut
        self.assertEqual(self.strategy._participation_counts["ProjectManagerAgent"], 1)

    async def test_balanced_participation(self):
        """Teste que la stratégie équilibre effectivement la participation des agents."""
        # Simuler plusieurs tours sans désignation explicite
        participation_counts = {"ProjectManagerAgent": 0, "PropositionalLogicAgent": 0, "InformalAnalysisAgent": 0}
        
        # Exécuter 30 tours pour avoir un échantillon significatif
        for _ in range(30):
            selected_agent = await self.strategy.next(self.agents, self.empty_history)
            participation_counts[selected_agent.name] += 1
        
        # Vérifier que tous les agents ont participé
        for agent_name in participation_counts:
            self.assertGreater(participation_counts[agent_name], 0,
                              f"L'agent {agent_name} n'a pas participé")
        
        # Vérifier que les taux de participation sont proches des cibles
        total_turns = sum(participation_counts.values())
        for agent_name, count in participation_counts.items():
            actual_rate = count / total_turns
            target_rate = self.strategy._target_participation[agent_name]
            # Tolérance de 20% pour tenir compte de la variabilité statistique
            self.assertAlmostEqual(actual_rate, target_rate, delta=0.2,
                                  msg=f"Taux de participation pour {agent_name}: {actual_rate} vs cible {target_rate}")
        
        # Vérifier que les compteurs internes correspondent aux compteurs que nous avons suivis
        for agent_name in participation_counts:
            self.assertEqual(self.strategy._participation_counts[agent_name], participation_counts[agent_name])
        
        self.assertEqual(self.strategy._total_turns, total_turns)

    async def test_imbalance_budget_adjustment(self):
        """Teste que la stratégie gère correctement le budget de déséquilibre."""
        # Désigner explicitement le même agent plusieurs fois
        for _ in range(5):
            self.state.designate_next_agent("PropositionalLogicAgent")
            await self.strategy.next(self.agents, self.empty_history)
        
        # Vérifier que le budget de déséquilibre a été ajusté pour les autres agents
        self.assertGreater(self.strategy._imbalance_budget["ProjectManagerAgent"], 0)
        self.assertGreater(self.strategy._imbalance_budget["InformalAnalysisAgent"], 0)
        
        # Le budget de l'agent désigné devrait être réduit
        self.assertEqual(self.strategy._imbalance_budget["PropositionalLogicAgent"], 0)
        
        # Maintenant, laisser la stratégie équilibrer naturellement
        # Les agents avec un budget plus élevé devraient être sélectionnés en priorité
        selected_agent = await self.strategy.next(self.agents, self.empty_history)
        self.assertNotEqual(selected_agent, self.pl_agent,
                           "L'agent surreprésenté ne devrait pas être sélectionné immédiatement après")

    async def test_reset(self):
        """Teste la réinitialisation de la stratégie."""
        # Simuler quelques tours
        for _ in range(5):
            await self.strategy.next(self.agents, self.empty_history)
        
        # Vérifier que les compteurs ont été incrémentés
        self.assertEqual(self.strategy._total_turns, 5)
        total_participations = sum(self.strategy._participation_counts.values())
        self.assertEqual(total_participations, 5)
        
        # Désigner un agent pour le prochain tour
        self.state.designate_next_agent("PropositionalLogicAgent")
        
        # Réinitialiser
        await self.strategy.reset()
        
        # Vérifier que tous les compteurs ont été réinitialisés
        self.assertEqual(self.strategy._total_turns, 0)
        for agent_name in self.strategy._participation_counts:
            self.assertEqual(self.strategy._participation_counts[agent_name], 0)
            self.assertEqual(self.strategy._last_selected[agent_name], 0)
            self.assertEqual(self.strategy._imbalance_budget[agent_name], 0.0)
        
        # La désignation devrait avoir été consommée
        self.assertIsNone(self.state._next_agent_designated)


if __name__ == '__main__':
    unittest.main()