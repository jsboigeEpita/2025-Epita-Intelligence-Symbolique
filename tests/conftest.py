from unittest.mock import patch
patch('dotenv.main.dotenv_values', return_value={}, override=True).start()

import pytest
import jpype
import logging
import os
import threading
import time
import nest_asyncio
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
    Starts the JVM before any tests run and shuts it down after all tests are complete.
    """
    logger.info("---------- Pytest session starting: Initializing JVM... ----------")
    try:
        if not jpype.isJVMStarted():
            TweetyInitializer.initialize_jvm()
            logger.info("JVM started successfully for the test session.")
        else:
            logger.info("JVM was already started.")
    except Exception as e:
        logger.error(f"Failed to start JVM: {e}", exc_info=True)
        pytest.exit(f"JVM initialization failed: {e}", 1)

    yield

    logger.info("---------- Pytest session finished: Shutting down JVM... ----------")
    try:
        if jpype.isJVMStarted():
            logger.info("Preparing to shut down JVM. Waiting 1 second...")
            time.sleep(1)
            jpype.shutdownJVM()
            logger.info("JVM shut down successfully.")
        else:
            logger.info("JVM was already shut down or never started.")
    except Exception as e:
        logger.error(f"Error shutting down JVM: {e}", exc_info=True)

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