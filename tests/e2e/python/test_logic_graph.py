import re
import pytest
from playwright.async_api import Page, expect

# Les URLs des services sont injectées via les fixtures `frontend_url` et `backend_url`.
# so the web server is started automatically for all tests in this module.
@pytest.mark.asyncio
async def test_successful_graph_visualization(page: Page):
    """
    Scenario 4.1: Successful visualization of a logic graph (Happy Path)
    """
    await page.goto("/")
    
    # Attendre que l'API soit connectée
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)

    # Assurez-vous que l'onglet "Logic Graph" est cliquable et cliquez dessus
    logic_graph_tab = page.locator('[data-testid="logic-graph-tab"]')
    await expect(logic_graph_tab).to_be_enabled()
    await logic_graph_tab.click()

    # Localisateurs pour les éléments d'interaction
    text_input = page.locator('[data-testid="logic-graph-text-input"]')
    submit_button = page.locator('[data-testid="logic-graph-submit-button"]')
    graph_container = page.locator('[data-testid="logic-graph-container"]')
    
    # Remplir le champ de saisie et soumettre
    text_to_analyze = "A -> B; B -> C"
    await text_input.fill(text_to_analyze)
    await submit_button.click()
    
    # Attendre que le graphe (élément SVG) soit visible dans le conteneur
    graph_svg = graph_container.locator("svg")
    await expect(graph_svg).to_be_visible(timeout=10000)
    await expect(graph_svg).to_have_attribute("data-testid", "logic-graph-svg")

@pytest.mark.asyncio
async def test_logic_graph_api_error(page: Page):
    """
    Scenario 4.2: API error during graph generation
    """
    await page.goto("/")
    
    # Attendre que l'API soit connectée
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)

    logic_graph_tab = page.locator('[data-testid="logic-graph-tab"]')
    await logic_graph_tab.click()

    # Intercepter l'appel API pour simuler une erreur 500
    await page.route(
        re.compile(r"/api/logic/belief-set"),
        lambda route: route.fulfill(status=500, json={"message": "Internal Server Error"})
    )
    
    text_input = page.locator('[data-testid="logic-graph-text-input"]')
    submit_button = page.locator('[data-testid="logic-graph-submit-button"]')
    
    await text_input.fill("Some text that will cause an error")
    await submit_button.click()
    
    # Vérifier que le message d'erreur est affiché
    error_message = page.locator('[data-testid="logic-graph-error-message"]')
    await expect(error_message).to_be_visible()
    await expect(error_message).to_have_text("Internal Server Error")
    
    # Vérifier que le conteneur du graphe ne contient pas de SVG
    graph_container = page.locator('[data-testid="logic-graph-container"]')
    graph_svg = graph_container.locator("svg")
    await expect(graph_svg).not_to_be_visible()

@pytest.mark.asyncio
async def test_logic_graph_reset_button(page: Page):
    """
    Scenario 4.3: Reset button clears input and graph
    """
    await page.goto("/")
    
    # Attendre que l'API soit connectée
    await expect(page.locator('.api-status.connected')).to_be_visible(timeout=15000)

    logic_graph_tab = page.locator('[data-testid="logic-graph-tab"]')
    await logic_graph_tab.click()

    text_input = page.locator('[data-testid="logic-graph-text-input"]')
    submit_button = page.locator('[data-testid="logic-graph-submit-button"]')
    reset_button = page.locator('[data-testid="logic-graph-reset-button"]')
    graph_container = page.locator('[data-testid="logic-graph-container"]')

    # Générer un graphe (happy path)
    await text_input.fill("A -> B; B -> C")
    await submit_button.click()
    
    graph_svg = graph_container.locator("svg")
    await expect(graph_svg).to_be_visible(timeout=10000)
    
    # Cliquer sur le bouton de réinitialisation
    await reset_button.click()
    
    # Vérifier que le champ de saisie est vide
    await expect(text_input).to_have_value("")
    
    # Vérifier que le graphe a disparu
    await expect(graph_svg).not_to_be_visible()