import sys
import os
from pathlib import Path

# Ajoute la racine du projet au sys.path pour résoudre les problèmes d'import
# causés par le `rootdir` de pytest qui interfère avec la résolution des modules.
project_root = Path(__file__).parent.parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
"""
Configuration pour les tests pytest.

Ce fichier est automatiquement chargé par pytest avant l'exécution des tests.
Il configure les mocks nécessaires pour les tests et utilise les vraies bibliothèques
lorsqu'elles sont disponibles. Pour Python 3.12 et supérieur, le mock JPype1 est
automatiquement utilisé en raison de problèmes de compatibilité.
"""
# ========================== ATTENTION - PROTECTION CRITIQUE ==========================
# L'import suivant active le module 'auto_env', qui est ESSENTIEL pour la sécurité
# et la stabilité de tous les tests et scripts. Il garantit que le code s'exécute
# dans l'environnement Conda approprié (par défaut 'projet-is').
#
# NE JAMAIS DÉSACTIVER, COMMENTER OU SUPPRIMER CET IMPORT.
# Le faire contourne les gardes-fous de l'environnement et peut entraîner :
#   - Des erreurs de dépendances subtiles et difficiles à diagnostiquer.
#   - Des comportements imprévisibles des tests.
#   - L'utilisation de mocks à la place de composants réels (ex: JPype).
#   - Des résultats de tests corrompus ou non fiables.
#
# Ce mécanisme lève une RuntimeError si l'environnement n'est pas correctement activé,
# empêchant l'exécution des tests dans une configuration incorrecte.
# Voir project_core/core_from_scripts/auto_env.py pour plus de détails.
# =====================================================================================
import project_core.core_from_scripts.auto_env

import sys
import os
import pytest
from unittest.mock import patch, MagicMock
import importlib.util
import logging
import threading # Ajout de l'import pour l'inspection des threads
# --- Configuration globale du Logging pour les tests ---
# Le logger global pour conftest est déjà défini plus bas,
# mais nous avons besoin de configurer basicConfig tôt.
# Nous allons utiliser un logger temporaire ici ou le logger racine.
_conftest_setup_logger = logging.getLogger("conftest.setup")

if not logging.getLogger().handlers: # Si le root logger n'a pas de handlers, basicConfig n'a probablement pas été appelé efficacement.
    logging.basicConfig(
        level=logging.INFO, # Ou un autre niveau pertinent pour les tests globaux
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    _conftest_setup_logger.info("Configuration globale du logging appliquée.")
else:
    _conftest_setup_logger.info("Configuration globale du logging déjà présente ou appliquée par un autre module.")
# --- Début Patching JPype Mock au niveau module si nécessaire ---
os.environ['USE_REAL_JPYPE'] = 'false'
_SHOULD_USE_REAL_JPYPE = os.environ.get('USE_REAL_JPYPE', 'false').lower() in ('true', '1')
_conftest_setup_logger.info(f"conftest.py: USE_REAL_JPYPE={os.environ.get('USE_REAL_JPYPE', 'false')}, _SHOULD_USE_REAL_JPYPE={_SHOULD_USE_REAL_JPYPE}")

if not _SHOULD_USE_REAL_JPYPE:
    _conftest_setup_logger.info("conftest.py: Application du mock JPype au niveau module dans sys.modules.")
    try:
        # S'assurer que le répertoire des mocks est dans le path pour les imports suivants
        _current_dir_for_jpype_mock_patch = os.path.dirname(os.path.abspath(__file__))
        _mocks_dir_for_jpype_mock_patch = os.path.join(_current_dir_for_jpype_mock_patch, 'mocks')
        # if _mocks_dir_for_jpype_mock_patch not in sys.path:
        #     sys.path.insert(0, _mocks_dir_for_jpype_mock_patch)
        #     _conftest_setup_logger.info(f"Ajout de {_mocks_dir_for_jpype_mock_patch} à sys.path pour jpype_mock.")

        from .mocks import jpype_mock # Importer le module mock principal
        from .mocks.jpype_components.imports import imports_module as actual_mock_jpype_imports_module

        # Préparer l'objet mock principal pour 'jpype'
        _jpype_module_mock_obj = MagicMock(name="jpype_module_mock_from_conftest")
        _jpype_module_mock_obj.__path__ = [] # Nécessaire pour simuler un package
        _jpype_module_mock_obj.isJVMStarted = jpype_mock.isJVMStarted
        _jpype_module_mock_obj.startJVM = jpype_mock.startJVM
        _jpype_module_mock_obj.getJVMPath = jpype_mock.getJVMPath
        _jpype_module_mock_obj.getJVMVersion = jpype_mock.getJVMVersion
        _jpype_module_mock_obj.getDefaultJVMPath = jpype_mock.getDefaultJVMPath
        _jpype_module_mock_obj.JClass = jpype_mock.JClass
        _jpype_module_mock_obj.JException = jpype_mock.JException
        _jpype_module_mock_obj.JObject = jpype_mock.JObject
        _jpype_module_mock_obj.JVMNotFoundException = jpype_mock.JVMNotFoundException
        _jpype_module_mock_obj.__version__ = getattr(jpype_mock, '__version__', '1.x.mock.conftest')
        _jpype_module_mock_obj.imports = actual_mock_jpype_imports_module
        # Simuler d'autres attributs/méthodes si nécessaire pour la collecte
        _jpype_module_mock_obj.config = MagicMock(name="jpype.config_mock_from_conftest")
        _jpype_module_mock_obj.config.destroy_jvm = True # Comportement par défaut sûr pour un mock

        # Préparer le mock pour '_jpype' (le module C)
        _mock_dot_jpype_module = jpype_mock._jpype

        # Appliquer les mocks à sys.modules
        sys.modules['jpype'] = _jpype_module_mock_obj
        sys.modules['_jpype'] = _mock_dot_jpype_module 
        sys.modules['jpype._core'] = _mock_dot_jpype_module 
        sys.modules['jpype.imports'] = actual_mock_jpype_imports_module
        sys.modules['jpype.config'] = _jpype_module_mock_obj.config
        
        _mock_types_module = MagicMock(name="jpype.types_mock_from_conftest")
        for type_name in ["JString", "JArray", "JObject", "JBoolean", "JInt", "JDouble", "JLong", "JFloat", "JShort", "JByte", "JChar"]:
             setattr(_mock_types_module, type_name, getattr(jpype_mock, type_name, MagicMock(name=f"Mock{type_name}")))
        sys.modules['jpype.types'] = _mock_types_module
        sys.modules['jpype.JProxy'] = MagicMock(name="jpype.JProxy_mock_from_conftest")

        _conftest_setup_logger.info("Mock JPype appliqué à sys.modules DEPUIS conftest.py.")

    except ImportError as e_mock_load:
        _conftest_setup_logger.error(f"conftest.py: ERREUR CRITIQUE lors du chargement des mocks JPype (jpype_mock ou jpype_components): {e_mock_load}. Le mock JPype pourrait ne pas être actif.")
    except Exception as e_patching:
        _conftest_setup_logger.error(f"conftest.py: Erreur inattendue lors du patching de JPype: {e_patching}", exc_info=True)
else:
    _conftest_setup_logger.info("conftest.py: _SHOULD_USE_REAL_JPYPE est True. Aucun mock JPype appliqué au niveau module depuis conftest.py.")
# --- Fin Patching JPype Mock ---
# # --- Gestion des imports conditionnels NumPy et Pandas ---
# _conftest_setup_logger.info("Début de la gestion des imports conditionnels pour NumPy et Pandas.")
# try:
#     import numpy
#     import pandas
#     _conftest_setup_logger.info("NumPy et Pandas réels importés avec succès.")
# except ImportError:
#     _conftest_setup_logger.warning("Échec de l'import de NumPy et/ou Pandas. Tentative d'utilisation des mocks.")
    
#     # Mock pour NumPy
#     try:
#         # Tenter d'importer le contenu spécifique du mock si disponible
#         from tests.mocks.numpy_mock import array as numpy_array_mock # Importer un élément spécifique pour vérifier
#         # Si l'import ci-dessus fonctionne, on peut supposer que le module mock est complet
#         # et sera utilisé par les imports suivants dans le code testé.
#         # Cependant, pour forcer l'utilisation du mock complet, on le met dans sys.modules.
#         import tests.mocks.numpy_mock as numpy_mock_content
#         sys.modules['numpy'] = numpy_mock_content
#         _conftest_setup_logger.info("Mock pour NumPy (tests.mocks.numpy_mock) activé via sys.modules.")
#     except ImportError:
#         _conftest_setup_logger.error("Mock spécifique tests.mocks.numpy_mock non trouvé. Utilisation de MagicMock pour NumPy.")
#         sys.modules['numpy'] = MagicMock()
#     except Exception as e_numpy_mock:
#         _conftest_setup_logger.error(f"Erreur inattendue lors du chargement du mock NumPy: {e_numpy_mock}. Utilisation de MagicMock.")
#         sys.modules['numpy'] = MagicMock()

#     # Mock pour Pandas
#     try:
#         # Tenter d'importer le contenu spécifique du mock
#         from tests.mocks.pandas_mock import DataFrame as pandas_dataframe_mock # Importer un élément spécifique
#         import tests.mocks.pandas_mock as pandas_mock_content
#         sys.modules['pandas'] = pandas_mock_content
#         _conftest_setup_logger.info("Mock pour Pandas (tests.mocks.pandas_mock) activé via sys.modules.")
#     except ImportError:
#         _conftest_setup_logger.error("Mock spécifique tests.mocks.pandas_mock non trouvé. Utilisation de MagicMock pour Pandas.")
#         sys.modules['pandas'] = MagicMock()
#     except Exception as e_pandas_mock:
#         _conftest_setup_logger.error(f"Erreur inattendue lors du chargement du mock Pandas: {e_pandas_mock}. Utilisation de MagicMock.")
#         sys.modules['pandas'] = MagicMock()
# _conftest_setup_logger.info("Fin de la gestion des imports conditionnels pour NumPy et Pandas.")
# # --- Fin Gestion des imports conditionnels ---
# --- Fin Configuration globale du Logging ---

def pytest_addoption(parser):
    """Ajoute des options de ligne de commande personnalisées à pytest."""
    parser.addoption(
        "--backend-url", action="store", default="http://localhost:5003",
        help="URL du backend à tester"
    )
    parser.addoption(
        "--frontend-url", action="store", default="http://localhost:3000",
        help="URL du frontend à tester (si applicable)"
    )

@pytest.fixture(scope="session")
def backend_url(request):
    """Fixture pour récupérer l'URL du backend depuis les options pytest."""
    return request.config.getoption("--backend-url")

@pytest.fixture(scope="session")
def frontend_url(request):
    """Fixture pour récupérer l'URL du frontend depuis les options pytest."""
    return request.config.getoption("--frontend-url")
# --- Gestion du Path pour les Mocks (déplacé ici AVANT les imports des mocks) ---
current_dir_for_mock = os.path.dirname(os.path.abspath(__file__))
mocks_dir_for_mock = os.path.join(current_dir_for_mock, 'mocks')
# if mocks_dir_for_mock not in sys.path:
#     sys.path.insert(0, mocks_dir_for_mock)
#     _conftest_setup_logger.info(f"Ajout de {mocks_dir_for_mock} à sys.path pour l'accès aux mocks locaux.")

from .mocks.jpype_setup import (
    _REAL_JPYPE_MODULE,
    _REAL_JPYPE_AVAILABLE, # Ajouté pour skipif
    _JPYPE_MODULE_MOCK_OBJ_GLOBAL,
    _MOCK_DOT_JPYPE_MODULE_GLOBAL,
    activate_jpype_mock_if_needed,
    pytest_sessionstart,
    pytest_sessionfinish
)
from .mocks.numpy_setup import setup_numpy_for_tests_fixture

from .fixtures.integration_fixtures import (
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

# Les sections de code commentées pour le mocking global de Matplotlib, NetworkX,
# l'installation immédiate de Pandas, et ExtractDefinitions ont été supprimées.
# Ces mocks, s'ils sont nécessaires, devraient être gérés par des fixtures spécifiques
# ou une configuration au niveau du module mock lui-même, similaire à NumPy/Pandas.

# Ajout du répertoire racine du projet à sys.path pour assurer la découverte des modules du projet.
# Ceci est particulièrement utile si les tests sont exécutés d'une manière où le répertoire racine
# n'est pas automatiquement inclus dans PYTHONPATH (par exemple, exécution directe de pytest
# depuis un sous-répertoire ou avec certaines configurations d'IDE).
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    _conftest_setup_logger.info(f"Ajout du répertoire racine du projet ({parent_dir}) à sys.path.")
# Décommenté car l'environnement de test actuel en a besoin pour trouver les modules locaux.

# Les fixtures et hooks sont importés depuis leurs modules dédiés.
# Les commentaires résiduels concernant les déplacements de code et les refactorisations
# antérieures ont été supprimés pour améliorer la lisibilité.

# --- Fixtures déplacées depuis tests/integration/webapp/conftest.py ---

@pytest.fixture
def webapp_config():
    """Provides a basic webapp configuration dictionary."""
    return {
        "backend": {
            "start_port": 8008,
            "fallback_ports": [8009, 8010]
        },
        "frontend": {
            "port": 3008
        },
        "playwright": {
            "enabled": True
        }
    }

@pytest.fixture
def test_config_path(tmp_path):
    """Provides a temporary path for a config file."""
    return tmp_path / "test_config.yml"