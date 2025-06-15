import sys
import os
from unittest.mock import MagicMock
import pytest
import importlib
import logging

logger = logging.getLogger(__name__)

def is_module_available(module_name):
    """Vérifie si un module est réellement installé, sans être un mock."""
    if module_name in sys.modules and isinstance(sys.modules[module_name], MagicMock):
        return False
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ImportError, ValueError):
        return False

def setup_numpy():
    """
    Décide d'utiliser le vrai NumPy ou le mock.
    Le mock est utilisé si le vrai n'est pas installé ou si la version de Python est >= 3.12.
    """
    major, minor = sys.version_info.major, sys.version_info.minor
    use_mock = (major == 3 and minor >= 12) or not is_module_available('numpy')

    if use_mock:
        logger.info("Utilisation du MOCK NumPy (depuis numpy_setup.py).")
        try:
            from . import numpy_mock
            
            # Le module numpy_mock lui-même est configuré pour être un mock de module.
            # Il contient des sous-modules mockés comme `core`, `linalg`, etc.
            sys.modules['numpy'] = numpy_mock
            
            # S'assurer que les sous-modules sont aussi dans sys.modules pour les imports directs
            for sub_name in ['typing', 'core', '_core', 'linalg', 'fft', 'lib', 'random', 'rec']:
                if hasattr(numpy_mock, sub_name):
                    sys.modules[f'numpy.{sub_name}'] = getattr(numpy_mock, sub_name)
            
            return numpy_mock
        except ImportError as e:
            logger.error(f"Échec de l'import de tests.mocks.numpy_mock: {e}. Fallback sur MagicMock.")
            mock_fallback = MagicMock(name="numpy_fallback_mock")
            sys.modules['numpy'] = mock_fallback
            return mock_fallback
    else:
        logger.info("Utilisation du VRAI NumPy (depuis numpy_setup.py).")
        import numpy
        return numpy

@pytest.fixture(scope="session", autouse=True)
def setup_numpy_for_tests_fixture():
    """
    Fixture de session qui configure NumPy (réel ou mock) pour toute la session de test.
    `autouse=True` garantit qu'elle est exécutée au début de la session.
    """
    setup_numpy()
    yield