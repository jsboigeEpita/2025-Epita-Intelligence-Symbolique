#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration pytest globale pour l'ensemble des tests du projet.
"""

import pytest
import logging
import os
import sys
from pathlib import Path
import shutil
from unittest.mock import patch, MagicMock


# Ajouter le répertoire racine au PYTHONPATH pour assurer la découvrabilité des modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Importations nécessaires pour les fixtures ci-dessous
from argumentation_analysis.core.jvm_setup import (
    initialize_jvm, shutdown_jvm, is_jvm_started, is_jvm_owned_by_session_fixture
)
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.models.extract_result import ExtractResult
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract


logger = logging.getLogger(__name__)

# --- Mocking de python-dotenv ---
_dotenv_patcher = None
MOCK_DOTENV = os.environ.get("MOCK_DOTENV_IN_TESTS", "true").lower() in ("true", "1", "t")


def pytest_addoption(parser):
    """Ajoute des options de ligne de commande personnalisées à pytest."""
    parser.addoption(
        "--allow-dotenv", action="store_true", default=False, help="Désactive le mock de dotenv et autorise le chargement du vrai fichier .env."
    )
    parser.addoption(
        "--disable-e2e-servers-fixture", action="store_true", default=False, help="Désactive la fixture qui gère les serveurs E2E."
    )
    parser.addoption("--frontend-url", action="store", default="http://localhost:3000", help="URL pour le serveur frontend E2E.")
    parser.addoption("--backend-url", action="store", default="http://localhost:5003", help="URL pour le serveur backend E2E.")

def pytest_configure(config):
    """
    Hook de configuration précoce de pytest.
    """
    try:
        from argumentation_analysis.core.environment import ensure_env
        ensure_env()
    except RuntimeError as e:
        pytest.exit(f"\n\n[FATAL] ERREUR DE CONFIGURATION DE L'ENVIRONNEMENT:\n{e}", returncode=1)

    global MOCK_DOTENV, _dotenv_patcher
    
    from dotenv import dotenv_values

    if config.getoption("--allow-dotenv"):
        MOCK_DOTENV = False
        print("\n[INFO] Dotenv mocking is DISABLED. Real .env file will be used.")

        project_dir = Path(__file__).parent.parent
        dotenv_path = project_dir / '.env'
        if dotenv_path.exists():
            print(f"[INFO] Loading .env file from: {dotenv_path}")
            
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
    
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "api: marks tests related to the API")
    config.addinivalue_line("markers", "real_llm: marks tests that require a real LLM service")
    config.addinivalue_line("markers", "real_jpype: marks tests that require a real JPype/JVM environment")
    config.addinivalue_line("markers", "no_jvm_session: marks tests that should not start the shared JVM session")

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

def _ensure_tweety_jars_are_correctly_placed():
    """
    Code défensif pour les tests.
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


@pytest.fixture(scope="session", autouse=True)
def apply_nest_asyncio():
    """
    DEPRECATED/DISABLED
    """
    logger.warning("The 'apply_nest_asyncio' fixture in conftest.py is currently disabled to ensure compatibility with Playwright.")
    yield


@pytest.fixture(scope="session")
def jvm_session():
    """
    Manages the JPype JVM lifecycle for the entire test session.
    """
    logger.info("---------- [JVM_SESSION_FIXTURE] Pytest session starting: Provisioning dependencies and Initializing JVM... ----------")
    
    try:
        logger.info("[JVM_SESSION_FIXTURE] STEP 1: Checking Tweety JARs location...")
        _ensure_tweety_jars_are_correctly_placed()
        logger.info("[JVM_SESSION_FIXTURE] STEP 1: Done.")

        logger.info(f"[JVM_SESSION_FIXTURE] STEP 2: Checking if JVM is already started... is_jvm_started() -> {is_jvm_started()}")
        if not is_jvm_started():
            logger.info("[JVM_SESSION_FIXTURE] STEP 3: Attempting to initialize JVM via core.jvm_setup.initialize_jvm...")
            success = initialize_jvm(session_fixture_owns_jvm=True)
            logger.info(f"[JVM_SESSION_FIXTURE] STEP 3: initialize_jvm returned: {success}")
            if success:
                logger.info("[JVM_SESSION_FIXTURE] JVM started successfully for the test session.")
            else:
                 logger.error("[JVM_SESSION_FIXTURE] initialize_jvm returned False. Failing test session.")
                 pytest.fail("JVM initialization failed as reported by initialize_jvm.", pytrace=False)
        else:
            logger.warning("[JVM_SESSION_FIXTURE] JVM was already started. Assuming it is correctly configured.")
            
    except Exception as e:
        logger.error(f"[JVM_SESSION_FIXTURE] A critical error occurred during JVM session setup: {e}", exc_info=True)
        pytest.exit(f"JVM setup failed with exception: {e}", 1)

    logger.info("[JVM_SESSION_FIXTURE] Handing over control to tests (yield)...")
    yield True

    logger.info("---------- [JVM_SESSION_FIXTURE] Pytest session finished: Shutting down JVM... ----------")
    logger.info(f"[JVM_SESSION_FIXTURE] Checking ownership before shutdown... is_jvm_owned_by_session_fixture() -> {is_jvm_owned_by_session_fixture()}")
    if is_jvm_owned_by_session_fixture():
        shutdown_jvm(called_by_session_fixture=True)
    else:
        logger.warning("[JVM_SESSION_FIXTURE] The JVM is not (or no longer) controlled by the global fixture. It will not be shut down here.")

@pytest.fixture(scope="function", autouse=True)
def manage_jvm_for_test(request):
    """
    This 'autouse' fixture runs for every test and decides if the global
    `jvm_session` fixture is required by manually invoking it.
    """
    if 'no_jvm_session' in request.node.keywords:
        logger.debug(
            f"Test '{request.node.name}' is marked with 'no_jvm_session'. "
            "The global JVM fixture will not be requested for this test."
        )
        yield
    else:
        request.getfixturevalue('jvm_session')
        yield


# Charger les fixtures définies dans d'autres fichiers comme des plugins
pytest_plugins = [
   "tests.fixtures.integration_fixtures",
   "tests.fixtures.jvm_subprocess_fixture",
    "pytest_playwright",
]

@pytest.fixture(scope="function", autouse=True)
def check_mock_llm_is_forced(request, monkeypatch):
    """
    Ce "coupe-circuit" est une sécurité pour tous les tests.
    """
    from argumentation_analysis.config.settings import settings
    if 'real_llm' in request.node.keywords:
        logger.warning(f"Le test {request.node.name} utilise le marqueur 'real_llm'. Le mock LLM est désactivé.")
        monkeypatch.setattr(settings, 'MOCK_LLM', False)
        monkeypatch.setattr(settings, 'use_mock_llm', False)
        yield
    else:
        monkeypatch.setattr(settings, 'MOCK_LLM', True)
        monkeypatch.setattr(settings, 'use_mock_llm', True)
        yield
        
@pytest.fixture(scope="session")
def backend_url(request):
    """Provides the backend URL from command-line options."""
    return request.config.getoption("--backend-url")
        
@pytest.fixture
def mock_kernel():
    """Provides a mocked Semantic Kernel."""
    kernel = MagicMock()
    kernel.plugins = MagicMock()
    mock_plugin = MagicMock()
    mock_function = MagicMock()
    mock_function.invoke.return_value = '{"formulas": ["exists X: (Cat(X))"]}'
    mock_plugin.__getitem__.return_value = mock_function
    kernel.plugins.__getitem__.return_value = mock_plugin
    return kernel

@pytest.fixture
def fol_agent(mock_kernel):
    """Provides a concrete, testable instance of FOLLogicAgent."""

    class ConcreteFOLAgent(FOLLogicAgent):
        async def validate_argument(self, premises: list[str], conclusion: str, **kwargs) -> bool:
            return True

    agent = ConcreteFOLAgent(kernel=mock_kernel, agent_name="fol_test_agent")
    agent._tweety_bridge = MagicMock()
    agent._tweety_bridge.validate_fol_belief_set.return_value = (True, "Valid")
    return agent

@pytest.fixture
def extract_result_dict():
    """Provides a dictionary for a valid ExtractResult."""
    return {
        "source_name": "Test Source",
        "extract_name": "Test Extract",
        "status": "valid",
        "message": "Extraction réussie",
        "start_marker": "DEBUT_EXTRAIT",
        "end_marker": "FIN_EXTRAIT",
        "template_start": "T{0}",
        "explanation": "Explication de l'extraction",
        "extracted_text": "Texte extrait de test"
    }

@pytest.fixture
def valid_extract_result(extract_result_dict):
    """Provides a valid instance of ExtractResult."""
    return ExtractResult.from_dict(extract_result_dict)

@pytest.fixture
def error_extract_result(extract_result_dict):
    """Provides an error instance of ExtractResult."""
    error_dict = extract_result_dict.copy()
    error_dict["status"] = "error"
    error_dict["message"] = "Erreur lors de l'extraction"
    return ExtractResult.from_dict(error_dict)

@pytest.fixture
def rejected_extract_result(extract_result_dict):
    """Provides a rejected instance of ExtractResult."""
    rejected_dict = extract_result_dict.copy()
    rejected_dict["status"] = "rejected"
    rejected_dict["message"] = "Extraction rejetée"
    return ExtractResult.from_dict(rejected_dict)

@pytest.fixture
def sample_definitions():
    """Provides a sample ExtractDefinitions object for tests."""
    extract = Extract(
        extract_name="Test Extract",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT",
        template_start="T{0}"
    )
    source = SourceDefinition(
        source_name="Test Source",
        source_type="url",
        schema="https",
        host_parts=["example", "com"],
        path="/test",
        extracts=[extract]
    )
    return ExtractDefinitions(sources=[source])

@pytest.fixture
def mock_parse_args(mocker):
    """Fixture to mock argparse.ArgumentParser.parse_args."""
    return mocker.patch("argparse.ArgumentParser.parse_args")

@pytest.fixture
def successful_simple_argument_analysis_fixture_path(tmp_path):
    """
    Creates a temporary JSON file for testing the successful
    analysis of a simple argument.
    """
    data = {
        "text": "Socrates is a man, all men are mortal, therefore Socrates is mortal.",
        "analysis_mode": "simple"
    }
    file_path = tmp_path / "simple_argument.json"
    file_path.write_text(json.dumps(data))
    return str(file_path)
