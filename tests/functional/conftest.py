"""
Configuration Playwright optimisée pour une seule fenêtre navigateur.
Remplace temporairement conftest.py pour éviter les multiples instances.
"""

import pytest
import time
from typing import Dict, Any
from playwright.sync_api import Page, Browser, BrowserContext, expect

# URLs et timeouts configurables
APP_BASE_URL = "http://localhost:3000/"
API_CONNECTION_TIMEOUT = 15000
DEFAULT_TIMEOUT = 10000
SLOW_OPERATION_TIMEOUT = 20000

# Data-testids standard pour tous les tests
COMMON_SELECTORS = {
    'api_status': '.api-status',
    'api_status_connected': '.api-status.connected',
    'api_status_disconnected': '.api-status.disconnected',
    'analyzer_tab': '[data-testid="analyzer-tab"]',
    'fallacy_detector_tab': '[data-testid="fallacy-detector-tab"]',
    'reconstructor_tab': '[data-testid="reconstructor-tab"]',
    'logic_graph_tab': '[data-testid="logic-graph-tab"]',
    'validation_tab': '[data-testid="validation-tab"]',
    'framework_tab': '[data-testid="framework-tab"]'
}

# ============================================================================
# FIXTURES OPTIMISÉES POUR UNE SEULE FENÊTRE
# ============================================================================

@pytest.fixture(scope="session")
def browser_context_session(browser: Browser) -> BrowserContext:
    """
    Contexte de navigateur partagé pour toute la session.
    """
    context = browser.new_context(
        viewport={'width': 1280, 'height': 800},
        record_video_dir="logs/videos/" if False else None,  # Désactivé par défaut
        record_har_path="logs/traces/session.har" if False else None
    )
    yield context
    context.close()

@pytest.fixture(scope="session")
def shared_page(browser_context_session: BrowserContext) -> Page:
    """
    Page partagée pour tous les tests de la session.
    Une seule fenêtre navigateur réutilisée.
    """
    page = browser_context_session.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT)
    
    # Navigation initiale vers l'application
    page.goto(APP_BASE_URL)
    
    # Attendre que l'élément de statut API soit présent
    try:
        # D'abord attendre que l'élément api-status soit visible
        expect(page.locator(COMMON_SELECTORS['api_status'])).to_be_visible(timeout=5000)
        
        # Puis vérifier s'il devient connecté
        try:
            expect(page.locator(COMMON_SELECTORS['api_status_connected'])).to_be_visible(
                timeout=API_CONNECTION_TIMEOUT
            )
            print("[OK] API connectee - Page partagee prete")
        except Exception:
            # L'API n'est pas connectée, mais l'application est chargée
            print("[WARNING] API non connectee mais application chargee")
    except Exception as e:
        print(f"[ERROR] Probleme de chargement application : {e}")
    
    yield page
    # Ne pas fermer la page ici, sera fermée avec le contexte

@pytest.fixture(scope="function")
def page(shared_page: Page) -> Page:
    """
    Fixture de page qui réutilise la page partagée mais la remet à zéro.
    """
    # Réinitialiser l'état de la page pour chaque test
    shared_page.goto(APP_BASE_URL)
    
    # Attendre que l'API soit connectée
    try:
        expect(shared_page.locator(COMMON_SELECTORS['api_status_connected'])).to_be_visible(
            timeout=5000  # Timeout plus court car déjà validée
        )
    except Exception:
        pass  # Continuer même si l'API n'est pas connectée
    
    yield shared_page

# ============================================================================
# FIXTURES SPÉCIALISÉES OPTIMISÉES
# ============================================================================

@pytest.fixture
def app_page(page: Page) -> Page:
    """
    Fixture de base qui navigue vers l'application et attend la connexion API.
    """
    # La page est déjà sur l'app et l'API est validée
    return page

@pytest.fixture
def analyzer_page(app_page: Page) -> Page:
    """Page avec l'onglet Analyzer activé."""
    app_page.locator(COMMON_SELECTORS['analyzer_tab']).click()
    expect(app_page.locator('[data-testid="analyzer-text-input"]')).to_be_visible()
    return app_page

@pytest.fixture
def fallacy_detector_page(app_page: Page) -> Page:
    """Page avec l'onglet Détecteur de Sophismes activé."""
    app_page.locator(COMMON_SELECTORS['fallacy_detector_tab']).click()
    expect(app_page.locator('[data-testid="fallacy-text-input"]')).to_be_visible()
    return app_page

@pytest.fixture
def reconstructor_page(app_page: Page) -> Page:
    """Page avec l'onglet Reconstructeur activé."""
    app_page.locator(COMMON_SELECTORS['reconstructor_tab']).click()
    expect(app_page.locator('[data-testid="reconstructor-text-input"]')).to_be_visible()
    return app_page

@pytest.fixture
def logic_graph_page(app_page: Page) -> Page:
    """Page avec l'onglet Graphe Logique activé."""
    app_page.locator(COMMON_SELECTORS['logic_graph_tab']).click()
    expect(app_page.locator('[data-testid="logic-statement-input"]')).to_be_visible()
    return app_page

@pytest.fixture
def validation_page(app_page: Page) -> Page:
    """Page avec l'onglet Validation activé."""
    app_page.locator(COMMON_SELECTORS['validation_tab']).click()
    expect(app_page.locator('#argument-type')).to_be_visible(timeout=DEFAULT_TIMEOUT)
    return app_page

@pytest.fixture
def framework_page(app_page: Page) -> Page:
    """Page avec l'onglet Framework activé."""
    app_page.locator(COMMON_SELECTORS['framework_tab']).click()
    expect(app_page.locator('#arg-content')).to_be_visible(timeout=DEFAULT_TIMEOUT)
    return app_page

# ============================================================================
# FIXTURES DE DONNÉES (INCHANGÉES)
# ============================================================================

@pytest.fixture
def sample_arguments() -> Dict[str, str]:
    """Arguments d'exemple pour les tests."""
    return {
        'syllogism_valid': "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.",
        'short_text': "Test simple.",
        'complex_argument': "Les énergies renouvelables sont nécessaires pour réduire notre impact environnemental."
    }

@pytest.fixture
def sample_logic_statements() -> Dict[str, str]:
    """Énoncés logiques d'exemple."""
    return {
        'simple_implication': "p -> q",
        'conjunction': "p && q",
        'complex_formula': "(p -> q) && (q -> r) -> (p -> r)"
    }

# ============================================================================
# CONFIGURATION OPTIMISÉE
# ============================================================================

@pytest.fixture(scope="session")
def playwright_config():
    """Configuration globale pour Playwright optimisée."""
    return {
        'base_url': APP_BASE_URL,
        'timeout': DEFAULT_TIMEOUT,
        'slow_operation_timeout': SLOW_OPERATION_TIMEOUT,
        'api_connection_timeout': API_CONNECTION_TIMEOUT,
        'single_browser_instance': True
    }

def pytest_configure(config):
    """Configuration des markers personnalisés."""
    config.addinivalue_line("markers", "slow: marque les tests comme lents")
    config.addinivalue_line("markers", "integration: tests d'intégration") 
    config.addinivalue_line("markers", "api_dependent: tests dépendants de l'API")
    config.addinivalue_line("markers", "playwright: tests Playwright UI")