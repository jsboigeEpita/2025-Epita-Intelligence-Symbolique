import re
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.playwright
@pytest.mark.asyncio
async def test_homepage_has_correct_title_and_header(page: Page, webapp_service: dict):
    """
    Ce test vérifie que la page d'accueil de l'application web se charge correctement,
    affiche le bon titre et un en-tête H1 visible.
    Il dépend de la fixture `webapp_service["frontend_url"]` pour obtenir l'URL de base dynamique.
    """
    # Naviguer vers la racine de l'application web en utilisant l'URL fournie par la fixture.
    await page.goto(webapp_service["frontend_url"], wait_until='networkidle')

    # Vérifier que le titre de la page est correct
    expect(page).to_have_title(re.compile("Argumentation Analysis App"))

    # Vérifier qu'un élément h1 contenant le texte "Argumentation Analysis" est visible
    heading = page.locator("h1", has_text=re.compile(r"Argumentation Analysis", re.IGNORECASE))
    expect(heading).to_be_visible(timeout=10000)