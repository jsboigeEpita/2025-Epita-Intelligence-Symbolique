import pytest
import subprocess
import time
import requests
from requests.exceptions import ConnectionError
import os
import sys
import logging
import socket
from typing import Generator
from pathlib import Path
from playwright.sync_api import expect

# Configuration du logger
logger = logging.getLogger(__name__)

# ============================================================================
# Webapp Service Fixture for E2E Tests
def pytest_addoption(parser):
   """Ajoute des options personnalisées à la ligne de commande pytest."""
   parser.addoption(
       "--backend-url", action="store", default=None, help="URL du backend à utiliser pour les tests"
   )
   parser.addoption(
       "--frontend-url", action="store", default=None, help="URL du frontend à utiliser pour les tests"
   )

@pytest.fixture(scope="session")
def backend_url(request):
   """Fixture pour obtenir l'URL du backend depuis la ligne de commande ou les variables d'env."""
   url = request.config.getoption("--backend-url")
   if not url:
       url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000") # Défaut si rien n'est fourni
   return url

@pytest.fixture(scope="session")
def frontend_url(request):
   """Fixture pour obtenir l'URL du frontend depuis la ligne de commande ou les variables d'env."""
   url = request.config.getoption("--frontend-url")
   if not url:
       url = os.environ.get("FRONTEND_URL", "http://localhost:3000") # Défaut si rien n'est fourni
   return url


# ============================================================================

def find_free_port():
    """Trouve et retourne un port TCP libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]

# ============================================================================
# Webapp Service Fixture for E2E Tests
# ============================================================================

@pytest.fixture(scope="session")
def webapp_service(backend_url):
    """
    Fixture qui fournit simplement l'URL du backend.
    Le démarrage et l'arrêt du service sont gérés par l'orchestrateur externe.
    """
    logger.info(f"Service webapp utilisé (URL fournie par l'orchestrateur): {backend_url}")
    # On s'assure juste que le service est joignable avant de lancer les tests
    try:
        response = requests.get(f"{backend_url}/api/health", timeout=10)
        response.raise_for_status()
    except (ConnectionError, requests.exceptions.HTTPError) as e:
        pytest.fail(f"Le service backend à l'adresse {backend_url} n'est pas joignable. Erreur: {e}")
    
    yield backend_url
    logger.info("Fin des tests, le service webapp reste actif (géré par l'orchestrateur).")
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