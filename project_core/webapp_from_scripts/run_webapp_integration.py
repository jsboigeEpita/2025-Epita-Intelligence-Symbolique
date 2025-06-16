#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Point d'Entrée Simple - Tests d'Intégration Web App
===================================================

Script simplifié pour remplacer tous les anciens scripts PowerShell.

Usage:
    python scripts/run_webapp_integration.py           # Test complet headless
    python scripts/run_webapp_integration.py --visible # Test complet visible
    python scripts/run_webapp_integration.py --backend # Backend seulement

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Ajout chemin pour imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_core.webapp_from_scripts import UnifiedWebOrchestrator

async def main():
    """Point d'entrée principal simplifié"""
    parser = argparse.ArgumentParser(
        description="Tests d'intégration application web unifiés",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python scripts/run_webapp_integration.py                    # Test complet headless
  python scripts/run_webapp_integration.py --visible          # Test complet visible  
  python scripts/run_webapp_integration.py --backend          # Backend seulement
  python scripts/run_webapp_integration.py --quick            # Tests rapides
  python scripts/run_webapp_integration.py --frontend         # Avec frontend React
        """
    )
    
    # Options principales
    parser.add_argument('--visible', action='store_true',
                       help='Mode visible (non-headless) pour Playwright')
    parser.add_argument('--backend', action='store_true',
                       help='Teste seulement le backend (pas de Playwright)')
    parser.add_argument('--frontend', action='store_true',
                       help='Active le frontend React')
    parser.add_argument('--quick', action='store_true',
                       help='Tests rapides (subset)')
    
    # Options avancées
    parser.add_argument('--config', 
                       help='Chemin configuration personnalisée')
    parser.add_argument('--timeout', type=int, default=10,
                       help='Timeout en minutes (défaut: 10)')
    
    args = parser.parse_args()
    
    print("TESTS D'INTEGRATION APPLICATION WEB")
    print("=" * 50)
    
    # Configuration orchestrateur
    config_path = args.config or 'config/webapp_config.yml'
    orchestrator = UnifiedWebOrchestrator(config_path)
    orchestrator.headless = not args.visible
    orchestrator.timeout_minutes = args.timeout
    
    try:
        if args.backend:
            # Mode backend seulement
            print("🔧 Mode: Backend seulement")
            success = await orchestrator.start_webapp(
                headless=orchestrator.headless, 
                frontend_enabled=False
            )
            
            if success:
                print(f"Backend opérationnel: {orchestrator.app_info.backend_url}")
                
                # Test health check
                health_ok = await orchestrator.backend_manager.health_check()
                print(f"Health check: {'OK' if health_ok else 'KO'}")
                
                # Attente pour inspection manuelle
                print("Backend actif. Appuyez sur Ctrl+C pour arrêter...")
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    print("\nArrêt demandé")
            else:
                print("Échec démarrage backend")
                return False
                
        else:
            # Mode intégration complète
            mode = "Mode: Intégration complète"
            if args.visible:
                mode += " (Visible)"
            if args.frontend:
                mode += " + Frontend React"
            if args.quick:
                mode += " (Rapide)"
                
            print(mode)
            
            # Sélection tests
            test_paths = None
            if args.quick:
                test_paths = ['tests/functional/test_webapp_homepage.py']
            
            # Exécution
            success = await orchestrator.full_integration_test(
                headless=orchestrator.headless,
                frontend_enabled=args.frontend if args.frontend else None,
                test_paths=test_paths
            )
            
        # Affichage résultats
        print("\n" + "=" * 50)
        if success:
            print("🎉 TESTS RÉUSSIS!")
            print("\n📋 Résumé:")
            print(f"   Backend: {orchestrator.app_info.backend_url or 'Non démarré'}")
            print(f"   Frontend: {orchestrator.app_info.frontend_url or 'Non démarré'}")
            print(f"   Mode: {'Visible' if not orchestrator.headless else 'Headless'}")
            print(f"   Durée: {(orchestrator.trace_log[-1].timestamp if orchestrator.trace_log else 'N/A')}")
        else:
            print("TESTS ÉCHOUÉS")
            print("Voir logs dans logs/webapp_integration_trace.md")
        
        return success
        
    except KeyboardInterrupt:
        print("\nInterruption utilisateur")
        await orchestrator.stop_webapp()
        return False
    except Exception as e:
        print(f"Erreur critique: {e}")
        await orchestrator.stop_webapp()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    print(f"\nScript terminé - {'Succès' if success else 'Échec'}")
    sys.exit(0 if success else 1)