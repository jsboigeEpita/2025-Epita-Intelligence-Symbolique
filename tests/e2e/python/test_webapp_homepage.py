import re
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.playwright
def test_homepage_has_correct_title_and_header(page: Page, webapp_service: str):
    """
    Ce test vérifie que la page d'accueil de l'application web se charge correctement,
    affiche le bon titre et un en-tête H1 visible.
    Il dépend de la fixture `webapp_service` pour obtenir l'URL de base dynamique.
    """
    # Naviguer vers la racine de l'application web en utilisant l'URL fournie par la fixture.
    page.goto(webapp_service, wait_until='networkidle', timeout=30000)

    # Attendre que l'indicateur de statut de l'API soit visible et connecté
    api_status_indicator = page.locator('.api-status.connected')
    expect(api_status_indicator).to_be_visible(timeout=20000)

    # Vérifier que le titre de la page est correct
    expect(page).to_have_title(re.compile("Argumentation Analysis App"))

    # Vérifier qu'un élément h1 contenant le texte "Argumentation Analysis" est visible
    heading = page.locator("h1", has_text=re.compile(r"Argumentation Analysis", re.IGNORECASE))
    expect(heading).to_be_visible(timeout=10000)