#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de démonstration Playwright simple
=========================================

Démontre l'interface React sans dépendances complexes
"""

import asyncio
import time
from playwright.async_api import async_playwright

async def demo_webapp():
    """Démonstration de l'interface web argumentative"""
    
    async with async_playwright() as p:
        # Lancer le navigateur en mode visible
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()
        
        print("[DEMO] Demonstration Interface d'Analyse Argumentative")
        print("=" * 55)
        
        try:
            # Aller à l'interface React
            print("[NAV] Navigation vers l'interface...")
            await page.goto("http://localhost:3000", wait_until="networkidle")
            
            # Prendre une capture d'écran initiale
            await page.screenshot(path="logs/demo_homepage.png")
            print("[IMG] Capture d'ecran sauvee: logs/demo_homepage.png")
            
            # Attendre que la page se charge complètement
            await page.wait_for_selector('h1', timeout=10000)
            print("[OK] Page chargee avec succes")
            
            # Vérifier le titre
            title = await page.title()
            print(f"[INFO] Titre de la page: {title}")
            
            # Tester chaque onglet
            tabs = [
                ("analyzer", "Analyseur"),
                ("fallacies", "Sophismes"), 
                ("reconstructor", "Reconstructeur"),
                ("logic-graph", "Graphe Logique"),
                ("validation", "Validation"),
                ("framework", "Framework")
            ]
            
            for tab_id, tab_name in tabs:
                print(f"\n[TAB] Test de l'onglet: {tab_name}")
                
                # Cliquer sur l'onglet
                tab_selector = f'[data-testid="{tab_id}-tab"]'
                try:
                    await page.click(tab_selector, timeout=5000)
                    await page.wait_for_timeout(2000)  # Pause pour voir l'interface
                    
                    # Prendre une capture d'écran
                    screenshot_path = f"logs/demo_{tab_id}.png"
                    await page.screenshot(path=screenshot_path)
                    print(f"   [IMG] Capture: {screenshot_path}")
                    
                except Exception as e:
                    print(f"   [WARN] Onglet non trouve ou erreur: {e}")
                    # Essayer avec un sélecteur alternatif
                    try:
                        alt_selector = f'button:has-text("{tab_name}")'
                        await page.click(alt_selector, timeout=3000)
                        await page.wait_for_timeout(2000)
                        screenshot_path = f"logs/demo_{tab_id}_alt.png"
                        await page.screenshot(path=screenshot_path)
                        print(f"   [IMG] Capture alternative: {screenshot_path}")
                    except:
                        print(f"   [ERROR] Impossible d'acceder a l'onglet {tab_name}")
            
            # Test d'interaction avec le premier onglet trouvé
            print(f"\n[INTERACT] Test d'interaction...")
            
            # Retourner au premier onglet
            try:
                await page.click('[data-testid="analyzer-tab"]', timeout=5000)
                await page.wait_for_timeout(1000)
                
                # Essayer de remplir un champ de texte s'il existe
                text_input = await page.query_selector('textarea, input[type="text"]')
                if text_input:
                    await text_input.fill("Voici un exemple d'argument pour la demonstration.")
                    await page.wait_for_timeout(2000)
                    print("   [OK] Texte saisi dans le champ")
                    
                    # Capture après saisie
                    await page.screenshot(path="logs/demo_interaction.png")
                    print("   [IMG] Capture apres interaction: logs/demo_interaction.png")
                
            except Exception as e:
                print(f"   [WARN] Interaction limitee: {e}")
            
            # Capture finale
            await page.screenshot(path="logs/demo_final.png")
            print("\n[SUCCESS] Demonstration terminee avec succes!")
            print(f"[INFO] Captures d'ecran disponibles dans le dossier 'logs/'")
            
            # Pause pour observer
            print("\n[WAIT] Pause de 5 secondes pour observer l'interface...")
            await page.wait_for_timeout(5000)
            
        except Exception as e:
            print(f"[ERROR] Erreur pendant la demonstration: {e}")
            await page.screenshot(path="logs/demo_error.png")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    print("[START] Demarrage de la demonstration Playwright...")
    print("[INFO] Assurez-vous que l'interface React fonctionne sur http://localhost:3000")
    print("")
    
    asyncio.run(demo_webapp())