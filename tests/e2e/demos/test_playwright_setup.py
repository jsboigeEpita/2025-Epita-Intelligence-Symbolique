#!/usr/bin/env python3
"""
Test de configuration Playwright - Vérification du système
"""

import sys
import importlib.util
import importlib.metadata
from pathlib import Path

def check_playwright_setup():
    """Vérifie l'installation de Playwright"""
    print("=" * 60)
    print("VERIFICATION SETUP PLAYWRIGHT")
    print("=" * 60)
    
    # Vérifier l'import de Playwright
    try:
        import playwright
        version = importlib.metadata.version("playwright")
        print(f"✅ Playwright Python installé: {version}")
    except (ImportError, importlib.metadata.PackageNotFoundError):
        print("❌ Playwright Python non installé ou métadonnées introuvables.")
        return False
    
    # Vérifier playwright.sync_api
    try:
        from playwright.sync_api import sync_playwright
        print("✅ Playwright sync_api disponible")
    except ImportError:
        print("❌ Playwright sync_api non disponible")
        return False
    
    # Vérifier pytest-playwright
    try:
        import pytest_playwright
        print("✅ pytest-playwright installé")
    except ImportError:
        print("❌ pytest-playwright non installé")
        return False
    
    return True

def test_browser_availability():
    """Test la disponibilité des navigateurs"""
    print("\n" + "=" * 60)
    print("TEST DISPONIBILITÉ NAVIGATEURS")
    print("=" * 60)
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            # Test Chromium
            try:
                browser = p.chromium.launch(headless=True)
                browser.close()
                print("✅ Chromium disponible")
            except Exception as e:
                print(f"❌ Chromium non disponible: {e}")
            
            # Test Firefox
            try:
                browser = p.firefox.launch(headless=True)
                browser.close()
                print("✅ Firefox disponible")
            except Exception as e:
                print(f"❌ Firefox non disponible: {e}")
            
            # Test WebKit
            try:
                browser = p.webkit.launch(headless=True)
                browser.close()
                print("✅ WebKit disponible")
            except Exception as e:
                print(f"❌ WebKit non disponible: {e}")
    
    except Exception as e:
        print(f"❌ Erreur lors du test des navigateurs: {e}")
        return False
    
    return True

def main():
    """Point d'entrée principal"""
    print("DEBUT DES TESTS PLAYWRIGHT\n")
    
    # Vérification setup
    setup_ok = check_playwright_setup()
    
    if setup_ok:
        # Test navigateurs
        browsers_ok = test_browser_availability()
        
        if browsers_ok:
            print("\n" + "=" * 60)
            print("✅ PLAYWRIGHT COMPLETEMENT FONCTIONNEL")
            print("✅ PRÊT POUR LES TESTS WEB")
            print("=" * 60)
            return 0
        else:
            print("\n" + "=" * 60)
            print("⚠️  PLAYWRIGHT PARTIELLEMENT FONCTIONNEL")
            print("⚠️  CERTAINS NAVIGATEURS MANQUENT")
            print("=" * 60)
            return 1
    else:
        print("\n" + "=" * 60)
        print("❌ PLAYWRIGHT NON FONCTIONNEL")
        print("❌ INSTALLATION REQUISE")
        print("=" * 60)
        return 2

if __name__ == "__main__":
    sys.exit(main())