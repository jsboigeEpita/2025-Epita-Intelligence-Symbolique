import pytest
import jpype
import logging
import os
import time
import nest_asyncio
from pathlib import Path
from argumentation_analysis.core.setup.manage_portable_tools import setup_tools
from argumentation_analysis.core.jvm_setup import initialize_jvm, shutdown_jvm, is_jvm_started
from argumentation_analysis.agents.core.logic.tweety_initializer import TweetyInitializer

logger = logging.getLogger(__name__)

@pytest.fixture(scope="session")
def anyio_backend(request):
    return request.config.getoption("anyio_backend", "asyncio")

@pytest.fixture(scope="session", autouse=True)
def apply_nest_asyncio(anyio_backend):
    """
    Applies nest_asyncio to allow nested event loops.
    This is necessary for running asyncio tests in some environments.
    Only applied for the 'asyncio' backend.
    """
    if anyio_backend == "asyncio":
        logger.info(f"Applying nest_asyncio for '{anyio_backend}' backend.")
        nest_asyncio.apply()
        yield
        logger.info("nest_asyncio teardown for 'asyncio' backend.")
    else:
        logger.info(f"Skipping nest_asyncio for '{anyio_backend}' backend.")
        yield

@pytest.fixture(scope="session", autouse=True)
def jvm_session():
    """
    Manages the JPype JVM lifecycle for the entire test session.
    1. Ensures all portable dependencies (JDK, Tweety JARs) are provisioned.
    2. Starts the JVM using the centralized jvm_setup module.
    3. Shuts down the JVM after all tests are complete.
    """
    logger.info("---------- Pytest session starting: Provisioning dependencies and Initializing JVM... ----------")
    try:
        # Étape 1: Provisioning des outils (JDK et Tweety)
        # La racine du projet est un niveau au-dessus du dossier 'tests'
        project_root = Path(__file__).parent.parent.resolve()
        # Correction: Le répertoire des outils doit pointer vers 'argumentation_analysis/libs'
        tools_dir = project_root / "argumentation_analysis" / "libs"
        tools_dir.mkdir(exist_ok=True)
        logger.info(f"Running dependency provisioning via setup_tools... Tools directory set to {tools_dir}")
        setup_tools(tools_dir_base_path=tools_dir, force_reinstall=False)
        
        # Le script de setup doit définir JAVA_HOME
        if not os.environ.get('JAVA_HOME'):
            pytest.fail("setup_tools() did not set the JAVA_HOME environment variable.", pytrace=False)
        
        logger.info(f"JAVA_HOME is set to: {os.environ.get('JAVA_HOME')}")

        # Étape 2: Démarrage de la JVM
        if not is_jvm_started():
            logger.info("Attempting to initialize JVM via core.jvm_setup.initialize_jvm...")
            # La fixture de session est propriétaire de la JVM
            success = initialize_jvm(session_fixture_owns_jvm=True)
            if success:
                logger.info("JVM started successfully for the test session.")
            else:
                 pytest.fail("JVM initialization failed via core.jvm_setup.initialize_jvm.", pytrace=False)
        else:
            logger.info("JVM was already started.")
            
    except Exception as e:
        logger.error(f"A critical error occurred during test session setup: {e}", exc_info=True)
        pytest.exit(f"Test session setup failed: {e}", 1)

    yield

    logger.info("---------- Pytest session finished: Shutting down JVM... ----------")
    # L'arrêt est géré par la fixture elle-même, donc on passe True
    shutdown_jvm(called_by_session_fixture=True)


# Charger les fixtures définies dans d'autres fichiers comme des plugins
pytest_plugins = [
   "tests.fixtures.integration_fixtures",
   "tests.fixtures.jvm_subprocess_fixture",
    "pytest_playwright",
    "tests.mocks.numpy_setup"
]

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