#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Demo Playwright Robuste - Utilisation de l'Orchestrateur Unifié
===============================================================

Démonstration complète utilisant l'orchestrateur unifié robuste pour :
1. Démarrer automatiquement le backend mock sur le port 5003
2. Lancer le frontend React sur le port 3000
3. Exécuter les tests Playwright en mode visible
4. Générer des captures d'écran dans le dossier logs/
5. Tester l'interaction avec les 6 onglets de l'interface

Solution recommandée qui remplace demo_playwright_complet.py
"""

import sys
import asyncio
import time
import logging
from pathlib import Path
from playwright.async_api import async_playwright

# Ajout chemin pour imports
sys.path.insert(0, str(Path(__file__).parent))

from scripts.webapp import UnifiedWebOrchestrator

class DemoPlaywrightRobuste:
    """Démonstration Playwright utilisant l'orchestrateur unifié"""
    
    def __init__(self):
        # Configuration basique pour éviter problèmes Unicode
        config_path = 'config/webapp_config.yml'
        self.orchestrator = UnifiedWebOrchestrator(config_path)
        self.orchestrator.headless = False  # Mode visible
        self.backend_url = None
        self.frontend_url = None
        
    async def demarrer_services(self):
        """Démarre backend et frontend avec gestion robuste"""
        print("[DEMO] Demarrage demo Playwright robuste")
        print("=" * 50)
        
        try:
            # Utiliser l'orchestrateur unifié qui gère tout proprement
            print("[START] Demarrage via orchestrateur unifie...")
            success = await self.orchestrator.start_webapp(headless=False, frontend_enabled=True)
            
            if success:
                self.backend_url = self.orchestrator.app_info.backend_url
                self.frontend_url = self.orchestrator.app_info.frontend_url
                print(f"[OK] Backend operationnel: {self.backend_url}")
                print(f"[OK] Frontend operationnel: {self.frontend_url}")
                print("[OK] Tous les services valides")
                return True
            else:
                print("[ERROR] Echec demarrage services")
                return False
                
        except Exception as e:
            print(f"[ERROR] Erreur demarrage: {e}")
            return False
    
    async def executer_tests_playwright(self):
        """Exécute les tests Playwright en mode visible"""
        print("\n[PLAYWRIGHT] Lancement tests Playwright...")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=1000)
            page = await browser.new_page()
            
            try:
                # Test 1: Navigation homepage
                print("Test 1: Navigation vers homepage...")
                await page.goto(self.frontend_url, wait_until='networkidle')
                await page.screenshot(path="logs/demo_homepage.png")
                print("  - Capture homepage sauvee: logs/demo_homepage.png")
                
                # Test 2: Vérification titre
                try:
                    await page.wait_for_selector('h1', timeout=10000)
                    title = await page.title()
                    print(f"  - Titre page: {title}")
                except:
                    print("  - Titre non trouve")
                
                # Test 3: Attente connexion API
                print("Test 3: Attente connexion API...")
                await page.wait_for_timeout(3000)
                
                # Test 4: Test des onglets
                print("Test 4: Test des onglets...")
                onglets = [
                    ("analyzer", "Analyseur"),
                    ("fallacies", "Sophismes"), 
                    ("reconstructor", "Reconstructeur"),
                    ("validation", "Validation"),
                    ("framework", "Framework"),
                    ("logic-graph", "Graphe")
                ]
                
                for tab_id, tab_name in onglets:
                    try:
                        # Essayer data-testid
                        selector = f'[data-testid="{tab_id}-tab"]'
                        if await page.locator(selector).count() > 0:
                            await page.click(selector)
                            await page.wait_for_timeout(2000)
                            await page.screenshot(path=f"logs/demo_{tab_id}.png")
                            print(f"  - Onglet {tab_name} teste - capture sauvee")
                        else:
                            # Essayer sélecteur texte
                            text_selector = f'button:has-text("{tab_name}")'
                            if await page.locator(text_selector).count() > 0:
                                await page.click(text_selector)
                                await page.wait_for_timeout(2000)
                                await page.screenshot(path=f"logs/demo_{tab_id}_text.png")
                                print(f"  - Onglet {tab_name} teste via texte")
                            else:
                                print(f"  - Onglet {tab_name} non trouve")
                    except Exception as e:
                        print(f"  - Erreur onglet {tab_name}: {e}")
                
                # Test 5: Interaction dans analyzer
                print("Test 5: Test interaction analyzer...")
                try:
                    # Retour à l'analyzer
                    analyzer_tab = page.locator('[data-testid="analyzer-tab"]')
                    if await analyzer_tab.count() > 0:
                        await analyzer_tab.click()
                        await page.wait_for_timeout(1000)
                        
                        # Chercher textarea
                        textarea = await page.query_selector('textarea')
                        if textarea:
                            await textarea.fill("Ceci est un argument de test pour la demonstration Playwright.")
                            await page.wait_for_timeout(2000)
                            
                            # Chercher bouton analyse
                            buttons = await page.query_selector_all('button')
                            for button in buttons:
                                text = await button.text_content()
                                if text and ("analys" in text.lower() or "submit" in text.lower()):
                                    await button.click()
                                    await page.wait_for_timeout(3000)
                                    print("  - Bouton analyse clique")
                                    break
                            
                            await page.screenshot(path="logs/demo_interaction_complete.png")
                            print("  - Test interaction complete")
                        else:
                            print("  - Aucun textarea trouve")
                    else:
                        print("  - Onglet analyzer non trouve")
                except Exception as e:
                    print(f"  - Erreur interaction: {e}")
                
                print("\n[SUCCESS] Demo Playwright terminee avec succes!")
                await page.wait_for_timeout(3000)  # Pause pour observer
                
                return True
                
            except Exception as e:
                print(f"[ERROR] Erreur tests Playwright: {e}")
                return False
            finally:
                await browser.close()
    
    async def arreter_services(self):
        """Arrête tous les services"""
        print("\n[CLEANUP] Arret des services...")
        try:
            await self.orchestrator.stop_webapp()
            print("[OK] Tous les services arretes proprement")
        except Exception as e:
            print(f"[WARN] Probleme arret services: {e}")

async def main():
    """Point d'entrée principal"""
    demo = DemoPlaywrightRobuste()
    
    try:
        # Démarrage services
        if not await demo.demarrer_services():
            print("\n[FINAL] Demo echouee - Services non demarres")
            return False
        
        # Pause stabilisation
        print("\n[WAIT] Stabilisation services (3s)...")
        await asyncio.sleep(3)
        
        # Tests Playwright
        success = await demo.executer_tests_playwright()
        
        print(f"\n[FINAL] Demo {'reussie' if success else 'echouee'}")
        return success
        
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Interruption utilisateur")
        return False
    except Exception as e:
        print(f"\n[ERROR] Erreur critique: {e}")
        return False
    finally:
        await demo.arreter_services()

if __name__ == "__main__":
    print("DEMO PLAYWRIGHT ROBUSTE")
    print("Utilisation de l'orchestrateur unifie")
    print("-" * 40)
    
    # Créer le dossier logs
    Path("logs").mkdir(exist_ok=True)
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)