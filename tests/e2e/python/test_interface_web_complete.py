#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test complet de l'interface web avec démarrage du serveur
=========================================================

Version améliorée utilisant l'orchestrateur unifié quand disponible.
"""

import subprocess
import time
import sys
import os
import requests
import asyncio
from pathlib import Path
# Configuration encodage pour Windows
if sys.platform == "win32":
    import locale
    try:
        # Force UTF-8 pour stdout/stderr
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        print("Configuration UTF-8 chargee automatiquement")
    except:
        print("Configuration encodage chargee automatiquement")
else:
    print("Configuration UTF-8 chargee automatiquement")

# Tentative d'import de l'orchestrateur unifié
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from project_core.webapp_from_scripts import UnifiedWebOrchestrator
    ORCHESTRATOR_AVAILABLE = True
    print("[INFO] Orchestrateur unifié disponible")
except ImportError:
    ORCHESTRATOR_AVAILABLE = False
    print("[INFO] Orchestrateur unifié non disponible, utilisation méthode simple")

def start_flask_server():
    """Démarre le serveur Flask en arrière-plan"""
    print("Demarrage du serveur Flask sur localhost:3000...")
    
    # Changer vers le répertoire interface_web (à la racine du projet)
    interface_web_dir = Path(__file__).parent.parent.parent / "interface_web"
    
    # Lancer le serveur Flask
    process = subprocess.Popen(
        [sys.executable, "app.py"],
        cwd=str(interface_web_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Attendre que le serveur démarre
    for attempt in range(15):  # 15 secondes max
        try:
            response = requests.get("http://localhost:3000/", timeout=1)
            if response.status_code == 200:
                print(f"[OK] Serveur Flask demarré après {attempt + 1} tentatives")
                return process
        except:
            pass
        time.sleep(1)
    
    print("[ERREUR] Impossible de démarrer le serveur Flask")
    if process.poll() is None:
        process.terminate()
    return None

def run_playwright_tests():
    """Lance les tests Playwright"""
    print("Lancement des tests Playwright...")
    
    # Répertoire racine du projet pour exécuter les tests
    project_root = Path(__file__).parent.parent.parent
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/functional/test_webapp_homepage.py",
             "-v", "--tb=short"],
            cwd=str(project_root),  # Exécuter depuis la racine du projet
            capture_output=True,
            text=True,
            timeout=60
        )
        
        print("=== STDOUT des tests ===")
        print(result.stdout)
        
        if result.stderr:
            print("=== STDERR des tests ===")
            print(result.stderr)
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("[ERREUR] Timeout lors de l'exécution des tests")
        return False
    except Exception as e:
        print(f"[ERREUR] Erreur lors des tests: {e}")
        return False

def stop_flask_server(process):
    """Arrête le serveur Flask"""
    if process and process.poll() is None:
        print("Arrêt du serveur Flask...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print("[OK] Serveur Flask arrêté")

async def run_with_orchestrator():
    """Exécute les tests avec l'orchestrateur unifié"""
    print("=" * 60)
    print("TEST INTERFACE WEB - ORCHESTRATEUR UNIFIÉ")
    print("=" * 60)
    
    orchestrator = UnifiedWebOrchestrator()
    
    try:
        print("\n[STEP 1] Démarrage backend Flask...")
        success = await orchestrator.start_webapp(
            headless=True,
            frontend_enabled=False
        )
        
        if not success:
            print("[ÉCHEC] Impossible de démarrer l'application web")
            return False
        
        print("[SUCCESS] Application web démarrée")
        
        print("\n[STEP 2] Exécution des tests Playwright...")
        tests_success = await orchestrator.run_tests(
            test_paths=['tests/functional/test_webapp_homepage.py'],
            headless=True,
            timeout_ms=15000
        )
        
        if tests_success:
            print("\n✓ [SUCCESS] Tests interface web complets : 2/2 PASSED")
            print("✓ MISSION CRITIQUE 3/3 - INTERFACE WEB : RÉUSSIE")
            return True
        else:
            print("\n✗ [FAILED] Tests interface web échoués")
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Erreur lors de l'exécution: {e}")
        return False
    finally:
        print("\n[CLEANUP] Arrêt de l'application web...")
        await orchestrator.stop_webapp()
        print("[OK] Cleanup terminé")

def main_simple():
    """Méthode simple sans orchestrateur"""
    print("=" * 60)
    print("TEST INTERFACE WEB - MÉTHODE SIMPLE")
    print("=" * 60)
    
    server_process = None
    success = False
    
    try:
        # 1. Démarrer le serveur
        server_process = start_flask_server()
        if not server_process:
            print("[ERREUR] Impossible de démarrer le serveur")
            return False
            
        # 2. Lancer les tests
        success = run_playwright_tests()
        
        if success:
            print("\n✓ [SUCCESS] Tests d'interface web réussis!")
            print("✓ MISSION CRITIQUE 3/3 - INTERFACE WEB : RÉUSSIE")
        else:
            print("\n✗ [ERROR] Échec des tests d'interface web")
            
    except KeyboardInterrupt:
        print("\n[INFO] Interruption par l'utilisateur")
    except Exception as e:
        print(f"\n[ERREUR] Erreur inattendue: {e}")
    finally:
        # 3. Arrêter le serveur
        stop_flask_server(server_process)
        
    return success

async def main():
    """Point d'entrée principal"""
    if ORCHESTRATOR_AVAILABLE:
        return await run_with_orchestrator()
    else:
        return main_simple()

if __name__ == '__main__':
    if ORCHESTRATOR_AVAILABLE:
        success = asyncio.run(main())
    else:
        success = main_simple()
    
    print(f"\n{'='*60}")
    print(f"RÉSULTAT FINAL: {'SUCCESS - 2/2 TESTS OK' if success else 'FAILED - 0/2 TESTS OK'}")
    print(f"{'='*60}")
    
    sys.exit(0 if success else 1)