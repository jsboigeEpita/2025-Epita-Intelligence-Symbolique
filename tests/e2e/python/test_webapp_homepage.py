import re
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.playwright
def test_homepage_has_correct_title_and_header(page: Page):
    """
    Ce test vérifie que la page d'accueil de l'application web se charge correctement,
    affiche le bon titre et un en-tête H1 visible.
    """
    # La configuration de Playwright pour Python ne lit pas automatiquement
    # la section `webServer` comme le fait la version TS.
    # L'URL doit être spécifiée ici ou dans une configuration pytest.
    # Pour ce test, nous supposons que le serveur de développement tourne sur localhost:3000.
    # L'utilisateur devra lancer le serveur frontend manuellement avant d'exécuter ce test.
    page.goto("/", wait_until='networkidle')

    # Vérifier que le titre de la page est correct
    expect(page).to_have_title(re.compile("Argumentation Analysis App"))

    # Vérifier qu'un élément h1 contenant le texte "Argumentation Analysis" est visible
    heading = page.locator("h1", has_text=re.compile(r"Interface d'Analyse Argumentative", re.IGNORECASE))
    expect(heading).to_be_visible()