import pytest
from playwright.sync_api import Page, expect

# The 'webapp_service' session fixture in conftest.py is autouse=True,
# so the web server is started automatically for all tests in this module.
@pytest.fixture(scope="function")
def validation_page(page: Page, frontend_url: str) -> Page:
    """Navigue vers la page, attend le chargement et clique sur l'onglet de validation."""
    # Attend que le réseau soit inactif, ce qui est un bon indicateur que le chargement initial est terminé.
    page.goto(frontend_url, wait_until="networkidle")

    # Vérification robuste que nous sommes sur la bonne application.
    expect(page).to_have_title("Argumentation Analysis App", timeout=10000)

    # Clic sur l'onglet de validation
    validation_tab = page.locator('[data-testid="validation-tab"]')
    expect(validation_tab).to_be_enabled(timeout=10000)
    validation_tab.click()

    # Attendre que le panneau de l'onglet soit visible après le clic
    expect(page.locator('div[role="tabpanel"][aria-hidden="false"]')).to_be_visible()

    return page

class TestValidationForm:
    """Tests fonctionnels pour l'onglet Validation."""

    @pytest.mark.asyncio
    async def test_validation_form_argument_validation(self, validation_page: Page):
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

    @pytest.mark.asyncio
    async def test_validation_error_scenarios(self, validation_page: Page):
        """Test des scénarios d'erreur et de validation invalide."""
        validate_button = validation_page.locator('.validate-button')
        expect(validate_button).to_be_disabled()

        validation_page.locator('.premise-textarea').first.fill('')
        validation_page.locator('#conclusion').fill('Une conclusion sans prémisses')
        expect(validate_button).to_be_disabled()

        validation_page.locator('.premise-textarea').first.fill('Une prémisse incomplète')
        validation_page.locator('#conclusion').fill('')
        expect(validate_button).to_be_disabled()

    @pytest.mark.asyncio
    async def test_validation_form_reset_functionality(self, validation_page: Page):
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

    @pytest.mark.asyncio
    async def test_validation_example_functionality(self, validation_page: Page):
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
