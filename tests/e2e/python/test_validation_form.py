import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
@pytest.mark.playwright
class TestValidationForm:
    """Tests fonctionnels pour l'onglet Validation."""

    @pytest.fixture(autouse=True)
    def setup_page(self, page: Page, e2e_servers):
        """Fixture pour préparer la page avant chaque test de cette classe."""
        _, frontend_url = e2e_servers
        
        # Étape 1: Navigation et attente de la page chargée
        page.goto(frontend_url, wait_until="networkidle")
        expect(page).to_have_title("Argumentation Analysis App", timeout=10000)
        
        # Étape 2: Attente de la connexion API backend.
        # Le test vérifie que l'indicateur de statut a la bonne couleur de fond (vert),
        # ce qui est un indicateur fiable que le JS de statut a bien fonctionné.
        status_indicator = page.locator('.status-indicator')
        expect(status_indicator).to_be_visible(timeout=10000)
        # La couleur du statut n'est pas directement sur cet élément dans la version React.
        # Nous allons donc attendre le conteneur parent qui a la classe 'connected'.
        expect(page.locator('.api-status.connected')).to_be_visible(timeout=20000)
        
        # Étape 3: Clic sur l'onglet et attente de l'affichage du contenu
        validation_tab = page.locator('[data-testid="validation-tab"]')
        expect(validation_tab).to_be_enabled(timeout=10000)
        validation_tab.click()

        # Attente robuste que le contenu de l'onglet soit visible et prêt
        # On attend l'un des éléments clés du formulaire de validation.
        expect(page.locator('#argument-type')).to_be_visible(timeout=10000)
        expect(page.locator('.premise-textarea')).to_be_visible(timeout=5000)
        
        # Le `yield` n'est pas nécessaire ici car la fixture `page` est déjà gérée par pytest-playwright.

    def test_validation_form_argument_validation(self, page: Page):
        """Test du workflow principal de validation d'argument."""
        expect(page.locator('#argument-type')).to_be_visible()
        expect(page.locator('.premise-textarea')).to_be_visible()
        expect(page.locator('#conclusion')).to_be_visible()
        expect(page.locator('.validate-button')).to_be_visible()

        page.locator('#argument-type').select_option('deductive')
        page.locator('.premise-textarea').first.fill('Tous les hommes sont mortels')
        page.locator('.add-premise-button').click()
        page.locator('.premise-textarea').nth(1).fill('Socrate est un homme')
        page.locator('#conclusion').fill('Socrate est mortel')
        page.locator('.validate-button').click()
        expect(page.locator('.validation-status')).to_be_visible(timeout=15000)
        results = page.locator('.results-section')
        expect(results).to_be_visible()
        confidence_score = page.locator('.confidence-score')
        if confidence_score.is_visible():
            expect(confidence_score).to_contain_text('%')

    def test_validation_error_scenarios(self, page: Page):
        """Test des scénarios d'erreur et de validation invalide."""
        validate_button = page.locator('.validate-button')
        expect(validate_button).to_be_disabled()

        page.locator('.premise-textarea').first.fill('')
        page.locator('#conclusion').fill('Une conclusion sans prémisses')
        expect(validate_button).to_be_disabled()

        page.locator('.premise-textarea').first.fill('Une prémisse incomplète')
        page.locator('#conclusion').fill('')
        expect(validate_button).to_be_disabled()

    def test_validation_form_reset_functionality(self, page: Page):
        """Test de la fonctionnalité de réinitialisation du formulaire."""
        page.locator('#argument-type').select_option('inductive')
        page.locator('.premise-textarea').first.fill('Test prémisse pour reset')
        page.locator('#conclusion').fill('Test conclusion pour reset')

        expect(page.locator('.premise-textarea').first).to_have_value('Test prémisse pour reset')
        expect(page.locator('#conclusion')).to_have_value('Test conclusion pour reset')
        expect(page.locator('#argument-type')).to_have_value('inductive')

        page.locator('.reset-button').click()

        expect(page.locator('.premise-textarea').first).to_have_value('')
        expect(page.locator('#conclusion')).to_have_value('')
        expect(page.locator('#argument-type')).to_have_value('deductive')  # Valeur par défaut

    def test_validation_example_functionality(self, page: Page):
        """Test de la fonctionnalité de chargement d'exemple."""
        page.locator('.example-button').click()

        expect(page.locator('.premise-textarea').first).not_to_have_value('')
        expect(page.locator('#conclusion')).not_to_have_value('')

        premise_value = page.locator('.premise-textarea').first.input_value()
        conclusion_value = page.locator('#conclusion').input_value()

        assert len(premise_value) > 0, "L'exemple devrait charger une prémisse"
        assert len(conclusion_value) > 0, "L'exemple devrait charger une conclusion"

        page.locator('.validate-button').click()
        expect(page.locator('.validation-status')).to_be_visible(timeout=15000)
