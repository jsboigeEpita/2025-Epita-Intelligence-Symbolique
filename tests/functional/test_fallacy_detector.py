import re
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.playwright
def test_successful_simple_fallacy_detection(page: Page):
    """
    Scenario 2.1: Successful detection of a simple fallacy (Happy Path)
    """
    # Navigate to the React app
    page.goto("http://localhost:3000/")

    # --- Select the Fallacy Detector tab ---
    # The selector for the tab needs to be identified. Let's assume it's a button with the text "Détecteur de Sophismes".
    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    fallacy_tab.click()

    # --- Interact with the fallacy detector components ---
    argument_input = page.locator('[data-testid="fallacy-text-input"]') # Assuming a different ID for this input
    submit_button = page.locator('[data-testid="fallacy-submit-button"]') # Assuming a different form
    results_container = page.locator('[data-testid="fallacy-results-container"]') # Assuming a different results container
    loading_spinner = page.locator(".loading-spinner")

    # Define the argument with a fallacy
    argument_text = "Le vendeur a dit que c'était une bonne voiture, donc ça doit être vrai." # Ad Verecundiam (Appeal to authority)

    # Fill the input and submit
    expect(argument_input).to_be_visible()
    argument_input.fill(argument_text)
    submit_button.click()

    # Wait for the loading spinner to disappear
    expect(loading_spinner).not_to_be_visible(timeout=20000)

    # Wait for the results and check for the fallacy name
    expect(results_container).to_be_visible()
    expect(results_container).to_contain_text("Affirmation du conséquent")
@pytest.mark.playwright
def test_submission_with_empty_input_disables_button(page: Page):
    """
    Scenario 2.2: Submission with empty input
    Checks if the submit button is disabled when the input is empty.
    """
    page.goto("http://localhost:3000/")

    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    fallacy_tab.click()

    submit_button = page.locator('[data-testid="fallacy-submit-button"]')
    
    # The button should be disabled initially
    expect(submit_button).to_be_disabled()

    # Optional: check if it remains disabled after interaction
    argument_input = page.locator('[data-testid="fallacy-text-input"]')
    argument_input.fill("test")
    argument_input.fill("")
    expect(submit_button).to_be_disabled()
@pytest.mark.playwright
def test_reset_button_clears_input_and_results(page: Page):
    """
    Scenario 2.3: Reset button functionality
    Checks if the reset button clears the input field and the results.
    """
    page.goto("http://localhost:3000/")

    # Navigate to the tab
    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    fallacy_tab.click()

    # Locate elements
    argument_input = page.locator('[data-testid="fallacy-text-input"]')
    submit_button = page.locator('[data-testid="fallacy-submit-button"]')
    reset_button = page.locator('[data-testid="fallacy-reset-button"]')
    results_container = page.locator('[data-testid="fallacy-results-container"]')
    loading_spinner = page.locator(".loading-spinner")

    # Perform an analysis to get results
    argument_input.fill("Ceci est un test pour le bouton reset.")
    submit_button.click()
    expect(loading_spinner).not_to_be_visible(timeout=20000)
    expect(results_container).to_be_visible()

    # Click the reset button
    reset_button.click()

    # Assert that the input is cleared and results are hidden
    expect(argument_input).to_have_value("")
    expect(results_container).not_to_be_visible()