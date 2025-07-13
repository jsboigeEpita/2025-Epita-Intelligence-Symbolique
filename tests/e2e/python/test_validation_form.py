import pytest
from playwright.async_api import Page, expect

# Les URLs des services sont injectées via les fixtures `frontend_url` et `backend_url`.
# so the web server is started automatically for all tests in this module.
@pytest.fixture(scope="function")
async def validation_page(page: Page) -> Page:
    """Navigue vers la page, attend le chargement et clique sur l'onglet de validation."""
    # Attend que le réseau soit inactif, ce qui est un bon indicateur que le chargement initial est terminé.
    await page.goto("/", wait_until="networkidle")

    # Vérification robuste que nous sommes sur la bonne application.
    await expect(page).to_have_title("Argumentation Analysis App", timeout=10000)

    # Attendre que le backend soit connecté
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    validation_tab = page.locator('[data-testid="validation-tab"]')
    await expect(validation_tab).to_be_enabled(timeout=10000)
    await validation_tab.click()

    # Attendre que le panneau de l'onglet soit visible après le clic
    await expect(page.locator('div[role="tabpanel"][aria-hidden="false"]')).to_be_visible()

    return page

class TestValidationForm:
    """Tests fonctionnels pour l'onglet Validation."""

    @pytest.mark.asyncio
    async def test_validation_form_argument_validation(self, validation_page: Page):
        """Test du workflow principal de validation d'argument."""
        await expect(validation_page.locator('#argument-type')).to_be_visible()
        await expect(validation_page.locator('.premise-textarea')).to_be_visible()
        await expect(validation_page.locator('#conclusion')).to_be_visible()
        await expect(validation_page.locator('.validate-button')).to_be_visible()

        await validation_page.locator('#argument-type').select_option('deductive')
        await validation_page.locator('.premise-textarea').first.fill('Tous les hommes sont mortels')
        await validation_page.locator('.add-premise-button').click()
        await validation_page.locator('.premise-textarea').nth(1).fill('Socrate est un homme')
        await validation_page.locator('#conclusion').fill('Socrate est mortel')
        await validation_page.locator('.validate-button').click()
        await expect(validation_page.locator('.validation-status')).to_be_visible(timeout=15000)
        results = validation_page.locator('.results-section')
        await expect(results).to_be_visible()
        confidence_score = validation_page.locator('.confidence-score')
        if await confidence_score.is_visible():
            await expect(confidence_score).to_contain_text('%')

    @pytest.mark.asyncio
    async def test_validation_error_scenarios(self, validation_page: Page):
        """Test des scénarios d'erreur et de validation invalide."""
        validate_button = validation_page.locator('.validate-button')
        await expect(validate_button).to_be_disabled()

        await validation_page.locator('.premise-textarea').first.fill('')
        await validation_page.locator('#conclusion').fill('Une conclusion sans prémisses')
        await expect(validate_button).to_be_disabled()

        await validation_page.locator('.premise-textarea').first.fill('Une prémisse incomplète')
        await validation_page.locator('#conclusion').fill('')
        await expect(validate_button).to_be_disabled()

    @pytest.mark.asyncio
    async def test_validation_form_reset_functionality(self, validation_page: Page):
        """Test de la fonctionnalité de réinitialisation du formulaire."""
        await validation_page.locator('#argument-type').select_option('inductive')
        await validation_page.locator('.premise-textarea').first.fill('Test prémisse pour reset')
        await validation_page.locator('#conclusion').fill('Test conclusion pour reset')

        await expect(validation_page.locator('.premise-textarea').first).to_have_value('Test prémisse pour reset')
        await expect(validation_page.locator('#conclusion')).to_have_value('Test conclusion pour reset')
        await expect(validation_page.locator('#argument-type')).to_have_value('inductive')

        await validation_page.locator('.reset-button').click()

        await expect(validation_page.locator('.premise-textarea').first).to_have_value('')
        await expect(validation_page.locator('#conclusion')).to_have_value('')
        await expect(validation_page.locator('#argument-type')).to_have_value('deductive')  # Valeur par défaut

    @pytest.mark.asyncio
    async def test_validation_example_functionality(self, validation_page: Page):
        """Test de la fonctionnalité de chargement d'exemple."""
        await validation_page.locator('.example-button').click()

        await expect(validation_page.locator('.premise-textarea').first).not_to_have_value('')
        await expect(validation_page.locator('#conclusion')).not_to_have_value('')

        premise_value = await validation_page.locator('.premise-textarea').first.input_value()
        conclusion_value = await validation_page.locator('#conclusion').input_value()

        assert len(premise_value) > 0, "L'exemple devrait charger une prémisse"
        assert len(conclusion_value) > 0, "L'exemple devrait charger une conclusion"

        await validation_page.locator('.validate-button').click()
        await expect(validation_page.locator('.validation-status')).to_be_visible(timeout=15000)
