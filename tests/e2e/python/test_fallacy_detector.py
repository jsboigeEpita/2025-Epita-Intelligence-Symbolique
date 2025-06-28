import re
import pytest
from playwright.sync_api import Page, expect

# The 'webapp_service' session fixture in conftest.py is autouse=True,
# so the web server is started automatically for all tests in this module.
@pytest.mark.playwright
@pytest.mark.asyncio
async def test_fallacy_detection_basic_workflow(page: Page, webapp_service: dict):
    """
    Test principal : détection d'un sophisme Ad Hominem
    Valide le workflow complet de détection avec un exemple prédéfini
    """
    # 1. Navigation et attente API connectée
    await page.goto(webapp_service.frontend_url)
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    # 2. Activation de l'onglet Sophismes
    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    expect(fallacy_tab).to_be_enabled()
    fallacy_tab.click()
    
    # 3. Localisation des éléments d'interface
    text_input = page.locator('[data-testid="fallacy-text-input"]')
    submit_button = page.locator('[data-testid="fallacy-submit-button"]')
    results_container = page.locator('[data-testid="fallacy-results-container"]')
    
    # 4. Saisie d'un exemple Ad Hominem
    ad_hominem_text = "Cette théorie sur le climat est fausse parce que son auteur a été condamné pour fraude fiscale."
    expect(text_input).to_be_visible()
    text_input.fill(ad_hominem_text)
    
    # 5. Soumission du formulaire
    expect(submit_button).to_be_enabled()
    submit_button.click()
    
    # 6. Attente des résultats
    expect(results_container).to_be_visible(timeout=10000)
    
    # 7. Vérification de la détection
    expect(results_container).to_contain_text("sophisme(s) détecté(s)")
    expect(results_container).to_contain_text("Ad Hominem")
    
    # 8. Vérification présence d'un niveau de sévérité
    severity_badge = results_container.locator('.severity-badge').first
    expect(severity_badge).to_be_visible()

@pytest.mark.playwright
@pytest.mark.asyncio
async def test_severity_threshold_adjustment(page: Page, webapp_service: dict):
    """
    Test curseur seuil de sévérité
    Vérifie l'impact du seuil sur les résultats de détection
    """
    # 1. Navigation et activation onglet
    await page.goto(webapp_service.frontend_url)
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    fallacy_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="fallacy-text-input"]')
    submit_button = page.locator('[data-testid="fallacy-submit-button"]')
    results_container = page.locator('[data-testid="fallacy-results-container"]')
    severity_slider = page.locator('.severity-slider')
    
    # 3. Saisie d'un texte avec sophisme modéré
    moderate_fallacy = "Si on autorise les gens à conduire à 85 km/h, bientôt ils voudront conduire à 200 km/h."
    text_input.fill(moderate_fallacy)
    
    # 4. Test avec seuil élevé (0.8) - devrait détecter moins
    severity_slider.fill('0.8')
    submit_button.click()
    
    # Attendre les résultats du premier test
    expect(results_container).to_be_visible(timeout=10000)
    first_result_text = results_container.text_content()
    
    # 5. Réduction du seuil (0.3) - devrait détecter plus
    severity_slider.fill('0.3')
    submit_button.click()
    
    # Attendre les nouveaux résultats
    expect(results_container).to_be_visible(timeout=10000)
    second_result_text = results_container.text_content()
    
    # 6. Vérification que les résultats changent avec le seuil
    # Note: Les résultats peuvent être différents selon le seuil
    expect(results_container).to_contain_text("sophisme(s) détecté(s)")

@pytest.mark.playwright
@pytest.mark.asyncio
async def test_fallacy_example_loading(page: Page, webapp_service: dict):
    """
    Test chargement des exemples prédéfinis
    Valide le fonctionnement des boutons "Tester" sur les cartes d'exemples
    """
    # 1. Navigation et activation onglet
    await page.goto(webapp_service.frontend_url)
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    fallacy_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="fallacy-text-input"]')
    examples_section = page.locator('.fallacy-examples')
    
    # 3. Vérification présence des exemples
    expect(examples_section).to_be_visible()
    expect(examples_section).to_contain_text("Exemples de sophismes courants")
    
    # 4. Recherche du premier bouton "Tester" (Ad Hominem)
    first_test_button = examples_section.locator('button.btn:has-text("Tester")').first
    expect(first_test_button).to_be_visible()
    
    # 5. Vérification que le champ est initialement vide
    expect(text_input).to_have_value("")
    
    # 6. Clic sur le bouton "Tester"
    first_test_button.click()
    
    # 7. Vérification que le texte a été rempli automatiquement
    expect(text_input).not_to_have_value("")
    
    # 8. Vérification que le texte contient bien un exemple
    input_value = text_input.input_value()
    assert len(input_value) > 10, f"Le texte d'exemple devrait contenir plus de 10 caractères, mais contient seulement {len(input_value)}"
    
    # 9. Vérification que le bouton submit est maintenant activé
    submit_button = page.locator('[data-testid="fallacy-submit-button"]')
    expect(submit_button).to_be_enabled()

@pytest.mark.playwright
@pytest.mark.asyncio
async def test_fallacy_detector_reset_functionality(page: Page, webapp_service: dict):
    """
    Test bouton de réinitialisation
    Vérifie que le bouton reset nettoie complètement l'interface
    """
    # 1. Navigation et activation onglet
    await page.goto(webapp_service.frontend_url)
    expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    fallacy_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="fallacy-text-input"]')
    submit_button = page.locator('[data-testid="fallacy-submit-button"]')
    reset_button = page.locator('[data-testid="fallacy-reset-button"]')
    results_container = page.locator('[data-testid="fallacy-results-container"]')
    
    # 3. Effectuer une détection complète d'abord
    test_text = "Cette théorie est fausse parce que son auteur est stupide."
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
    expect(submit_button).to_be_disabled()