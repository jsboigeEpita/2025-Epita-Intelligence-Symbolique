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

import pytest
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
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
        chat_service = OpenAIChatCompletion(
            service_id="gpt-5-mini", ai_model_id="gpt-5-mini"
        )
        k.add_service(chat_service)
        return k
    except Exception as e:
        pytest.fail(f"Erreur configuration kernel: {e}")


@pytest.fixture(scope="module")
def sherlock_agent(kernel):
    """Fixture pour l'agent Sherlock JTMS."""
    settings = AppSettings()
    return SherlockJTMSAgent(
        kernel=kernel, settings=settings, agent_name="Sherlock_Test_Real"
    )


# watson_agent/group_chat fixtures et les tests watson retirés avec le bras
# mort watson (#2122 A4) — l'agent Watson et le hub n'existent plus.


# --- Tests d'import et de structure ---


def test_imports_jtms_reels():
    """Vérifie les imports essentiels du système JTMS."""
    try:
        from argumentation_analysis.services.jtms_service import JTMSService
        from argumentation_analysis.plugins.semantic_kernel.jtms_plugin import (
            JTMSSemanticKernelPlugin,
        )
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


@pytest.mark.requires_api
def test_interaction_sherlock_reelle(sherlock_agent):
    """Teste une interaction de base avec l'agent Sherlock."""

    async def _async_test():
        contexte_test = "ENQUÊTE TEST: Objet manquant. INDICES: Porte ouverte."
        result = await sherlock_agent.formulate_hypothesis(context=contexte_test)
        assert result and not result.get(
            "error"
        ), f"Sherlock a retourné une erreur: {result}"
        assert result.get("confidence", 0) > 0, "La confiance de Sherlock est nulle."

    asyncio.run(_async_test())
