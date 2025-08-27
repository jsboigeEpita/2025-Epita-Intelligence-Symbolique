# -*- coding: utf-8 -*-
"""Tests unitaires pour les composants core du système d'analyse rhétorique."""

import pytest
import json
from types import SimpleNamespace
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from argumentation_analysis.core.strategies import SimpleTerminationStrategy, BalancedParticipationStrategy

# Fixture pour l'état, utilisée par les autres fixtures et tests
@pytest.fixture
def rhetorical_state():
    """Fixture pour fournir une instance fraîche de RhetoricalAnalysisState."""
    return RhetoricalAnalysisState("Texte initial pour le test.")

# --- Tests pour RhetoricalAnalysisState ---

@pytest.mark.no_jvm_session
def test_rhetorical_analysis_state_initialization(rhetorical_state):
    """Teste l'initialisation correcte de RhetoricalAnalysisState."""
    assert rhetorical_state.raw_text == "Texte initial pour le test."
    assert isinstance(rhetorical_state.analysis_tasks, dict)
    assert isinstance(rhetorical_state.identified_arguments, dict)
    assert isinstance(rhetorical_state.identified_fallacies, dict)
    assert rhetorical_state.final_conclusion is None

@pytest.mark.no_jvm_session
def test_rhetorical_analysis_state_manipulation(rhetorical_state):
    """Teste les méthodes de manipulation de RhetoricalAnalysisState."""
    # CORRECTION: La méthode est `add_argument`.
    # CORRECTION: La méthode est `add_argument` et ne prend qu'un argument de description
    rhetorical_state.add_argument("Ceci est un premier argument.")
    assert "arg_1" in rhetorical_state.identified_arguments
    assert rhetorical_state.identified_arguments["arg_1"] == "Ceci est un premier argument."

    rhetorical_state.designate_next_agent("AnalystAgent")
    # CORRECTION: Il n'y a pas de `get_next_agent_to_act`. On vérifie via la consommation.
    assert rhetorical_state.consume_next_agent_designation() == "AnalystAgent"
    assert rhetorical_state.consume_next_agent_designation() is None

# --- Tests pour StateManagerPlugin ---

@pytest.fixture
def state_manager_plugin(rhetorical_state):
    """Fixture pour fournir une instance de StateManagerPlugin."""
    return StateManagerPlugin(rhetorical_state)

@pytest.mark.no_jvm_session
def test_state_manager_plugin_read(state_manager_plugin):
    """Teste que le StateManagerPlugin peut lire correctement depuis l'état."""
    # CORRECTION: La méthode pour lire est `get_current_state_snapshot`.
    state_json = state_manager_plugin.get_current_state_snapshot(summarize=False)
    state_data = json.loads(state_json)
    assert state_data["raw_text"] == "Texte initial pour le test."

@pytest.mark.no_jvm_session
def test_state_manager_plugin_write(state_manager_plugin):
    """Teste que le StateManagerPlugin peut écrire correctement dans l'état."""
    # CORRECTION: La méthode `add_identified_argument` ne prend qu'un seul argument.
    state_manager_plugin.add_identified_argument("Argument ajouté via le plugin.")
    assert "arg_1" in state_manager_plugin._state.identified_arguments
    assert state_manager_plugin._state.identified_arguments["arg_1"] == "Argument ajouté via le plugin."

# --- Tests pour Strategies ---

@pytest.mark.asyncio
@pytest.mark.no_jvm_session
async def test_simple_termination_strategy(rhetorical_state):
    """Teste la stratégie SimpleTerminationStrategy."""
    strategy = SimpleTerminationStrategy(rhetorical_state, max_steps=3)
    
    # CORRECTION: La méthode should_terminate est `async` et doit être `await`.
    # Les arguments sont (agent, history).
    assert await strategy.should_terminate(None, []) is False # Tour 1
    assert await strategy.should_terminate(None, []) is False # Tour 2
    assert await strategy.should_terminate(None, []) is True  # Tour 3

@pytest.mark.asyncio
@pytest.mark.no_jvm_session
async def test_balanced_participation_strategy(rhetorical_state):
    """Teste la stratégie BalancedParticipationStrategy."""
    # CORRECTION: La stratégie attend des objets Agent (avec un .name), pas des strings.
    mock_agents = [
        SimpleNamespace(name="Agent_A"),
        SimpleNamespace(name="Agent_B"),
        SimpleNamespace(name="Agent_C")
    ]
    strategy = BalancedParticipationStrategy(mock_agents, rhetorical_state, "Agent_A")
    
    # CORRECTION: La méthode `next` est `async`.
    # La stratégie maintient l'état de participation en interne.
    # On vérifie que les agents sont sélectionnés à tour de rôle (approximation).
    # Premier appel, pas d'historique, devrait retourner l'agent par défaut.
    next_agent_1 = await strategy.next(mock_agents, [])
    assert next_agent_1.name == "Agent_A"

    # Deuxième appel
    next_agent_2 = await strategy.next(mock_agents, [])
    assert next_agent_2.name != "Agent_A" # Devrait être B ou C

    # Troisième appel
    next_agent_3 = await strategy.next(mock_agents, [])
    assert next_agent_3.name not in ["Agent_A", next_agent_2.name]
