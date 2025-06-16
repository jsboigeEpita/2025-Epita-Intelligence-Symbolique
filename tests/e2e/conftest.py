"""
Configuration et fixtures communes pour les tests fonctionnels Playwright.
Fournit des utilitaires réutilisables pour l'ensemble de la suite de tests.
"""

import pytest
import time
from typing import Dict, Any
from playwright.sync_api import Page, expect

# ============================================================================
# CONFIGURATION GÉNÉRALE
# ============================================================================

import os
from pathlib import Path

# La fonction get_frontend_url a été supprimée pour utiliser une URL fixe
# et simplifier les tests locaux. L'orchestrateur n'est pas toujours
# actif lors de l'exécution des tests.

# URLs et timeouts configurables
APP_BASE_URL = "http://localhost:3000"  # URL fixe pour les tests E2E
API_CONNECTION_TIMEOUT = 30000  # Augmenté pour les environnements de CI/CD lents
DEFAULT_TIMEOUT = 15000
SLOW_OPERATION_TIMEOUT = 20000

# Data-testids standard pour tous les tests
COMMON_SELECTORS = {
    'api_status_connected': '.api-status.connected',
    'analyzer_tab': '[data-testid="analyzer-tab"]',
    'fallacy_detector_tab': '[data-testid="fallacy-detector-tab"]',
    'reconstructor_tab': '[data-testid="reconstructor-tab"]',
    'logic_graph_tab': '[data-testid="logic-graph-tab"]',
    'validation_tab': '[data-testid="validation-tab"]',
    'framework_tab': '[data-testid="framework-tab"]'
}

# ============================================================================
# FIXTURES DE BASE
# ============================================================================

@pytest.fixture
def app_page(page: Page) -> Page:
    """
    Fixture de base qui navigue vers l'application et attend la connexion API.
    Utilisée par tous les tests nécessitant l'application prête.
    """
    page.goto(APP_BASE_URL)
    
    # Attendre que l'API soit connectée avant de continuer
    expect(page.locator(COMMON_SELECTORS['api_status_connected'])).to_be_visible(
        timeout=API_CONNECTION_TIMEOUT
    )
    
    return page

@pytest.fixture
def api_ready_page(app_page: Page) -> Page:
    """
    Alias pour app_page pour la clarté du code.
    """
    return app_page

# ============================================================================
# FIXTURES SPÉCIALISÉES PAR ONGLET
# ============================================================================

@pytest.fixture
def analyzer_page(app_page: Page) -> Page:
    """
    Page avec l'onglet Analyzer activé et prêt à utiliser.
    """
    analyzer_tab = app_page.locator(COMMON_SELECTORS['analyzer_tab'])
    expect(analyzer_tab).to_be_enabled()
    analyzer_tab.click()
    
    # Attendre que l'interface soit chargée
    expect(app_page.locator('[data-testid="analyzer-text-input"]')).to_be_visible()
    
    return app_page

@pytest.fixture
def fallacy_detector_page(app_page: Page) -> Page:
    """
    Page avec l'onglet Détecteur de Sophismes activé et prêt à utiliser.
    """
    fallacy_tab = app_page.locator(COMMON_SELECTORS['fallacy_detector_tab'])
    expect(fallacy_tab).to_be_enabled()
    fallacy_tab.click()
    
    # Attendre que l'interface soit chargée
    expect(app_page.locator('[data-testid="fallacy-text-input"]')).to_be_visible()
    
    return app_page

@pytest.fixture
def reconstructor_page(app_page: Page) -> Page:
    """
    Page avec l'onglet Reconstructeur activé et prêt à utiliser.
    """
    reconstructor_tab = app_page.locator(COMMON_SELECTORS['reconstructor_tab'])
    expect(reconstructor_tab).to_be_enabled()
    reconstructor_tab.click()
    
    # Attendre que l'interface soit chargée
    expect(app_page.locator('[data-testid="reconstructor-text-input"]')).to_be_visible()
    
    return app_page

@pytest.fixture
def logic_graph_page(app_page: Page) -> Page:
    """
    Page avec l'onglet Graphe Logique activé et prêt à utiliser.
    """
    logic_tab = app_page.locator(COMMON_SELECTORS['logic_graph_tab'])
    expect(logic_tab).to_be_enabled()
    logic_tab.click()
    
    # Attendre que l'interface soit chargée
    expect(app_page.locator('[data-testid="logic-statement-input"]')).to_be_visible()
    
    return app_page

@pytest.fixture
def validation_page(app_page: Page) -> Page:
    """
    Page avec l'onglet Validation activé et prêt à utiliser.
    """
    validation_tab = app_page.locator(COMMON_SELECTORS['validation_tab'])
    expect(validation_tab).to_be_enabled()
    validation_tab.click()
    
    # Attendre que l'interface soit chargée - utiliser les vrais sélecteurs
    expect(app_page.locator('#argument-type')).to_be_visible(timeout=DEFAULT_TIMEOUT)
    
    return app_page

@pytest.fixture
def framework_page(app_page: Page) -> Page:
    """
    Page avec l'onglet Framework activé et prêt à utiliser.
    """
    framework_tab = app_page.locator(COMMON_SELECTORS['framework_tab'])
    expect(framework_tab).to_be_enabled()
    framework_tab.click()
    
    # Attendre que l'interface soit chargée - utiliser les vrais sélecteurs
    expect(app_page.locator('#arg-content')).to_be_visible(timeout=DEFAULT_TIMEOUT)
    
    return app_page

# ============================================================================
# FIXTURES DE DONNÉES DE TEST
# ============================================================================

@pytest.fixture
def sample_arguments() -> Dict[str, str]:
    """
    Arguments d'exemple pour les tests de reconstruction et d'analyse.
    """
    return {
        'syllogism_valid': "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.",
        'syllogism_invalid': "Tous les chats sont noirs. Mon chat est noir. Donc tous les animaux noirs sont des chats.",
        'ad_hominem': "Cette théorie sur le climat est fausse parce que son auteur a été condamné pour fraude fiscale.",
        'slippery_slope': "Si on autorise les gens à conduire à 85 km/h, bientôt ils voudront conduire à 200 km/h.",
        'straw_man': "Les végétariens disent qu'il ne faut jamais manger de viande, mais c'est ridicule car l'homme a toujours été omnivore.",
        'complex_argument': """
        Les énergies renouvelables sont nécessaires pour réduire notre impact environnemental.
        Le solaire et l'éolien sont des sources d'énergie propres et durables.
        Les technologies actuelles permettent un stockage efficace de l'énergie.
        Par conséquent, nous devons investir massivement dans les énergies renouvelables.
        """,
        'short_text': "Test.",
        'no_argument': "J'aime les pommes. Les pommes sont rouges. Le rouge est une couleur."
    }

@pytest.fixture
def sample_logic_statements() -> Dict[str, str]:
    """
    Énoncés logiques d'exemple pour les tests du graphe logique.
    """
    return {
        'simple_implication': "p -> q",
        'conjunction': "p && q",
        'disjunction': "p || q",
        'negation': "!p",
        'complex_formula': "(p -> q) && (q -> r) -> (p -> r)",
        'biconditional': "p <-> q",
        'invalid_syntax': "p -> q &&",
        'empty_formula': "",
        'quantified': "forall x: P(x) -> Q(x)"
    }

@pytest.fixture
def sample_validation_scenarios() -> Dict[str, Dict[str, Any]]:
    """
    Scénarios de validation avec différents types de données.
    """
    return {
        'basic_argument': {
            'premises': ['Tous les hommes sont mortels', 'Socrate est un homme'],
            'conclusion': 'Socrate est mortel',
            'expected_valid': True
        },
        'fallacious_argument': {
            'premises': ['Cette personne est stupide'],
            'conclusion': 'Son argument est faux',
            'expected_valid': False,
            'expected_fallacy': 'Ad Hominem'
        },
        'incomplete_argument': {
            'premises': ['Il pleut'],
            'conclusion': 'La route est glissante',
            'expected_valid': False,
            'missing_premise': 'Quand il pleut, la route devient glissante'
        }
    }

# ============================================================================
# UTILITAIRES DE TEST
# ============================================================================

class PlaywrightHelpers:
    """
    Classe d'utilitaires pour les opérations communes de test.
    Peut être utilisée directement dans les tests ou via la fixture test_helpers.
    """
    # Constantes de timeout
    API_CONNECTION_TIMEOUT = API_CONNECTION_TIMEOUT
    DEFAULT_TIMEOUT = DEFAULT_TIMEOUT
    SLOW_OPERATION_TIMEOUT = SLOW_OPERATION_TIMEOUT
    
    def __init__(self, page: Page):
        self.page = page
    
    def navigate_to_tab(self, tab_name: str):
        """
        Navigue vers un onglet spécifique et attend qu'il soit chargé.
        La page doit déjà être chargée via la fixture `app_page`.
        
        Args:
            tab_name: Nom de l'onglet ('validation', 'framework', etc.)
        """
        # La navigation et la vérification de l'API sont maintenant gérées par la fixture `app_page`.
        # Cette méthode suppose que la page est déjà prête.
        
        # Mapper les noms d'onglets vers leurs sélecteurs data-testid
        tab_selectors = {
            'validation': COMMON_SELECTORS['validation_tab'],
            'framework': COMMON_SELECTORS['framework_tab'],
            'analyzer': COMMON_SELECTORS['analyzer_tab'],
            'fallacy_detector': COMMON_SELECTORS['fallacy_detector_tab'],
            'reconstructor': COMMON_SELECTORS['reconstructor_tab'],
            'logic_graph': COMMON_SELECTORS['logic_graph_tab']
        }
        
        if tab_name not in tab_selectors:
            raise ValueError(f"Onglet '{tab_name}' non reconnu. Onglets disponibles: {list(tab_selectors.keys())}")
        
        # Cliquer sur l'onglet
        tab_selector = tab_selectors[tab_name]
        tab = self.page.locator(tab_selector)
        expect(tab).to_be_enabled(timeout=DEFAULT_TIMEOUT)
        tab.click()
        
        # Attendre que l'interface de l'onglet soit chargée
        time.sleep(0.5)  # Petite pause pour la transition
        
        # Vérifications spécifiques selon l'onglet
        if tab_name == 'validation':
            # Attendre que le formulaire de validation soit visible
            expect(self.page.locator('#argument-type')).to_be_visible(timeout=DEFAULT_TIMEOUT)
        elif tab_name == 'framework':
            # Attendre que l'interface de construction de framework soit visible
            expect(self.page.locator('#arg-content')).to_be_visible(timeout=DEFAULT_TIMEOUT)
    
    def fill_and_submit(self, input_selector: str, text: str, submit_selector: str):
        """Remplit un champ et soumet le formulaire."""
        text_input = self.page.locator(input_selector)
        submit_button = self.page.locator(submit_selector)
        
        expect(text_input).to_be_visible()
        text_input.fill(text)
        
        expect(submit_button).to_be_enabled()
        submit_button.click()
    
    def wait_for_results(self, results_selector: str, timeout: int = DEFAULT_TIMEOUT):
        """Attend l'apparition des résultats."""
        results = self.page.locator(results_selector)
        expect(results).to_be_visible(timeout=timeout)
        return results
    
    def reset_form(self, reset_selector: str):
        """Réinitialise un formulaire."""
        reset_button = self.page.locator(reset_selector)
        expect(reset_button).to_be_enabled()
        reset_button.click()
    
    def switch_tab(self, tab_selector: str):
        """Change d'onglet et attend le chargement."""
        tab = self.page.locator(tab_selector)
        expect(tab).to_be_enabled()
        tab.click()
        time.sleep(0.5)  # Petite pause pour la transition
    
    def verify_error_message(self, container_selector: str, expected_message: str):
        """Vérifie qu'un message d'erreur attendu est affiché."""
        container = self.page.locator(container_selector)
        expect(container).to_be_visible()
        expect(container).to_contain_text(expected_message)
    
    def verify_success_state(self, success_indicators: list):
        """Vérifie plusieurs indicateurs de succès."""
        for indicator in success_indicators:
            expect(self.page.locator(indicator)).to_be_visible()
    
    def take_screenshot_on_failure(self, test_name: str):
        """Prend une capture d'écran en cas d'échec."""
        try:
            self.page.screenshot(path=f"test-results/failure-{test_name}.png")
        except Exception:
            pass  # Ignore les erreurs de screenshot


@pytest.fixture
def test_helpers(page: Page) -> PlaywrightHelpers:
    """
    Fixture qui retourne une instance de PlaywrightHelpers pour la page courante.
    """
    return PlaywrightHelpers(page)

# ============================================================================
# FIXTURES DE CONFIGURATION
# ============================================================================

@pytest.fixture(scope="session")
def playwright_config():
    """
    Configuration globale pour Playwright.
    """
    return {
        'base_url': APP_BASE_URL,
        'timeout': DEFAULT_TIMEOUT,
        'slow_operation_timeout': SLOW_OPERATION_TIMEOUT,
        'api_connection_timeout': API_CONNECTION_TIMEOUT
    }

# La fixture `autouse` `setup_test_environment` a été supprimée.
# La configuration de la page est maintenant gérée exclusivement par la fixture `app_page`,
# que les tests doivent demander explicitement. Cela rend les dépendances plus claires.
# ============================================================================
# MARKERS PERSONNALISÉS
# ============================================================================

def pytest_configure(config):
    """Configuration des markers personnalisés."""
    config.addinivalue_line(
        "markers", "slow: marque les tests comme lents"
    )
    config.addinivalue_line(
        "markers", "integration: tests d'intégration"
    )
    config.addinivalue_line(
        "markers", "api_dependent: tests dépendants de l'API"
    )