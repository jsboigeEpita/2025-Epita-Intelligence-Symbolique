import sys
import os
import pytest
import logging
from unittest.mock import MagicMock
from importlib.machinery import ModuleSpec
import importlib

logger = logging.getLogger(__name__)

def create_module_mock(name, submodules=None):
    """
    Crée un mock de module avec un __spec__ et potentiellement des sous-modules.
    `submodules` peut être une liste de chaînes ou un dictionnaire pour une structure récursive.
    """
    mock = MagicMock(name=f'{name}_mock')
    mock.__spec__ = ModuleSpec(name, None)
    mock.__name__ = name
    mock.__path__ = [f"/mock/path/{name.replace('.', '/')}"]

    if submodules:
        if isinstance(submodules, dict):
            for sub_name, sub_submodules in submodules.items():
                full_sub_name = f"{name}.{sub_name}"
                sub_mock = create_module_mock(full_sub_name, sub_submodules)
                setattr(mock, sub_name, sub_mock)
                sys.modules[full_sub_name] = sub_mock
        elif isinstance(submodules, list):
            for sub_name in submodules:
                full_sub_name = f"{name}.{sub_name}"
                sub_mock = create_module_mock(full_sub_name)
                setattr(mock, sub_name, sub_mock)
                sys.modules[full_sub_name] = sub_mock

    return mock

def deep_delete_from_sys_modules(module_name_prefix, logger_instance):
    """Supprime un module et tous ses sous-modules de sys.modules."""
    keys_to_delete = [k for k in sys.modules if k == module_name_prefix or k.startswith(module_name_prefix + '.')]
    if keys_to_delete:
        logger.info(f"Nettoyage des modules sys pour préfixe '{module_name_prefix}': {keys_to_delete}")
    for key in keys_to_delete:
        try:
            del sys.modules[key]
        except KeyError:
            logger.warning(f"Clé '{key}' non trouvée dans sys.modules lors de la suppression (deep_delete).")

@pytest.fixture(scope="function", autouse=True)
def setup_numpy_for_tests_fixture(request):
    """
    Fixture Pytest qui configure l'environnement NumPy pour chaque test.
    - Soit en utilisant la vraie bibliothèque NumPy (si le marqueur @pytest.mark.use_real_numpy est présent).
    - Soit en installant un mock complet de NumPy pour isoler les tests.
    """
    if request.node.get_closest_marker("e2e_test"):
        logger.info(f"NUMPY_SETUP: Skipping for E2E test {request.node.name}.")
        yield
        return

    # --- Nettoyage systématique avant chaque test ---
    logger.info(f"Fixture numpy_setup pour {request.node.name}: Nettoyage initial de numpy, pandas, etc.")
    deep_delete_from_sys_modules("numpy", logger)
    deep_delete_from_sys_modules("pandas", logger)
    deep_delete_from_sys_modules("scipy", logger)
    deep_delete_from_sys_modules("matplotlib", logger)
    
    numpy_state_before = sys.modules.get('numpy') # Devrait être None

    use_real_numpy = request.node.get_closest_marker("use_real_numpy")

    if use_real_numpy:
        # --- Branche 1: Utiliser le VRAI NumPy ---
        logger.info(f"Test {request.node.name} marqué 'use_real_numpy': Configuration pour VRAI NumPy.")
        original_numpy = None
        try:
            original_numpy = importlib.import_module('numpy')
            sys.modules['numpy'] = original_numpy
            logger.info(f"Vrai NumPy (version {original_numpy.__version__}) importé pour {request.node.name}.")
            yield original_numpy
        except ImportError as e:
            pytest.skip(f"Impossible d'importer le vrai NumPy: {e}")
        finally:
            logger.info(f"Fin de la section 'use_real_numpy' pour {request.node.name}. Restauration de l'état pré-fixture.")
            # Nettoyer le vrai numpy après le test
            deep_delete_from_sys_modules("numpy", logger)
            if numpy_state_before: # Si quelque chose existait avant, le restaurer
                sys.modules['numpy'] = numpy_state_before
                logger.info("État NumPy pré-fixture restauré.")
    else:
        # --- Branche 2: Utiliser le MOCK NumPy ---
        logger.info(f"Test {request.node.name}: Configuration pour MOCK NumPy.")
        numpy_mock = None
        try:
            from tests.mocks.numpy_mock import create_numpy_mock
            numpy_mock = create_numpy_mock()
            sys.modules['numpy'] = numpy_mock
            
            # Installer également des mocks réalistes pour les dépendances pour éviter les erreurs d'import et de spec.
            if 'pandas' not in sys.modules:
                sys.modules['pandas'] = create_module_mock('pandas')
            if 'matplotlib' not in sys.modules:
                # Mock matplotlib et son sous-module commun 'pyplot'
                # Le mock doit simuler la structure d'un package avec des sous-modules
                matplotlib_mock = create_module_mock('matplotlib', submodules={
                    'pyplot': None,
                    'backends': {
                        'backend_agg': None
                    }
                })
                sys.modules['matplotlib'] = matplotlib_mock
                sys.modules['matplotlib.pyplot'] = matplotlib_mock.pyplot
                sys.modules['matplotlib.backends'] = matplotlib_mock.backends
                sys.modules['matplotlib.backends.backend_agg'] = matplotlib_mock.backends.backend_agg
                # Ajouter les attributs attendus par matplotlib sur le backend mocké
                backend_agg_mock = matplotlib_mock.backends.backend_agg
                backend_agg_mock.FigureCanvas = MagicMock()
                backend_agg_mock.FigureManager = MagicMock()
                backend_ag_mock.backend_version = '1.0.mock'
            if 'scipy' not in sys.modules:
                sys.modules['scipy'] = create_module_mock('scipy', submodules=['stats'])
                sys.modules['scipy.stats'] = sys.modules['scipy'].stats

            logger.info(f"Mock NumPy installé pour {request.node.name}.")
            yield numpy_mock
        except ImportError as e:
            pytest.fail(f"Impossible d'importer create_numpy_mock depuis tests.mocks.numpy_mock: {e}")
        finally:
            logger.info(f"Fin de la section MOCK pour {request.node.name}. Restauration de l'état pré-fixture.")
            # Nettoyer le mock et ses amis après le test
            deep_delete_from_sys_modules("numpy", logger)
            deep_delete_from_sys_modules("pandas", logger)
            deep_delete_from_sys_modules("matplotlib", logger)
            deep_delete_from_sys_modules("scipy", logger)

            if numpy_state_before: # Si quelque chose existait avant (improbable), le restaurer
                sys.modules['numpy'] = numpy_state_before
                logger.info("État NumPy pré-fixture restauré.")