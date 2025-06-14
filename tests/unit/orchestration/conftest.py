#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration pytest locale pour les tests d'orchestration.
Évite les dépendances JPype du conftest.py global.
"""

import project_core.core_from_scripts.auto_env

import jpype
import jpype.imports

import pytest
import sys
import os
import logging
from pathlib import Path

# Configuration du logging pour les tests
logging.basicConfig(level=logging.WARNING)

# Ajouter le répertoire racine au PYTHONPATH
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


# @pytest.fixture(scope="session")
# def jvm_session_manager():
#     """
#     [DÉSACTIVÉ] Conflit avec la gestion globale de la JVM dans tests/conftest.py.
#     La gestion de la JVM doit être centralisée pour éviter les crashs.
#     Les tests doivent utiliser les fixtures JVM globales (ex: 'integration_jvm').
#
#     Initialise la JVM une fois pour toute la session de test et l'arrête à la fin.
#
#     Utilise une portée 'session' pour éviter l'erreur 'OSError: JVM cannot be restarted'
#     car JPype ne permet qu'un seul cycle de vie JVM par processus Python.
#
#     Cette fixture prend le contrôle exclusif de la JVM pendant toute la session.
#     """
#     import jpype
#     import logging
#     from argumentation_analysis.core.jvm_setup import (
#         initialize_jvm, shutdown_jvm_if_needed,
#         set_session_fixture_owns_jvm, is_session_fixture_owns_jvm
#     )
#
#     logger = logging.getLogger("tests.jvm_session_manager")
#
#     # Vérifier l'état initial de la JVM
#     logger.info(f"JVM_SESSION_MANAGER: Début de session. JVM déjà démarrée: {jpype.isJVMStarted()}")
#     logger.info(f"JVM_SESSION_MANAGER: Session fixture owns JVM initial: {is_session_fixture_owns_jvm()}")
#
#     # PRENDRE LE CONTRÔLE EXCLUSIF DE LA JVM POUR CETTE SESSION
#     set_session_fixture_owns_jvm(True)
#     logger.info("JVM_SESSION_MANAGER: Prise de contrôle exclusif de la JVM par la fixture de session")
#
#     # Démarrer la JVM seulement si elle ne l'est pas déjà
#     jvm_was_started_by_us = False
#     if not jpype.isJVMStarted():
#         logger.info("JVM_SESSION_MANAGER: Démarrage de la JVM pour la session de tests")
#         success = initialize_jvm()
#         if not success:
#             logger.error("JVM_SESSION_MANAGER: Échec du démarrage de la JVM")
#             set_session_fixture_owns_jvm(False)  # Libérer le contrôle en cas d'échec
#             raise RuntimeError("Impossible de démarrer la JVM pour les tests")
#         jvm_was_started_by_us = True
#         logger.info("JVM_SESSION_MANAGER: JVM démarrée avec succès par la fixture de session")
#     else:
#         logger.info("JVM_SESSION_MANAGER: JVM déjà démarrée, prise de contrôle par la fixture de session")
#
#     try:
#         yield
#     finally:
#         logger.info("JVM_SESSION_MANAGER: Fin de session - nettoyage de la JVM")
#         try:
#             # Arrêter la JVM seulement si nous la contrôlons et qu'elle est démarrée
#             if jpype.isJVMStarted():
#                 logger.info("JVM_SESSION_MANAGER: Arrêt de la JVM à la fin de la session")
#                 shutdown_jvm_if_needed()
#             else:
#                 logger.info("JVM_SESSION_MANAGER: JVM déjà arrêtée")
#         finally:
#             # Toujours libérer le contrôle de la JVM
#             set_session_fixture_owns_jvm(False)
#             logger.info("JVM_SESSION_MANAGER: Libération du contrôle de la JVM")

@pytest.fixture
def llm_service():
    """Crée une instance réelle du service LLM pour les tests d'intégration."""
    from argumentation_analysis.core.llm_service import create_llm_service
    
    # Assurez-vous que votre fichier .env est correctement configuré
    # avec OPENAI_API_KEY et OPENAI_CHAT_MODEL_ID
    try:
        service = create_llm_service(
            service_id="real_test_llm_service",
            force_mock=False
        )
        return service
    except Exception as e:
        pytest.skip(f"Impossible de créer le service LLM réel : {e}")

@pytest.fixture
def sample_text():
    """Texte d'exemple standard pour les tests."""
    return "Ceci est un argument de test pour l'analyse d'orchestration."

# Markers pour les tests
def pytest_configure(config):
    """Configuration des markers pytest."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")