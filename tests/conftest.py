# -*- coding: utf-8 -*-
"""
Fichier de configuration racine pour les tests pytest, s'applique à l'ensemble du projet.

Ce fichier est exécuté avant tous les tests et est l'endroit idéal pour :
1. Charger les fixtures globales (portée "session").
2. Configurer l'environnement de test (ex: logging).
3. Définir des hooks pytest personnalisés.
4. Effectuer des imports critiques qui doivent avoir lieu avant tout autre code.
"""

# --- Step 1: Résolution du Conflit de Librairies Natives (torch vs jpype) ---
# Un crash "Fatal Python error: Aborted" ou "access violation" peut se produire
# lors du démarrage de la JVM, avec une trace d'appel impliquant `torch_python.dll`.
# Ceci indique un conflit entre les librairies C de JPype et de PyTorch.
# L'import de `torch` au tout début, avant tout autre import (surtout jpype),
# force son initialisation et semble résoudre ce conflit.
try:
    import torch
except ImportError:
    # Si torch n'est pas installé, nous ne pouvons rien faire mais nous ne voulons pas
    # que les tests plantent à cause de ça si l'environnement d'un utilisateur
    # ne l'inclut pas. Les tests dépendant de la JVM risquent de planter plus tard.
    pass

import pytest
import os
import sys
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
# Le patching global de JPype est maintenant géré exclusivement par `jpype_setup.py`
# et ses hooks `pytest_sessionstart`/`pytest_sessionfinish`, qui sont importés plus bas.
# Cela centralise la logique, élimine les conflits de chargement potentiels et
# garantit que le patching est appliqué de manière cohérente au bon moment.
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

# Charger les fixtures définies dans d'autres fichiers comme des plugins
pytest_plugins = ["tests.fixtures.integration_fixtures"]

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

# L'initialisation des mocks jpype et numpy est maintenant gérée par le bootstrap
# via l'option `addopts = -p tests.mocks.bootstrap` dans pytest.ini.
# Les imports de jpype_setup et numpy_setup ne sont plus nécessaires ici.

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
pytest_plugins = [
   "tests.fixtures.jvm_subprocess_fixture"
]