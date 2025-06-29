#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration pytest locale pour les tests d'orchestration.
Évite les dépendances JPype du conftest.py global.
"""

import argumentation_analysis.core.environment

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


@pytest.fixture(scope="session")
def jvm_session_manager():
    """
    RÉACTIVÉ: Restaure la gestion de la JVM via une fixture de session pour les tests
    d'orchestration, afin de résoudre les crashs "access violation".

    Initialise la JVM une fois pour toute la session de test et l'arrête proprement à la fin.
    Utilise une portée 'session' pour éviter l'erreur 'OSError: JVM cannot be restarted'
    car JPype ne permet qu'un seul cycle de vie JVM par processus Python.

    Cette fixture prend le contrôle exclusif de la JVM pendant toute la session de test.
    """
    import jpype
    import logging
    from argumentation_analysis.core.jvm_setup import (
        initialize_jvm, shutdown_jvm, is_jvm_started, is_jvm_owned_by_session_fixture
    )

    logger = logging.getLogger("tests.jvm_session_manager")
    
    # Ne rien faire si la JVM est déjà gérée par une autre fixture de session
    if is_jvm_owned_by_session_fixture() and is_jvm_started():
        logger.info("JVM_SESSION_MANAGER: La JVM est déjà démarrée et gérée par une autre fixture. On ne fait rien.")
        yield
        return

    logger.info("="*20 + " Début Fixture Session JVM " + "="*20)
    logger.info(f"État initial -> Démarrée: {is_jvm_started()}, Gérée par session: {is_jvm_owned_by_session_fixture()}")

    # Démarrer la JVM si nécessaire, en déclarant que cette fixture en est propriétaire
    if not is_jvm_started():
        logger.info("JVM non démarrée. Démarrage par la fixture de session...")
        success = initialize_jvm(session_fixture_owns_jvm=True)
        if not success:
            logger.error("ÉCHEC CRITIQUE: Impossible de démarrer la JVM pour la session de tests.")
            raise RuntimeError("Impossible de démarrer la JVM pour les tests d'orchestration.")
        logger.info("JVM démarrée avec succès par la fixture de session.")
    else:
        logger.info("JVM déjà démarrée. La fixture de session en prend le contrôle (attention aux conflits).")
        # Il n'y a pas de fonction pour "prendre le contrôle" a posteriori,
        # l'initialisation au démarrage est la méthode privilégiée.
        # On assume que si on arrive ici, c'est ok.

    try:
        yield
    finally:
        logger.info("="*20 + " Fin Fixture Session JVM " + "="*20)
        # N'arrêter la JVM que si cette fixture l'a démarrée et la contrôle
        if is_jvm_owned_by_session_fixture():
            logger.info("Arrêt de la JVM demandé par la fixture de session qui la contrôle.")
            shutdown_jvm(called_by_session_fixture=True)
        else:
            logger.warning("Fin de session, mais la JVM n'est pas (ou plus) contrôlée par cette fixture. Elle ne sera pas arrêtée ici.")

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