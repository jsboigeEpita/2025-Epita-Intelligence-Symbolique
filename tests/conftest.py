import json
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
import nest_asyncio


# Ajouter le répertoire racine au PYTHONPATH pour assurer la découvrabilité des modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Importations nécessaires pour les fixtures ci-dessous
from argumentation_analysis.core.jvm_setup import is_jvm_started, initialize_jvm, shutdown_jvm
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.models.extract_result import ExtractResult
from argumentation_analysis.models.extract_definition import ExtractDefinitions, SourceDefinition, Extract


logger = logging.getLogger(__name__)

# --- Mocking de python-dotenv ---
_dotenv_patcher = None
MOCK_DOTENV = os.environ.get("MOCK_DOTENV_IN_TESTS", "false").lower() in ("true", "1", "t")


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
    # ========================== VÉRIFICATION CRITIQUE DE L'ENVIRONNEMENT ==========================
    # Le bloc suivant est essentiel pour garantir que les tests s'exécutent dans le bon environnement Conda.
    # NE PAS COMMENTER OU DÉSACTIVER, sauf en cas de maintenance délibérée de l'infrastructure de test.
    try:
        from argumentation_analysis.core.environment import ensure_env
        ensure_env()
    except RuntimeError as e:
        pytest.exit(f"\n\n[FATAL] ERREUR DE CONFIGURATION DE L'ENVIRONNEMENT:\n{e}", returncode=1)
    # ===============================================================================================

    global MOCK_DOTENV, _dotenv_patcher
    
    from dotenv import dotenv_values

    if config.getoption("--allow-dotenv"):
        MOCK_DOTENV = False
        print("\n[INFO] Dotenv mocking is DISABLED. Real .env file will be used.")

        project_dir = Path(__file__).parent.parent
        # Hiérarchie de chargement: .env.test > .env
        dotenv_test_path = project_dir / '.env.test'
        dotenv_path = project_dir / '.env'

        if dotenv_test_path.exists():
            print(f"[INFO] Loading .env.test file from: {dotenv_test_path}")
            env_vars = dotenv_values(dotenv_path=dotenv_test_path)
        elif dotenv_path.exists():
            print(f"[INFO] Loading .env file from: {dotenv_path}")
            env_vars = dotenv_values(dotenv_path=dotenv_path)
        else:
            env_vars = {}
            print("[INFO] No .env or .env.test file found.")

        if env_vars:
            
            if not env_vars:
                print(f"[WARNING] .env file found at '{dotenv_path}' but it seems to be empty.")
                return

            updated_vars = 0
            for key, value in env_vars.items():
                if value is not None:
                    if key in os.environ:
                        print(f"[INFO] Overriding existing environment variable '{key}'.")
                    os.environ[key] = value
                    updated_vars += 1
                else:
                    print(f"[WARNING] Skipping .env variable '{key}' because its value is None.")
            
            print(f"[INFO] Loaded {updated_vars} variables from .env into os.environ.")
            
            if 'OPENAI_API_KEY' not in os.environ:
                 print(f"[WARNING] OPENAI_API_KEY was not found in the loaded .env variables.")
            else:
                 print("[INFO] OPENAI_API_KEY successfully loaded.")

        else:
            print(f"[INFO] No .env file found at '{dotenv_path}'.")
    
    # --- Désactivation d'OpenTelemetry pour les tests ---
    # Pour éviter les erreurs de connexion pendant les tests, nous désactivons
    # explicitement les exportateurs OTLP, sauf si demandé autrement.
    print("\\n[INFO] Disabling OpenTelemetry exporters for tests by default.")
    os.environ["OTEL_TRACES_EXPORTER"] = "none"
    os.environ["OTEL_METRICS_EXPORTER"] = "none"
    os.environ["OTEL_LOGS_EXPORTER"] = "none"

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

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Fixture de session pour configurer l'environnement de test global.
    Définit une variable d'environnement pour signaler que les tests sont en cours.
    """
    os.environ['PYTEST_RUNNING'] = '1'
    logger.info("Variable d'environnement 'PYTEST_RUNNING' définie à '1'.")
    yield
    del os.environ['PYTEST_RUNNING']
    logger.info("Variable d'environnement 'PYTEST_RUNNING' supprimée.")


@pytest.fixture(scope="session", autouse=True)
def apply_nest_asyncio():
    """
    Applique nest_asyncio pour permettre l'exécution de boucles d'événements imbriquées,
    ce qui est crucial pour la compatibilité entre pytest-asyncio et Playwright.
    """
    try:
        import nest_asyncio
        nest_asyncio.apply()
        logger.info("nest_asyncio patch applied successfully.")
    except ImportError:
        logger.error("`nest_asyncio` is not installed. Please install it with `pip install nest-asyncio`.")
        pytest.fail("Missing dependency: nest_asyncio is required for running async tests with Playwright.", pytrace=False)
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
        # This part of the logic seems to be handled elsewhere now, so we keep it minimal.
        
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
    """
    Provides a mocked Semantic Kernel that is compatible with Pydantic validation.
    It returns a real Kernel instance with a mocked chat completion service.
    """
    try:
        import semantic_kernel as sk
        from argumentation_analysis.core.llm_service import MockChatCompletion
    except ImportError:
        pytest.fail("Failed to import semantic_kernel or MockChatCompletion for mock_kernel fixture.")

    kernel = sk.Kernel()
    mock_service = MockChatCompletion(service_id="mock_service", ai_model_id="mock_model")
    kernel.add_service(mock_service)
    
    # Conserver une certaine compatibilité avec l'ancien mock pour les plugins si nécessaire
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

@pytest.fixture(scope="function")
def page_with_console_logs(page: "Page"):
    """
    Wraps the Playwright page to automatically log console messages,
    especially JS errors.
    """
    def handle_console_message(msg):
        # Filtrer pour ne montrer que les messages pertinents (erreurs, warnings)
        if msg.type.lower() in ['error', 'warning']:
            print(f"\n[CONSOLE {msg.type.upper()}] {msg.text}")
            # Si c'est une erreur, afficher la pile d'appels si disponible
            if msg.location:
                print(f"    at {msg.location['url']}:{msg.location['lineNumber']}:{msg.location['columnNumber']}")

    page.on("console", handle_console_message)
    yield page
    # Le nettoyage se fait automatiquement à la fin du test
    page.remove_listener("console", handle_console_message)


# --- Gestion des Serveurs E2E ---

@pytest.fixture(scope="session")
def e2e_servers(request):
    """
    Fixture de session pour démarrer et arrêter les serveurs backend et frontend
    nécessaires pour les tests E2E.
    """
    # Forcer l'initialisation des dépendances lourdes avant de démarrer les serveurs
    from argumentation_analysis.services.web_api.app import initialize_heavy_dependencies
    initialize_heavy_dependencies()

    if request.config.getoption("--disable-e2e-servers-fixture"):
        logger.warning("E2E servers fixture is disabled via command-line flag.")
        yield None, None
        return

    import subprocess
    import requests
    import signal
    import time
    import re

    # --- Helper pour nettoyer les ports ---
    def _kill_process_using_port(port: int):
        if sys.platform != "win32":
            logger.warning(f"Port cleanup function is only implemented for Windows. Skipping for port {port}.")
            return
        
        try:
            logger.info(f"Checking if port {port} is in use...")
            # Exécute netstat pour trouver le PID utilisant le port
            result = subprocess.run(
                ["netstat", "-aon"],
                capture_output=True,
                text=True,
                check=True
            )
            
            # Chercher la ligne correspondant au port
            pid_found = None
            for line in result.stdout.splitlines():
                if f":{port}" in line and 'LISTENING' in line:
                    # La sortie est du genre: '  TCP    0.0.0.0:5003           0.0.0.0:0              LISTENING       12345'
                    match = re.search(r'LISTENING\s+(\d+)', line)
                    if match:
                        pid_found = match.group(1)
                        logger.warning(f"Port {port} is currently being used by PID {pid_found}.")
                        break
            
            if pid_found:
                logger.info(f"Attempting to terminate process with PID {pid_found}...")
                kill_result = subprocess.run(
                    ["taskkill", "/PID", pid_found, "/F"],
                    capture_output=True,
                    text=True
                )
                if kill_result.returncode == 0:
                    logger.info(f"Successfully terminated process {pid_found}.")
                else:
                    # Il se peut que le processus se soit terminé entre-temps
                    logger.warning(f"Could not terminate process {pid_found}. It might have already finished. Output: {kill_result.stdout} {kill_result.stderr}")
                
                time.sleep(2) # Laisser le temps au port de se libérer
            else:
                logger.info(f"Port {port} is free.")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Failed to check or kill process for port {port}: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during port cleanup for port {port}: {e}", exc_info=True)


    processes = []
    backend_url_opt = request.config.getoption("--backend-url")
    frontend_url_opt = request.config.getoption("--frontend-url")
    
    project_root = Path(__file__).parent.parent
    
    # Création d'un répertoire pour les logs des serveurs E2E
    log_dir = project_root / "_e2e_logs"
    log_dir.mkdir(exist_ok=True)
    logger.info(f"E2E server logs will be stored in: {log_dir.resolve()}")
    
    # Ouverture des fichiers de log
    backend_log_file = open(log_dir / "backend.log", "w", encoding="utf-8")
    frontend_log_file = open(log_dir / "frontend.log", "w", encoding="utf-8")
    
    # --- Helper Functions (tirées de test_react_interface_complete.py) ---
    def wait_for_service(url, name, timeout=60):
        logger.info(f"Waiting for {name} on {url}...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code in [200, 404]: # 404 is ok for base URL of an API
                    logger.info(f"[OK] {name} available after {time.time() - start_time:.1f}s")
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        logger.error(f"[ERROR] {name} not available after {timeout}s")
        return False

    def start_backend():
        logger.info("--- Starting E2E Backend Server (Forced) ---")

        backend_cmd = [
            sys.executable,
            str(project_root / "scripts" / "run_e2e_backend.py")
        ]
        
        logger.info(f"Running backend command: {' '.join(backend_cmd)}")
        process = subprocess.Popen(backend_cmd, cwd=str(project_root), stdout=backend_log_file, stderr=subprocess.STDOUT)
        if wait_for_service(f"{backend_url_opt}/api/health", "Backend API"):
            logger.info("Backend server started successfully.")
            return process
        else:
            logger.error("Failed to start backend server. Check '_e2e_logs/backend_launcher.log' for details.")
            process.terminate()
            return None

    def start_frontend():
        logger.info("--- Starting E2E Frontend Server (Forced) ---")
            
        react_dir = project_root / "services" / "web_api" / "interface-web-argumentative"
        if not (react_dir / "node_modules").exists():
            logger.info("Installing npm dependencies for frontend...")
            subprocess.run("npm install", cwd=str(react_dir), shell=True, check=True)

        env = os.environ.copy()
        env["BROWSER"] = "none"
        env["PORT"] = "3000"
        env["REACT_APP_BACKEND_URL"] = backend_url_opt

        logger.info(f"Running frontend command: npm start in {react_dir}")
        process = subprocess.Popen("npm start", cwd=str(react_dir), stdout=frontend_log_file, stderr=subprocess.STDOUT, env=env, shell=True)
        if wait_for_service(frontend_url_opt, "Frontend React"):
            logger.info("Frontend server started successfully. Adding a stabilization delay.")
            time.sleep(5) # Ajout d'une attente de stabilisation pour le serveur de dév React
            return process
        else:
            logger.error("Failed to start frontend server.")
            process.terminate()
            return None

    # --- Démarrage ---
    logger.info("=== E2E Servers Fixture Setup ===")
    
    # Nettoyage préventif des ports
    _kill_process_using_port(5003) # Backend
    _kill_process_using_port(3000) # Frontend
    
    backend_process = start_backend()
    frontend_process = start_frontend()
    
    if backend_process:
        processes.append(("Backend", backend_process))
    if frontend_process:
        processes.append(("Frontend", frontend_process))

    yield backend_url_opt, frontend_url_opt

    # --- Nettoyage ---
    logger.info("=== E2E Servers Fixture Teardown ===")
    
    # Fermeture des fichiers de log
    backend_log_file.close()
    frontend_log_file.close()
    
    for name, process in reversed(processes):
        if process:
            logger.info(f"Stopping {name} server (PID: {process.pid})...")
            if sys.platform == "win32":
                # Utilisation de taskkill pour un nettoyage plus robuste sur Windows
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    logger.info(f"Process {name} (PID: {process.pid}) and its children terminated successfully.")
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    logger.warning(f"Could not terminate process {name} (PID: {process.pid}) using taskkill. Error: {e}. Falling back to process.kill().")
                    process.kill() # Fallback au cas où taskkill échouerait
            else:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Process {name} did not terminate gracefully. Killing it.")
                    process.kill()

    logger.info("E2E servers teardown complete.")
