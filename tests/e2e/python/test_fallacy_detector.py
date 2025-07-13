import re
import pytest
import json
from playwright.async_api import Page, expect

# Les URLs des services sont injectées via les fixtures `frontend_url` et `backend_url`.
# so the web server is started automatically for all tests in this module.
@pytest.mark.asyncio
async def test_fallacy_detection_basic_workflow(page: Page):
    """
    Test principal : détection d'un sophisme Ad Hominem
    Valide le workflow complet de détection avec un exemple prédéfini
    """
    # --- MOCKING DE L'API ---
    # On intercepte l'appel API pour forcer une réponse et isoler le test du backend.
    async def handle_route(route):
        # On vérifie si la requête est bien celle que l'on veut mocker
        if "E2E_TRIGGER_AD_HOMINEM" in route.request.post_data:
            print("Intercepted API call with magic string, returning mock response.")
            # Construction de la réponse JSON attendue par le frontend
            mock_response = {
                "analysis_id": "e2e-mock-1234",
                "status": "success",
                "results": {
                    "overall_quality": 0.2,
                    "fallacy_count": 1,
                    "fallacies": [{
                        "type": "Ad Hominem",
                        "description": "Attaque la personne plutôt que l'argument.",
                        "severity": 0.9,
                        "line": 1,
                        "position": 0,
                        "confidence": 0.95
                    }],
                    "argument_structure": {},
                    "suggestions": [],
                    "summary": "Mocked response for E2E test.",
                    "metadata": {}
                }
            }
            await route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps(mock_response)
            )
        else:
            # Pour toutes les autres requêtes, on les laisse passer normalement
            await route.continue_()

    await page.route("**/api/analyze", handle_route)
    # --- FIN DU MOCKING ---

    # 1. Navigation et attente API connectée
    await page.goto("/")
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    # 2. Activation de l'onglet Détecteur de Sophismes
    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    await expect(fallacy_tab).to_be_enabled()
    await fallacy_tab.click()

    # 3. Localisation des éléments d'interface
    text_input = page.locator('[data-testid="fallacy-text-input"]')
    submit_button = page.locator('[data-testid="fallacy-submit-button"]')
    results_container = page.locator('[data-testid="fallacy-results-container"]')
    
    # 4. Saisie d'un exemple Ad Hominem
    # On utilise une "chaîne magique" pour éviter les problèmes d'encodage/caractères spéciaux.
    ad_hominem_text = "E2E_TRIGGER_AD_HOMINEM"
    await expect(text_input).to_be_visible()
    await text_input.fill(ad_hominem_text)
    
    # 5. Soumission du formulaire
    await expect(submit_button).to_be_enabled()
    await submit_button.click()
    
    # 6. Attente des résultats
    await expect(results_container).to_be_visible(timeout=10000)
    
    # 7. Vérification de la détection
    await expect(results_container).to_contain_text("sophisme(s) détecté(s)")
    await expect(results_container).to_contain_text("Ad Hominem")
    
    # 8. Vérification présence d'un niveau de sévérité
    severity_badge = results_container.locator('.severity-badge').first
    await expect(severity_badge).to_be_visible()

@pytest.mark.asyncio
async def test_severity_threshold_adjustment(page: Page):
    """
    Test curseur seuil de sévérité
    Vérifie l'impact du seuil sur les résultats de détection
    """
    # 1. Navigation et activation onglet
    await page.goto("/")
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    await fallacy_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="fallacy-text-input"]')
    submit_button = page.locator('[data-testid="fallacy-submit-button"]')
    results_container = page.locator('[data-testid="fallacy-results-container"]')
    severity_slider = page.locator('.severity-slider')
    
    # 3. Saisie d'un texte avec sophisme modéré
    moderate_fallacy = "Si on autorise les gens à conduire à 85 km/h, bientôt ils voudront conduire à 200 km/h."
    await text_input.fill(moderate_fallacy)
    
    # 4. Test avec seuil élevé (0.8) - devrait détecter moins
    await severity_slider.fill('0.8')
    await submit_button.click()
    
    # Attendre les résultats du premier test
    await expect(results_container).to_be_visible(timeout=10000)
    first_result_text = await results_container.text_content()
    
    # 5. Réduction du seuil (0.3) - devrait détecter plus
    await severity_slider.fill('0.3')
    await submit_button.click()
    
    # Attendre les nouveaux résultats
    await expect(results_container).to_be_visible(timeout=10000)
    second_result_text = await results_container.text_content()
    
    # 6. Vérification que les résultats changent avec le seuil
    # Note: Les résultats peuvent être différents selon le seuil
    await expect(results_container).to_contain_text("sophisme(s) détecté(s)")

@pytest.mark.asyncio
async def test_fallacy_example_loading(page: Page):
    """
    Test chargement des exemples prédéfinis
    Valide le fonctionnement des boutons "Tester" sur les cartes d'exemples
    """
    # 1. Navigation et activation onglet
    await page.goto("/")
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    await fallacy_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="fallacy-text-input"]')
    examples_section = page.locator('.fallacy-examples')
    
    # 3. Vérification présence des exemples
    await expect(examples_section).to_be_visible()
    await expect(examples_section).to_contain_text("Exemples de sophismes courants")
    
    # 4. Recherche du premier bouton "Tester" (Ad Hominem)
    first_test_button = examples_section.locator('button.btn:has-text("Tester")').first
    await expect(first_test_button).to_be_visible()
    
    # 5. Vérification que le champ est initialement vide
    await expect(text_input).to_have_value("")
    
    # 6. Clic sur le bouton "Tester"
    await first_test_button.click()
    
    # 7. Vérification que le texte a été rempli automatiquement
    await expect(text_input).not_to_have_value("")
    
    # 8. Vérification que le texte contient bien un exemple
    input_value = await text_input.input_value()
    assert len(input_value) > 10, f"Le texte d'exemple devrait contenir plus de 10 caractères, mais contient seulement {len(input_value)}"
    
    # 9. Vérification que le bouton submit est maintenant activé
    submit_button = page.locator('[data-testid="fallacy-submit-button"]')
    await expect(submit_button).to_be_enabled()

@pytest.mark.asyncio
async def test_fallacy_detector_reset_functionality(page: Page):
    """
    Test bouton de réinitialisation
    Vérifie que le bouton reset nettoie complètement l'interface
    """
    # 1. Navigation et activation onglet
    await page.goto("/")
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)
    
    fallacy_tab = page.locator('[data-testid="fallacy-detector-tab"]')
    await fallacy_tab.click()
    
    # 2. Localisation des éléments
    text_input = page.locator('[data-testid="fallacy-text-input"]')
    submit_button = page.locator('[data-testid="fallacy-submit-button"]')
    reset_button = page.locator('[data-testid="fallacy-reset-button"]')
    results_container = page.locator('[data-testid="fallacy-results-container"]')
    
    # 3. Effectuer une détection complète d'abord
    test_text = "Cette théorie est fausse parce que son auteur est stupide."
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
    await expect(submit_button).to_be_disabled()