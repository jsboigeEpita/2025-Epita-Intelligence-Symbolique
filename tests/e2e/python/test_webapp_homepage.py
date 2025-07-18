import logging
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.e2e
@pytest.mark.playwright
class TestWebAppHomepage:
    def test_homepage_has_correct_title_and_header(self, page: Page, frontend_url: str):
        """
        Ce test vérifie que la page d'accueil de l'application web se charge correctement,
        affiche le bon titre, un en-tête H1 visible et que la connexion à l'API est active.
        """
        def handle_console_message(msg):
            logging.info(f"BROWSER CONSOLE: [{msg.type}] {msg.text}")

        page.on("console", handle_console_message)
        assert frontend_url, "L'URL du frontend n'a pas été fournie par la fixture"

        logging.info(f"Navigating to frontend URL: {frontend_url}")
        page.goto(frontend_url, wait_until='domcontentloaded', timeout=30000)

        api_status_indicator = page.locator('.api-status.connected')
        try:
            expect(api_status_indicator).to_be_visible(timeout=20000)
            logging.info("API status is connected.")
        except Exception as e:
            page_content = page.content()
            logging.error(f"Could not find connected API status. Error: {e}\nPage content:\n{page_content}")
            page.screenshot(path="failed_homepage_connection.png")
            raise

        expect(page).to_have_title("Argumentation Analysis App")
        header = page.locator('h1')
        expect(header).to_be_visible()
        expect(header).to_have_text("Argumentation Analysis Platform")
