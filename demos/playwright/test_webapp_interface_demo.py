#!/usr/bin/env python3
"""
Test Playwright de l'interface web statique
"""

import pytest
import sys
from pathlib import Path
from playwright.sync_api import Page, expect

# URL de l'interface de test statique
DEMO_HTML_PATH = Path(__file__).parent / "test_interface_demo.html"
DEMO_URL = f"file://{DEMO_HTML_PATH.absolute()}"

class TestWebAppInterfaceDemo:
    """Tests de l'interface de démonstration statique"""
    
    def test_page_loads_correctly(self, page: Page):
        """Test que la page se charge correctement"""
        page.goto(DEMO_URL)
        
        # Vérifier le titre
        expect(page).to_have_title("Interface d'Analyse Argumentative - Test")
        
        # Vérifier la présence des éléments principaux
        expect(page.locator("h1")).to_contain_text("Interface d'Analyse Argumentative")
        expect(page.locator("#text-input")).to_be_visible()
        expect(page.locator("#analyze-btn")).to_be_visible()
        expect(page.locator("#clear-btn")).to_be_visible()
        expect(page.locator("#example-btn")).to_be_visible()
        
        print("✅ Page chargée avec succès")
    
    def test_example_button_functionality(self, page: Page):
        """Test du bouton d'exemple"""
        page.goto(DEMO_URL)
        
        # Cliquer sur le bouton exemple
        page.locator("#example-btn").click()
        
        # Vérifier que le texte d'exemple est chargé
        text_input = page.locator("#text-input")
        expect(text_input).to_have_value("Si tous les hommes sont mortels, et que Socrate est un homme, alors Socrate est mortel. Cet argument est valide car il suit la structure logique du syllogisme.")
        
        # Vérifier le message de statut
        expect(page.locator("#status")).to_contain_text("Exemple chargé")
        
        print("✅ Bouton exemple fonctionne")
    
    def test_clear_button_functionality(self, page: Page):
        """Test du bouton d'effacement"""
        page.goto(DEMO_URL)
        
        # Remplir le champ avec du texte
        page.locator("#text-input").fill("Texte de test")
        
        # Cliquer sur effacer
        page.locator("#clear-btn").click()
        
        # Vérifier que le champ est vide
        expect(page.locator("#text-input")).to_have_value("")
        
        # Vérifier que les résultats sont réinitialisés
        expect(page.locator("#results")).to_contain_text("Aucune analyse effectuée")
        
        # Vérifier le message de statut
        expect(page.locator("#status")).to_contain_text("Texte effacé")
        
        print("✅ Bouton effacer fonctionne")
    
    def test_analyze_button_functionality(self, page: Page):
        """Test du bouton d'analyse"""
        page.goto(DEMO_URL)
        
        # Entrer du texte
        test_text = "Ceci est un test d'analyse argumentative."
        page.locator("#text-input").fill(test_text)
        
        # Cliquer sur analyser
        page.locator("#analyze-btn").click()
        
        # Vérifier que les résultats apparaissent
        results = page.locator("#results")
        expect(results).to_contain_text("Analyse de:")
        expect(results).to_contain_text("Arguments détectés:")
        expect(results).to_contain_text("Sophismes potentiels:")
        expect(results).to_contain_text("Score de cohérence:")
        
        print("✅ Bouton analyser fonctionne")
    
    def test_empty_text_validation(self, page: Page):
        """Test de validation du texte vide"""
        page.goto(DEMO_URL)
        
        # Essayer d'analyser sans texte
        page.locator("#analyze-btn").click()
        
        # Vérifier le message d'erreur
        expect(page.locator("#status")).to_contain_text("Veuillez entrer du texte à analyser")
        
        print("✅ Validation du texte vide fonctionne")
    
    def test_ui_responsive_elements(self, page: Page):
        """Test de la responsivité de l'interface"""
        page.goto(DEMO_URL)
        
        # Tester différentes tailles d'écran
        page.set_viewport_size({"width": 1280, "height": 800})
        expect(page.locator(".container")).to_be_visible()
        
        page.set_viewport_size({"width": 768, "height": 1024})
        expect(page.locator(".container")).to_be_visible()
        
        page.set_viewport_size({"width": 375, "height": 667})
        expect(page.locator(".container")).to_be_visible()
        
        print("✅ Interface responsive")

def main():
    """Exécution autonome des tests"""
    print("=" * 60)
    print("TESTS PLAYWRIGHT - INTERFACE WEB STATIQUE")
    print("=" * 60)
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            test_instance = TestWebAppInterfaceDemo()
            
            # Exécuter les tests
            test_instance.test_page_loads_correctly(page)
            test_instance.test_example_button_functionality(page)
            test_instance.test_clear_button_functionality(page)
            test_instance.test_analyze_button_functionality(page)
            test_instance.test_empty_text_validation(page)
            test_instance.test_ui_responsive_elements(page)
            
            browser.close()
            
            print("\n" + "=" * 60)
            print("✅ TOUS LES TESTS PASSÉS")
            print("✅ INTERFACE WEB STATIQUE FONCTIONNELLE")
            print("=" * 60)
            return 0
            
    except Exception as e:
        print(f"❌ Erreur lors des tests: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())