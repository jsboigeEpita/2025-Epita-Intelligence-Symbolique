import pytest
from typing import Dict

@pytest.fixture(scope="session")
def urls(request) -> Dict[str, str]:
    """
    Fixture synchrone qui récupère les URLs des services web depuis les
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

    return {"backend_url": backend_url, "frontend_url": frontend_url}


@pytest.fixture(scope="session")
def backend_url(urls: Dict[str, str]) -> str:
    """Fixture pour obtenir l'URL du backend."""
    return urls["backend_url"]

@pytest.fixture(scope="session")
def frontend_url(urls: Dict[str, str]) -> str:
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
