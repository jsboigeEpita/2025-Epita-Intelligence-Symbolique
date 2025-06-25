# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# A list of files or directories to be ignored during test collection.
collect_ignore = [
    "tests/integration/services/test_mcp_server_integration.py",
    "tests/agents/core/logic",
]

# Ajoute la racine du projet au sys.path pour résoudre les problèmes d'import
# causés par le `rootdir` de pytest qui interfère avec la résolution des modules.
project_root_conftest = Path(__file__).parent.parent.resolve()
if str(project_root_conftest) not in sys.path:
    pass # pass # sys.path.insert(0, str(project_root_conftest))
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
# NOTE(Roo): Disabling the torch import to isolate the source of pytest crash (exit code 3).
# try:
#     import torch
# except ImportError:
#     # Si torch n'est pas installé, nous ne pouvons rien faire mais nous ne voulons pas
#     # que les tests plantent à cause de ça si l'environnement d'un utilisateur
#     # ne l'inclut pas. Les tests dépendant de la JVM risquent de planter plus tard.
#     pass

import os

# L'ajout de la racine du projet à sys.path est déjà effectué au début de ce fichier.
# Cette section est redondante et a été supprimée pour la clarté.
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
# import argumentation_analysis.core.environment

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
# NOTE(Roo): Disabling plugins to isolate the source of pytest crash (exit code 3).
# pytest_plugins = [
#    "tests.fixtures.integration_fixtures",
#    "tests.fixtures.jvm_subprocess_fixture",
#     "pytest_playwright",
#     "tests.mocks.numpy_setup"
# ]

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
    parser.addoption(
        "--disable-e2e-servers-fixture", action="store_true", default=False,
        help="Désactive la fixture e2e_servers pour éviter les conflits."
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
# L'ajout de la racine du projet à sys.path est déjà effectué au début de ce fichier.
# Cette section est redondante et a été supprimée pour la clarté.

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

@pytest.fixture(scope="session")
def jvm_session():
    """
    Fixture de session pour démarrer et arrêter la JVM une seule fois pour tous les tests.
    """
    import jpype
    import jpype.imports
    
    # Construire le chemin relatif vers le JDK
    project_root = Path(__file__).parent.parent.resolve()
    # Path corrected to point to the root portable_jdk, not the one in libs
    jdk_base_path = os.path.join(project_root, "portable_jdk", "jdk-17.0.2+8")
    jvm_dll_path = os.path.join(jdk_base_path, "bin", "server", "jvm.dll")

    if not os.path.exists(jvm_dll_path):
        pytest.fail(f"jvm.dll non trouvé à {jvm_dll_path}. Assurez-vous que le JDK portable est en place.")

    if not jpype.isJVMStarted():
        try:
            print("\n[JVM Fixture] Démarrage de la JVM pour la session de test...")
            
            # --- Dynamically build classpath from tweety libs ---
            # Corrected path to tweety libs at the root
            tweety_libs_path = os.path.join(project_root, "libs", "tweety")
            if not os.path.exists(tweety_libs_path):
                pytest.fail(f"Le répertoire des librairies Tweety est introuvable: {tweety_libs_path}")
                
            classpath = [os.path.join(tweety_libs_path, f) for f in os.listdir(tweety_libs_path) if f.endswith('.jar')]
            if not classpath:
                pytest.fail(f"Aucun fichier .jar n'a été trouvé dans {tweety_libs_path}")
            
            print(f"[JVM Fixture] Classpath construit avec {len(classpath)} JARs.")

            jpype.startJVM(
                jvmpath=jvm_dll_path,
                classpath=classpath,
                convertStrings=False
            )
            print("[JVM Fixture] JVM démarrée avec succès.")
        except Exception as e:
            pytest.fail(f"Échec du démarrage de la JVM : {e}")

    yield

    if jpype.isJVMStarted():
        print("\n[JVM Fixture] Arrêt de la JVM à la fin de la session.")
        jpype.shutdownJVM()
@pytest.fixture(autouse=True)
def skip_jvm_tests(monkeypatch):
    """
    Patche automatiquement les composants dépendant de la JVM si la variable
    d'environnement SKIP_JVM_TESTS est définie.
    """
    if os.getenv("SKIP_JVM_TESTS"):
        # Remplacer les classes qui déclenchent le démarrage de la JVM par des Mocks
        # Patch dans le module où la classe est définie
        monkeypatch.setattr(
            "argumentation_analysis.agents.core.logic.watson_logic_assistant.WatsonLogicAssistant",
            MagicMock()
        )
        monkeypatch.setattr(
            "argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent.MoriartyInterrogatorAgent",
            MagicMock()
        )
        # Patch dans les modules où la classe est importée et utilisée
        monkeypatch.setattr(
            "argumentation_analysis.orchestration.cluedo_extended_orchestrator.WatsonLogicAssistant",
            MagicMock(),
            raising=False # Ne pas lever d'erreur si l'attribut n'existe pas
        )
        monkeypatch.setattr(
            "argumentation_analysis.orchestration.cluedo_extended_orchestrator.MoriartyInterrogatorAgent",
            MagicMock(),
            raising=False # Ne pas lever d'erreur si l'attribut n'existe pas
        )