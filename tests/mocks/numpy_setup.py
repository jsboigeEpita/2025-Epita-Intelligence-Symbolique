"""
Configuration et setup pour NumPy dans les tests.

Ce module gère la configuration de NumPy pour les tests, incluant les mocks
si NumPy n'est pas disponible.
"""
import sys
import logging
from unittest.mock import MagicMock
import pytest

logger = logging.getLogger(__name__)

@pytest.fixture(name="setup_numpy_for_tests_fixture")
def setup_numpy_for_tests_fixture():
    """
    Fixture pour configurer NumPy dans les tests.
    Essaie d'utiliser NumPy réel, sinon utilise des mocks.
    """
    try:
        import numpy as np
        logger.info("NumPy réel disponible pour les tests")
        return np
    except ImportError:
        logger.warning("NumPy non disponible, utilisation de mocks")
        
        # Créer un mock NumPy basique
        numpy_mock = MagicMock(name="numpy_mock")
        numpy_mock.__version__ = "1.x.mock"
        
        # Fonctions principales
        numpy_mock.array = MagicMock(return_value=MagicMock())
        numpy_mock.zeros = MagicMock(return_value=MagicMock())
        numpy_mock.ones = MagicMock(return_value=MagicMock())
        numpy_mock.arange = MagicMock(return_value=MagicMock())
        numpy_mock.linspace = MagicMock(return_value=MagicMock())
        
        # Types de données
        numpy_mock.int32 = int
        numpy_mock.int64 = int
        numpy_mock.float32 = float
        numpy_mock.float64 = float
        numpy_mock.bool_ = bool
        
        # Constantes
        numpy_mock.pi = 3.141592653589793
        numpy_mock.e = 2.718281828459045
        
        # Modules
        numpy_mock.linalg = MagicMock()
        numpy_mock.random = MagicMock()
        numpy_mock.fft = MagicMock()
        
        # Activer le mock dans sys.modules
        sys.modules['numpy'] = numpy_mock
        sys.modules['np'] = numpy_mock
        
        return numpy_mock

@pytest.fixture
def numpy_mock():
    """Fixture pytest pour NumPy mock."""
    return setup_numpy_for_tests_fixture()