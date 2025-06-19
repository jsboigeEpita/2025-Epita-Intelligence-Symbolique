import pytest
from typing import Dict
from playwright.async_api import expect

# La fonction pytest_addoption est supprimée car les plugins pytest (comme pytest-base-url
# ou pytest-playwright) gèrent maintenant la définition des options d'URL,
# ce qui créait un conflit.

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
