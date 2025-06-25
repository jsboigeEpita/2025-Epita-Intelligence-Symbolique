# -*- coding: utf-8 -*-
import sys
import os

# =============================================================================
# PATCH DE DÉCHARGEMENT FORCÉ DE TORCH (TENTATIVE DÉSESPÉRÉE)
# Objectif : Supprimer torch et les librairies associées de la mémoire AVANT
# que pytest ne charge quoi que ce soit d'autre, pour éviter le conflit
# avec la JVM de JPype.
# =============================================================================
print("--- PATCH DE DÉCHARGEMENT FORCÉ DE TORCH ACTIVÉ ---")
modules_to_remove = ['torch', 'transformers', 'sentence_transformers']
modules_to_delete = [name for name in sys.modules if any(name.startswith(prefix) for prefix in modules_to_remove)]
if modules_to_delete:
    print(f"Modules à décharger: {modules_to_delete}")
    for name in modules_to_delete:
        try:
            del sys.modules[name]
        except KeyError:
            pass
    print(f"--- {len(modules_to_delete)} modules relatifs à torch déchargés ---")
else:
    print("--- Aucun module relatif à torch n'était chargé. ---")
# -*- coding: utf-8 -*-
import sys
from pathlib import Path

# A list of files or directories to be ignored during test collection.
collect_ignore = [
    "tests/integration/services/test_mcp_server_integration.py",
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
import pytest
import logging
import jpype
from argumentation_analysis.core import jvm_setup

# Variable globale pour s'assurer que le shutdown n'est appelé qu'une fois.
_jvm_shutting_down = False

def pytest_sessionstart(session):
    """
    Hook exécuté au tout début de la session de test.
    Idéal pour les initialisations globales comme la JVM, qui doivent avoir lieu
    avant toute collecte de tests ou exécution de fixtures.
    """
    start_logger = logging.getLogger("conftest.sessionstart")
    start_logger.info("--- DÉMARRAGE DE LA SESSION PYTEST ---")
    
    # --- PATCH DE DÉCHARGEMENT FORCÉ DE TORCH ---
    # Pour éviter le conflit "fatal access violation" avec la JVM de JPype.
    start_logger.info("Vérification et déchargement des modules conflictuels (torch, etc)...")
    modules_to_remove = ['torch', 'transformers', 'sentence_transformers']
    modules_to_delete = [name for name in sys.modules if any(name.startswith(prefix) for prefix in modules_to_remove)]
    if modules_to_delete:
        start_logger.warning(f"Modules conflictuels détectés. Déchargement de : {modules_to_delete}")
        for name in modules_to_delete:
            try:
                del sys.modules[name]
            except KeyError:
                pass
        start_logger.info(f"{len(modules_to_delete)} modules relatifs à torch ont été déchargés.")
    else:
        start_logger.info("Aucun module conflictuel (torch, etc.) n'était chargé.")
        
    # --- DÉMARRAGE DE LA JVM DÉPLACÉ DANS UNE FIXTURE ---
    # Le démarrage de la JVM est maintenant géré par une fixture `jvm_session`
    # pour permettre une initialisation "lazy" (paresseuse), uniquement lorsque
    # les tests en ont réellement besoin. Cela évite les conflits potentiels
    # lors du démarrage de la session pytest.
    start_logger.info("Le démarrage de la JVM est maintenant géré par une fixture dédiée.")

def pytest_sessionfinish(session):
    """
    Hook exécuté à la toute fin de la session de test.
    Nettoie les ressources globales comme la JVM.
    """
    global _jvm_shutting_down
    finish_logger = logging.getLogger("conftest.sessionfinish")
    finish_logger.info("--- FIN DE LA SESSION PYTEST ---")
    
    if jpype.isJVMStarted() and not _jvm_shutting_down:
        finish_logger.info("Arrêt de la JVM...")
        _jvm_shutting_down = True
        try:
            jpype.shutdownJVM()
            finish_logger.info("JVM arrêtée avec succès.")
        except Exception as e:
            finish_logger.error(f"Erreur lors de l'arrêt de la JVM: {e}")
            # Ne pas faire échouer la session pour une erreur de shutdown

# Charger les fixtures définies dans d'autres fichiers comme des plugins
# NOTE(Roo): Plugins réactivés pour permettre le chargement de `integration_fixtures`
pytest_plugins = [
   "tests.fixtures.integration_fixtures",
   "tests.fixtures.jvm_subprocess_fixture",
    "pytest_playwright",
    "tests.mocks.numpy_setup"
]

import threading # Ajout de l'import pour l'inspection des threads
from unittest.mock import patch, MagicMock
import importlib.util

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
    jdk_base_path = os.path.join(project_root, "portable_jdk", "jdk-17.0.11+9")
    jvm_dll_path = os.path.join(jdk_base_path, "bin", "server", "jvm.dll")

    if not os.path.exists(jvm_dll_path):
        pytest.fail(f"jvm.dll non trouvé à {jvm_dll_path}. Assurez-vous que le JDK portable est en place.")

    if not jpype.isJVMStarted():
        try:
            # --- PATCH ANTI-CRASH (torch vs jpype) ---
            # Manipulation directe de sys.modules au lieu de monkeypatch pour
            # éviter le ScopeMismatch, car cette fixture a une portée "session".
            print("\n[JVM Fixture Pre-init] Application de l'isolation de torch...")
            modules_to_remove = ['torch', 'transformers', 'sentence_transformers']
            modules_to_delete = [name for name in sys.modules if any(name.startswith(prefix) for prefix in modules_to_remove)]
            for name in modules_to_delete:
                del sys.modules[name]
            print(f"[JVM Fixture Pre-init] {len(modules_to_delete)} modules relatifs à torch ont été déchargés.")
            # --- FIN PATCH ---

            # --- CORRECTIF CRASH JVM (Leçon de l'historique Git) ---
            # On désactive la fermeture automatique par JPype pour éviter les conflits.
            # L'arrêt sera géré manuellement à la fin de la session dans cette fixture.
            if hasattr(jpype, 'config'):
                print("[JVM Fixture] Définition de jpype.config.destroy_jvm = False")
                jpype.config.destroy_jvm = False
            # --- FIN CORRECTIF ---

            print("\n[JVM Fixture] Démarrage de la JVM pour la session de test...")
            # La logique de recherche du JDK/classpath est maintenant centralisée dans jvm_setup.
            # L'import est local à la fixture pour éviter les effets de bord.
            from argumentation_analysis.core.jvm_setup import initialize_jvm
            
            if not initialize_jvm():
                pytest.fail("initialize_jvm() a retourné False. Échec critique du démarrage de la JVM.")

            print("[JVM Fixture] JVM démarrée avec succès via jvm_setup.")
        except SystemExit as se:
            active_threads = [t.name for t in threading.enumerate()]
            print(f"[JVM Fixture] ERREUR FATALE (SystemExit): Le processus Python se termine. Code: {se.code}")
            print(f"[JVM Fixture] Threads actifs au moment du crash: {active_threads}")
            pytest.fail(f"Crash JVM intercepté comme SystemExit ({se.code}).")
        except Exception as e:
            # Maintenant que initialize_jvm lève une exception, nous la propageons
            # pour un rapport d'erreur clair et immédiat.
            pytest.fail(f"Échec du démarrage de la JVM lors de l'appel à initialize_jvm : {e}", pytrace=True)

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