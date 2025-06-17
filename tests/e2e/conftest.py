import pytest
import subprocess
import time
import requests
from requests.exceptions import ConnectionError
import os
import sys
import logging
import socket
import asyncio
from typing import Generator, Dict
from pathlib import Path
from playwright.sync_api import expect

from project_core.webapp_from_scripts.frontend_manager import FrontendManager

# Configuration du logger
logger = logging.getLogger(__name__)

def find_free_port():
    """Trouve et retourne un port TCP libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

# ============================================================================
# Webapp Service Fixture for E2E Tests
# ============================================================================

@pytest.fixture(scope="session")
async def webapp_service() -> Generator[Dict[str, str], None, None]:
    """
    Fixture de session qui démarre et arrête les serveurs backend (Uvicorn)
    et frontend (React).
    S'assure que la JVM est réinitialisée, utilise un port libre et s'assure
    que l'environnement est propagé.
    """
    # 1. S'assurer d'un environnement JVM propre avant de faire quoi que ce soit
    # Le démarrage de la JVM est maintenant entièrement délégué au serveur backend.
    # Le processus de test n'interagit plus du tout avec JPype.

    # 2. Démarrer le serveur backend sur un port libre
    host = "127.0.0.1"
    backend_port = find_free_port()
    base_url = f"http://{host}:{backend_port}"
    api_health_url = f"{base_url}/api/status" # Note: app.py définit le préfixe /api

    # Mettre à jour la variable d'environnement pour que les tests API la trouvent.
    os.environ["BACKEND_URL"] = base_url

    # La commande doit maintenant utiliser le script d'activation pour garantir
    # que l'environnement du sous-processus est correctement configuré.
    project_root = Path(__file__).parent.parent.parent
    activation_script = project_root / "activate_project_env.ps1"
    
    # La commande à exécuter par le script d'activation
    backend_command_to_run = (
        f"python -m uvicorn interface_web.app:app "
        f"--host {host} --port {backend_port} --log-level debug"
    )

    # Commande complète pour Popen
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command",
        f"& '{activation_script}' -CommandToRun \"{backend_command_to_run}\""
    ]

    print(f"\n[E2E Fixture] Starting Starlette webapp server on port {backend_port} via activation script...")
    print(f"[E2E Fixture] Full command: {' '.join(command)}")

    # Use Popen to run the server in the background
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)

    stdout_log_path = log_dir / f"backend_stdout_{backend_port}.log"
    stderr_log_path = log_dir / f"backend_stderr_{backend_port}.log"

    # Préparation de l'environnement pour le sous-processus
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")

    with open(stdout_log_path, "wb") as stdout_log, open(stderr_log_path, "wb") as stderr_log:
        process = subprocess.Popen(
            command,
            stdout=stdout_log,
            stderr=stderr_log,
            cwd=str(project_root),
            env=env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )

        # Wait for the backend to be ready by polling the health endpoint
        start_time = time.time()
        timeout = 300  # 300 seconds (5 minutes) timeout for startup
        ready = False

        print(f"[E2E Fixture] Waiting for backend at {api_health_url}...")

        while time.time() - start_time < timeout:
            try:
                response = requests.get(api_health_url, timeout=2)
                if response.status_code == 200:
                    status_data = response.json()
                    current_status = status_data.get('status')

                    if current_status == 'operational':
                        print(f"[E2E Fixture] Starlette webapp is ready! Status: 'operational'. (took {time.time() - start_time:.2f}s)")
                        ready = True
                        break
                    elif current_status == 'initializing':
                        print(f"[E2E Fixture] Backend is initializing... (NLP models loading). Waiting. (elapsed {time.time() - start_time:.2f}s)")
                        # Continue waiting, do not break
                    else:
                        print(f"[E2E Fixture] Backend reported an unexpected status: '{current_status}'. Failing early.")
                        break # Exit loop to fail
            except (ConnectionError, requests.exceptions.RequestException) as e:
                # This is expected at the very beginning
                pass # Silently ignore and retry

            time.sleep(1)

        if not ready:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
            pytest.fail(f"Backend failed to start within {timeout} seconds. Check logs in {log_dir}")
        
        # 3. Démarrer le serveur frontend
        frontend_manager = None
        urls = {"backend_url": base_url, "frontend_url": None}

        try:
            frontend_port = find_free_port()
            
            # Le chemin est relatif à la racine du projet
            frontend_path = project_root / 'services' / 'web_api' / 'interface-web-argumentative'

            # Préparation de l'environnement pour le frontend manager
            frontend_env = os.environ.copy()
            frontend_env["PYTHONPATH"] = str(project_root) + os.pathsep + frontend_env.get("PYTHONPATH", "")
            frontend_env['REACT_APP_API_URL'] = base_url
            frontend_env['PORT'] = str(frontend_port)
            
            frontend_config = {
                'enabled': True,
                'path': str(frontend_path),
                'port': frontend_port,
                'timeout_seconds': 300
            }

            print(f"\n[E2E Fixture] Starting Frontend service...")
            
            frontend_manager = FrontendManager(
                config=frontend_config,
                logger=logger,
                backend_url=base_url,
                env=frontend_env
            )

            frontend_status = await frontend_manager.start()

            if not frontend_status.get('success'):
                pytest.fail(f"Frontend failed to start: {frontend_status.get('error')}. Check logs/ for frontend_*.log files.")
            
            urls["frontend_url"] = frontend_status['url']
            print(f"[E2E Fixture] Frontend service is ready at {urls['frontend_url']}")

            # Yield control to the tests avec les deux URLs
            yield urls

        finally:
            # Teardown: Stop the servers after tests are done
            if frontend_manager:
                print("\n[E2E Fixture] Stopping frontend service...")
                await frontend_manager.stop()
                print("[E2E Fixture] Frontend service stopped.")

            print("\n[E2E Fixture] Stopping backend server...")
            try:
                if os.name == 'nt':
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