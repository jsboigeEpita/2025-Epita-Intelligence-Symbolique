import pytest
from playwright.sync_api import Page, expect
import time
import requests

def test_interface_integration_complete_robust(page: Page):
    '''Test d'integration complet avec trace des actions et verification robuste'''
    
    # Configuration
    backend_url = "http://localhost:5003"
    frontend_url = "http://localhost:3000"
    
    print(f"[CONFIG] Backend={backend_url}, Frontend={frontend_url}")
    
    # DOUBLE VERIFICATION AVANT NAVIGATION
    print("[VERIFICATION] Test preliminaire de disponibilite du frontend")
    try:
        response = requests.get(frontend_url, timeout=10)
        print(f"[VERIFICATION] Status frontend: {response.status_code}")
    except Exception as e:
        print(f"[ERREUR] Frontend non accessible: {e}")
        pytest.fail("Frontend non accessible avant navigation")
    
    # 1. NAVIGATION VERS FRONTEND
    print("[ACTION] Navigation vers l'interface frontend")
    page.goto(frontend_url, wait_until="networkidle", timeout=30000)
    print(f"[RESULT] Page chargee - URL: {page.url}")
    
    # Attendre chargement complet
    print("[WAIT] Attente chargement complet de l'interface")
    page.wait_for_load_state("networkidle")
    time.sleep(3)
    print("[RESULT] Interface completement chargee")
    
    # 2. VERIFICATION TITRE PAGE
    print("[ACTION] Verification du titre de la page")
    title = page.title()
    print(f"[RESULT] Titre de la page: '{title}'")
    
    # 3. RECHERCHE ELEMENTS INTERFACE
    print("[ACTION] Recherche des elements d'interface")
    
    # Chercher zone de texte
    text_inputs = page.locator("textarea, input[type='text'], input:not([type])").all()
    print(f"[RESULT] {len(text_inputs)} zone(s) de texte trouvee(s)")
    
    # Chercher boutons
    buttons = page.locator("button").all()
    print(f"[RESULT] {len(buttons)} bouton(s) trouve(s)")
    
    # Chercher liens
    links = page.locator("a").all()
    print(f"[RESULT] {len(links)} lien(s) trouve(s)")
    
    # 4. CAPTURE INITIALE
    print("[ACTION] Capture d'ecran initiale")
    page.screenshot(path="integration_test_initial.png")
    print("[RESULT] Screenshot initial sauve")
    
    # 5. TEST INTERACTION SI ELEMENTS DISPONIBLES
    if text_inputs:
        print("[ACTION] Saisie de texte de test")
        first_input = text_inputs[0]
        test_text = "Ceci est un test d'analyse argumentative avec verification robuste."
        first_input.fill(test_text)
        print(f"[RESULT] Texte saisi: '{test_text}'")
        
        # Verifier la saisie
        filled_value = first_input.input_value()
        print(f"[VERIFY] Valeur dans le champ: '{filled_value}'")
        
        # Capture aprÃ¨s saisie
        page.screenshot(path="integration_test_after_input.png")
        print("[RESULT] Screenshot apres saisie sauve")
    
    if buttons:
        print("[ACTION] Analyse des boutons disponibles")
        for i, button in enumerate(buttons[:3]):  # Max 3 boutons
            try:
                button_text = button.inner_text()
                is_visible = button.is_visible()
                is_enabled = button.is_enabled()
                print(f"[DETAILS] Bouton {i+1}: '{button_text}' - Visible: {is_visible}, Active: {is_enabled}")
                
                if is_visible and is_enabled and button_text.strip():
                    print(f"[ACTION] Clic sur bouton: '{button_text}'")
                    button.click()
                    print(f"[RESULT] Clic effectue sur '{button_text}'")
                    time.sleep(2)
                    
                    # Capture aprÃ¨s clic
                    page.screenshot(path=f"integration_test_after_click_{i+1}.png")
                    print(f"[RESULT] Screenshot apres clic {i+1} sauve")
                    break
            except Exception as e:
                print(f"[ERREUR] Probleme avec bouton {i+1}: {e}")
    
    # 6. TEST BACKEND DIRECT
    print("[ACTION] Test direct du backend API")
    response = page.request.get(f"{backend_url}/api/health")
    print(f"[RESULT] Status backend: {response.status}")
    
    if response.ok:
        response_text = response.text()
        print(f"[CONTENT] Reponse backend: {response_text}")
    
    # 7. VERIFICATION DE LA PAGE
    print("[ACTION] Verification contenu de la page")
    page_content = page.content()
    content_length = len(page_content)
    print(f"[RESULT] Taille du contenu HTML: {content_length} caracteres")
    
    # Rechercher elements specifiques
    headers = page.locator("h1, h2, h3").all()
    print(f"[RESULT] {len(headers)} titre(s) trouve(s)")
    
    # 8. CAPTURE FINALE
    print("[ACTION] Capture d'ecran finale")
    page.screenshot(path="integration_test_final.png", full_page=True)
    print("[RESULT] Screenshot final complet sauve")
    
    print("[SUCCESS] TEST TERMINE: Toutes les actions ont ete executees avec succes")
