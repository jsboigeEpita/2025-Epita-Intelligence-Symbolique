#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Test - Orchestrateur d'Application Web Unifié
=======================================================

Script de validation et démonstration de l'orchestrateur unifié.

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Configuration UTF-8 pour Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        pass

# Ajout du chemin parent pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.webapp import UnifiedWebOrchestrator

async def test_backend_only():
    """Test démarrage backend seul"""
    print("[BACKEND] Test démarrage backend seul...")
    
    orchestrator = UnifiedWebOrchestrator()
    
    try:
        # Démarrage backend
        success = await orchestrator.start_webapp(headless=True, frontend_enabled=False)
        
        if success:
            print(f"[OK] Backend démarré: {orchestrator.app_info.backend_url}")
            
            # Test health check
            health_ok = await orchestrator.backend_manager.health_check()
            print(f"[HEALTH] Health check: {'OK' if health_ok else 'KO'}")
            
        else:
            print("[ERROR] Échec démarrage backend")
            
    finally:
        # Arrêt
        await orchestrator.stop_webapp()
        print("[STOP] Backend arrêté")

async def test_full_integration():
    """Test intégration complète"""
    print("\n[INTEGRATION] Test intégration complète...")
    
    orchestrator = UnifiedWebOrchestrator()
    
    # Test avec frontend désactivé et mode headless
    success = await orchestrator.full_integration_test(
        headless=True,
        frontend_enabled=False,
        test_paths=['tests/functional/test_webapp_homepage.py']
    )
    
    if success:
        print("[SUCCESS] Test intégration réussi!")
    else:
        print("[ERROR] Test intégration échoué")
        
    return success

async def test_configuration():
    """Test chargement configuration"""
    print("\n[CONFIG] Test chargement configuration...")
    
    orchestrator = UnifiedWebOrchestrator()
    
    print(f"Config chargée: {orchestrator.config_path}")
    print(f"Backend activé: {orchestrator.config['backend']['enabled']}")
    print(f"Frontend activé: {orchestrator.config['frontend']['enabled']}")
    print(f"Playwright activé: {orchestrator.config['playwright']['enabled']}")
    
    return True

def test_imports():
    """Test imports des modules"""
    print("[IMPORT] Test imports...")
    
    try:
        from scripts.webapp import (
            UnifiedWebOrchestrator, BackendManager, FrontendManager,
            PlaywrightRunner, ProcessCleaner
        )
        print("[OK] Tous les imports OK")
        return True
    except ImportError as e:
        print(f"[ERROR] Erreur import: {e}")
        return False

async def main():
    """Point d'entrée principal du test"""
    print("TESTS ORCHESTRATEUR WEB UNIFIE")
    print("=" * 50)
    
    # Tests de base
    if not test_imports():
        return False
    
    if not await test_configuration():
        return False
    
    # Tests fonctionnels
    try:
        await test_backend_only()
        success = await test_full_integration()
        
        print("\n" + "=" * 50)
        if success:
            print("[SUCCESS] TOUS LES TESTS REUSSIS!")
            print("\n[INFO] Orchestrateur prêt à remplacer les scripts PowerShell redondants:")
            print("   - integration_test_with_trace.ps1")
            print("   - integration_test_with_trace_robust.ps1")
            print("   - integration_test_with_trace_fixed.ps1")
            print("   - integration_test_trace_working.ps1")
            print("   - integration_test_trace_simple_success.ps1")
            print("   - sprint3_final_validation.py")
        else:
            print("[ERROR] CERTAINS TESTS ECHOUS")
            
        return success
        
    except Exception as e:
        print(f"[ERROR] Erreur critique: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)