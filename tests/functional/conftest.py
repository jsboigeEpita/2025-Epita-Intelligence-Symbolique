"""
Configuration Playwright compatible avec pytest-playwright.
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

def setup_page_for_app(page: Page) -> Page:
    """Helper pour configurer une page pour l'application."""
    print(f"DEBUG: Entrée dans setup_page_for_app. URL actuelle de la page: {page.url}")
    page.set_default_timeout(DEFAULT_TIMEOUT)
    
    # Boucle de re-essai pour page.goto
    max_retries = 3
    retry_delay_seconds = 5
    for attempt in range(max_retries):
        try:
            page.goto(APP_BASE_URL)
            # Si goto réussit, sortir de la boucle
            break
        except Exception as e:
            print(f"Tentative {attempt + 1}/{max_retries} de connexion à {APP_BASE_URL} échouée: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay_seconds)
            else:
                # Si toutes les tentatives échouent, relancer l'exception
                raise
    
    # Attendre que l'API soit connectée (logique existante)
    try:
        expect(page.locator(COMMON_SELECTORS['api_status_connected'])).to_be_visible(
            timeout=API_CONNECTION_TIMEOUT
        )
    except Exception:
        pass  # Continuer même si l'API n'est pas connectée
    
    return page

# ============================================================================
# FIXTURES SPÉCIALISÉES POUR LES ONGLETS
# ============================================================================

@pytest.fixture
def app_page(page: Page) -> Page:
    """
    Fixture de base qui navigue vers l'application et attend la connexion API.
    """
    return setup_page_for_app(page)

@pytest.fixture
def analyzer_page(page: Page) -> Page:
    """Page avec l'onglet Analyzer activé."""
    app_page = setup_page_for_app(page)
    app_page.locator(COMMON_SELECTORS['analyzer_tab']).click()
    expect(app_page.locator('[data-testid="analyzer-text-input"]')).to_be_visible()
    return app_page

@pytest.fixture
def fallacy_detector_page(page: Page) -> Page:
    """Page avec l'onglet Détecteur de Sophismes activé."""
    app_page = setup_page_for_app(page)
    app_page.locator(COMMON_SELECTORS['fallacy_detector_tab']).click()
    expect(app_page.locator('[data-testid="fallacy-text-input"]')).to_be_visible()
    return app_page

@pytest.fixture
def reconstructor_page(page: Page) -> Page:
    """Page avec l'onglet Reconstructeur activé."""
    app_page = setup_page_for_app(page)
    app_page.locator(COMMON_SELECTORS['reconstructor_tab']).click()
    expect(app_page.locator('[data-testid="reconstructor-text-input"]')).to_be_visible()
    return app_page

@pytest.fixture
def logic_graph_page(page: Page) -> Page:
    """Page avec l'onglet Graphe Logique activé."""
    app_page = setup_page_for_app(page)
    app_page.locator(COMMON_SELECTORS['logic_graph_tab']).click()
    expect(app_page.locator('[data-testid="logic-statement-input"]')).to_be_visible()
    return app_page

@pytest.fixture
def validation_page(page: Page) -> Page:
    """Page avec l'onglet Validation activé."""
    app_page = setup_page_for_app(page)
    app_page.locator(COMMON_SELECTORS['validation_tab']).click()
    expect(app_page.locator('[data-testid="validation-argument-input"]')).to_be_visible()
    return app_page

@pytest.fixture
def framework_page(page: Page) -> Page:
    """Page avec l'onglet Framework Builder activé."""
    app_page = setup_page_for_app(page)
    # Vérification explicite de la visibilité et de l'activation de l'onglet avant le clic
    framework_tab_selector = COMMON_SELECTORS['framework_tab']
    expect(app_page.locator(framework_tab_selector)).to_be_visible(timeout=DEFAULT_TIMEOUT)
    expect(app_page.locator(framework_tab_selector)).to_be_enabled(timeout=DEFAULT_TIMEOUT)
    
    app_page.locator(framework_tab_selector).click()
    expect(app_page.locator('#arg-content')).to_be_visible(timeout=DEFAULT_TIMEOUT)
    return app_page

# ============================================================================
# UTILITAIRES POUR TESTS
# ============================================================================

def wait_for_element_and_text(page: Page, selector: str, expected_text: str = None, timeout: int = DEFAULT_TIMEOUT):
    """
    Attend qu'un élément soit visible et optionnellement contienne un texte spécifique.
    """
    element = page.locator(selector)
    expect(element).to_be_visible(timeout=timeout)
    if expected_text:
        expect(element).to_contain_text(expected_text, timeout=timeout)
    return element

def click_and_wait(page: Page, selector: str, wait_selector: str = None, timeout: int = DEFAULT_TIMEOUT):
    """
    Clique sur un élément et attend qu'un autre élément soit visible.
    """
    page.click(selector, timeout=timeout)
    if wait_selector:
        expect(page.locator(wait_selector)).to_be_visible(timeout=timeout)

def fill_and_submit(page: Page, input_selector: str, text: str, submit_selector: str, timeout: int = DEFAULT_TIMEOUT):
    """
    Remplit un champ et clique sur un bouton de soumission.
    """
    page.fill(input_selector, text, timeout=timeout)
    page.click(submit_selector, timeout=timeout)