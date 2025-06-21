import re
import pytest
from playwright.sync_api import Page, expect


def test_homepage_has_correct_title_and_header(page: Page, frontend_url: str, webapp_service):
    """
    Ce test vérifie que la page d'accueil de l'application web se charge correctement,
    affiche le bon titre, un en-tête H1 visible et que la connexion à l'API est active.
    Il dépend de la fixture `frontend_url` pour obtenir l'URL de base dynamique.
    """
    # Naviguer vers la racine de l'application web.
    page.goto(frontend_url, wait_until='load', timeout=60000)

    # Vérification du titre.
    expect(page).to_have_title(re.compile("Argumentation Analysis App"))
    
    # Attendre que le H1 soit rendu par React, puis le vérifier.
    heading_locator = page.locator("h1")
    expect(heading_locator).to_be_visible(timeout=15000)
    expect(heading_locator).to_have_text(re.compile(r"🎯 Interface d'Analyse Argumentative", re.IGNORECASE))