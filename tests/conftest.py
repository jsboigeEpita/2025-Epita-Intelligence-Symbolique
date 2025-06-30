from unittest.mock import patch
from dotenv import dotenv_values
import os
from pathlib import Path
import pytest
import jpype
import logging
import time
import shutil
import nest_asyncio

# ##################################################################################
# ##################################################################################
# ATTENTION : VÉRIFICATION D'ENVIRONNEMENT CRITIQUE
# CE BLOC EST UN COUPE-CIRCUIT DE SÉCURITÉ NON NÉGOCIABLE.
# IL EMPÊCHE L'EXÉCUTION DES TESTS EN DEHORS DE L'ENVIRONNEMENT CONDA 'projet-is',
# CE QUI POURRAIT ENTRAÎNER DES ERREURS IMPRÉVISIBLES ET CORROMPRE LES RÉSULTATS.
#
# NE PAS MODIFIER, DÉSACTIVER OU SUPPRIMER SOUS AUCUN PRÉTEXTE.
# ##################################################################################
# ##################################################################################
# ===== INTÉGRATION AUTO_ENV - CRITIQUE POUR ÉVITER LES ENVIRONNEMENTS GLOBAUX =====
# DOIT ÊTRE EXÉCUTÉ AVANT TOUTE AUTRE CONFIGURATION
try:
   # L'import a été mis à jour suite à la refactorisation du projet
   import argumentation_analysis.core.environment
   print("✅ Environnement projet activé via auto_env (conftest.py principal)")
except ImportError as e:
   print(f"⚠️ Auto_env non disponible dans conftest principal: {e}. L'environnement conda 'projet-is' doit être activé manuellement.")
except Exception as e:
   print(f"⚠️ Erreur auto_env dans conftest principal: {e}")
# ==================================================================================
# ##################################################################################
# FIN DU BLOC DE VÉRIFICATION D'ENVIRONNEMENT CRITIQUE
# ##################################################################################

# --- Gestion du patch de dotenv ---
MOCK_DOTENV = True
_dotenv_patcher = None

def pytest_configure(config):
    """
    Hook de configuration précoce de pytest.
    1. Charge les variables .env via une mise à jour manuelle de os.environ.
    2. Gère le cycle de vie du patch de dotenv.
    """
    global MOCK_DOTENV, _dotenv_patcher

    if config.getoption("--allow-dotenv"):
        MOCK_DOTENV = False
        print("\n[INFO] Dotenv mocking is DISABLED. Real .env file will be used.")

        project_dir = Path(__file__).parent.parent
        dotenv_path = project_dir / '.env'
        if dotenv_path.exists():
            print(f"[INFO] Loading .env file from: {dotenv_path}")
            
            # Utilisation de la méthode standard et propre maintenant que le .env est sain
            env_vars = dotenv_values(dotenv_path=dotenv_path)
            
            if not env_vars:
                print(f"[WARNING] .env file found at '{dotenv_path}' but it seems to be empty.")
                return

            updated_vars = 0
            for key, value in env_vars.items():
                if key not in os.environ and value is not None:
                    os.environ[key] = value
                    updated_vars += 1
                elif value is None:
                    print(f"[WARNING] Skipping .env variable '{key}' because its value is None.")
                else:
                    print(f"[INFO] Skipping .env variable '{key}' because it's already set in the environment.")
            
            print(f"[INFO] Loaded {updated_vars} variables from .env into os.environ.")
            
            if 'OPENAI_API_KEY' not in os.environ:
                 print(f"[WARNING] OPENAI_API_KEY was not found in the loaded .env variables.")
            else:
                 print("[INFO] OPENAI_API_KEY successfully loaded.")

        else:
            print(f"[INFO] No .env file found at '{dotenv_path}'.")
    
    if MOCK_DOTENV:
        print("[INFO] Dotenv mocking is ENABLED. .env files will be ignored by tests.")
        _dotenv_patcher = patch('dotenv.main.dotenv_values', return_value={}, override=True)
        _dotenv_patcher.start()

def pytest_unconfigure(config):
    """
    Arrête le patcher dotenv à la fin de la session de test pour nettoyer.
    """
    global _dotenv_patcher
    if _dotenv_patcher:
        print("\n[INFO] Stopping dotenv mock.")
        _dotenv_patcher.stop()
        _dotenv_patcher = None
from argumentation_analysis.core.setup.manage_portable_tools import setup_tools
from argumentation_analysis.core.jvm_setup import initialize_jvm, shutdown_jvm, is_jvm_started
from argumentation_analysis.agents.core.logic.tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)

def _ensure_tweety_jars_are_correctly_placed():
    """
    Code défensif pour les tests. Vérifie si des JARs Tweety sont dans le
    répertoire 'libs' au lieu de 'libs/tweety' et les déplace.
    """
    try:
        project_root = Path(__file__).parent.parent.resolve()
        libs_dir = project_root / "argumentation_analysis" / "libs"
        tweety_dir = libs_dir / "tweety"
        
        if not libs_dir.is_dir():
            logger.debug("Le répertoire 'libs' n'existe pas, rien à faire.")
            return

        tweety_dir.mkdir(exist_ok=True)
        
        jars_in_libs = [f for f in libs_dir.iterdir() if f.is_file() and f.suffix == '.jar']
        
        if not jars_in_libs:
            logger.debug("Aucun fichier JAR trouvé directement dans 'libs'.")
            return
            
        logger.warning(f"JARs trouvés directement dans '{libs_dir}'. Ils devraient être dans '{tweety_dir}'.")
        for jar_path in jars_in_libs:
            destination = tweety_dir / jar_path.name
            logger.info(f"Déplacement de '{jar_path.name}' vers '{destination}'...")
            shutil.move(str(jar_path), str(destination))
        logger.info("Déplacement des JARs terminé.")

    except Exception as e:
        logger.error(f"Erreur lors du déplacement défensif des JARs Tweety: {e}", exc_info=True)


# @pytest.fixture(scope="session")
# def anyio_backend(request):
#     """
#     DEPRECATED: This fixture was causing conflicts with pytest-playwright.
#     The `apply_nest_asyncio` fixture is now disabled.
#     """
#     return request.config.getoption("anyio_backend", "asyncio")

@pytest.fixture(scope="session", autouse=True)
def apply_nest_asyncio():
    """
    DEPRECATED/DISABLED: This fixture, which applies nest_asyncio, creates a
    fundamental conflict with the pytest-playwright plugin, causing tests to
    hang indefinitely. It is disabled for now.
    If other dedicated asyncio tests fail, a more targeted solution will be
    needed, for example, by creating a custom marker to enable nest_asyncio
    only for specific tests that require it, instead of using `autouse=True`.
    """
    # Original problematic code:
    # if anyio_backend == "asyncio":
    #     logger.info(f"Applying nest_asyncio for '{anyio_backend}' backend.")
    #     nest_asyncio.apply()
    #     yield
    #     logger.info("nest_asyncio teardown for 'asyncio' backend.")
    # else:
    #     logger.info(f"Skipping nest_asyncio for '{anyio_backend}' backend.")
    #     yield
    logger.warning("The 'apply_nest_asyncio' fixture in conftest.py is currently disabled to ensure compatibility with Playwright.")
    yield

@pytest.fixture(scope="session")
def jvm_session():
    """
    Manages the JPype JVM lifecycle for the entire test session.
    This fixture is NOT auto-used; it must be requested by another fixture.
    When activated, it:
    1. Ensures all portable dependencies (JDK, Tweety JARs) are provisioned.
    2. Starts the JVM using the centralized jvm_setup module.
    3. Guarantees the JVM is shut down after all tests are complete.
    """
    logger.info("---------- Pytest session starting: Provisioning dependencies and Initializing JVM... ----------")
    
    try:
        logger.info("Checking Tweety JARs location...")
        _ensure_tweety_jars_are_correctly_placed()

        if not is_jvm_started():
            logger.info("Attempting to initialize JVM via core.jvm_setup.initialize_jvm...")
            success = initialize_jvm(session_fixture_owns_jvm=True)
            if success:
                logger.info("JVM started successfully for the test session.")
            else:
                 pytest.fail("JVM initialization failed.", pytrace=False)
        else:
            logger.info("JVM was already started.")
            
    except Exception as e:
        logger.error(f"A critical error occurred during JVM session setup: {e}", exc_info=True)
        pytest.exit(f"JVM setup failed: {e}", 1)

    yield True

    logger.info("---------- Pytest session finished: Shutting down JVM... ----------")
    shutdown_jvm(called_by_session_fixture=True)


@pytest.fixture(scope="function", autouse=True)
def manage_jvm_for_test(request):
    """
    This 'autouse' fixture runs for every test and decides if the global
    `jvm_session` fixture is required by manually invoking it.
    
    It checks for a 'no_jvm_session' marker on the test. If found, it does nothing.
    If not found, it uses `request.getfixturevalue()` to activate the `jvm_session`
    fixture, ensuring the JVM is started for the test.
    """
    if 'no_jvm_session' in request.node.keywords:
        logger.warning(
            f"Test '{request.node.name}' is marked with 'no_jvm_session'. "
            "The global JVM fixture will not be requested for this test."
        )
        yield
    else:
        # Manually trigger the session-scoped JVM fixture.
        # This will only run it once and then retrieve the cached result
        # for all subsequent calls.
        request.getfixturevalue('jvm_session')
        yield


# Charger les fixtures définies dans d'autres fichiers comme des plugins
pytest_plugins = [
   "tests.fixtures.integration_fixtures",
   # "tests.fixtures.jvm_subprocess_fixture", # TEMPORAIREMENT DÉSACTIVÉ - CAUSE UN CRASH JVM
    "pytest_playwright",
    # "tests.mocks.numpy_setup" # DÉSACTIVÉ GLOBALEMENT - Provoque un comportement instable pour les tests E2E
]

@pytest.fixture(autouse=True)
def check_mock_llm_is_forced(request):
    """
    Ce "coupe-circuit" est une sécurité pour tous les tests.
    Il vérifie que nous ne pouvons pas accidentellement utiliser un vrai LLM,
    SAUF si le test est explicitement marqué avec 'real_llm'.
    """
    if 'real_llm' in request.node.keywords:
        logger.warning(f"Le test {request.node.name} utilise le marqueur 'real_llm'. Le mock LLM est désactivé.")
        yield
        return

    # Le reste de la logique de mock s'applique si le marqueur n'est pas présent.
    from argumentation_analysis.core.bootstrap import initialize_project_environment as original_init

    def new_init(*args, **kwargs):
        """
        Wrapper autour de l'initialiseur d'environnement pour forcer le mock LLM.
        """
        if not kwargs.get("force_mock_llm"):
             pytest.fail(
                "ERREUR DE SÉCURITÉ: Appel à initialize_project_environment() sans "
                "'force_mock_llm=True'. Tous les tests doivent forcer l'utilisation "
                "d'un LLM mocké pour éviter d'utiliser des services réels.",
                pytrace=False
            )
        
        # S'assurer que le service_id est correct pour les tests mockés
        service_id = kwargs.get("service_id")
        if service_id and service_id != "default_llm_bootstrap":
            pytest.fail(
                f"ERREUR DE CONFIGURATION TEST: 'service_id' doit être 'default_llm_bootstrap' "
                f"lorsque 'force_mock_llm=True', mais a reçu '{service_id}'.",
                pytrace=False
            )
        
        # Forcer le service_id par défaut pour les tests si non spécifié
        if not service_id:
            kwargs["service_id"] = "default_llm_bootstrap"
            
        return original_init(*args, **kwargs)

    with patch('argumentation_analysis.core.bootstrap.initialize_project_environment', new=new_init):
        yield

def pytest_addoption(parser):
    """Ajoute des options de ligne de commande personnalisées à pytest."""
    parser.addoption(
        "--allow-dotenv", action="store_true", default=False,
        help="Permet le chargement du vrai fichier .env pour les tests (désactive le mock)."
    )
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
    parser.addoption(
        "--skip-octave", action="store_true", default=False,
        help="Saute le téléchargement et la configuration d'Octave."
    )

@pytest.fixture(scope="session")
def backend_url(request):
    """
    Fixture to get the backend URL.
    It prioritizes the BACKEND_URL environment variable, then falls back
    to the --backend-url command-line option.
    """
    return os.environ.get("BACKEND_URL", request.config.getoption("--backend-url"))

@pytest.fixture(scope="session")
def frontend_url(request):
    """
    Fixture to get the frontend URL.
    It prioritizes the FRONTEND_URL environment variable, then falls back
    to the --frontend-url command-line option.
    """
    return os.environ.get("FRONTEND_URL", request.config.getoption("--frontend-url"))

@pytest.fixture(autouse=True)
def mock_crypto_passphrase(monkeypatch):
    """
    Mocks the settings.passphrase for all tests to ensure crypto operations
    have a valid default passphrase.
    """
    from unittest.mock import MagicMock
    mock_passphrase = MagicMock()
    mock_passphrase.get_secret_value.return_value = "test-passphrase-for-crypto"
    monkeypatch.setattr("argumentation_analysis.core.utils.crypto_utils.settings.passphrase", mock_passphrase)
