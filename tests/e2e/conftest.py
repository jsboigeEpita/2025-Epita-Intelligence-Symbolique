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
async def urls(request) -> Dict[str, str]:
    """
    Fixture simplifiée qui récupère les URLs des services web depuis les
    arguments de la ligne de commande.
    
    L'orchestrateur `unified_web_orchestrator.py` est maintenant la seule
    source de vérité pour démarrer et arrêter les services. Cette fixture
    ne fait que consommer les URLs qu'il fournit.
    """
    backend_url = request.config.getoption("--backend-url")
    frontend_url = request.config.getoption("--frontend-url")

    if not backend_url or not frontend_url:
        pytest.fail(
            "Les URLs du backend et du frontend doivent être fournies via "
            "`--backend-url` et `--frontend-url`. "
            "Exécutez les tests via `unified_web_orchestrator.py`."
        )

    print("\n[E2E Fixture] URLs des services récupérées depuis l'orchestrateur:")
    print(f"[E2E Fixture]   - Backend: {backend_url}")
    print(f"[E2E Fixture]   - Frontend: {frontend_url}")
    
    # Même si la fonction n'a pas d'await, elle doit être async
    # pour être compatible avec les tests qui l'utilisent.
    await asyncio.sleep(0.01)

    return {"backend_url": backend_url, "frontend_url": frontend_url}

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