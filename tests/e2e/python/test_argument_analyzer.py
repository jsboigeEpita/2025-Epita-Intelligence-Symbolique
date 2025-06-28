import re
import pytest
import logging
from playwright.sync_api import Page, Playwright, expect, TimeoutError as PlaywrightTimeoutError
from datetime import datetime

# Configure logging to be visible in pytest output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_dummy_health_check_to_isolate_playwright():
    """
    A simple, dependency-free test to ensure the pytest runner itself is working.
    If this test runs and the next one hangs, the problem is with Playwright/fixture initialization.
    """
    assert True


@pytest.mark.playwright
def test_health_check_endpoint(playwright: Playwright, backend_url: str):
    """
    Test a lightweight, dependency-free /api/health endpoint using a raw API request.
    This avoids launching a full browser page, which can cause asyncio conflicts.
    """
    logger.info("--- DEBUT test_health_check_endpoint (API only) ---")
    health_check_url = f"{backend_url}/api/health"
    logger.info(f"Tentative de requête API vers l'endpoint de health check: {health_check_url}")

    try:
        api_request_context = playwright.request.new_context()
        response = api_request_context.get(health_check_url, timeout=20000)
        logger.info(f"SUCCES: La requête vers {health_check_url} a abouti avec le statut {response.status}.")

        # Vérifier que la réponse est bien 200 OK
        assert response.status == 200, f"Le statut de la réponse attendu était 200, mais j'ai obtenu {response.status}"
        logger.info("SUCCES: Le statut de la réponse est correct (200).")

        # Vérifier le contenu de la réponse JSON
        json_response = response.json()
        assert json_response.get("status") == "ok", f"La réponse JSON ne contient pas 'status: ok'. Reçu: {json_response}"
        logger.info("SUCCES: La réponse JSON contient bien 'status: ok'.")

    except PlaywrightTimeoutError as e:
        logger.error(f"ERREUR FATALE: Timeout Playwright en essayant d'atteindre {health_check_url}. Détails: {e}")
        pytest.fail(f"Timeout Playwright: Le serveur n'a pas répondu à temps sur l'endpoint de health check. Il est probablement bloqué. Détails: {e}")
    except Exception as e:
        logger.error(f"ERREUR INATTENDUE: Une exception s'est produite dans test_health_check_endpoint. Détails: {e}", exc_info=True)
        pytest.fail(f"Exception inattendue: {e}")

    logger.info("--- FIN test_health_check_endpoint ---")

@pytest.mark.playwright
def test_successful_simple_argument_analysis(page: Page, frontend_url: str):
    """
    Scenario 1.1: Successful analysis of a simple argument (Happy Path)
    This test targets the React application.
    """
    logger.info("--- DEBUT test_successful_simple_argument_analysis ---")
    
    try:
        # --- Instrumentation pour le débogage ---
        def log_console_message(msg):
            logger.info(f"[BROWSER CONSOLE] {msg.type}: {msg.text}")

        def log_network_request(request):
            logger.info(f"[BROWSER NETWORK] >> {request.method} {request.url}")

        def log_network_response(response):
            logger.info(f"[BROWSER NETWORK] << {response.status} {response.url}")

        page.on("console", log_console_message)
        page.on("request", log_network_request)
        page.on("response", log_network_response)
        # --- Fin de l'instrumentation ---

        logger.info(f"Étape 1: Navigation vers l'URL du frontend: {frontend_url}")
        page.goto(frontend_url, timeout=90000)  # Timeout augmenté
        logger.info("SUCCES: Navigation terminée.")

        logger.info("Étape 2: Attente de la connexion à l'API.")
        logger.info("CHERCHE: Indicateur de connexion '.api-status.connected'")
        api_status_locator = page.locator(".api-status.connected")
        logger.info("TROUVÉ: Localisateur pour '.api-status.connected'.")
        logger.info("VÉRIFICATION: L'indicateur est visible (timeout=60s).")
        expect(api_status_locator).to_be_visible(timeout=60000) # Timeout augmenté
        logger.info("SUCCES: Indicateur de connexion API visible.")

        logger.info("Étape 3: Clic sur l'onglet 'Analyse'.")
        logger.info("CHERCHE: Onglet 'Analyse' avec le sélecteur '[data-testid=\"analyzer-tab\"]'")
        analyzer_tab_locator = page.locator('[data-testid="analyzer-tab"]')
        logger.info("TROUVÉ: Localisateur pour l'onglet 'Analyse'.")
        logger.info("ACTION: Clic.")
        analyzer_tab_locator.click()
        logger.info("SUCCES: Clic sur l'onglet 'Analyse' effectué.")

        # Définition des localisateurs
        argument_input = page.locator("#argument-text")
        submit_button = page.locator("form.analyzer-form button[type=\"submit\"]")
        results_container = page.locator(".analysis-results")
        loading_spinner = page.locator(".loading-spinner")
        
        argument_text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."

        logger.info("Étape 4: Remplissage du champ d'analyse.")
        logger.info("CHERCHE: Champ de texte '#argument-text'")
        logger.info("VÉRIFICATION: Le champ est visible (timeout=10s).")
        expect(argument_input).to_be_visible(timeout=10000)
        logger.info("TROUVÉ: Champ de texte visible.")
        logger.info(f"ACTION: Remplissage avec le texte : '{argument_text[:30]}...'")
        argument_input.fill(argument_text)
        logger.info("SUCCES: Champ d'analyse rempli.")

        logger.info("Étape 5: Clic sur le bouton de soumission.")
        logger.info("CHERCHE: Bouton de soumission 'form.analyzer-form button[type=\"submit\"]'")
        logger.info("TROUVÉ: Localisateur pour le bouton de soumission.")
        logger.info("ACTION: Clic.")
        submit_button.click()
        logger.info("SUCCES: Bouton de soumission cliqué.")

        logger.info("Étape 6: Attente de la disparition du spinner de chargement.")
        logger.info("CHERCHE: Spinner de chargement '.loading-spinner'")
        logger.info("VÉRIFICATION: Le spinner n'est plus visible (timeout=120s).")
        expect(loading_spinner).not_to_be_visible(timeout=120000)
        logger.info("SUCCES: Spinner de chargement disparu.")

        logger.info("Étape 7: Attente et vérification des résultats.")
        logger.info("CHERCHE: Conteneur de résultats '.analysis-results'")
        logger.info("VÉRIFICATION: Le conteneur de résultats est visible (timeout=10s).")
        expect(results_container).to_be_visible(timeout=10000)
        logger.info("TROUVÉ: Conteneur de résultats visible.")
        logger.info("VÉRIFICATION: Le conteneur contient le texte 'Structure argumentative'.")
        expect(results_container).to_contain_text("Structure argumentative")
        logger.info("SUCCES: Conteneur de résultats visible et contient le texte attendu.")
        
    except PlaywrightTimeoutError as e:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        screenshot_path = f"playwright-timeout-screenshot-{timestamp}.png"
        html_path = f"playwright-timeout-page-{timestamp}.html"
        
        logger.error(f"ERREUR FATALE: Timeout Playwright détecté. {e}")
        try:
            logger.info(f"Tentative de sauvegarde de la capture d'écran dans : {screenshot_path}")
            page.screenshot(path=screenshot_path, full_page=True)
            logger.info("Capture d'écran sauvegardée avec succès.")
            
            logger.info(f"Tentative de sauvegarde du HTML de la page dans : {html_path}")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(page.content())
            logger.info("HTML de la page sauvegardé avec succès.")
        except Exception as save_exc:
            logger.error(f"ÉCHEC de la sauvegarde des artefacts de débogage. Erreur : {save_exc}")
            
        pytest.fail(f"Timeout Playwright. Artefacts de débogage (screenshot/html) sauvegardés. Erreur originale: {e}")
    except Exception as e:
        logger.error(f"ERREUR INATTENDUE dans le test: {e}", exc_info=True)
        pytest.fail(f"Une exception inattendue est survenue: {e}")

    logger.info("--- FIN test_successful_simple_argument_analysis ---")


@pytest.mark.playwright
def test_empty_argument_submission_displays_error(page: Page, frontend_url: str):
    """
    Scenario 1.2: Empty submission (Error Path)
    Checks if an error message is displayed when submitting an empty argument.
    """
    # Navigate to the React app
    page.goto(frontend_url)

    # Wait for the API to be connected
    expect(page.locator(".api-status.connected")).to_be_visible(timeout=30000)

    # Navigate to the "Analyse" tab using the robust data-testid selector
    page.locator('[data-testid="analyzer-tab"]').click()

    # Locate the submit button and the argument input
    submit_button = page.locator("form.analyzer-form button[type=\"submit\"]")
    argument_input = page.locator("#argument-text")

    # Ensure the input is empty
    expect(argument_input).to_have_value("")

    # The submit button should be disabled when the input is empty
    expect(submit_button).to_be_disabled()

    # Let's also verify that if we type something and then erase it, the button becomes enabled and then disabled again.
    argument_input.fill("test")
    expect(submit_button).to_be_enabled()
    argument_input.fill("")
    expect(submit_button).to_be_disabled()


@pytest.mark.playwright
def test_reset_button_clears_input_and_results(page: Page, frontend_url: str):
    """
    Scenario 1.3: Reset functionality
    Ensures the reset button clears the input field and the analysis results.
    """
    # Navigate to the React app
    page.goto(frontend_url)

    # Wait for the API to be connected
    expect(page.locator(".api-status.connected")).to_be_visible(timeout=30000)

    # Navigate to the "Analyse" tab using the robust data-testid selector
    page.locator('[data-testid="analyzer-tab"]').click()

    # --- Perform an analysis first ---
    argument_input = page.locator("#argument-text")
    submit_button = page.locator("form.analyzer-form button[type=\"submit\"]")
    results_container = page.locator(".analysis-results")
    loading_spinner = page.locator(".loading-spinner")

    argument_text = "Ceci est un test pour la réinitialisation."

    argument_input.fill(argument_text)
    submit_button.click()

    # Wait for results to be visible
    expect(loading_spinner).not_to_be_visible(timeout=20000)
    expect(results_container).to_be_visible()
    expect(results_container).to_contain_text("Résultats de l'analyse")
    expect(argument_input).to_have_value(argument_text)

    # --- Now, test the reset button ---
    # The selector for the reset button is based on its text content.
    reset_button = page.locator("button", has_text="🗑️ Effacer tout")
    reset_button.click()

    # --- Verify that everything is cleared ---
    # Input field should be empty
    expect(argument_input).to_have_value("")

    # Results container should not be visible anymore
    expect(results_container).not_to_be_visible()