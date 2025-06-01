# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module strategies.
"""

import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from semantic_kernel.agents import Agent
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from argumentation_analysis.core.strategies import SimpleTerminationStrategy, DelegatingSelectionStrategy, BalancedParticipationStrategy
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
# from tests.async_test_case import AsyncTestCase # Suppression de l'import


import pytest # Ajout de pytest pour les fixtures

class TestSimpleTerminationStrategy:
    """Tests pour la classe SimpleTerminationStrategy."""

    @pytest.fixture
    def strategy_components(self):
        """Fixture pour initialiser les composants de test."""
        state = RhetoricalAnalysisState("Texte de test pour l'analyse rhétorique.")
        strategy = SimpleTerminationStrategy(state, max_steps=5)
        agent = MagicMock(spec=Agent)
        history = []
        return state, strategy, agent, history

    async def test_initialization(self, strategy_components):
        """Teste l'initialisation correcte de la stratégie."""
        state, strategy, _, _ = strategy_components
        assert strategy._state == state
        assert strategy._max_steps == 5
        assert strategy._step_count == 0
        assert strategy._instance_id is not None
        assert strategy._logger is not None

    async def test_should_terminate_max_steps(self, strategy_components):
        """Teste la terminaison basée sur le nombre maximum d'étapes."""
        _, strategy, agent, history = strategy_components
        # Simuler 5 appels (le max configuré)
        for _ in range(5):
            result = await strategy.should_terminate(agent, history)
            assert not result
        
        # Le 6ème appel devrait retourner True (max atteint)
        result = await strategy.should_terminate(agent, history)
        assert result

    async def test_should_terminate_conclusion(self, strategy_components):
        """Teste la terminaison basée sur la présence d'une conclusion."""
        state, strategy, agent, history = strategy_components
        # Sans conclusion, ne devrait pas terminer
        result = await strategy.should_terminate(agent, history)
        assert not result
        
        # Avec une conclusion, devrait terminer
        state.set_conclusion("Conclusion finale de test.")
        result = await strategy.should_terminate(agent, history)
        assert result

    async def test_reset(self, strategy_components):
        """Teste la réinitialisation de la stratégie."""
        _, strategy, agent, history = strategy_components
        # Simuler quelques appels
        for _ in range(3):
            await strategy.should_terminate(agent, history)
        
        # Vérifier que le compteur a été incrémenté
        assert strategy._step_count == 3
        
        # Réinitialiser
        await strategy.reset()
        
        # Vérifier que le compteur a été réinitialisé
        assert strategy._step_count == 0


class TestDelegatingSelectionStrategy:
    """Tests pour la classe DelegatingSelectionStrategy."""

    @pytest.fixture
    def delegating_strategy_components(self):
        """Fixture pour initialiser les composants de test."""
        state = RhetoricalAnalysisState("Texte de test pour l'analyse rhétorique.")
        
        pm_agent = MagicMock(spec=Agent)
        pm_agent.name = "ProjectManagerAgent"
        
        pl_agent = MagicMock(spec=Agent)
        pl_agent.name = "PropositionalLogicAgent"
        
        informal_agent = MagicMock(spec=Agent)
        informal_agent.name = "InformalAnalysisAgent"
        
        agents = [pm_agent, pl_agent, informal_agent]
        strategy = DelegatingSelectionStrategy(agents, state)
        empty_history = []
        return state, strategy, agents, pm_agent, pl_agent, informal_agent, empty_history

    async def test_initialization(self, delegating_strategy_components):
        """Teste l'initialisation correcte de la stratégie."""
        state, strategy, _, _, _, _, _ = delegating_strategy_components
        assert strategy._analysis_state == state
        assert strategy._default_agent_name == "ProjectManagerAgent"
        assert len(strategy._agents_map) == 3
        assert "ProjectManagerAgent" in strategy._agents_map
        assert "PropositionalLogicAgent" in strategy._agents_map
        assert "InformalAnalysisAgent" in strategy._agents_map

    async def test_next_with_empty_history(self, delegating_strategy_components):
        """Teste la sélection avec un historique vide."""
        _, strategy, agents, pm_agent, _, _, empty_history = delegating_strategy_components
        # Sans désignation, devrait retourner l'agent par défaut (PM)
        selected_agent = await strategy.next(agents, empty_history)
        assert selected_agent == pm_agent

    async def test_next_with_designation(self, delegating_strategy_components):
        """Teste la sélection avec une désignation explicite."""
        state, strategy, agents, _, pl_agent, _, empty_history = delegating_strategy_components
        # Désigner explicitement l'agent PL
        state.designate_next_agent("PropositionalLogicAgent")
        
        # Devrait sélectionner l'agent PL
        selected_agent = await strategy.next(agents, empty_history)
        assert selected_agent == pl_agent
        
        # La désignation devrait avoir été consommée
        assert state._next_agent_designated is None

    async def test_next_with_invalid_designation(self, delegating_strategy_components):
        """Teste la sélection avec une désignation invalide."""
        state, strategy, agents, pm_agent, _, _, empty_history = delegating_strategy_components
        # Désigner un agent qui n'existe pas
        state.designate_next_agent("NonExistentAgent")
        
        # Devrait retourner l'agent par défaut (PM)
        selected_agent = await strategy.next(agents, empty_history)
        assert selected_agent == pm_agent
        
        # La désignation devrait avoir été consommée
        assert state._next_agent_designated is None

    async def test_next_after_user_message(self, delegating_strategy_components):
        """Teste la sélection après un message utilisateur."""
        _, strategy, agents, pm_agent, _, _, _ = delegating_strategy_components
        # Créer un message utilisateur
        user_message = MagicMock(spec=ChatMessageContent)
        user_message.role = AuthorRole.USER
        user_message.name = "User"
        
        history = [user_message]
        
        # Devrait sélectionner l'agent par défaut (PM)
        selected_agent = await strategy.next(agents, history)
        assert selected_agent == pm_agent

    async def test_next_after_assistant_message(self, delegating_strategy_components):
        """Teste la sélection après un message assistant."""
        _, strategy, agents, pm_agent, _, _, _ = delegating_strategy_components
        # Créer un message assistant (non PM)
        assistant_message = MagicMock(spec=ChatMessageContent)
        assistant_message.role = AuthorRole.ASSISTANT
        assistant_message.name = "InformalAnalysisAgent"
        
        history = [assistant_message]
        
        # Devrait retourner au PM
        selected_agent = await strategy.next(agents, history)
        assert selected_agent == pm_agent

    async def test_reset(self, delegating_strategy_components):
        """Teste la réinitialisation de la stratégie."""
        state, strategy, _, _, _, _, _ = delegating_strategy_components
        # Désigner un agent
        state.designate_next_agent("PropositionalLogicAgent")
        
        # Réinitialiser
        await strategy.reset()
        
        # La désignation devrait avoir été consommée
        assert state._next_agent_designated is None


class TestBalancedParticipationStrategy:
    """Tests pour la classe BalancedParticipationStrategy."""

    @pytest.fixture
    def balanced_strategy_components(self):
        """Fixture pour initialiser les composants de test."""
        state = RhetoricalAnalysisState("Texte de test pour l'analyse rhétorique.")
        
        pm_agent = MagicMock(spec=Agent)
        pm_agent.name = "ProjectManagerAgent"
        
        pl_agent = MagicMock(spec=Agent)
        pl_agent.name = "PropositionalLogicAgent"
        
        informal_agent = MagicMock(spec=Agent)
        informal_agent.name = "InformalAnalysisAgent"
        
        agents = [pm_agent, pl_agent, informal_agent]
        strategy = BalancedParticipationStrategy(agents, state)
        empty_history = []
        return state, strategy, agents, pm_agent, pl_agent, informal_agent, empty_history


    async def test_initialization_default(self, balanced_strategy_components):
        """Teste l'initialisation correcte de la stratégie avec configuration par défaut."""
        state, strategy, _, _, _, _, _ = balanced_strategy_components
        assert strategy._analysis_state == state
        assert strategy._default_agent_name == "ProjectManagerAgent"
        assert len(strategy._agents_map) == 3
        assert "ProjectManagerAgent" in strategy._agents_map
        assert "PropositionalLogicAgent" in strategy._agents_map
        assert "InformalAnalysisAgent" in strategy._agents_map
        
        # Vérifier que les compteurs sont initialisés à zéro
        assert strategy._total_turns == 0
        for agent_name in strategy._participation_counts:
            assert strategy._participation_counts[agent_name] == 0
            assert strategy._last_selected[agent_name] == 0
            assert strategy._imbalance_budget[agent_name] == 0.0
        
        # Vérifier la distribution des participations cibles (PM devrait avoir une part plus importante)
        assert strategy._target_participation["ProjectManagerAgent"] > strategy._target_participation["PropositionalLogicAgent"]
        assert strategy._target_participation["ProjectManagerAgent"] > strategy._target_participation["InformalAnalysisAgent"]
        
        # Vérifier que la somme des participations cibles est égale à 1.0
        total_participation = sum(strategy._target_participation.values())
        assert abs(total_participation - 1.0) < 1e-9 # Utiliser une tolérance pour les flottants

    async def test_initialization_custom(self, balanced_strategy_components):
        """Teste l'initialisation avec une configuration personnalisée."""
        state, _, agents, _, _, _, _ = balanced_strategy_components
        # Définir des participations cibles personnalisées
        custom_targets = {
            "ProjectManagerAgent": 0.5,
            "PropositionalLogicAgent": 0.3,
            "InformalAnalysisAgent": 0.2
        }
        
        # Créer une stratégie avec configuration personnalisée
        custom_strategy = BalancedParticipationStrategy(
            agents,
            state,
            default_agent_name="PropositionalLogicAgent",
            target_participation=custom_targets
        )
        
        # Vérifier la configuration
        assert custom_strategy._default_agent_name == "PropositionalLogicAgent"
        assert custom_strategy._target_participation["ProjectManagerAgent"] == 0.5
        assert custom_strategy._target_participation["PropositionalLogicAgent"] == 0.3
        assert custom_strategy._target_participation["InformalAnalysisAgent"] == 0.2

    async def test_next_with_designation(self, balanced_strategy_components):
        """Teste que la stratégie respecte les désignations explicites."""
        state, strategy, agents, _, pl_agent, _, empty_history = balanced_strategy_components
        # Désigner explicitement l'agent PL
        state.designate_next_agent("PropositionalLogicAgent")
        
        # Devrait sélectionner l'agent PL
        selected_agent = await strategy.next(agents, empty_history)
        assert selected_agent == pl_agent
        
        # La désignation devrait avoir été consommée
        assert state._next_agent_designated is None
        
        # Vérifier que les compteurs ont été mis à jour
        assert strategy._participation_counts["PropositionalLogicAgent"] == 1
        assert strategy._total_turns == 1

    async def test_next_with_invalid_designation(self, balanced_strategy_components):
        """Teste la sélection avec une désignation invalide."""
        state, strategy, agents, pm_agent, _, _, empty_history = balanced_strategy_components
        # Désigner un agent qui n'existe pas
        state.designate_next_agent("NonExistentAgent")
        
        # Devrait retourner l'agent par défaut (PM)
        selected_agent = await strategy.next(agents, empty_history)
        assert selected_agent == pm_agent
        
        # La désignation devrait avoir été consommée
        assert state._next_agent_designated is None
        
        # Vérifier que les compteurs ont été mis à jour pour l'agent par défaut
        assert strategy._participation_counts["ProjectManagerAgent"] == 1

    async def test_balanced_participation(self, balanced_strategy_components):
        """Teste que la stratégie équilibre effectivement la participation des agents."""
        _, strategy, agents, _, _, _, empty_history = balanced_strategy_components
        # Simuler plusieurs tours sans désignation explicite
        participation_counts = {"ProjectManagerAgent": 0, "PropositionalLogicAgent": 0, "InformalAnalysisAgent": 0}
        
        # Exécuter 30 tours pour avoir un échantillon significatif
        for _ in range(30):
            selected_agent = await strategy.next(agents, empty_history)
            participation_counts[selected_agent.name] += 1
        
        # Vérifier que tous les agents ont participé
        for agent_name in participation_counts:
            assert participation_counts[agent_name] > 0, f"L'agent {agent_name} n'a pas participé"
        
        # Vérifier que les taux de participation sont proches des cibles
        total_turns = sum(participation_counts.values())
        for agent_name, count in participation_counts.items():
            actual_rate = count / total_turns
            target_rate = strategy._target_participation[agent_name]
            # Tolérance de 20% pour tenir compte de la variabilité statistique
            assert abs(actual_rate - target_rate) <= 0.2, f"Taux de participation pour {agent_name}: {actual_rate} vs cible {target_rate}"
        
        # Vérifier que les compteurs internes correspondent aux compteurs que nous avons suivis
        for agent_name in participation_counts:
            assert strategy._participation_counts[agent_name] == participation_counts[agent_name]
        
        assert strategy._total_turns == total_turns

    async def test_imbalance_budget_adjustment(self, balanced_strategy_components):
        """Teste que la stratégie gère correctement le budget de déséquilibre."""
        state, strategy, agents, _, pl_agent, _, empty_history = balanced_strategy_components
        # Désigner explicitement le même agent plusieurs fois
        for _ in range(5):
            state.designate_next_agent("PropositionalLogicAgent")
            await strategy.next(agents, empty_history)
        
        # Vérifier que le budget de déséquilibre a été ajusté pour les autres agents
        assert strategy._imbalance_budget["ProjectManagerAgent"] > 0
        assert strategy._imbalance_budget["InformalAnalysisAgent"] > 0
        
        # Le budget de l'agent désigné devrait être réduit
        assert strategy._imbalance_budget["PropositionalLogicAgent"] == 0
        
        # Maintenant, laisser la stratégie équilibrer naturellement
        # Les agents avec un budget plus élevé devraient être sélectionnés en priorité
        selected_agent = await strategy.next(agents, empty_history)
        assert selected_agent != pl_agent, "L'agent surreprésenté ne devrait pas être sélectionné immédiatement après"

    async def test_reset(self, balanced_strategy_components):
        """Teste la réinitialisation de la stratégie."""
        state, strategy, agents, _, _, _, empty_history = balanced_strategy_components
        # Simuler quelques tours
        for _ in range(5):
            await strategy.next(agents, empty_history)
        
        # Vérifier que les compteurs ont été incrémentés
        assert strategy._total_turns == 5
        total_participations = sum(strategy._participation_counts.values())
        assert total_participations == 5
        
        # Désigner un agent pour le prochain tour
        state.designate_next_agent("PropositionalLogicAgent")
        
        # Réinitialiser
        await strategy.reset()
        
        # Vérifier que tous les compteurs ont été réinitialisés
        assert strategy._total_turns == 0
        for agent_name in strategy._participation_counts:
            assert strategy._participation_counts[agent_name] == 0
            assert strategy._last_selected[agent_name] == 0
            assert strategy._imbalance_budget[agent_name] == 0.0
        
        # La désignation devrait avoir été consommée
        assert state._next_agent_designated is None


if __name__ == '__main__':
    unittest.main()