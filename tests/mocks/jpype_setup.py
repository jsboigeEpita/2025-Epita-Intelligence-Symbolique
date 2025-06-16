# tests/mocks/jpype_setup.py
"""
Ce module fournit des fixtures pytest pour gérer le cycle de vie de JPype
et de la JVM, permettant de basculer entre un mock complet et la vraie bibliothèque.
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch
import importlib.util
from argumentation_analysis.core.jvm_setup import shutdown_jvm_if_needed, start_jvm_if_needed, is_jvm_started
import logging

# Configuration du logging
logger = logging.getLogger(__name__)

# --- Configuration Globale ---

_use_real_jpype = os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1')
_jpype_mock = None
_jpype_patcher = None

# --- Fonctions de Hook Pytest (si utilisées directement dans ce module) ---

def pytest_sessionstart(session):
    """
    Démarre la JVM si USE_REAL_JPYPE est activé, sinon prépare le mock.
    """
    global _jpype_mock, _jpype_patcher
    
    if _use_real_jpype:
        logger.info("Démarrage de la JVM pour la session de test.")
        try:
            start_jvm_if_needed()
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la JVM: {e}")
            pytest.exit(f"Impossible de démarrer la JVM: {e}")
    else:
        logger.info("Configuration du mock JPype pour la session de test.")
        _jpype_mock = MagicMock()
        
        # Simuler les comportements de base du module jpype
        _jpype_mock.isJVMStarted.return_value = True
        _jpype_mock.JClass.return_value = MagicMock()
        _jpype_mock.JException = Exception # Simuler les exceptions Java
        
        # Patcher le module jpype dans le système
        _jpype_patcher = patch('sys.modules', {**sys.modules, 'jpype': _jpype_mock})
        _jpype_patcher.start()


def pytest_sessionfinish(session, exitstatus):
    """
    Arrête la JVM si elle a été démarrée pour les tests.
    """
    global _jpype_patcher
    
    if _use_real_jpype:
        logger.info("Arrêt de la JVM à la fin de la session de test.")
        shutdown_jvm_if_needed()
    elif _jpype_patcher:
        logger.info("Arrêt du patcher JPype.")
        _jpype_patcher.stop()

# --- Fixtures Pytest ---

@pytest.fixture(scope="session")
def real_jpype_fixture():
    """
    Fixture qui gère le cycle de vie de la vraie JVM pour toute la session de test.
    Ne fait rien si USE_REAL_JPYPE est désactivé.
    """
    if not _use_real_jpype:
        yield None
        return

    # La gestion est faite par les hooks pytest_sessionstart/finish
    yield
    

@pytest.fixture(scope="function")
def mock_jpype(request):
    """
    Fixture pour mocker JPype au niveau de la fonction, permettant une configuration
    spécifique au test.
    """
    if _use_real_jpype:
        pytest.skip("Test incompatible avec la vraie JVM. Utilise un mock.")

    start_path = 'sys.modules'
    
    # Création du mock
    jpype_mock = MagicMock()
    jpype_mock.isJVMStarted.return_value = True
    jpype_mock.JClass.return_value = MagicMock()
    
    # Patcher le module jpype
    patcher = patch.dict(start_path, {'jpype': jpype_mock})
    patcher.start()
    
    yield jpype_mock
    
    # Nettoyage après le test
    patcher.stop()


@pytest.fixture(scope="session", autouse=True)
def manage_global_jpype_mock():
    """
    Fixture auto-utilisée pour gérer le mock JPype global pour la session.
    """
    if _use_real_jpype:
        yield
        return

    # Création et configuration du mock global
    global_jpype_mock = MagicMock(name="GlobalJPypeMock")
    global_jpype_mock.isJVMStarted.return_value = True
    global_jpype_mock.JClass.return_value = MagicMock()
    global_jpype_mock.JException = Exception

    # Patcher sys.modules pour que toute importation de 'jpype' retourne notre mock
    patcher = patch.dict(sys.modules, {'jpype': global_jpype_mock})
    patcher.start()

    yield global_jpype_mock

    # Nettoyage à la fin de la session
    patcher.stop()