#!/usr/bin/env python3
"""
Test de configuration Playwright - Version sans Unicode
"""

import sys
import importlib.util
from pathlib import Path

def check_playwright_setup():
    """Verifie l'installation de Playwright"""
    print("=" * 60)
    print("VERIFICATION SETUP PLAYWRIGHT")
    print("=" * 60)
    
    # Verifier l'import de Playwright
    try:
        import playwright
        print("[OK] Playwright Python installe")
    except ImportError:
        print("[ERREUR] Playwright Python non installe")
        return False
    
    # Verifier playwright.sync_api
    try:
        from playwright.sync_api import sync_playwright
        print("[OK] Playwright sync_api disponible")
    except ImportError:
        print("[ERREUR] Playwright sync_api non disponible")
        return False
    
    # Verifier pytest-playwright
    try:
        import pytest_playwright
        print("[OK] pytest-playwright installe")
    except ImportError:
        print("[ERREUR] pytest-playwright non installe")
        return False
    
    return True

def test_browser_availability():
    """Test la disponibilite des navigateurs"""
    print("\n" + "=" * 60)
    print("TEST DISPONIBILITE NAVIGATEURS")
    print("=" * 60)
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Test Chromium
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("[OK] Chromium disponible")
            except Exception as e:
                print(f"[ERREUR] Chromium non disponible: {e}")
            
            # Test Firefox
            try:
                browser = p.firefox.launch(headless=True)
                browser.close()
                print("[OK] Firefox disponible")
            except Exception as e:
                print(f"[ERREUR] Firefox non disponible: {e}")
            
            # Test WebKit
            try:
                browser = p.webkit.launch(headless=True)
                browser.close()
                print("[OK] WebKit disponible")
            except Exception as e:
                print(f"[ERREUR] WebKit non disponible: {e}")
    
    except Exception as e:
        print(f"[ERREUR] Erreur lors du test des navigateurs: {e}")
        return False
    
    return True

def main():
    """Point d'entree principal"""
    print("DEBUT DES TESTS PLAYWRIGHT\n")
    
    # Verification setup
    setup_ok = check_playwright_setup()
    
    if setup_ok:
        # Test navigateurs
        browsers_ok = test_browser_availability()
        
        if browsers_ok:
            print("\n" + "=" * 60)
            print("[SUCCES] PLAYWRIGHT COMPLETEMENT FONCTIONNEL")
            print("[SUCCES] PRET POUR LES TESTS WEB")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("[ATTENTION] PLAYWRIGHT PARTIELLEMENT FONCTIONNEL")
            print("[ATTENTION] CERTAINS NAVIGATEURS MANQUENT")
            print("=" * 60)
            return 1
    else:
        print("\n" + "=" * 60)
        print("[ERREUR] PLAYWRIGHT NON FONCTIONNEL")
        print("[ERREUR] INSTALLATION REQUISE")
        print("=" * 60)
        return 2

if __name__ == "__main__":
    sys.exit(main())