import pytest
import subprocess
import time
import requests
from requests.exceptions import ConnectionError
import os
import sys
import logging
from typing import Generator
from pathlib import Path
from playwright.sync_api import expect

# Configuration du logger
logger = logging.getLogger(__name__)

def deep_delete_from_sys_modules(module_name_prefix):
    """Supprime un module et tous ses sous-modules de sys.modules."""
    keys_to_delete = [k for k in sys.modules if k == module_name_prefix or k.startswith(module_name_prefix + '.')]
    if keys_to_delete:
        logger.info(f"[E2E Conftest] Nettoyage en profondeur des modules pour le préfixe '{module_name_prefix}': {keys_to_delete}")
    for key in keys_to_delete:
        try:
            del sys.modules[key]
        except KeyError:
            pass

# ============================================================================
# Pytest Configuration Hooks
# ============================================================================

def pytest_configure(config):
    """
    Hook pour configurer pytest avant le début des tests.
    Définit une base_url par défaut si elle n'est pas déjà fournie,
    ce qui est crucial pour les tests UI de Playwright.
    """
    if not config.option.base_url:
        # L'URL du frontend est généralement servie par un serveur de développement React,
        # mais pour les tests E2E, on peut la pointer vers le backend directement
        # si les tests n'interagissent qu'avec l'API via l'UI.
        # Pour une vraie UI, ce serait l'URL du serveur React.
        # On assume que le frontend est servi ou que les tests ne nécessitent que l'API.
        config.option.base_url = os.environ.get("FRONTEND_URL", "http://127.0.0.1:3001")


# ============================================================================
# Simplified Webapp Service Fixture
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def webapp_service() -> Generator:
    """
    Fixture de session E2E complète:
    1. Nettoie l'environnement des mocks (NumPy, JPype).
    2. Initialise le vrai JPype et la JVM.
    3. Démarre l'orchestrateur web complet (backend & frontend).
    4. Exécute les tests.
    5. Arrête proprement l'orchestrateur.
    """
    # 1. Éradiquer les mocks et initialiser la JVM
    logger.info("[E2E Conftest] Éradication de tout mock résiduel.")
    deep_delete_from_sys_modules("numpy")
    deep_delete_from_sys_modules("jpype")
    
    try:
        # S'assurer que le chemin des mocks n'est pas dans sys.path
        mocks_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../mocks'))
        if mocks_path in sys.path:
            sys.path.remove(mocks_path)
            
        import jpype
        import jpype.imports
        from argumentation_analysis.core.jvm_setup import initialize_jvm
        
        logger.info(f"[E2E Conftest] Vrai JPype (version {jpype.__version__}) importé.")
        initialize_jvm(force_restart=False)
        if not jpype.isJVMStarted():
            pytest.fail("[E2E Conftest] La JVM n'a pas pu démarrer après le nettoyage.")

    except Exception as e:
        pytest.fail(f"[E2E Conftest] Échec critique de l'initialisation de JPype/JVM: {e}")

    # 2. Démarrer le serveur backend
    backend_port = 5003
    # L'URL de santé pointe maintenant vers la route /status de l'application Flask
    api_health_url = f"http://127.0.0.1:{backend_port}/status"
    
    # La commande lance maintenant l'application principale Flask (interface_web/app.py)
    # et non plus l'API FastAPI (api/main.py).
    # La commande est modifiée pour utiliser 'python -m uvicorn'.
    # Cela permet à 'environment_manager.py' de la traiter comme une commande Python directe,
    # ce qui est plus robuste car cela évite une couche de 'conda run'.
    command = [
        "powershell", "-File", ".\\activate_project_env.ps1",
        "-CommandToRun", f"python -m uvicorn interface_web.app:app --host 127.0.0.1 --port {backend_port} --log-level debug"
    ]
    
    print(f"\n[E2E Fixture] Starting Flask webapp server on port {backend_port}...")
    
    # Use Popen to run the server in the background
    project_root = Path(__file__).parent.parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    stdout_log_path = log_dir / f"backend_stdout_{backend_port}.log"
    stderr_log_path = log_dir / f"backend_stderr_{backend_port}.log"

    with open(stdout_log_path, "wb") as stdout_log, open(stderr_log_path, "wb") as stderr_log:
        process = subprocess.Popen(
            command,
            stdout=stdout_log,
            stderr=stderr_log,
            cwd=str(project_root),
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP # For Windows to kill the whole process tree
        )
        
        # Wait for the backend to be ready by polling the health endpoint
        start_time = time.time()
        timeout = 90  # 90 seconds timeout for startup
        ready = False
        
        print(f"[E2E Fixture] Waiting for backend at {api_health_url}...")
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(api_health_url, timeout=2)
                # L'application Flask renvoie un JSON. On vérifie que le statut interne est 'operational'.
                if response.status_code == 200 and response.json().get('status') == 'operational':
                    print(f"[E2E Fixture] Flask webapp is ready! (took {time.time() - start_time:.2f}s)")
                    ready = True
                    break
            except ConnectionError:
                time.sleep(1) # Wait and retry
                
        if not ready:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            
            pytest.fail(f"Backend failed to start within {timeout} seconds. Check logs in {log_dir}")

        # At this point, the server is running. Yield control to the tests.
        yield
        
        # Teardown: Stop the server after tests are done
        print("\n[E2E Fixture] Stopping backend server...")
        try:
            if os.name == 'nt':
                # On Windows, terminate the whole process group
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
            else:
                process.terminate()

            process.wait(timeout=10)
        except (subprocess.TimeoutExpired, ProcessLookupError):
            if process.poll() is None:
                print("[E2E Fixture] process.terminate() timed out, killing.")
                process.kill()
        finally:
            print("[E2E Fixture] Backend server stopped.")
# ============================================================================
# Helper Classes
# ============================================================================

class PlaywrightHelpers:
    """
    Classe utilitaire pour simplifier les interactions communes avec Playwright
    dans les tests E2E.
    """
    def __init__(self, page):
        self.page = page

    def navigate_to_tab(self, tab_name: str):
        """
        Navigue vers un onglet spécifié en utilisant son data-testid.
        """
        tab_selector = f'[data-testid="{tab_name}-tab"]'
        tab = self.page.locator(tab_selector)
        expect(tab).to_be_enabled(timeout=15000)
        tab.click()