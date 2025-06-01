"""
Configuration pour les tests pytest.

Ce fichier est automatiquement chargé par pytest avant l'exécution des tests.
Il configure les mocks nécessaires pour les tests et utilise les vraies bibliothèques
lorsqu'elles sont disponibles. Pour Python 3.12 et supérieur, le mock JPype1 est
automatiquement utilisé en raison de problèmes de compatibilité.
"""
# Ignorer la collecte de run_tests.py qui n'est pas un fichier de test
# Déplacé plus bas pour avoir accès à os
# collect_ignore = ["../argumentation_analysis/run_tests.py"]

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import importlib.util
# Ignorer la collecte de run_tests.py qui n'est pas un fichier de test
# Chemin relatif depuis tests/conftest.py vers argumentation_analysis/run_tests.py
# collect_ignore = ["../argumentation_analysis/run_tests.py"] # Commenté pour tester l'effet de python_classes
import logging
import threading # Ajout de l'import pour l'inspection des threads

# --- Gestion du Path pour les Mocks (déplacé ici AVANT les imports des mocks) ---
current_dir_for_mock = os.path.dirname(os.path.abspath(__file__))
mocks_dir_for_mock = os.path.join(current_dir_for_mock, 'mocks')
if mocks_dir_for_mock not in sys.path:
    sys.path.insert(0, mocks_dir_for_mock)
    print(f"INFO: tests/conftest.py: Ajout de {mocks_dir_for_mock} à sys.path.")

from tests.mocks.jpype_setup import (
    _REAL_JPYPE_MODULE,
    _REAL_JPYPE_AVAILABLE, # Ajouté pour skipif
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL,
    _MOCK_DOT_JPYPE_MODULE_GLOBAL,
    activate_jpype_mock_if_needed,
    pytest_sessionstart,
    pytest_sessionfinish
)
from tests.mocks.numpy_setup import setup_numpy_for_tests_fixture

from tests.fixtures.integration_fixtures import (
    integration_jvm, dung_classes, dl_syntax_parser, fol_syntax_parser,
    pl_syntax_parser, cl_syntax_parser, tweety_logics_classes,
    tweety_string_utils, tweety_math_utils, tweety_probability,
    tweety_conditional_probability, tweety_parser_exception,
    tweety_io_exception, tweety_qbf_classes, belief_revision_classes,
    dialogue_classes
)

# --- Configuration du Logger (déplacé avant la sauvegarde JPype pour l'utiliser) ---
logger = logging.getLogger(__name__)

# _REAL_JPYPE_MODULE, _JPYPE_MODULE_MOCK_OBJ_GLOBAL, _MOCK_DOT_JPYPE_MODULE_GLOBAL sont maintenant importés de jpype_setup.py

# Nécessaire pour la fixture integration_jvm
# La variable _integration_jvm_started_session_scope et les imports de jvm_setup
# ne sont plus nécessaires ici, gérés dans integration_fixtures.py

# --- Gestion du Path pour les Mocks ---
# Bloc déplacé plus haut

# print("INFO: conftest.py: Logger configuré pour pytest hooks jpype.") # Déjà fait plus haut

# --- Mock Matplotlib et NetworkX au plus tôt ---
# try:
#     from matplotlib_mock import pyplot as mock_pyplot_instance
#     from matplotlib_mock import cm as mock_cm_instance
#     from matplotlib_mock import MatplotlibMock as MockMatplotlibModule_class
    
#     sys.modules['matplotlib.pyplot'] = mock_pyplot_instance
#     sys.modules['matplotlib.cm'] = mock_cm_instance
#     mock_mpl_module = MockMatplotlibModule_class()
#     mock_mpl_module.pyplot = mock_pyplot_instance
#     mock_mpl_module.cm = mock_cm_instance
#     sys.modules['matplotlib'] = mock_mpl_module
#     print("INFO: Matplotlib mocké globalement.")

#     from networkx_mock import NetworkXMock as MockNetworkXModule_class
#     sys.modules['networkx'] = MockNetworkXModule_class()
#     print("INFO: NetworkX mocké globalement.")

# except ImportError as e:
#     print(f"ERREUR CRITIQUE lors du mocking global de matplotlib ou networkx: {e}")
#     if 'matplotlib' not in str(e).lower():
#         sys.modules['matplotlib.pyplot'] = MagicMock()
#         sys.modules['matplotlib.cm'] = MagicMock()
#         sys.modules['matplotlib'] = MagicMock()
#         sys.modules['matplotlib'].pyplot = sys.modules['matplotlib.pyplot']
#         sys.modules['matplotlib'].cm = sys.modules['matplotlib.cm']
#     if 'networkx' not in str(e).lower():
#         sys.modules['networkx'] = MagicMock()
print("INFO: Mocking global de Matplotlib et NetworkX commenté pour débogage.")

# --- Mock NumPy Immédiat ---

# MockRecarray, _install_numpy_mock_immediately sont maintenant dans numpy_setup.py
# L'appel à _install_numpy_mock_immediately est géré par la fixture setup_numpy_for_tests_fixture.

# --- Mock Pandas Immédiat ---
# def _install_pandas_mock_immediately():
#     if 'pandas' not in sys.modules:
#         try:
#             from pandas_mock import DataFrame, read_csv, read_json
#             sys.modules['pandas'] = type('pandas', (), {
#                 'DataFrame': DataFrame, 'read_csv': read_csv, 'read_json': read_json, 'Series': list,
#                 'NA': None, 'NaT': None, 'isna': lambda x: x is None, 'notna': lambda x: x is not None,
#                 '__version__': '1.5.3',
#             })
#             sys.modules['pandas.core'] = type('pandas.core', (), {})
#             sys.modules['pandas.core.api'] = type('pandas.core.api', (), {})
#             sys.modules['pandas._libs'] = type('pandas._libs', (), {})
#             sys.modules['pandas._libs.pandas_datetime'] = type('pandas._libs.pandas_datetime', (), {})
#             print("INFO: Mock Pandas installé immédiatement dans conftest.py")
#         except ImportError as e:
#             print(f"ERREUR lors de l'installation immédiate du mock Pandas: {e}")

# Installation immédiate si Python 3.12+ ou si pandas n'est pas disponible (de HEAD)
# if (sys.version_info.major == 3 and sys.version_info.minor >= 12):
#     _install_pandas_mock_immediately()
print("INFO: Installation immédiate du mock Pandas commentée pour débogage.")

# --- Mock JPype ---
# Définition de _JPYPE_MODULE_MOCK_OBJ_GLOBAL et _MOCK_DOT_JPYPE_MODULE_GLOBAL déplacée vers jpype_setup.py

# --- Mock ExtractDefinitions ---
# try:
#     from extract_definitions_mock import setup_extract_definitions_mock
#     setup_extract_definitions_mock()
#     print("INFO: ExtractDefinitions mocké globalement.")
# except ImportError as e_extract:
#     print(f"ERREUR lors du mocking d'ExtractDefinitions: {e_extract}")
# except Exception as e_extract_setup:
#     print(f"ERREUR lors de la configuration du mock ExtractDefinitions: {e_extract_setup}")
print("INFO: Mocking global de ExtractDefinitions commenté pour débogage.")

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Fonctions is_module_available, is_python_version_compatible_with_jpype, setup_numpy, setup_pandas
# déplacées vers leurs modules respectifs (numpy_setup.py, pandas_setup.py) ou plus utilisées ici.

# Fixtures setup_numpy_for_tests_fixture, logger_conftest_integration, integration_jvm,
# activate_jpype_mock_if_needed, dung_classes, qbf_classes, belief_revision_classes, dialogue_classes
# et les hooks pytest_sessionstart, pytest_sessionfinish sont maintenant importés
# depuis leurs modules respectifs.
# Le code commenté pour setup_pandas_for_tests_fixture et l'ancienne version de integration_jvm
# peut également être supprimé.
# Les fixtures spécifiques à Tweety (dung_classes, etc.) sont supprimées ici car elles sont importées.
# Les hooks de session sont également supprimés car importés.
# La section "Pytest Session Hooks pour la gestion globale de JPype ---" (ligne 1212)
# et tout ce qui suit jusqu'à la fin du fichier est supprimé.
