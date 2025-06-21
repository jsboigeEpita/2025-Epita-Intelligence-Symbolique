import re
from playwright.sync_api import Page, expect
import pytest

@pytest.mark.playwright
@pytest.mark.asyncio
async def test_successful_simple_argument_analysis(page: Page, frontend_url: str):
    """
    Scenario 1.1: Successful analysis of a simple argument (Happy Path)
    This test targets the React application.
    """
    # Navigate to the React app
    await page.goto(frontend_url)

    # Wait for the API to be connected
    expect(page.locator(".api-status.connected")).to_be_visible(timeout=30000)

    # Navigate to the "Analyse" tab using the robust data-testid selector
    await page.locator('[data-testid="analyzer-tab"]').click()

    # Use the selectors identified in the architecture analysis
    argument_input = page.locator("#argument-text")
    submit_button = page.locator("form.analyzer-form button[type=\"submit\"]")
    results_container = page.locator(".analysis-results")
    loading_spinner = page.locator(".loading-spinner")

    # Define the argument
    argument_text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."

    # Wait for the input to be visible and then fill it
    await expect(argument_input).to_be_visible()
    await argument_input.fill(argument_text)
    
    # Click the submit button
    await submit_button.click()

    # Wait for the loading spinner to disappear
    await expect(loading_spinner).not_to_be_visible(timeout=60000)

    # Wait for the results to be displayed and check for content
    await expect(results_container).to_be_visible()
    await expect(results_container).to_contain_text("Structure argumentative")


@pytest.mark.playwright
@pytest.mark.asyncio
async def test_empty_argument_submission_displays_error(page: Page, frontend_url: str):
    """
    Scenario 1.2: Empty submission (Error Path)
    Checks if an error message is displayed when submitting an empty argument.
    """
    # Navigate to the React app
    await page.goto(frontend_url)

    # Wait for the API to be connected
    expect(page.locator(".api-status.connected")).to_be_visible(timeout=30000)

    # Navigate to the "Analyse" tab using the robust data-testid selector
    await page.locator('[data-testid="analyzer-tab"]').click()

    # Locate the submit button and the argument input
    submit_button = page.locator("form.analyzer-form button[type=\"submit\"]")
    argument_input = page.locator("#argument-text")
    
    # Ensure the input is empty
    await expect(argument_input).to_have_value("")

    # The submit button should be disabled when the input is empty
    await expect(submit_button).to_be_disabled()

    # Let's also verify that if we type something and then erase it, the button becomes enabled and then disabled again.
    await argument_input.fill("test")
    await expect(submit_button).to_be_enabled()
    await argument_input.fill("")
    await expect(submit_button).to_be_disabled()


@pytest.mark.playwright
@pytest.mark.asyncio
async def test_reset_button_clears_input_and_results(page: Page, frontend_url: str):
    """
    Scenario 1.3: Reset functionality
    Ensures the reset button clears the input field and the analysis results.
    """
    # Navigate to the React app
    await page.goto(frontend_url)

    # Wait for the API to be connected
    expect(page.locator(".api-status.connected")).to_be_visible(timeout=30000)

    # Navigate to the "Analyse" tab using the robust data-testid selector
    await page.locator('[data-testid="analyzer-tab"]').click()

    # --- Perform an analysis first ---
    argument_input = page.locator("#argument-text")
    submit_button = page.locator("form.analyzer-form button[type=\"submit\"]")
    results_container = page.locator(".analysis-results")
    loading_spinner = page.locator(".loading-spinner")
    
    argument_text = "Ceci est un test pour la réinitialisation."
    
    await argument_input.fill(argument_text)
    await submit_button.click()
    
    # Wait for results to be visible
    await expect(loading_spinner).not_to_be_visible(timeout=20000)
    await expect(results_container).to_be_visible()
    await expect(results_container).to_contain_text("Résultats de l'analyse")
    await expect(argument_input).to_have_value(argument_text)

    # --- Now, test the reset button ---
    # The selector for the reset button is based on its text content.
    reset_button = page.locator("button", has_text="🗑️ Effacer tout")
    await reset_button.click()

    # --- Verify that everything is cleared ---
    # Input field should be empty
    await expect(argument_input).to_have_value("")
    
    # Results container should not be visible anymore
    await expect(results_container).not_to_be_visible()