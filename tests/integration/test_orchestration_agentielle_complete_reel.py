#!/usr/bin/env python3
"""
TEST ORCHESTRATION AGENTIELLE RÉELLE - AUCUN MOCK
Test des couches d'orchestration complètes avec agents JTMS réels

Architecture testée :
- SherlockJTMSAgent + WatsonJTMSAgent (agents réels)
- CluedoExtendedOrchestrator (orchestration)  
- GroupChatOrchestration (service)
- ServiceManager (coordination)
"""

import asyncio
import sys
import os
import logging
from pathlib import Path
from datetime import datetime

# Configuration auto-env
sys.path.insert(0, str(Path(__file__).parent))

# Imports des vrais agents
from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
from argumentation_analysis.agents.watson_jtms_agent import WatsonJTMSAgent

# Imports des orchestrateurs réels
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
    CyclicSelectionStrategy, 
    OracleTerminationStrategy,
    Agent
)
from argumentation_analysis.orchestration.group_chat import GroupChatOrchestration
from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager

# Semantic Kernel
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

import pytest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture(scope="module")
def kernel():
    """Fixture pour le kernel Semantic Kernel."""
    try:
        k = Kernel()
        chat_service = OpenAIChatCompletion(
            service_id="gpt-4o-mini",
            ai_model_id="gpt-4o-mini"
        )
        k.add_service(chat_service)
        logger.info("✅ Kernel Semantic Kernel configuré")
        return k
    except Exception as e:
        pytest.fail(f"❌ Erreur configuration kernel: {e}")

@pytest.fixture(scope="module")
def sherlock_agent(kernel):
    """Fixture pour l'agent Sherlock JTMS."""
    try:
        agent = SherlockJTMSAgent(
            kernel=kernel,
            agent_name="Sherlock_JTMS_Real",
            system_prompt="""Vous êtes Sherlock Holmes avec JTMS intégré..."""
        )
        logger.info("✅ Agent Sherlock initialisé")
        return agent
    except Exception as e:
        pytest.fail(f"❌ Erreur initialisation Sherlock: {e}")

@pytest.fixture(scope="module")
def watson_agent(kernel):
    """Fixture pour l'agent Watson JTMS."""
    try:
        agent = WatsonJTMSAgent(
            kernel=kernel,
            agent_name="Watson_JTMS_Real",
            system_prompt="""Vous êtes Watson avec capacités de validation formelle JTMS..."""
        )
        logger.info("✅ Agent Watson initialisé")
        return agent
    except Exception as e:
        pytest.fail(f"❌ Erreur initialisation Watson: {e}")

@pytest.fixture
def group_chat(sherlock_agent, watson_agent):
    """Fixture pour le GroupChat."""
    gc = GroupChatOrchestration()
    session_id = f"test_real_orchestration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    agents_dict = {"sherlock": sherlock_agent, "watson": watson_agent}
    gc.initialize_session(session_id, agents_dict)
    return gc

@pytest.mark.asyncio
async def test_sherlock_jtms_hypotheses(sherlock_agent, group_chat):
    """Test des capacités JTMS de Sherlock."""
    logger.info("🧪 TEST: Hypothèses JTMS Sherlock")
    enquete_context = "ENQUÊTE: Vol de diamant au musée..."
    
    result = await sherlock_agent.formulate_hypothesis(context=enquete_context)
    
    group_chat.add_message(
        agent_id="sherlock",
        message=f"Hypothèse formulée: {result.get('hypothesis', 'N/A')}",
        analysis_results=result
    )
    
    print_results("SHERLOCK JTMS", result)
    assert result.get('confidence', 0) > 0.3, "La confiance de Sherlock est trop basse."
    assert result.get('jtms_validity', False), "La validité JTMS de Sherlock est fausse."

@pytest.mark.asyncio
async def test_watson_jtms_validation(watson_agent, group_chat):
    """Test des capacités JTMS de Watson."""
    logger.info("🧪 TEST: Validation JTMS Watson")
    validation_chain = [
        {"step": 1, "proposition": "Gardien absent", "evidence": "confirmed"},
        {"step": 2, "proposition": "Caméra sabotée", "evidence": "confirmed"},
        {"step": 3, "hypothesis": "Voleur connaît procédures", "hypothesis_id": "insider_knowledge"}
    ]
    
    validation_result = await watson_agent.validate_reasoning_chain(validation_chain)
    
    group_chat.add_message(
        agent_id="watson",
        message=f"Validation: {validation_result.get('chain_valid', False)}",
        analysis_results=validation_result
    )
    
    print_results("WATSON JTMS", validation_result)
    assert validation_result.get('chain_valid', False), "La chaîne de raisonnement de Watson est invalide."

@pytest.mark.asyncio
async def test_orchestration_collaborative(sherlock_agent, watson_agent, group_chat):
    """Test de l'orchestration collaborative complète."""
    logger.info("🧪 TEST: Orchestration Collaborative Sherlock-Watson")
    probleme_complexe = "CASE COMPLEXE: Fraude financière..."
    
    sherlock_result = await sherlock_agent.formulate_hypothesis(context=probleme_complexe)
    
    watson_validation = {}
    if sherlock_result.get('hypothesis_id'):
        watson_validation = await watson_agent.validate_hypothesis(
            hypothesis_id=sherlock_result.get('hypothesis_id', 'unknown_hypothesis'),
            hypothesis_data=sherlock_result
        )

    group_chat.add_message("sherlock", "Hypothèse sur fraude", sherlock_result)
    group_chat.add_message("watson", "Validation de l'hypothèse", watson_validation)
    
    summary = group_chat.get_conversation_summary()
    
    print_collaboration_results(sherlock_result, watson_validation, summary)
    
    assert sherlock_result.get('confidence', 0) > 0.3
    assert watson_validation.get('validation_result') != 'error'
    assert summary.get('total_messages', 0) >= 2

def print_results(title, data):
    """Helper pour afficher les résultats."""
    print(f"\n📋 RÉSULTAT {title}:")
    for key, value in data.items():
        print(f"  {key.capitalize()}: {value}")

def print_collaboration_results(sherlock_result, watson_validation, summary):
    """Helper pour afficher les résultats de collaboration."""
    print("\n🤝 RÉSULTAT ORCHESTRATION COLLABORATIVE:")
    print(f"  Sherlock confiance: {sherlock_result.get('confidence', 0):.2f}")
    print(f"  Watson validation: {watson_validation.get('validation_result', 'N/A')}")
    print(f"  Messages échangés: {summary.get('total_messages', 0)}")