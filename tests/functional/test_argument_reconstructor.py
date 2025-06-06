import pytest
from playwright.sync_api import Page, expect

@pytest.mark.playwright
def test_successful_simple_reconstruction(page: Page):
    """
    Scenario 3.1: Successful reconstruction of a simple argument (Happy Path)
    """
    page.goto("http://localhost:3000/")

    # --- Wait for API to be connected and select the tab ---
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    expect(reconstructor_tab).to_be_enabled(timeout=15000) # Wait for the tab to be clickable
    reconstructor_tab.click()

    # --- Interact with the reconstructor components ---
    argument_input = page.locator('[data-testid="reconstructor-text-input"]') # Assumed selector
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]') # Assumed selector
    results_container = page.locator('[data-testid="reconstructor-results-container"]') # Assumed selector
    loading_spinner = page.locator(".loading-spinner") # Assuming a shared spinner

    # Define the argument
    argument_text = "Tous les hommes sont mortels. Socrate est un homme. Donc, Socrate est mortel."

    # Fill the input and submit
    expect(argument_input).to_be_visible()
    argument_input.fill(argument_text)
    submit_button.click()

    # Wait for the loading spinner to disappear
    expect(loading_spinner).not_to_be_visible(timeout=20000)

    # Wait for the results and check for some expected text
    expect(results_container).to_be_visible()
    expect(results_container).to_contain_text("Prémisse 1")
    expect(results_container).to_contain_text("Conclusion")


@pytest.mark.playwright
def test_reconstruction_api_error(page: Page):
    """
    Scenario 3.2: API error during reconstruction
    """
    page.goto("http://localhost:3000/")

    # --- Wait for API to be connected and select the tab ---
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    expect(reconstructor_tab).to_be_enabled(timeout=15000)
    reconstructor_tab.click()

    # --- Mock the API call to return an error ---
    page.route(
        "**/api/analyze",
        lambda route: route.fulfill(
            status=500,
            json={"error": "Internal Server Error"},
        ),
    )

    # --- Interact with the reconstructor components ---
    argument_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    error_container = page.locator('[data-testid="reconstructor-error-message"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')

    # Fill the input and submit
    argument_input.fill("Some text that will cause an error.")
    submit_button.click()

    # --- Assertions for error case ---
    expect(error_container).to_be_visible()
    expect(error_container).to_contain_text("Une erreur inattendue est survenue.")
    expect(results_container).not_to_be_visible()


@pytest.mark.playwright
def test_reconstruction_reset_button(page: Page):
    """
    Scenario 3.3: Reset button clears the input and results
    """
    page.goto("http://localhost:3000/")

    # --- Wait for API to be connected and select the tab ---
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    expect(reconstructor_tab).to_be_enabled(timeout=15000)
    reconstructor_tab.click()

    # --- Interact with the reconstructor components ---
    argument_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    reset_button = page.locator('[data-testid="reconstructor-reset-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    error_container = page.locator('[data-testid="reconstructor-error-message"]')
    loading_spinner = page.locator(".loading-spinner")

    # --- Perform a successful reconstruction first ---
    argument_text = "Tous les hommes sont mortels. Socrate est un homme. Donc, Socrate est mortel."
    argument_input.fill(argument_text)
    submit_button.click()
    expect(loading_spinner).not_to_be_visible(timeout=20000)
    expect(results_container).to_be_visible()

    # --- Click the reset button ---
    reset_button.click()

    # --- Assertions for reset case ---
    expect(argument_input).to_have_value("")
    expect(results_container).not_to_be_visible()
    expect(error_container).not_to_be_visible()