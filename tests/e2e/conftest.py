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
from typing import Generator, Dict, AsyncGenerator
from pathlib import Path
from playwright.sync_api import expect

from project_core.webapp_from_scripts.frontend_manager import FrontendManager

# Configuration du logger
logger = logging.getLogger(__name__)

# ============================================================================
# Command-line options and URL Fixtures
# ============================================================================
def pytest_addoption(parser):
   """Ajoute des options personnalisées à la ligne de commande pytest."""
   parser.addoption(
       "--backend-url", action="store", default=None, help="URL du backend à utiliser pour les tests"
   )
   parser.addoption(
       "--frontend-url", action="store", default=None, help="URL du frontend à utiliser pour les tests"
   )

def find_free_port():
    """Trouve et retourne un port TCP libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

# ============================================================================
# Webapp Service Fixture for E2E Tests
# ============================================================================

@pytest.fixture(scope="session")
@pytest.mark.asyncio
async def webapp_service(request) -> AsyncGenerator[Dict[str, str], None]:
    """
    Fixture de session qui gère le cycle de vie des services web.

    Comportement dynamique :
    - Si les URLs (backend/frontend) sont fournies via les options CLI (--backend-url, 
      --frontend-url), la fixture ne démarre aucun service. Elle vérifie simplement
      que les services sont accessibles et fournit les URLs aux tests.
      C'est idéal pour tester des environnements déjà déployés.

    - Si aucune URL n'est fournie, la fixture démarre les serveurs backend (Uvicorn)
      et frontend (React) dans des processus séparés. Elle gère leur configuration,
      le nettoyage des ports, et leur arrêt propre à la fin de la session de test.
      C'est le mode par défaut pour les tests locaux et la CI.
    """
    backend_url_cli = request.config.getoption("--backend-url")
    frontend_url_cli = request.config.getoption("--frontend-url")

    # --- Mode 1: Utiliser un service externe déjà en cours d'exécution ---
    if backend_url_cli and frontend_url_cli:
        print(f"\n[E2E Fixture] Utilisation de services externes fournis:")
        print(f"[E2E Fixture]   - Backend: {backend_url_cli}")
        print(f"[E2E Fixture]   - Frontend: {frontend_url_cli}")

        # Vérifier que le backend est accessible
        try:
            health_url = f"{backend_url_cli}/api/status"
            response = requests.get(health_url, timeout=10)
            response.raise_for_status()
            print(f"[E2E Fixture] Backend externe est accessible (status: {response.status_code}).")
        except (ConnectionError, requests.exceptions.HTTPError) as e:
            pytest.fail(f"Le service backend externe à l'adresse {backend_url_cli} n'est pas joignable. Erreur: {e}")

        # Pas besoin de teardown, car les processus sont gérés de manière externe
        yield {"backend_url": backend_url_cli, "frontend_url": frontend_url_cli}
        return

    # --- Mode 2: Démarrer et gérer les services localement ---
    print("\n[E2E Fixture] Démarrage des services locaux (backend et frontend)...")
    
    host = "127.0.0.1"
    backend_port = find_free_port()
    base_url = f"http://{host}:{backend_port}"
    api_health_url = f"{base_url}/api/status" # Note: app.py définit le préfixe /api

    project_root = Path(__file__).parent.parent.parent
    activation_script = project_root / "activate_project_env.ps1"
    
    backend_command_to_run = (
        f"python -m uvicorn interface_web.app:app "
        f"--host {host} --port {backend_port} --log-level debug"
    )

    command = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-Command", f"& '{activation_script}' -CommandToRun \"{backend_command_to_run}\""
    ]

    print(f"[E2E Fixture] Démarrage du serveur web Starlette sur le port {backend_port}...")
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    stdout_log_path = log_dir / f"backend_stdout_{backend_port}.log"
    stderr_log_path = log_dir / f"backend_stderr_{backend_port}.log"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
    env["BACKEND_URL"] = base_url

    process = None
    frontend_manager = None
    try:
        with open(stdout_log_path, "wb") as stdout_log, open(stderr_log_path, "wb") as stderr_log:
            process = subprocess.Popen(
                command,
                stdout=stdout_log, stderr=stderr_log,
                cwd=str(project_root), env=env,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
            )

        # Attendre que le backend soit prêt
        start_time = time.time()
        timeout = 300  # 5 minutes
        ready = False
        print(f"[E2E Fixture] En attente du backend à {api_health_url}...")
        while time.time() - start_time < timeout:
            try:
                response = requests.get(api_health_url, timeout=2)
                if response.status_code == 200 and response.json().get('status') == 'operational':
                    print(f"[E2E Fixture] Webapp Starlette prête! (en {time.time() - start_time:.2f}s)")
                    ready = True
                    break
            except (ConnectionError, requests.exceptions.RequestException):
                pass
            time.sleep(1)

        if not ready:
            pytest.fail(f"Le backend n'a pas pu démarrer dans le temps imparti ({timeout}s). Vérifiez les logs dans {log_dir}")

        # Démarrer le serveur frontend
        frontend_port = find_free_port()
        frontend_path = project_root / 'services' / 'web_api' / 'interface-web-argumentative'
        
        frontend_env = env.copy()
        frontend_env['REACT_APP_API_URL'] = base_url
        frontend_env['PORT'] = str(frontend_port)
        
        frontend_config = {
            'enabled': True, 'path': str(frontend_path),
            'port': frontend_port, 'timeout_seconds': 300
        }

        print(f"\n[E2E Fixture] Démarrage du service Frontend...")
        frontend_manager = FrontendManager(
            config=frontend_config, logger=logger,
            backend_url=base_url, env=frontend_env
        )

        frontend_status = await frontend_manager.start()
        if not frontend_status.get('success'):
            pytest.fail(f"Le frontend n'a pas pu démarrer: {frontend_status.get('error')}.")
        
        urls = {"backend_url": base_url, "frontend_url": frontend_status['url']}
        print(f"[E2E Fixture] Service Frontend prêt à {urls['frontend_url']}")

        yield urls

    finally:
        # Teardown: Arrêter les serveurs
        if frontend_manager:
            print("\n[E2E Fixture] Arrêt du service frontend...")
            await frontend_manager.stop()
            print("[E2E Fixture] Service frontend arrêté.")
        
        if process:
            print("\n[E2E Fixture] Arrêt du serveur backend...")
            try:
                if os.name == 'nt':
                    subprocess.call(['taskkill', '/F', '/T', '/PID', str(process.pid)])
                else:
                    process.terminate()
                process.wait(timeout=10)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                if process.poll() is None:
                    print("[E2E Fixture] process.terminate() a expiré, on force l'arrêt.")
                    process.kill()
            finally:
                print("[E2E Fixture] Serveur backend arrêté.")


@pytest.fixture(scope="session")
@pytest.mark.asyncio
async def urls(webapp_service: Dict[str, str]) -> Dict[str, str]:
    """Fixture qui fournit simplement le dictionnaire d'URLs généré par webapp_service."""
    return webapp_service

@pytest.fixture(scope="session")
@pytest.mark.asyncio
async def backend_url(urls: Dict[str, str]) -> str:
    """Fixture pour obtenir l'URL du backend."""
    return urls["backend_url"]

@pytest.fixture(scope="session")
@pytest.mark.asyncio
async def frontend_url(urls: Dict[str, str]) -> str:
    """Fixture pour obtenir l'URL du frontend."""
    return urls["frontend_url"]


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