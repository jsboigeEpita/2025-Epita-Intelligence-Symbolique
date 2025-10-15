# -*- coding: utf-8 -*-
# tests/agents/core/logic/test_fol_logic_agent_authentic.py
"""
Tests unitaires authentiques pour la classe FOLLogicAgent.
Phase 5 - Élimination complète des mocks - Version authentique
"""

import pytest
from semantic_kernel import Kernel
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent


@pytest.mark.jvm_test
@pytest.mark.asyncio
async def test_agent_initialization_simplified(tweety_bridge_fixture):
    """
    Test d'initialisation simplifié pour valider la configuration de base.
    Utilise l'injection de dépendances pour TweetyBridge.
    """
    kernel = Kernel()
    llm_service_id = "test_service"

    tweety_bridge = tweety_bridge_fixture
    tweety_available = tweety_bridge.initializer.is_jvm_ready()
    assert tweety_available, "La JVM de TweetyBridge devrait être prête via la fixture."

    agent = FOLLogicAgent(
        kernel, tweety_bridge=tweety_bridge, service_id=llm_service_id
    )
    assert agent is not None
    assert agent.tweety_bridge is tweety_bridge
