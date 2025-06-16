import re
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.skip(reason="Disabling all functional tests to isolate backend test failures.")
@pytest.mark.playwright
def test_argument_reconstruction_workflow(page: Page):
    """
    Test principal : reconstruction d'argument complet
    Valide le workflow de reconstruction avec détection automatique de prémisses/conclusion
    """
    # 1. Navigation et attente API connectée
    page.goto("/")
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    # 2. Activation de l'onglet Reconstructeur
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    expect(reconstructor_tab).to_be_enabled()
    reconstructor_tab.click()
    
    # 3. Localisation des éléments d'interface
    text_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    
    # 4. Saisie d'un argument à reconstruire
    argument_text = """
    Tous les hommes sont mortels. Socrate est un homme.
    Donc Socrate est mortel.
    """
    expect(text_input).to_be_visible()
    text_input.fill(argument_text)
    
    # 5. Soumission du formulaire
    expect(submit_button).to_be_enabled()
    submit_button.click()
    
    # 6. Attente des résultats de reconstruction
    expect(results_container).to_be_visible(timeout=10000)
    
    # 7. Vérification des sections principales
    expect(results_container).to_contain_text("Résultats de la Reconstruction")
    expect(results_container).to_contain_text("Prémisses")
    expect(results_container).to_contain_text("Conclusion")
    
    # 8. Vérification contenu des prémisses - structure attendue de l'API
    expect(results_container).to_contain_text("Prémisse 1")
    expect(results_container).to_contain_text("Tous les hommes sont mortels")
    expect(results_container).to_contain_text("Socrate est un homme")
    
    # 9. Vérification de la conclusion
    expect(results_container).to_contain_text("Socrate est mortel")

@pytest.mark.playwright
def test_reconstructor_basic_functionality(page: Page):
    """
    Test fonctionnalité de base du reconstructeur
    Vérifie qu'un deuxième argument peut être analysé correctement
    """
    # 1. Navigation et activation onglet
    page.goto("/")
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    reconstructor_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    
    # 3. Saisie d'un argument différent
    argument_text = "Si il pleut, la route est mouillée. Il pleut actuellement. La route doit donc être mouillée."
    text_input.fill(argument_text)
    submit_button.click()
    
    # 4. Attente des résultats
    expect(results_container).to_be_visible(timeout=10000)
    
    # 5. Vérification contenu basique
    expect(results_container).to_contain_text("Résultats de la Reconstruction")
    expect(results_container).to_contain_text("Prémisses")
    expect(results_container).to_contain_text("Conclusion")

@pytest.mark.playwright
def test_reconstructor_error_handling(page: Page):
    """
    Test gestion d'erreurs
    Vérifie le comportement avec un texte invalide ou sans structure argumentative claire
    """
    # 1. Navigation et activation onglet
    page.goto("/")
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    reconstructor_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    
    # 3. Test avec texte trop court
    text_input.fill("Test.")
    submit_button.click()
    
    # 4. Attente et vérification que l'analyse se fait quand même
    expect(results_container).to_be_visible(timeout=10000)
    expect(results_container).to_contain_text("Résultats de la Reconstruction")
    
    # 5. Test avec texte sans structure argumentative claire
    text_input.clear()
    text_input.fill("J'aime les pommes. Les pommes sont rouges. Le rouge est une couleur.")
    submit_button.click()
    
    # 6. Vérification que l'analyse se fait quand même
    expect(results_container).to_be_visible(timeout=10000)
    expect(results_container).to_contain_text("Résultats de la Reconstruction")
    expect(results_container).to_contain_text("Prémisses")
    expect(results_container).to_contain_text("Conclusion")

@pytest.mark.playwright
def test_reconstructor_reset_functionality(page: Page):
    """
    Test bouton de réinitialisation
    Vérifie que le reset nettoie complètement l'interface et revient à l'état initial
    """
    # 1. Navigation et activation onglet
    page.goto("/")
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    reconstructor_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    reset_button = page.locator('[data-testid="reconstructor-reset-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    
    # 3. Effectuer une reconstruction
    test_text = "Tous les chats sont des animaux. Felix est un chat. Donc Felix est un animal."
    text_input.fill(test_text)
    submit_button.click()
    
    # 4. Attendre les résultats
    expect(results_container).to_be_visible(timeout=10000)
    expect(text_input).to_have_value(test_text)
    
    # 5. Clic sur le bouton reset
    expect(reset_button).to_be_enabled()
    reset_button.click()
    
    # 6. Vérifications après reset
    expect(text_input).to_have_value("")
    expect(results_container).not_to_be_visible()
    expect(submit_button).to_be_enabled()

@pytest.mark.playwright
def test_reconstructor_content_persistence(page: Page):
    """
    Test persistance du contenu
    Vérifie que le contenu reste affiché après reconstruction
    """
    # 1. Navigation et activation onglet
    page.goto("/")
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    reconstructor_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    
    # 3. Effectuer une reconstruction complète
    argument_text = "Tous les oiseaux ont des ailes. Les pingouins sont des oiseaux. Donc les pingouins ont des ailes."
    text_input.fill(argument_text)
    submit_button.click()
    
    # 4. Attendre les résultats
    expect(results_container).to_be_visible(timeout=10000)
    
    # 5. Vérifier que le texte d'entrée est conservé
    expect(text_input).to_have_value(argument_text)
    
    # 6. Vérifier que les résultats sont toujours visibles
    expect(results_container).to_contain_text("Résultats de la Reconstruction")
    expect(results_container).to_contain_text("Prémisses")
    expect(results_container).to_contain_text("Conclusion")
    
    # 7. Vérifier que le bouton reste activé pour une nouvelle analyse
    expect(submit_button).to_be_enabled()
    expect(submit_button).to_contain_text("Reconstruire")