import pytest
from playwright.sync_api import Page, expect, TimeoutError
from tests.functional.conftest import PlaywrightHelpers


class TestValidationForm:
    """Tests fonctionnels pour l'onglet Validation basés sur la structure réelle"""

    def test_validation_form_argument_validation(self, validation_page: Page, test_helpers: PlaywrightHelpers):
        """Test du workflow principal de validation d'argument"""
        page = validation_page
        
        # Navigation vers l'onglet Validation
        test_helpers.navigate_to_tab("validation")
        
        # Vérification de la présence des éléments du formulaire réels
        expect(page.locator('#argument-type')).to_be_visible()
        expect(page.locator('.premise-textarea')).to_be_visible()
        expect(page.locator('#conclusion')).to_be_visible()
        expect(page.locator('.validate-button')).to_be_visible()
        
        # Sélection du type d'argument
        page.locator('#argument-type').select_option('deductive')
        
        # Saisie d'une prémisse
        page.locator('.premise-textarea').first.fill('Tous les hommes sont mortels')
        
        # Ajout d'une seconde prémisse
        page.locator('.add-premise-button').click()
        premise_textareas = page.locator('.premise-textarea')
        premise_textareas.nth(1).fill('Socrate est un homme')
        
        # Saisie de la conclusion
        page.locator('#conclusion').fill('Socrate est mortel')
        
        # Déclenchement de la validation
        page.locator('.validate-button').click()
        
        # Attendre les résultats
        expect(page.locator('.validation-status')).to_be_visible(timeout=test_helpers.API_CONNECTION_TIMEOUT)
        
        # Vérification des résultats
        results = page.locator('.results-section')
        expect(results).to_be_visible()
        
        # Vérification du score de confiance si présent
        confidence_score = page.locator('.confidence-score')
        if confidence_score.is_visible():
            expect(confidence_score).to_contain_text('%')

    def test_validation_error_scenarios(self, validation_page: Page, test_helpers: PlaywrightHelpers):
        """Test des scénarios d'erreur et de validation invalide"""
        page = validation_page
        
        # Navigation vers l'onglet Validation
        test_helpers.navigate_to_tab("validation")
        
        # Test avec formulaire vide - le bouton devrait être désactivé
        validate_button = page.locator('.validate-button')
        expect(validate_button).to_be_disabled()
        
        # Test avec seulement des prémisses vides
        page.locator('.premise-textarea').first.fill('')
        page.locator('#conclusion').fill('Une conclusion sans prémisses')
        expect(validate_button).to_be_disabled()
        
        # Test avec argument incomplet
        page.locator('.premise-textarea').first.fill('Une prémisse incomplète')
        page.locator('#conclusion').fill('')
        expect(validate_button).to_be_disabled()
        
        # Test avec argument valide mais avec erreur réseau simulée
        page.locator('.premise-textarea').first.fill('Test prémisse')
        page.locator('#conclusion').fill('Test conclusion')
        
        # Le bouton devrait maintenant être activé
        expect(validate_button).to_be_enabled()
        
        # Clic sur validation
        validate_button.click()
        
        # Attendre soit un résultat soit un message d'erreur
        try:
            page.wait_for_selector('.validation-status, .error-message', timeout=test_helpers.API_CONNECTION_TIMEOUT)
        except TimeoutError:
            pytest.fail("Aucun résultat ou message d'erreur affiché après validation")

    def test_validation_form_reset_functionality(self, validation_page: Page, test_helpers: PlaywrightHelpers):
        """Test de la fonctionnalité de réinitialisation du formulaire"""
        page = validation_page
        
        # Navigation vers l'onglet Validation
        test_helpers.navigate_to_tab("validation")
        
        # Remplissage du formulaire
        page.locator('#argument-type').select_option('inductive')
        page.locator('.premise-textarea').first.fill('Test prémisse pour reset')
        page.locator('#conclusion').fill('Test conclusion pour reset')
        
        # Vérification que les champs sont remplis
        expect(page.locator('.premise-textarea').first).to_have_value('Test prémisse pour reset')
        expect(page.locator('#conclusion')).to_have_value('Test conclusion pour reset')
        expect(page.locator('#argument-type')).to_have_value('inductive')
        
        # Réinitialisation
        page.locator('.reset-button').click()
        
        # Vérification que les champs sont réinitialisés
        expect(page.locator('.premise-textarea').first).to_have_value('')
        expect(page.locator('#conclusion')).to_have_value('')
        expect(page.locator('#argument-type')).to_have_value('deductive')  # Valeur par défaut

    def test_validation_example_functionality(self, validation_page: Page, test_helpers: PlaywrightHelpers):
        """Test de la fonctionnalité de chargement d'exemple"""
        page = validation_page
        
        # Navigation vers l'onglet Validation
        test_helpers.navigate_to_tab("validation")
        
        # Chargement d'un exemple
        page.locator('.example-button').click()
        
        # Vérification que l'exemple est chargé
        expect(page.locator('.premise-textarea').first).not_to_have_value('')
        expect(page.locator('#conclusion')).not_to_have_value('')
        
        # L'exemple devrait charger des prémisses logiques
        premise_value = page.locator('.premise-textarea').first.input_value()
        conclusion_value = page.locator('#conclusion').input_value()
        
        assert len(premise_value) > 0, "L'exemple devrait charger une prémisse"
        assert len(conclusion_value) > 0, "L'exemple devrait charger une conclusion"
        
        # Test de validation avec l'exemple chargé
        page.locator('.validate-button').click()
        
        # Attendre les résultats
        expect(page.locator('.validation-status')).to_be_visible(timeout=test_helpers.API_CONNECTION_TIMEOUT)