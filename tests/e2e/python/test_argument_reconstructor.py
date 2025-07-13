import re
import pytest
import logging
from playwright.async_api import Page, expect

logger = logging.getLogger(__name__)

# Les fixtures frontend_url et backend_url sont injectées par l'orchestrateur de test.
@pytest.mark.asyncio
async def test_argument_reconstruction_workflow(page: Page):
    """
    Test principal : reconstruction d'argument complet
    Valide le workflow de reconstruction avec détection automatique de prémisses/conclusion
    """
    logger.info("--- DEBUT test_argument_reconstruction_workflow ---")
    
    # 1. Navigation et attente API connectée
    logger.info("Étape 1: Navigation vers le frontend et attente de la connexion API.")
    await page.goto("/", wait_until='networkidle')
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    logger.info("Connexion API confirmée.")
    
    # 2. Activation de l'onglet Reconstructeur
    logger.info("Étape 2: Activation de l'onglet Reconstructeur.")
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    await expect(reconstructor_tab).to_be_enabled()
    await reconstructor_tab.click()
    logger.info("Onglet Reconstructeur cliqué.")
    
    # 3. Localisation des éléments d'interface
    text_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    
    # 4. Saisie d'un argument à reconstruire
    logger.info("Étape 4: Saisie du texte de l'argument.")
    argument_text = """
    Tous les hommes sont mortels. Socrate est un homme.
    Donc Socrate est mortel.
    """
    await expect(text_input).to_be_visible()
    await text_input.fill(argument_text)
    logger.info("Texte saisi.")
    
    # 5. Soumission du formulaire
    logger.info("Étape 5: Soumission du formulaire de reconstruction.")
    await expect(submit_button).to_be_enabled()
    await submit_button.click()
    logger.info("Bouton de soumission cliqué.")
    
    # 6. Attente des résultats de reconstruction
    logger.info("Étape 6: Attente de l'affichage du conteneur de résultats...")
    await expect(results_container).to_be_visible(timeout=20000) # Timeout augmenté pour les traitements longs
    
    # 7. Vérification des sections principales
    await expect(results_container).to_contain_text("Résultats de la Reconstruction")
    await expect(results_container).to_contain_text("Prémisses")
    await expect(results_container).to_contain_text("Conclusion")
    
    # 8. Vérification contenu des prémisses - structure attendue de l'API
    await expect(results_container).to_contain_text("Prémisse 1")
    await expect(results_container).to_contain_text("Tous les hommes sont mortels")
    await expect(results_container).to_contain_text("Socrate est un homme")
    
    # 9. Vérification de la conclusion
    await expect(results_container).to_contain_text("Socrate est mortel")

@pytest.mark.asyncio
async def test_reconstructor_basic_functionality(page: Page):
    """
    Test fonctionnalité de base du reconstructeur
    Vérifie qu'un deuxième argument peut être analysé correctement
    """
    # 1. Navigation et activation onglet
    await page.goto("/", wait_until='networkidle')
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    await reconstructor_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    
    # 3. Saisie d'un argument différent
    argument_text = "Si il pleut, la route est mouillée. Il pleut actuellement. La route doit donc être mouillée."
    await text_input.fill(argument_text)
    await submit_button.click()
    
    # 4. Attente des résultats
    await expect(results_container).to_be_visible(timeout=10000)
    
    # 5. Vérification contenu basique
    await expect(results_container).to_contain_text("Résultats de la Reconstruction")
    await expect(results_container).to_contain_text("Prémisses")
    await expect(results_container).to_contain_text("Conclusion")

@pytest.mark.asyncio
async def test_reconstructor_error_handling(page: Page):
    """
    Test gestion d'erreurs
    Vérifie le comportement avec un texte invalide ou sans structure argumentative claire
    """
    # 1. Navigation et activation onglet
    await page.goto("/", wait_until='networkidle')
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    await reconstructor_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    
    # 3. Test avec texte trop court
    await text_input.fill("Test.")
    await submit_button.click()
    
    # 4. Attente et vérification que l'analyse se fait quand même
    await expect(results_container).to_be_visible(timeout=10000)
    await expect(results_container).to_contain_text("Résultats de la Reconstruction")
    
    # 5. Test avec texte sans structure argumentative claire
    await text_input.clear()
    await text_input.fill("J'aime les pommes. Les pommes sont rouges. Le rouge est une couleur.")
    await submit_button.click()
    
    # 6. Vérification que l'analyse se fait quand même
    await expect(results_container).to_be_visible(timeout=10000)
    await expect(results_container).to_contain_text("Résultats de la Reconstruction")
    await expect(results_container).to_contain_text("Prémisses")
    await expect(results_container).to_contain_text("Conclusion")

@pytest.mark.asyncio
async def test_reconstructor_reset_functionality(page: Page):
    """
    Test bouton de réinitialisation
    Vérifie que le reset nettoie complètement l'interface et revient à l'état initial
    """
    # 1. Navigation et activation onglet
    await page.goto("/", wait_until='networkidle')
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    await reconstructor_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    reset_button = page.locator('[data-testid="reconstructor-reset-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    
    # 3. Effectuer une reconstruction
    test_text = "Tous les chats sont des animaux. Felix est un chat. Donc Felix est un animal."
    await text_input.fill(test_text)
    await submit_button.click()
    
    # 4. Attendre les résultats
    await expect(results_container).to_be_visible(timeout=10000)
    await expect(text_input).to_have_value(test_text)
    
    # 5. Clic sur le bouton reset
    await expect(reset_button).to_be_enabled()
    await reset_button.click()
    
    # 6. Vérifications après reset
    await expect(text_input).to_have_value("")
    await expect(results_container).not_to_be_visible()
    await expect(submit_button).to_be_enabled()

@pytest.mark.asyncio
async def test_reconstructor_content_persistence(page: Page):
    """
    Test persistance du contenu
    Vérifie que le contenu reste affiché après reconstruction
    """
    # 1. Navigation et activation onglet
    await page.goto("/", wait_until='networkidle')
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    reconstructor_tab = page.locator('[data-testid="reconstructor-tab"]')
    await reconstructor_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="reconstructor-text-input"]')
    submit_button = page.locator('[data-testid="reconstructor-submit-button"]')
    results_container = page.locator('[data-testid="reconstructor-results-container"]')
    
    # 3. Effectuer une reconstruction complète
    argument_text = "Tous les oiseaux ont des ailes. Les pingouins sont des oiseaux. Donc les pingouins ont des ailes."
    await text_input.fill(argument_text)
    await submit_button.click()
    
    # 4. Attendre les résultats
    await expect(results_container).to_be_visible(timeout=10000)
    
    # 5. Vérifier que le texte d'entrée est conservé
    await expect(text_input).to_have_value(argument_text)
    
    # 6. Vérifier que les résultats sont toujours visibles
    await expect(results_container).to_contain_text("Résultats de la Reconstruction")
    await expect(results_container).to_contain_text("Prémisses")
    await expect(results_container).to_contain_text("Conclusion")
    
    # 7. Vérifier que le bouton reste activé pour une nouvelle analyse
    await expect(submit_button).to_be_enabled()
    await expect(submit_button).to_contain_text("Reconstruire")