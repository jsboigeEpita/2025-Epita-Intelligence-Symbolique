"""
Configuration pour les tests pytest.

Ce fichier est automatiquement chargé par pytest avant l'exécution des tests.
Il configure les mocks nécessaires pour les tests et utilise les vraies bibliothèques
lorsqu'elles sont disponibles. Pour Python 3.12 et supérieur, le mock JPype1 est
automatiquement utilisé en raison de problèmes de compatibilité.
"""
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
# --- Gestion des imports conditionnels NumPy et Pandas ---
_conftest_setup_logger.info("Début de la gestion des imports conditionnels pour NumPy et Pandas.")
try:
    import numpy
    import pandas
    _conftest_setup_logger.info("NumPy et Pandas réels importés avec succès.")
except ImportError:
    _conftest_setup_logger.warning("Échec de l'import de NumPy et/ou Pandas. Tentative d'utilisation des mocks.")
    
    # Mock pour NumPy
    try:
        # Tenter d'importer le contenu spécifique du mock si disponible
        from tests.mocks.numpy_mock import array as numpy_array_mock # Importer un élément spécifique pour vérifier
        # Si l'import ci-dessus fonctionne, on peut supposer que le module mock est complet
        # et sera utilisé par les imports suivants dans le code testé.
        # Cependant, pour forcer l'utilisation du mock complet, on le met dans sys.modules.
        import tests.mocks.numpy_mock as numpy_mock_content
        sys.modules['numpy'] = numpy_mock_content
        _conftest_setup_logger.info("Mock pour NumPy (tests.mocks.numpy_mock) activé via sys.modules.")
    except ImportError:
        _conftest_setup_logger.error("Mock spécifique tests.mocks.numpy_mock non trouvé. Utilisation de MagicMock pour NumPy.")
        sys.modules['numpy'] = MagicMock()
    except Exception as e_numpy_mock:
        _conftest_setup_logger.error(f"Erreur inattendue lors du chargement du mock NumPy: {e_numpy_mock}. Utilisation de MagicMock.")
        sys.modules['numpy'] = MagicMock()

    # Mock pour Pandas
    try:
        # Tenter d'importer le contenu spécifique du mock
        from tests.mocks.pandas_mock import DataFrame as pandas_dataframe_mock # Importer un élément spécifique
        import tests.mocks.pandas_mock as pandas_mock_content
        sys.modules['pandas'] = pandas_mock_content
        _conftest_setup_logger.info("Mock pour Pandas (tests.mocks.pandas_mock) activé via sys.modules.")
    except ImportError:
        _conftest_setup_logger.error("Mock spécifique tests.mocks.pandas_mock non trouvé. Utilisation de MagicMock pour Pandas.")
        sys.modules['pandas'] = MagicMock()
    except Exception as e_pandas_mock:
        _conftest_setup_logger.error(f"Erreur inattendue lors du chargement du mock Pandas: {e_pandas_mock}. Utilisation de MagicMock.")
        sys.modules['pandas'] = MagicMock()
_conftest_setup_logger.info("Fin de la gestion des imports conditionnels pour NumPy et Pandas.")
# --- Fin Gestion des imports conditionnels ---
# --- Fin Configuration globale du Logging ---

# --- Gestion du Path pour les Mocks (déplacé ici AVANT les imports des mocks) ---
current_dir_for_mock = os.path.dirname(os.path.abspath(__file__))
mocks_dir_for_mock = os.path.join(current_dir_for_mock, 'mocks')
if mocks_dir_for_mock not in sys.path:
    sys.path.insert(0, mocks_dir_for_mock)
    _conftest_setup_logger.info(f"Ajout de {mocks_dir_for_mock} à sys.path pour l'accès aux mocks locaux.")

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

# Les sections de code commentées pour le mocking global de Matplotlib, NetworkX,
# l'installation immédiate de Pandas, et ExtractDefinitions ont été supprimées.
# Ces mocks, s'ils sont nécessaires, devraient être gérés par des fixtures spécifiques
# ou une configuration au niveau du module mock lui-même, similaire à NumPy/Pandas.

# Ajout du répertoire racine du projet à sys.path pour assurer la découverte des modules du projet.
# Ceci est particulièrement utile si les tests sont exécutés d'une manière où le répertoire racine
# n'est pas automatiquement inclus dans PYTHONPATH (par exemple, exécution directe de pytest
# depuis un sous-répertoire ou avec certaines configurations d'IDE).
# parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# if parent_dir not in sys.path:
#     sys.path.insert(0, parent_dir)
#     _conftest_setup_logger.info(f"Ajout du répertoire racine du projet ({parent_dir}) à sys.path.")
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.

# Les fixtures et hooks sont importés depuis leurs modules dédiés.
# Les commentaires résiduels concernant les déplacements de code et les refactorisations
# antérieures ont été supprimés pour améliorer la lisibilité.
