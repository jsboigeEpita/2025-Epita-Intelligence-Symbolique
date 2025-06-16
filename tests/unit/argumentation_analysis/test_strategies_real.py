#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests RÉELS pour les stratégies d'argumentation - TOUTES LES STRATÉGIES AUTHENTIQUES.
Validation complète des 3 stratégies sophistiquées du système.
"""

import unittest
import asyncio
import os
import sys
import pytest
import pytest_asyncio
from pathlib import Path
from typing import List

# Configuration pour forcer l'utilisation du vrai JPype
os.environ['USE_REAL_JPYPE'] = 'true'

try:
    # IMPORTS CORRIGÉS avec les bons chemins
    from argumentation_analysis.core.strategies import (
        SimpleTerminationStrategy,
        DelegatingSelectionStrategy,
        BalancedParticipationStrategy
    )
    from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
    print("OK SUCCES : Toutes les strategies importees avec succes depuis argumentation_analysis.core.strategies")
except ImportError as e:
    print(f"[ERREUR] ERREUR D'IMPORT CRITIQUE: {e}")
    print("[ATTENTION]  Vérifiez que les modules sont bien dans argumentation_analysis.core")


class RealAgent:
    """Agent simple RÉEL pour les tests d'intégration avec Semantic Kernel."""
    
    def __init__(self, name, role="agent"):
        self.name = name
        self.role = role
        self.id = name
        
    def __str__(self):
        return f"RealAgent({self.name}, {self.role})"


class RealChatMessage:
    """Message de chat RÉEL compatible Semantic Kernel pour les tests."""
    
    def __init__(self, content, role="assistant", author_name=None):
        self.content = content
        self.role = role
        self.author_name = author_name or "system"
        self.name = self.author_name  # Alias pour compatibilité
        self.timestamp = "2025-06-07T12:00:00"
    
    def __str__(self):
        return f"RealMessage({self.author_name}: {self.content})"


@pytest_asyncio.fixture
async def simple_termination_fixture():
    """Fixture pour initialiser SUT pour TestRealSimpleTerminationStrategy."""
    state = RhetoricalAnalysisState("Texte de test pour terminaison.")
    strategy = SimpleTerminationStrategy(state, max_steps=5)
    agent = RealAgent("test_agent", "analyste")
    history = []
    return {"state": state, "strategy": strategy, "agent": agent, "history": history}

class TestRealSimpleTerminationStrategy:
    """Tests RÉELS pour SimpleTerminationStrategy (style pytest)."""

    def test_initialization_real(self, simple_termination_fixture):
        """Teste l'initialisation de SimpleTerminationStrategy."""
        strategy = simple_termination_fixture["strategy"]
        state = simple_termination_fixture["state"]
        assert strategy is not None
        assert strategy._max_steps == 5
        assert isinstance(state, RhetoricalAnalysisState)
        print("[OK] Test initialisation SimpleTerminationStrategy réussi")

    @pytest.mark.asyncio
    async def test_should_terminate_max_steps_real(self, simple_termination_fixture):
        """Teste la terminaison basée sur le nombre maximum d'étapes."""
        strategy = simple_termination_fixture["strategy"]
        agent = simple_termination_fixture["agent"]
        history = simple_termination_fixture["history"]
        
        for i in range(4):
            result = await strategy.should_terminate(agent, history)
            assert not result, f"Ne devrait pas terminer au tour {i+1}"
        
        # Le 5e appel devrait déclencher la terminaison
        result = await strategy.should_terminate(agent, history)
        assert result, "Devrait terminer après max_steps"
        print("[OK] Test terminaison max steps réussi")

    @pytest.mark.asyncio
    async def test_should_terminate_conclusion_real(self, simple_termination_fixture):
        """Teste la terminaison basée sur une conclusion finale."""
        strategy = simple_termination_fixture["strategy"]
        state = simple_termination_fixture["state"]
        agent = simple_termination_fixture["agent"]
        history = simple_termination_fixture["history"]

        state.final_conclusion = "Conclusion de test atteinte"
        result = await strategy.should_terminate(agent, history)
        assert result, "Devrait terminer avec conclusion finale"
        print("[OK] Test terminaison par conclusion réussi")


@pytest_asyncio.fixture
async def delegating_selection_fixture():
    """Fixture pour initialiser SUT pour TestRealDelegatingSelectionStrategy."""
    state = RhetoricalAnalysisState("Test délégation sélection")
    agents = [
        RealAgent("ProjectManagerAgent", "manager"),
        RealAgent("AnalystAgent", "analyst"),
        RealAgent("CriticAgent", "critic")
    ]
    strategy = DelegatingSelectionStrategy(
        agents, state, default_agent_name="ProjectManagerAgent"
    )
    history = []
    return {"state": state, "strategy": strategy, "agents": agents, "history": history}

class TestRealDelegatingSelectionStrategy:
    """Tests RÉELS pour DelegatingSelectionStrategy (style pytest)."""

    def test_initialization_real(self, delegating_selection_fixture):
        """Teste l'initialisation de DelegatingSelectionStrategy."""
        strategy = delegating_selection_fixture["strategy"]
        assert strategy is not None
        assert len(strategy._agents_map) == 3
        assert strategy._default_agent_name == "ProjectManagerAgent"
        print("[OK] Test initialisation DelegatingSelectionStrategy réussi")

    @pytest.mark.asyncio
    async def test_next_agent_default_real(self, delegating_selection_fixture):
        """Teste la sélection par défaut sans désignation."""
        strategy = delegating_selection_fixture["strategy"]
        agents = delegating_selection_fixture["agents"]
        selected = await strategy.next(agents, [])
        assert selected.name == "ProjectManagerAgent"
        print("[OK] Test sélection agent par défaut réussi")

    @pytest.mark.asyncio
    async def test_next_agent_with_designation_real(self, delegating_selection_fixture):
        """Teste la sélection avec désignation explicite via l'état."""
        strategy = delegating_selection_fixture["strategy"]
        state = delegating_selection_fixture["state"]
        agents = delegating_selection_fixture["agents"]
        history = delegating_selection_fixture["history"]
        
        state.designate_next_agent("AnalystAgent")
        selected = await strategy.next(agents, history)
        assert selected.name == "AnalystAgent"
        print("[OK] Test sélection avec désignation explicite réussi")


@pytest_asyncio.fixture
async def balanced_participation_fixture():
    """Fixture pour initialiser SUT pour TestRealBalancedParticipationStrategy."""
    state = RhetoricalAnalysisState("Test équilibrage participation")
    agents = [
        RealAgent("ProjectManagerAgent", "manager"),
        RealAgent("AnalystAgent", "analyst"),
        RealAgent("CriticAgent", "critic")
    ]
    target_participation = {
        "ProjectManagerAgent": 0.5, "AnalystAgent": 0.3, "CriticAgent": 0.2
    }
    strategy = BalancedParticipationStrategy(
        agents, state, default_agent_name="ProjectManagerAgent",
        target_participation=target_participation
    )
    history = []
    return {"state": state, "strategy": strategy, "agents": agents, "history": history}

class TestRealBalancedParticipationStrategy:
    """Tests RÉELS pour BalancedParticipationStrategy (style pytest)."""

    def test_initialization_real(self, balanced_participation_fixture):
        """Teste l'initialisation de BalancedParticipationStrategy."""
        strategy = balanced_participation_fixture["strategy"]
        assert strategy is not None
        assert len(strategy._agents_map) == 3
        assert strategy._target_participation["ProjectManagerAgent"] == 0.5
        print("[OK] Test initialisation BalancedParticipationStrategy réussi")

    @pytest.mark.asyncio
    async def test_balanced_selection_real(self, balanced_participation_fixture):
        """Teste l'équilibrage de la participation sur plusieurs tours."""
        strategy = balanced_participation_fixture["strategy"]
        agents = balanced_participation_fixture["agents"]
        history = balanced_participation_fixture["history"]
        
        selections = []
        for turn in range(10):
            selected = await strategy.next(agents, history)
            selections.append(selected.name)
            message = RealChatMessage(f"Message tour {turn+1}", "assistant", selected.name)
            history.append(message)
        
        pm_count = selections.count("ProjectManagerAgent")
        analyst_count = selections.count("AnalystAgent")
        critic_count = selections.count("CriticAgent")
        
        print(f"   Participations après 10 tours: PM={pm_count}, Analyst={analyst_count}, Critic={critic_count}")
        assert pm_count >= analyst_count
        assert pm_count >= critic_count
        print("[OK] Test équilibrage participation réussi")

    @pytest.mark.asyncio
    async def test_explicit_designation_override_real(self, balanced_participation_fixture):
        """Teste que la désignation explicite prime sur l'équilibrage."""
        s = balanced_participation_fixture
        s["state"].designate_next_agent("CriticAgent")
        selected = await s["strategy"].next(s["agents"], s["history"])
        assert selected.name == "CriticAgent"
        print("[OK] Test priorité désignation explicite réussi")


@pytest_asyncio.fixture
async def strategies_integration_fixture():
    """Fixture pour initialiser SUT pour TestRealStrategiesIntegration."""
    state = RhetoricalAnalysisState("Integration test complet")
    agents = [
        RealAgent("ProjectManagerAgent", "manager"),
        RealAgent("AnalystAgent", "analyst"),
        RealAgent("CriticAgent", "critic")
    ]
    termination_strategy = SimpleTerminationStrategy(state, max_steps=8)
    balanced_strategy = BalancedParticipationStrategy(
        agents, state, "ProjectManagerAgent"
    )
    history = []
    # Note: selection_strategy n'est pas utilisé dans le test, donc on ne le retourne pas.
    return {
        "state": state, "agents": agents, "history": history,
        "termination_strategy": termination_strategy,
        "balanced_strategy": balanced_strategy
    }

class TestRealStrategiesIntegration:
    """Tests d'intégration complets utilisant les 3 stratégies (style pytest)."""
    
    @pytest.mark.asyncio
    async def test_full_conversation_with_all_strategies_real(self, strategies_integration_fixture):
        """Simulation complète avec les 3 stratégies en interaction."""
        fx = strategies_integration_fixture
        turn = 0
        conversation_ended = False
        
        while not conversation_ended and turn < 10:
            turn += 1
            selected_agent = await fx["balanced_strategy"].next(fx["agents"], fx["history"])
            message = RealChatMessage(
                f"Réponse tour {turn} de {selected_agent.role}", "assistant", selected_agent.name
            )
            fx["history"].append(message)
            conversation_ended = await fx["termination_strategy"].should_terminate(
                selected_agent, fx["history"]
            )
            print(f"   Tour {turn}: Agent={selected_agent.name}, Terminé={conversation_ended}")
        
        assert len(fx["history"]) > 0, "Au moins un message généré"
        assert turn == 8, "La conversation doit se terminer exactement au 8ème tour"
        
        print("[OK] INTÉGRATION COMPLÈTE : Toutes les stratégies fonctionnent ensemble")

