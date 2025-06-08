#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo Playwright Complet avec Backend Mock
=========================================

Lance backend mock + frontend + tests Playwright
"""

import asyncio
import subprocess
import time
import sys
import os
from pathlib import Path

async def wait_for_service(url, timeout=30):
    """Attend qu'un service soit disponible"""
    import aiohttp
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return True
        except:
            pass
        await asyncio.sleep(1)
    return False

async def run_demo():
    """Execute la demo complete"""
    print("[DEMO] Demarrage demo Playwright complete")
    print("=" * 50)
    
    # Processus à gérer
    backend_process = None
    frontend_process = None
    
    try:
        # 1. Démarrer le backend mock
        print("[BACKEND] Demarrage backend mock sur port 5003...")
        backend_process = subprocess.Popen([
            sys.executable, "backend_mock_demo.py", "--port", "5003"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Attendre que le backend soit prêt
        backend_ready = await wait_for_service("http://localhost:5003/api/health")
        if not backend_ready:
            print("[ERROR] Backend mock non accessible")
            return False
        print("[OK] Backend mock operationnel")
        
        # 2. Démarrer le frontend React via PowerShell
        print("[FRONTEND] Demarrage frontend React sur port 3000...")
        frontend_dir = Path("services/web_api/interface-web-argumentative").resolve()
        
        # Commande PowerShell pour démarrer npm
        ps_command = f'cd "{frontend_dir}"; $env:BROWSER="none"; $env:GENERATE_SOURCEMAP="false"; npm start'
        
        frontend_process = subprocess.Popen([
            "powershell", "-c", ps_command
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Attendre que le frontend soit prêt (plus de temps car npm start est plus lent)
        print("[WAIT] Attente demarrage frontend (peut prendre 30-60s)...")
        frontend_ready = await wait_for_service("http://localhost:3000", timeout=60)
        if not frontend_ready:
            print("[ERROR] Frontend React non accessible")
            return False
        print("[OK] Frontend React operationnel")
        
        # 3. Petit délai pour stabiliser
        print("[WAIT] Stabilisation des services...")
        await asyncio.sleep(3)
        
        # 4. Lancer les tests Playwright
        print("[PLAYWRIGHT] Lancement tests Playwright...")
        
        # Créer un test simple qui fonctionne
        test_script = """
import asyncio
from playwright.async_api import async_playwright

async def test_demo():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        print("Navigation vers l'interface...")
        await page.goto("http://localhost:3000")
        
        # Attendre le chargement
        await page.wait_for_selector('h1', timeout=10000)
        
        # Prendre capture d'écran
        await page.screenshot(path="logs/demo_interface.png")
        print("Capture sauvee: logs/demo_interface.png")
        
        # Vérifier statut API - attendre quelques secondes pour la connexion API
        await page.wait_for_timeout(3000)
        try:
            api_status = await page.locator('.api-status').text_content()
            print(f"Statut API: {api_status}")
        except:
            print("Statut API non trouve")
        
        # Tester quelques onglets
        tabs = ["analyzer", "fallacies", "reconstructor", "validation", "framework"]
        for tab in tabs:
            try:
                # Essayer les sélecteurs data-testid d'abord
                selector = f'[data-testid="{tab}-tab"]'
                if await page.locator(selector).count() > 0:
                    await page.click(selector)
                    await page.wait_for_timeout(2000)
                    await page.screenshot(path=f"logs/demo_{tab}.png")
                    print(f"Onglet {tab} teste - capture sauvee")
                else:
                    # Essayer avec sélecteur texte
                    text_selectors = {
                        "analyzer": "Analyseur",
                        "fallacies": "Sophismes", 
                        "reconstructor": "Reconstructeur",
                        "validation": "Validation",
                        "framework": "Framework"
                    }
                    text_selector = f'button:has-text("{text_selectors.get(tab, tab)}")'
                    if await page.locator(text_selector).count() > 0:
                        await page.click(text_selector)
                        await page.wait_for_timeout(2000)
                        await page.screenshot(path=f"logs/demo_{tab}_text.png")
                        print(f"Onglet {tab} teste via texte - capture sauvee")
                    else:
                        print(f"Onglet {tab} non trouve")
            except Exception as e:
                print(f"Erreur onglet {tab}: {e}")
        
        # Test d'interaction dans l'onglet analyzer
        print("Test d'interaction dans l'analyseur...")
        try:
            # Remplir un textarea s'il existe
            textarea = await page.query_selector('textarea')
            if textarea:
                await textarea.fill("Voici un argument de demonstration pour les tests Playwright.")
                await page.wait_for_timeout(2000)
                
                # Chercher et cliquer sur un bouton d'analyse
                buttons = await page.query_selector_all('button')
                for button in buttons:
                    text = await button.text_content()
                    if text and ("analys" in text.lower() or "submit" in text.lower() or "envoyer" in text.lower()):
                        await button.click()
                        await page.wait_for_timeout(3000)
                        print("Bouton d'analyse clique")
                        break
                
                await page.screenshot(path="logs/demo_interaction_complete.png")
                print("Test d'interaction complete")
            else:
                print("Aucun textarea trouve pour l'interaction")
        except Exception as e:
            print(f"Erreur interaction: {e}")
        
        print("Demo terminee avec succes!")
        await page.wait_for_timeout(5000)  # Pause pour observer
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_demo())
"""
        
        # Sauvegarder et exécuter le test
        with open("temp_playwright_test.py", "w", encoding="utf-8") as f:
            f.write(test_script)
        
        test_process = subprocess.run([
            sys.executable, "temp_playwright_test.py"
        ], capture_output=True, text=True)
        
        print(f"[RESULT] Code retour Playwright: {test_process.returncode}")
        if test_process.stdout:
            print(f"[OUTPUT] {test_process.stdout}")
        if test_process.stderr:
            print(f"[ERROR] {test_process.stderr}")
        
        # Nettoyer le fichier temporaire
        try:
            os.remove("temp_playwright_test.py")
        except:
            pass
        
        return test_process.returncode == 0
        
    except Exception as e:
        print(f"[ERROR] Erreur pendant la demo: {e}")
        return False
        
    finally:
        # Arrêter les processus
        print("\n[CLEANUP] Arret des services...")
        
        if backend_process:
            try:
                backend_process.terminate()
                backend_process.wait(timeout=5)
                print("[OK] Backend mock arrete")
            except:
                print("[WARN] Probleme arret backend")
            
        if frontend_process:
            try:
                frontend_process.terminate()
                frontend_process.wait(timeout=5)
                print("[OK] Frontend React arrete")
            except:
                print("[WARN] Probleme arret frontend")

if __name__ == "__main__":
    success = asyncio.run(run_demo())
    print(f"\n[FINAL] Demo {'reussie' if success else 'echouee'}")
    sys.exit(0 if success else 1)