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
@pytest.mark.jvm_test
@pytest.mark.asyncio
async def test_agent_initialization_simplified(tweety_bridge_fixture):
    """
    Test d'initialisation simplifié pour valider la configuration de base
    sans la complexité de la fixture de classe et du patching.
    Utilise l'injection de dépendances pour TweetyBridge.
    """
    print("\n--- Démarrage du test d'initialisation simplifié ---")

    # 1. Initialisation du Kernel
    kernel = Kernel()
    llm_service_id = "test_service"
    
    # 2. Utilisation de la fixture TweetyBridge
    tweety_bridge = tweety_bridge_fixture
    tweety_available = tweety_bridge.initializer.is_jvm_ready()
    assert tweety_available, "La JVM de TweetyBridge devrait être prête via la fixture."
    print(f"✅ TweetyBridge est prêt (JVM démarrée par la fixture: {tweety_available})")

    # 3. Initialisation de l'agent avec injection de dépendance
    agent = FOLLogicAgent(kernel, tweety_bridge=tweety_bridge, service_id=llm_service_id)
    assert agent is not None
    assert agent.tweety_bridge is tweety_bridge
    print("✅ Agent FOLLogicAgent initialisé")

    # Le reste du test peut être décommenté si un service LLM est disponible
    # pour une validation plus complète.

    print("--- Test d'initialisation simplifié terminé avec succès ---")


# Configuration des marqueurs pytest pour cette classe
pytestmark = [
    pytest.mark.authentic,  # Marqueur pour tests authentiques
    pytest.mark.phase5,     # Marqueur Phase 5
    pytest.mark.no_mocks,   # Marqueur sans mocks
]