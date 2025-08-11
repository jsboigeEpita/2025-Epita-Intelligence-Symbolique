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
import asyncio
from pathlib import Path
import shutil
from unittest.mock import patch, MagicMock
import nest_asyncio
import jpype
from unittest.mock import patch, MagicMock

# --- Mocking global pour les tests E2E ---
# Si --disable-jvm-session est présent, on mocke jpype AVANT toute autre importation.
_disable_jvm_early_check = any(arg == '--disable-jvm-session' for arg in sys.argv)
if _disable_jvm_early_check:
    print("[INFO] Early check: --disable-jvm-session detected. Mocking jpype globally.")
    sys.modules['jpype'] = MagicMock()
    sys.modules['jpype.imports'] = MagicMock()

# Désactive la vérification de l'environnement Conda pour les tests E2E
os.environ['E2E_TESTING_MODE'] = '1'

# --- Importations préventives pour éviter les conflits de bas niveau ---
# NOTE: Ce bloc a été déplacé dans la fixture `jvm_session` pour garantir
# que les imports ont lieu dans le bon contexte, juste avant l'initialisation de la JVM.



# Ajouter le répertoire racine et les sous-répertoires pertinents au PYTHONPATH
project_root = Path(__file__).parent.parent
additional_paths = [
    str(project_root),
    str(project_root / "scripts"),
    str(project_root / "examples" / "scripts_demonstration"),
    str(project_root / "services"),
]
for path in additional_paths:
    if path not in sys.path:
        sys.path.insert(0, path)

# Importations nécessaires pour les fixtures ci-dessous
from argumentation_analysis.core.jvm_setup import is_jvm_started, initialize_jvm, shutdown_jvm
from argumentation_analysis.agents.core.logic.tweety_initializer import TweetyInitializer
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
    parser.addoption(
        "--disable-jvm-session", action="store_true", default=False, help="Désactive complètement la fixture de session JVM."
    )
    parser.addoption("--frontend-url", action="store", default="http://localhost:8085", help="URL pour le serveur frontend E2E.")
    parser.addoption("--backend-url", action="store", default="http://localhost:8095", help="URL pour le serveur backend E2E.")

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

    # Désactive dynamiquement le plugin opentelemetry pour éviter les conflits
    # avec jpype, qui peuvent causer un crash "access violation" sur Windows.
    if "opentelemetry" in config.pluginmanager.list_name_plugin():
        plugin = config.pluginmanager.get_plugin("opentelemetry")
        config.pluginmanager.unregister(plugin)
        print("Plugin opentelemetry désenregistré pour éviter le crash de la JVM.", file=sys.stderr)

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
    config.addinivalue_line("markers", "jvm_test: marks tests that require the JVM to be started.")

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
        nest_asyncio.apply() # Réactivé pour corriger le crash de la JVM
        logger.info("nest_asyncio.apply() has been re-enabled to prevent JVM crashes.")
    except ImportError:
        logger.error("`nest_asyncio` is not installed. Please install it with `pip install nest-asyncio`.")
        pytest.fail("Missing dependency: nest_asyncio is required for running async tests with Playwright.", pytrace=False)
    yield


@pytest.fixture(scope="session")
def jvm_session(request):
    """
    Fixture de session pour démarrer et arrêter la JVM une seule fois pour tous les tests.
    """
    # Option pour désactiver complètement la JVM pour une session de test (ex: E2E)
    if request.config.getoption("--disable-jvm-session"):
        logger.warning("La fixture jvm_session est désactivée via --disable-jvm-session.")
        yield
        return

    # Marqueur pour les tests qui ne doivent pas utiliser la JVM partagée.
    if 'no_jvm_session' in request.node.keywords:
        yield
        return

    logger.info("=" * 80)
    logger.info(f" début de la fixture jvm_session pour le test : {request.node.name} ")
    logger.info("=" * 80)

    # --- Importations préventives pour éviter les conflits de bas niveau ---
    # Il est crucial d'importer les bibliothèques lourdes comme torch et transformers
    # AVANT que jpype ne soit initialisé pour éviter des crashs de type "access violation".
    logger.info("[INFO] Pre-importing heavy libraries inside jvm_session to prevent conflicts...")
    try:
        import torch
        import transformers
        import semantic_kernel
        import openai
        logger.info("[INFO] Heavy libraries pre-imported successfully inside jvm_session.")
    except ImportError as e:
        logger.warning(f"[WARNING] A library pre-import failed inside jvm_session: {e}.")
    
    # On s'assure que la structure des JARs est correcte avant tout.
    # _ensure_tweety_jars_are_correctly_placed() # This logic is now in jvm_setup
    
    # Démarrage de la JVM. Le drapeau `session_fixture_owns_jvm=True` indique
    # que cette fixture est propriétaire de la JVM et est la seule autorisée à l'arrêter.
    initialize_jvm(session_fixture_owns_jvm=True)
    
    # La fixture cède le contrôle aux tests.
    yield
    
    # Le code après yield est exécuté à la fin de la session de test.
    logger.info("=" * 80)
    logger.info(f" Fin de la fixture jvm_session pour le test : {request.node.name} ")
    logger.info("=" * 80)
    
    # On arrête la JVM en indiquant que c'est bien la fixture de session qui le demande.
    # shutdown_jvm(called_by_session_fixture=True) # Désactivé car notoirement instable.
    logger.warning("L'arrêt de la JVM est désactivé à la fin de la session pour éviter les crashs.")

# La fixture jvm_fixture est supprimée car elle est la source des conflits.
# La gestion de la JVM est maintenant entièrement centralisée dans jvm_session.

@pytest.fixture(scope="function")
def tweety_bridge_fixture(jvm_session):
    """
    Fournit une instance de TweetyBridge connectée à la session JVM gérée
    par la fixture jvm_session.
    """
    # La dépendance à jvm_session garantit que la JVM est démarrée avant
    # l'exécution de ce code.
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
    logger.info("Création de l'instance TweetyBridge pour la fixture...")

    # Vérification explicite que la JVM est bien démarrée par la session
    assert is_jvm_started(), "La fixture jvm_session n'a pas réussi à démarrer la JVM."

    bridge = TweetyBridge()
    assert bridge.initializer.is_jvm_ready(), "La JVM devrait être prête grâce à jvm_session"
    logger.info("Instance TweetyBridge créée avec succès.")
    yield bridge



# Charger les fixtures définies dans d'autres fichiers comme des plugins
pytest_plugins = [
   "tests.fixtures.jvm_subprocess_fixture",
    "pytest_playwright",
]

# --- Chargement conditionnel des fixtures lourdes ---
# Ne charge les fixtures d'intégration (qui dépendent de la JVM) que si
# la session JVM n'est pas explicitement désactivée.
# Cela évite à pytest de tenter de résoudre la fixture jvm_session
# lorsque nous savons qu'elle ne sera pas disponible.
import pytest
_disable_jvm = any(arg == '--disable-jvm-session' for arg in sys.argv)

if not _disable_jvm:
    pytest_plugins.append("tests.fixtures.integration_fixtures")
else:
    # Utilise print pour s'assurer que le message est visible même si le logging n'est pas encore configuré
    print("\n[INFO] Fixtures d'intégration (integration_fixtures.py) non chargées en raison de l'option --disable-jvm-session.")
    # Utilise print pour s'assurer que le message est visible même si le logging n'est pas encore configuré
    print("\n[INFO] Fixtures d'intégration (integration_fixtures.py) non chargées en raison de l'option --disable-jvm-session.")

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

import subprocess
import time
import requests

def _wait_for_server(url: str, process: subprocess.Popen, timeout: int = 120):
    """Attend qu'un serveur soit disponible ou que le processus se termine."""
    start_time = time.time()
    try:
        while time.time() - start_time < timeout:
            # Vérifie si le processus a terminé prématurément
            if process.poll() is not None:
                # Le serveur s'est arrêté, on lève une erreur avec sa sortie
                stdout, stderr = process.communicate()
                stdout_decoded = stdout.decode('utf-8', 'ignore')
                stderr_decoded = stderr.decode('utf-8', 'ignore')
                
                # Utiliser le logger pour s'assurer que la sortie est capturée par pytest
                logger.error(f"Le serveur {url} a terminé prématurément. Code: {process.poll()}")
                logger.error(f"--- STDOUT DU SERVEUR ---\n{stdout_decoded}")
                logger.error(f"--- STDERR DU SERVEUR ---\n{stderr_decoded}")
                
                raise RuntimeError(
                    f"Le serveur à l'adresse {url} a terminé prématurément avec le code {process.poll()}.\n"
                    f"STDOUT:\n{stdout_decoded}\n\n"
                    f"STDERR:\n{stderr_decoded}"
                )

            try:
                response = requests.get(f"{url}/api/health", timeout=5)
                if response.status_code == 200:
                    logger.info(f"Serveur à l'adresse {url} est prêt !")
                    return True
            except requests.ConnectionError:
                time.sleep(2)  # Attend un peu avant de réessayer
            except requests.Timeout:
                logger.warning(f"Timeout lors de la connexion à {url}. Réessai...")
        
        # Si la boucle se termine, c'est un timeout
        raise TimeoutError(f"Le serveur à l'adresse {url} n'a pas démarré dans le temps imparti de {timeout}s.")
    finally:
        # Dans tous les cas (succès, exception), si le processus est toujours en vie mais que
        # la fonction se termine (par ex. timeout), on essaie de récupérer sa sortie.
        if process.poll() is None:
             logger.info("Le processus serveur est toujours en cours d'exécution après la fin de la vérification.")
        else:
            # S'il y a eu un timeout et que le processus s'est terminé entre-temps,
            # on tente une dernière fois de récupérer sa sortie pour le débogage.
            try:
                stdout, stderr = process.communicate(timeout=5) # Petit timeout pour ne pas bloquer
                logger.error("SORTIE DU SERVEUR CAPTURÉE APRÈS TIMEOUT:")
                logger.error(f"STDOUT:\n{stdout.decode('utf-8', 'ignore')}")
                logger.error(f"STDERR:\n{stderr.decode('utf-8', 'ignore')}")
            except subprocess.TimeoutExpired:
                logger.error("Impossible de récupérer la sortie du processus serveur après le timeout (il est peut-être bloqué).")
            except Exception as e:
                 logger.error(f"Une erreur est survenue en tentant de récupérer la sortie du serveur après timeout: {e}")

def _kill_process(proc):
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=10)
            logger.info(f"Processus {proc.pid} terminé avec la méthode terminate().")
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
            logger.warning(f"Processus {proc.pid} ne répondait pas, il a été tué (kill).")
        except Exception as e:
            logger.error(f"Erreur en terminant le processus {proc.pid}: {e}")

@pytest.fixture(scope="session")
def e2e_servers(request):
    """
    Fixture de session qui démarre et gère les serveurs backend et frontend pour les tests E2E.
    Elle utilise `subprocess.Popen` et garantit l'arrêt des serveurs à la fin.
    """
    if request.config.getoption("--disable-e2e-servers-fixture"):
        logger.info("Fixture e2e_servers désactivée via l'option en ligne de commande.")
        yield None, None
        return

    backend_url = request.config.getoption("--backend-url")
    frontend_url = request.config.getoption("--frontend-url")
    project_root = Path(__file__).parent.parent
    
    backend_process = None
    frontend_process = None

    try:
        # --- Démarrage du serveur Backend (Application Flask en tant que module) ---
        backend_module = "services.web_api_from_libs.app"
        backend_command = [sys.executable, "-m", backend_module]
        
        backend_port = backend_url.split(":")[-1]

        # --- Définition de l'environnement pour le sous-processus Backend ---
        # Il est crucial de reconstruire un environnement propre qui inclut
        # les variables du .env, car Popen n'hérite pas automatiquement de celles
        # chargées par pytest-dotenv dans le processus principal.
        from dotenv import dotenv_values

        # 1. Copier l'environnement courant
        backend_env = os.environ.copy()

        # 2. Charger les variables du fichier .env
        dotenv_path = project_root / '.env'
        if dotenv_path.exists():
            logger.info(f"Chargement des variables depuis {dotenv_path} pour le sous-processus backend.")
            env_vars = dotenv_values(dotenv_path)
            backend_env.update(env_vars)
            logger.info(f"{len(env_vars)} variables chargées. Clé OPENAI_API_KEY présente: {'OPENAI_API_KEY' in backend_env}")

        # 3. Ajouter/Surcharger les variables spécifiques au test
        backend_env["PORT"] = backend_port
        backend_env["PYTHONPATH"] = str(project_root)

        logger.info(f"Démarrage du serveur backend Flask avec la commande: {' '.join(backend_command)}")
        backend_process = subprocess.Popen(
            backend_command,
            cwd=project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=backend_env
        )

        # Attendre que le backend soit prêt
        _wait_for_server(backend_url, backend_process)

        # --- Démarrage du serveur Frontend ---
        frontend_command = ["npm", "start"]
        frontend_dir = project_root / "interface_web"
        # Création d'un environnement pour le frontend avec le port personnalisé
        frontend_env = os.environ.copy()
        frontend_env["PORT"] = frontend_url.split(":")[-1]
        
        logger.info(f"Démarrage du serveur frontend dans '{frontend_dir}' avec la commande: {' '.join(frontend_command)}")
        frontend_process = subprocess.Popen(
            frontend_command,
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=frontend_env,
            shell=True
        )

        # Simple attente pour le frontend, car il n'a pas de healthcheck standard
        logger.info("Attente de 15 secondes pour le démarrage du serveur frontend...")
        time.sleep(15)

        yield backend_url, frontend_url

    finally:
        logger.info("--- Nettoyage de la fixture e2e_servers ---")
        _kill_process(frontend_process)
        _kill_process(backend_process)
        logger.info("Serveurs E2E terminés.")
