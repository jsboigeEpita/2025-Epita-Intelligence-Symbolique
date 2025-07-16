# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_fol_logic_agent_authentic.py
"""
Tests unitaires authentiques pour la classe FOLLogicAgent.
Phase 5 - Élimination complète des mocks - Version authentique
"""

import unittest
import pytest
import asyncio
import os
import sys
from pathlib import Path

# Import du système d'auto-activation d'environnement
from argumentation_analysis.core import environment as auto_env

# Imports authentiques - vrai Semantic Kernel
from semantic_kernel import Kernel
from semantic_kernel.functions import KernelArguments

# Imports conditionnels pour les connecteurs LLM
try:
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
except ImportError:
    OpenAIChatCompletion = None

try:
    from semantic_kernel.connectors.ai.azure_open_ai import AzureOpenAIChatCompletion
except ImportError:
    try:
        from semantic_kernel.connectors.ai.azure_open_ai.azure_chat_completion import AzureOpenAIChatCompletion
    except ImportError:
        AzureOpenAIChatCompletion = None

# Imports du projet
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet, BeliefSet
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge


# Le test n'est plus marqué xfail. Le crash à la sortie a été résolu
# en désactivant l'appel à jpype.shutdownJVM() dans jvm_setup.py,
# qui est une opération notoirement instable.
@pytest.mark.asyncio
async def test_agent_initialization_simplified(jvm_session):
    """
    Test d'initialisation simplifié pour valider la configuration de base
    sans la complexité de la fixture de classe et du patching.
    """
    print("\n--- Démarrage du test d'initialisation simplifié ---")
    
    # 1. Initialisation du Kernel
    kernel = Kernel()
    llm_service_id = "test_service"
    llm_available = False
    # try:
    #     # Essai de configuration du service LLM (Azure ou OpenAI)
    #     azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    #     azure_api_key = os.getenv("AZRE_OPENAI_API_KEY")
    #     azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        
    #     if azure_endpoint and azure_api_key and AzureOpenAIChatCompletion:
    #         chat_service = AzureOpenAIChatCompletion(
    #             service_id=llm_service_id,
    #             deployment_name=azure_deployment,
    #             endpoint=azure_endpoint,
    #             api_key=azure_api_key
    #         )
    #         kernel.add_service(chat_service)
    #         llm_available = True
    #         print("✅ Service LLM Azure configuré")
    #     else:
    #         openai_api_key = os.getenv("OPENAI_API_KEY")
    #         if openai_api_key and OpenAIChatCompletion:
    #             chat_service = OpenAIChatCompletion(
    #                 service_id=llm_service_id, ai_model_id="gpt-4o-mini", api_key=openai_api_key
    #             )
    #             kernel.add_service(chat_service)
    #             llm_available = True
    #             print("✅ Service LLM OpenAI configuré")
    #         else:
    #             print("⚠️ Aucun service LLM disponible.")
    # except Exception as e:
    #     print(f"⚠️ Erreur lors de la configuration du LLM: {e}")

    # 2. Initialisation de TweetyBridge (en utilisant la fixture de session)
    try:
        tweety_bridge = TweetyBridge()
        tweety_available = tweety_bridge.is_jvm_ready()
        assert tweety_available, "La JVM de TweetyBridge n'est pas prête."
        print(f"✅ TweetyBridge est prêt (JVM démarrée par jvm_session: {tweety_available})")
    except Exception as e:
        pytest.fail(f"Échec de l'initialisation de TweetyBridge: {e}")

    # 3. Initialisation de l'agent
    agent = FOLLogicAgent(kernel, tweety_bridge=tweety_bridge, service_id=llm_service_id)
    assert agent is not None
    assert agent.tweety_bridge is tweety_bridge
    print("✅ Agent FOLLogicAgent initialisé")

    # # 4. Configuration de l'agent (si le LLM est disponible)
    # if llm_available:
    #     try:
    #         await agent.setup_agent_components(llm_service_id)
    #         print("✅ Composants de l'agent configurés avec succès")
    #     except Exception as e:
    #         pytest.fail(f"Échec de la configuration des composants de l'agent: {e}")
    # else:
    #     print("ℹ️ Configuration de l'agent sautée (pas de LLM).")

    print("--- Test d'initialisation simplifié terminé avec succès ---")


# Configuration des marqueurs pytest pour cette classe
pytestmark = [
    pytest.mark.authentic,  # Marqueur pour tests authentiques
    pytest.mark.phase5,     # Marqueur Phase 5
    pytest.mark.no_mocks,   # Marqueur sans mocks
]