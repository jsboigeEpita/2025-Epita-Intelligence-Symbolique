#!/usr/bin/env python3
"""
TEST DE RÉALITÉ PURE - AUCUN MENSONGE
====================================

Ce script teste SEULEMENT ce qui existe vraiment.
AUCUNE simulation, AUCUN mensonge, AUCUNE trace factice.
Si ça marche pas, ça marche pas. Point.
"""

# === HEADER AUTO_ENV ===
import os
import sys

# Activation de l'environnement automatique AVANT tout import
try:
    from scripts.auto_env import ensure_environment
    ensure_environment()
    print("✅ Environnement auto_env activé")
except ImportError:
    print("⚠️ Auto_env non disponible, environnement non activé automatiquement")
except Exception as e:
    print(f"⚠️ Erreur activation auto_env: {e}")

# === IMPORTS PRINCIPAUX ===
import logging
import asyncio
from datetime import datetime

import pytest
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
from argumentation_analysis.agents.watson_jtms_agent import WatsonJTMSAgent
from argumentation_analysis.orchestration.group_chat import GroupChatOrchestration
from argumentation_analysis.config.settings import AppSettings

# Configuration de base
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Fixtures pour l'injection de dépendances ---

@pytest.fixture(scope="module")
def kernel():
    """Fixture pour le kernel Semantic Kernel."""
    try:
        k = Kernel()
        chat_service = OpenAIChatCompletion(service_id="gpt-4o-mini", ai_model_id="gpt-4o-mini")
        k.add_service(chat_service)
        return k
    except Exception as e:
        pytest.fail(f"Erreur configuration kernel: {e}")

@pytest.fixture(scope="module")
def sherlock_agent(kernel):
    """Fixture pour l'agent Sherlock JTMS."""
    settings = AppSettings()
    return SherlockJTMSAgent(kernel=kernel, settings=settings, agent_name="Sherlock_Test_Real")

@pytest.fixture(scope="module")
def watson_agent(kernel):
    """Fixture pour l'agent Watson JTMS."""
    return WatsonJTMSAgent(kernel=kernel, agent_name="Watson_Test_Real")

@pytest.fixture
def group_chat(sherlock_agent, watson_agent):
    """Fixture pour une session de GroupChat."""
    gc = GroupChatOrchestration()
    session_id = f"test_real_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    agents_dict = {"sherlock": sherlock_agent, "watson": watson_agent}
    gc.initialize_session(session_id, agents_dict)
    return gc

# --- Tests d'import et de structure ---

def test_imports_jtms_reels():
    """Vérifie les imports essentiels du système JTMS."""
    try:
        from argumentation_analysis.services.jtms_service import JTMSService
        from argumentation_analysis.plugins.semantic_kernel.jtms_plugin import JTMSSemanticKernelPlugin
        from argumentation_analysis.api.jtms_models import CreateBeliefRequest
        
        assert JTMSService is not None
        assert JTMSSemanticKernelPlugin is not None
        assert CreateBeliefRequest is not None
    except ImportError as e:
        pytest.fail(f"Échec d'un import JTMS critique: {e}")

def test_existence_fichiers_reels():
    """Vérifie l'existence des fichiers de code source importants."""
    fichiers_importants = [
        "argumentation_analysis/services/jtms_service.py",
        "argumentation_analysis/agents/sherlock_jtms_agent.py",
        "argumentation_analysis/plugins/semantic_kernel/jtms_plugin.py",
    ]
    for fichier in fichiers_importants:
        assert os.path.exists(fichier), f"Le fichier {fichier} est manquant."

def test_interface_web_reelle():
    """Vérifie la présence de l'application Flask et de ses routes."""
    try:
        from interface_web.app import app
        assert app is not None
        assert len(app.routes) > 0, "Aucune route Starlette n'a été trouvée."
    except (ImportError, AssertionError) as e:
        pytest.fail(f"Test de l'interface web a échoué: {e}")

# --- Tests d'orchestration asynchrones ---

def test_interaction_sherlock_reelle(sherlock_agent):
    """Teste une interaction de base avec l'agent Sherlock."""
    async def _async_test():
        contexte_test = "ENQUÊTE TEST: Objet manquant. INDICES: Porte ouverte."
        result = await sherlock_agent.formulate_hypothesis(context=contexte_test)
        assert result and not result.get('error'), f"Sherlock a retourné une erreur: {result}"
        assert result.get('confidence', 0) > 0, "La confiance de Sherlock est nulle."

    asyncio.run(_async_test())

def test_validation_watson_reelle(watson_agent):
    """Teste une interaction de base avec l'agent Watson."""
    async def _async_test():
        validation_chain = [{"step": 1, "proposition": "Porte ouverte", "evidence": "confirmed"}]
        # Correction: Ajout de la croyance au JTMS de Watson avant la validation
        for step in validation_chain:
            proposition = step.get("proposition")
            if proposition and step.get("evidence") == "confirmed":
                watson_agent.add_belief(proposition, "TRUE")
                logger.info(f"Croyance '{proposition}' ajoutée au JTMS de Watson pour le test.")

        result = await watson_agent.validate_reasoning_chain(validation_chain)
        assert result and not result.get('error'), f"Watson a retourné une erreur: {result}"
        assert result.get('confidence', 0) > 0, "La confiance de Watson est nulle."

    asyncio.run(_async_test())

def test_collaboration_orchestration_reelle(group_chat, sherlock_agent, watson_agent):
    """Teste un cycle de collaboration simple entre Sherlock et Watson."""
    async def _async_test():
        # Sherlock formule une hypothèse
        sherlock_result = await sherlock_agent.formulate_hypothesis(context="Test collab")
        group_chat.add_message("sherlock", "Hypothèse initiale", sherlock_result)

        # Watson valide la chaîne
        validation_chain = [{"step": 1, "proposition": "Hypothèse de Sherlock", "evidence": "proposed"}]
        watson_result = await watson_agent.validate_reasoning_chain(validation_chain)
        group_chat.add_message("watson", "Validation de l'hypothèse", watson_result)

        summary = group_chat.get_conversation_summary()
        assert summary.get('total_messages', 0) >= 2, "La collaboration n'a pas eu lieu (messages < 2)."

    asyncio.run(_async_test())