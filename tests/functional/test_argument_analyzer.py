import re
from playwright.sync_api import Page, expect

def test_successful_simple_argument_analysis(page: Page):
    """
    Scenario 1.1: Successful analysis of a simple argument (Happy Path)
    This test targets the React application on port 3000.
    """
    # Navigate to the React app
    page.goto("http://localhost:3000/")

    # Wait for the API to be connected
    expect(page.locator(".api-status.connected")).to_be_visible(timeout=30000)

    # Pause for debugging if the element is not found
    try:
        # Wait for the form to be visible, which indicates the app has loaded
        expect(page.locator("form.analyzer-form")).to_be_visible(timeout=10000)
    except Exception:
        print("Could not find the form. Here is the page content:")
        print(page.content())
        page.pause() # This will pause the test and open a browser for inspection

    # Use the selectors identified in the architecture analysis
    argument_input = page.locator("#argument-text")
    # The submit button is inside the form with class 'analyzer-form'
    submit_button = page.locator("form.analyzer-form button[type=\"submit\"]")
    results_container = page.locator(".analysis-results")
    loading_spinner = page.locator(".loading-spinner")

    # Define the argument
    argument_text = "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel."

    # Wait for the input to be visible and then fill it
    expect(argument_input).to_be_visible()
    argument_input.fill(argument_text)
    
    # Click the submit button
    submit_button.click()

    # Wait for the loading spinner to disappear
    expect(loading_spinner).not_to_be_visible(timeout=20000)

    # Wait for the results to be displayed and check for content
    expect(results_container).to_be_visible()
    expect(results_container).to_contain_text("Structure argumentative")
def test_empty_argument_submission_displays_error(page: Page):
    """
    Scenario 1.2: Empty submission (Error Path)
    Checks if an error message is displayed when submitting an empty argument.
    """
    # Navigate to the React app
    page.goto("http://localhost:3000/")

    # Wait for the API to be connected
    expect(page.locator(".api-status.connected")).to_be_visible(timeout=30000)

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
def test_reset_button_clears_input_and_results(page: Page):
    """
    Scenario 1.3: Reset functionality
    Ensures the reset button clears the input field and the analysis results.
    """
    # Navigate to the React app
    page.goto("http://localhost:3000/")

    # Wait for the API to be connected
    expect(page.locator(".api-status.connected")).to_be_visible(timeout=30000)

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