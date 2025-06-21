import re
import pytest
import logging
from playwright.sync_api import Page, expect

def test_homepage_has_correct_title_and_header(page: Page, e2e_servers):
    """
    Ce test vérifie que la page d'accueil de l'application web se charge correctement,
    affiche le bon titre, un en-tête H1 visible et que la connexion à l'API est active.
    Il dépend de la fixture `e2e_servers` pour démarrer les serveurs et obtenir l'URL dynamique.
    """
    # Définir une fonction de rappel pour les messages de la console
    def handle_console_message(msg):
        logging.info(f"BROWSER CONSOLE: [{msg.type}] {msg.text}")

    # Attacher la fonction de rappel à l'événement 'console'
    page.on("console", handle_console_message)
    
    # Obtenir l'URL dynamique directement depuis la fixture des serveurs
    frontend_url_dynamic = e2e_servers.app_info.frontend_url
    assert frontend_url_dynamic, "L'URL du frontend n'a pas été définie par la fixture e2e_servers"

    # Naviguer vers la racine de l'application web en utilisant l'URL dynamique.
    page.goto(frontend_url_dynamic, wait_until='domcontentloaded', timeout=30000)

    # Attendre que l'indicateur de statut de l'API soit visible et connecté
    api_status_indicator = page.locator('.api-status.connected')
    expect(api_status_indicator).to_be_visible(timeout=20000)

    # Vérifier que le titre de la page est correct
    expect(page).to_have_title(re.compile("Argumentation Analysis App"))

    # Vérifier qu'un élément h1 contenant le texte "Interface d'Analyse Argumentative" est visible.
    # Le texte a été corrigé de "Argumentation Analysis" au texte français réel.
    heading = page.locator("h1", has_text=re.compile(r"Interface d'Analyse Argumentative", re.IGNORECASE))
    expect(heading).to_be_visible(timeout=10000)
