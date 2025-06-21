import pytest
from typing import Dict
from playwright.async_api import expect

# La fonction pytest_addoption est supprimée car les plugins pytest (comme pytest-base-url
# ou pytest-playwright) gèrent maintenant la définition des options d'URL,
# ce qui créait un conflit.
import time

@pytest.fixture(scope="session")
def frontend_url(request) -> str:
    """Fixture qui fournit l'URL du frontend, récupérée depuis les options pytest."""
    # On utilise directement request.config.getoption, en supposant que l'option
    # est fournie par un autre plugin ou sur la ligne de commande.
    return request.config.getoption("--frontend-url")

@pytest.fixture(scope="session")
def backend_url(request) -> str:
    """Fixture qui fournit l'URL du backend, récupérée depuis les options pytest."""
    return request.config.getoption("--backend-url")

# ============================================================================
# Webapp Service Fixture
# ============================================================================

@pytest.fixture(scope="session")
def webapp_service(backend_url) -> None:
    """
    Démarre le serveur web en arrière-plan pour la session de test.
    S'appuie sur la logique de lancement stabilisée (similaire aux commits récents).
    """
    import subprocess
    import sys
    import os
    from pathlib import Path
    import requests
    
    project_root = Path(__file__).parent.parent.parent
    
    # Récupère le port depuis l'URL du backend
    try:
        port = int(backend_url.split(":")[-1])
        host = backend_url.split(":")[1].strip("/")
    except (ValueError, IndexError):
        pytest.fail(f"L'URL du backend '{backend_url}' est invalide.")
        
    command = [
        sys.executable,
        "-m", "uvicorn",
        "interface_web.app:app",
        "--host", host,
        "--port", str(port),
        "--log-level", "info"
    ]
    
    print(f"\n[E2E Fixture] Démarrage du serveur Uvicorn avec la commande: {' '.join(command)}")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root) + os.pathsep + env.get("PYTHONPATH", "")
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8',
        cwd=project_root,
        env=env
    )
    
    # Attendre que le serveur soit prêt
    health_url = f"http://{host}:{port}/api/status" # L'URL du statut de l'API Flask
    try:
        for _ in range(40): # Timeout de 20 sec
            try:
                response = requests.get(health_url, timeout=0.5)
                if response.status_code == 200:
                    print(f"[E2E Fixture] Serveur prêt sur {health_url}")
                    break
            except requests.ConnectionError:
                pass
            time.sleep(0.5)
        else:
            pytest.fail("Timeout: Le serveur n'a pas démarré.")
    except Exception as e:
        pytest.fail(f"Erreur lors de l'attente du serveur: {e}")

    yield
    
    print("\n[E2E Fixture] Arrêt du serveur...")
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
    print("[E2E Fixture] Serveur arrêté.")


# ============================================================================
# Helper Classes (provenant de la branche distante)
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
