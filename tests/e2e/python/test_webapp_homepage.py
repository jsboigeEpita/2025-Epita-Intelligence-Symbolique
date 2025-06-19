import re
import pytest
import time
from playwright.sync_api import Page, expect


@pytest.mark.asyncio
async def test_homepage_has_correct_title_and_header(page: Page, frontend_url: str):
    """
    Ce test vérifie que la page d'accueil de l'application web se charge correctement,
    affiche le bon titre, un en-tête H1 visible et que la connexion à l'API est active.
    Il dépend de la fixture `frontend_url` pour obtenir l'URL de base dynamique.
    """
    # Attente forcée pour laisser le temps au serveur de démarrer
    time.sleep(15)
    
    # Naviguer vers la racine de l'application web en utilisant l'URL fournie par la fixture.
    await page.goto(frontend_url, wait_until='networkidle', timeout=30000)

    # Attendre que l'indicateur de statut de l'API soit visible et connecté
    api_status_indicator = page.locator('.api-status.connected')
    await expect(api_status_indicator).to_be_visible(timeout=20000)

    # Vérifier que le titre de la page est correct
    await expect(page).to_have_title(re.compile("Argumentation Analysis App"))

    # Vérifier qu'un élément h1 contenant le texte "Argumentation Analysis" est visible
    heading = page.locator("h1", has_text=re.compile(r"Argumentation Analysis", re.IGNORECASE))
    await expect(heading).to_be_visible(timeout=10000)