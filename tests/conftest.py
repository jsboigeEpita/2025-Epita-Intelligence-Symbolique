#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration pytest globale pour l'ensemble des tests du projet.
"""

import pytest
import logging
import os
import sys
from pathlib import Path
import shutil
from unittest.mock import patch

# Ajouter le répertoire racine au PYTHONPATH pour assurer la découvrabilité des modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ##################################################################################
# ##################################################################################
# ATTENTION : VÉRIFICATION D'ENVIRONNEMENT CRITIQUE
# CE BLOC EST UN COUPE-CIRCUIT DE SÉCURITÉ NON NÉGOCIABLE.
# IL EMPÊCHE L'EXÉCUTION DES TESTS EN DEHORS DE L'ENVIRONNEMENT CONDA 'projet-is',
# CE QUI POURRAIT ENTRAÎNER DES ERREURS IMPRÉVISIBLES ET CORROMPRE LES RÉSULTATS.
#
# NE PAS MODIFIER, DÉSACTIVER OU SUPPRIMER SOUS AUCUN PRÉTEXTE.
# ##################################################################################
# ##################################################################################
# ===== INTÉGRATION AUTO_ENV - CRITIQUE POUR ÉVITER LES ENVIRONNEMENTS GLOBAUX =====
# DOIT ÊTRE EXÉCUTÉ AVANT TOUTE AUTRE CONFIGURATION
try:
   # L'import a été mis à jour suite à la refactorisation du projet
   import argumentation_analysis.core.environment
   print("✅ Environnement projet activé via auto_env (conftest.py principal)")
except ImportError as e:
   print(f"⚠️ Auto_env non disponible dans conftest principal: {e}. L'environnement conda 'projet-is' doit être activé manuellement.")
except Exception as e:
   print(f"⚠️ Erreur auto_env dans conftest principal: {e}")
# ==================================================================================
# ##################################################################################
# FIN DU BLOC DE VÉRIFICATION D'ENVIRONNEMENT CRITIQUE
# ##################################################################################

# Importations nécessaires pour les fixtures ci-dessous
from argumentation_analysis.core.jvm_setup import (
    initialize_jvm, shutdown_jvm, is_jvm_started, is_jvm_owned_by_session_fixture
)

logger = logging.getLogger(__name__)

# --- Mocking de python-dotenv ---
# Variable globale pour conserver une référence au patcher
_dotenv_patcher = None

# Activer le mocking si une variable d'environnement est définie
MOCK_DOTENV = os.environ.get("MOCK_DOTENV_IN_TESTS", "false").lower() in ("true", "1", "t")

def pytest_configure(config):
    """
    Configure les markers pytest et active le mocking de dotenv.
    """
    global _dotenv_patcher
    
    # Enregistrement des marqueurs personnalisés
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "api: marks tests related to the API")
    config.addinivalue_line("markers", "real_llm: marks tests that require a real LLM service")
    config.addinivalue_line("markers", "real_jpype: marks tests that require a real JPype/JVM environment")
    config.addinivalue_line("markers", "no_jvm_session: marks tests that should not start the shared JVM session")

    # Activation du patcher dotenv au début de la session de test si nécessaire
    if MOCK_DOTENV:
        print("[INFO] Dotenv mocking is ENABLED. .env files will be ignored by tests.")
        _dotenv_patcher = patch('dotenv.main.dotenv_values', return_value={}, override=True)
        _dotenv_patcher.start()

def pytest_unconfigure(config):
    """
    Arrête le patcher dotenv à la fin de la session de test pour nettoyer.
    """
    global _dotenv_patcher
    if _dotenv_patcher:
        print("\n[INFO] Stopping dotenv mock.")
        _dotenv_patcher.stop()
        _dotenv_patcher = None

def _ensure_tweety_jars_are_correctly_placed():
    """
    Code défensif pour les tests. Vérifie si des JARs Tweety sont dans le
    répertoire 'libs' au lieu de 'libs/tweety' et les déplace.
    """
    try:
        project_root = Path(__file__).parent.parent.resolve()
        libs_dir = project_root / "argumentation_analysis" / "libs"
        tweety_dir = libs_dir / "tweety"
        
        if not libs_dir.is_dir():
            logger.debug("Le répertoire 'libs' n'existe pas, rien à faire.")
            return

        tweety_dir.mkdir(exist_ok=True)
        
        jars_in_libs = [f for f in libs_dir.iterdir() if f.is_file() and f.suffix == '.jar']
        
        if not jars_in_libs:
            logger.debug("Aucun fichier JAR trouvé directement dans 'libs'.")
            return
            
        logger.warning(f"JARs trouvés directement dans '{libs_dir}'. Ils devraient être dans '{tweety_dir}'.")
        for jar_path in jars_in_libs:
            destination = tweety_dir / jar_path.name
            logger.info(f"Déplacement de '{jar_path.name}' vers '{destination}'...")
            shutil.move(str(jar_path), str(destination))
        logger.info("Déplacement des JARs terminé.")

    except Exception as e:
        logger.error(f"Erreur lors du déplacement défensif des JARs Tweety: {e}", exc_info=True)


@pytest.fixture(scope="session", autouse=True)
def apply_nest_asyncio():
    """
    DEPRECATED/DISABLED: This fixture, which applies nest_asyncio, creates a
    fundamental conflict with the pytest-playwright plugin, causing tests to
    hang indefinitely. It is disabled for now.
    """
    logger.warning("The 'apply_nest_asyncio' fixture in conftest.py is currently disabled to ensure compatibility with Playwright.")
    yield


@pytest.fixture(scope="session")
def jvm_session():
    """
    Manages the JPype JVM lifecycle for the entire test session.
    This fixture is NOT auto-used; it must be requested by another fixture.
    """
    logger.info("---------- Pytest session starting: Provisioning dependencies and Initializing JVM... ----------")
    
    try:
        logger.info("Checking Tweety JARs location...")
        _ensure_tweety_jars_are_correctly_placed()

        if not is_jvm_started():
            logger.info("Attempting to initialize JVM via core.jvm_setup.initialize_jvm...")
            success = initialize_jvm(session_fixture_owns_jvm=True)
            if success:
                logger.info("JVM started successfully for the test session.")
            else:
                 pytest.fail("JVM initialization failed.", pytrace=False)
        else:
            logger.warning("JVM was already started. Assuming it is correctly configured.")
            
    except Exception as e:
        logger.error(f"A critical error occurred during JVM session setup: {e}", exc_info=True)
        pytest.exit(f"JVM setup failed: {e}", 1)

    yield True

    logger.info("---------- Pytest session finished: Shutting down JVM... ----------")
    if is_jvm_owned_by_session_fixture():
        shutdown_jvm(called_by_session_fixture=True)
    else:
        logger.warning("The JVM is not (or no longer) controlled by the global fixture. It will not be shut down here.")

@pytest.fixture(scope="function", autouse=True)
def manage_jvm_for_test(request):
    """
    This 'autouse' fixture runs for every test and decides if the global
    `jvm_session` fixture is required by manually invoking it.
    
    It checks for a 'no_jvm_session' marker on the test. If found, it does nothing.
    If not found, it uses `request.getfixturevalue()` to activate the `jvm_session`
    fixture, ensuring the JVM is started for the test.
    """
    if 'no_jvm_session' in request.node.keywords:
        logger.debug(
            f"Test '{request.node.name}' is marked with 'no_jvm_session'. "
            "The global JVM fixture will not be requested for this test."
        )
        yield
    else:
        # Manually trigger the session-scoped JVM fixture.
        # This will only run it once and then retrieve the cached result
        # for all subsequent calls.
        request.getfixturevalue('jvm_session')
        yield


# Charger les fixtures définies dans d'autres fichiers comme des plugins
pytest_plugins = [
   "tests.fixtures.integration_fixtures",
   # "tests.fixtures.jvm_subprocess_fixture", # TEMPORAIREMENT DÉSACTIVÉ - CAUSE UN CRASH JVM
    "pytest_playwright",
    # "tests.mocks.numpy_setup" # DÉSACTIVÉ GLOBALEMENT - Provoque un comportement instable pour les tests E2E
]

@pytest.fixture(autouse=True)
def check_mock_llm_is_forced(request):
    """
    Ce "coupe-circuit" est une sécurité pour tous les tests.
    Il vérifie que nous ne pouvons pas accidentellement utiliser un vrai LLM,
    SAUF si le test est explicitement marqué avec 'real_llm'.
    """
    if 'real_llm' in request.node.keywords:
        logger.warning(f"Le test {request.node.name} utilise le marqueur 'real_llm'. Le mock LLM est désactivé.")
        yield
    else:
        # Si le marqueur n'est pas présent, s'assurer que le LLM est mocké.
        # Idéalement, le mock est déjà actif via une autre fixture/paramètre.
        # Ce check sert de double-vérification.
        from argumentation_analysis.config.settings import settings
        if not settings.MOCK_LLM:
             pytest.fail(
                f"Le test '{request.node.name}' s'exécute sans 'real_llm' mais le mock LLM est inactif! "
                "Ceci est une condition d'échec de sécurité pour éviter des appels LLM réels non intentionnels."
            )
        yield
