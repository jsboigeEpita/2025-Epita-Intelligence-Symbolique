import pytest
from playwright.sync_api import Page, expect

# This mark ensures that the 'orchestrator_session' fixture is used for all tests in this module,
# which starts the web server and sets the base_url for playwright.
pytestmark = pytest.mark.usefixtures("orchestrator_session")


@pytest.fixture(scope="function")
def validation_page(page: Page) -> Page:
    """Navigue vers la page et l'onglet de validation."""
    page.goto("/")
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    validation_tab = page.locator('[data-testid="validation-tab"]')
    expect(validation_tab).to_be_enabled()
    validation_tab.click()
    return page

class TestValidationForm:
    """Tests fonctionnels pour l'onglet Validation."""

    def test_validation_form_argument_validation(self, validation_page: Page):
        """Test du workflow principal de validation d'argument."""
        expect(validation_page.locator('#argument-type')).to_be_visible()
        expect(validation_page.locator('.premise-textarea')).to_be_visible()
        expect(validation_page.locator('#conclusion')).to_be_visible()
        expect(validation_page.locator('.validate-button')).to_be_visible()

        validation_page.locator('#argument-type').select_option('deductive')
        validation_page.locator('.premise-textarea').first.fill('Tous les hommes sont mortels')
        validation_page.locator('.add-premise-button').click()
        validation_page.locator('.premise-textarea').nth(1).fill('Socrate est un homme')
        validation_page.locator('#conclusion').fill('Socrate est mortel')
        validation_page.locator('.validate-button').click()
        expect(validation_page.locator('.validation-status')).to_be_visible(timeout=15000)
        results = validation_page.locator('.results-section')
        expect(results).to_be_visible()
        confidence_score = validation_page.locator('.confidence-score')
        if confidence_score.is_visible():
            expect(confidence_score).to_contain_text('%')

    def test_validation_error_scenarios(self, validation_page: Page):
        """Test des scénarios d'erreur et de validation invalide."""
        validate_button = validation_page.locator('.validate-button')
        expect(validate_button).to_be_disabled()

        validation_page.locator('.premise-textarea').first.fill('')
        validation_page.locator('#conclusion').fill('Une conclusion sans prémisses')
        expect(validate_button).to_be_disabled()

        validation_page.locator('.premise-textarea').first.fill('Une prémisse incomplète')
        validation_page.locator('#conclusion').fill('')
        expect(validate_button).to_be_disabled()

    def test_validation_form_reset_functionality(self, validation_page: Page):
        """Test de la fonctionnalité de réinitialisation du formulaire."""
        validation_page.locator('#argument-type').select_option('inductive')
        validation_page.locator('.premise-textarea').first.fill('Test prémisse pour reset')
        validation_page.locator('#conclusion').fill('Test conclusion pour reset')

        expect(validation_page.locator('.premise-textarea').first).to_have_value('Test prémisse pour reset')
        expect(validation_page.locator('#conclusion')).to_have_value('Test conclusion pour reset')
        expect(validation_page.locator('#argument-type')).to_have_value('inductive')

        validation_page.locator('.reset-button').click()

        expect(validation_page.locator('.premise-textarea').first).to_have_value('')
        expect(validation_page.locator('#conclusion')).to_have_value('')
        expect(validation_page.locator('#argument-type')).to_have_value('deductive')  # Valeur par défaut

    def test_validation_example_functionality(self, validation_page: Page):
        """Test de la fonctionnalité de chargement d'exemple."""
        validation_page.locator('.example-button').click()

        expect(validation_page.locator('.premise-textarea').first).not_to_have_value('')
        expect(validation_page.locator('#conclusion')).not_to_have_value('')

        premise_value = validation_page.locator('.premise-textarea').first.input_value()
        conclusion_value = validation_page.locator('#conclusion').input_value()

        assert len(premise_value) > 0, "L'exemple devrait charger une prémisse"
        assert len(conclusion_value) > 0, "L'exemple devrait charger une conclusion"

        validation_page.locator('.validate-button').click()
        expect(validation_page.locator('.validation-status')).to_be_visible(timeout=15000)
