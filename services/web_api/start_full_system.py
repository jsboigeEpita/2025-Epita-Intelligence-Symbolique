#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de démarrage complet du système back/front
================================================

Utilise l'infrastructure Python existante UnifiedWebOrchestrator
pour démarrer le backend ServiceManager + frontend React avec 
gestion du timing et surveillance automatique.

Usage:
    python services/web_api/start_full_system.py
    python services/web_api/start_full_system.py --visible
    python services/web_api/start_full_system.py --backend-port 5000 --frontend-port 3000

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Ajout du chemin racine pour les imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.webapp import UnifiedWebOrchestrator

async def main():
    """Point d'entrée principal pour le démarrage complet."""
    parser = argparse.ArgumentParser(
        description="Démarrage complet backend + frontend React",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python services/web_api/start_full_system.py                    # Mode complet headless
  python services/web_api/start_full_system.py --visible          # Mode complet visible
  python services/web_api/start_full_system.py --backend-port 5001 # Port backend personnalisé
        """
    )
    
    # Options de configuration
    parser.add_argument('--backend-port', type=int, default=5000,
                       help='Port du backend ServiceManager (défaut: 5000)')
    parser.add_argument('--frontend-port', type=int, default=3000,
                       help='Port du frontend React (défaut: 3000)')
    parser.add_argument('--visible', action='store_true',
                       help='Mode visible pour les tests (non-headless)')
    parser.add_argument('--timeout', type=int, default=15,
                       help='Timeout en minutes (défaut: 15)')
    parser.add_argument('--skip-tests', action='store_true',
                       help='Démarre les services sans exécuter les tests')
    
    args = parser.parse_args()
    
    print("🚀 DÉMARRAGE SYSTÈME COMPLET BACK/FRONT")
    print("=" * 50)
    print(f"Backend: ServiceManager (port {args.backend_port})")
    print(f"Frontend: React (port {args.frontend_port})")
    print(f"Mode: {'Visible' if args.visible else 'Headless'}")
    print("=" * 50)
    
    # Configuration de l'orchestrateur
    config_path = PROJECT_ROOT / 'scripts' / 'webapp' / 'config' / 'webapp_config.yml'
    orchestrator = UnifiedWebOrchestrator(str(config_path))
    orchestrator.headless = not args.visible
    orchestrator.timeout_minutes = args.timeout
    
    try:
        # Démarrage des services avec frontend React activé
        print("📡 Démarrage du backend ServiceManager...")
        print("🌐 Démarrage du frontend React...")
        
        success = await orchestrator.start_webapp(
            headless=orchestrator.headless,
            frontend_enabled=True,  # Frontend React activé
            backend_port=args.backend_port,
            frontend_port=args.frontend_port
        )
        
        if not success:
            print("❌ Échec du démarrage des services")
            return False
        
        # Affichage des informations de connexion
        print("\n" + "=" * 50)
        print("🎉 SERVICES DÉMARRÉS AVEC SUCCÈS!")
        print("=" * 50)
        print(f"🔗 Backend API: {orchestrator.app_info.backend_url}")
        print(f"🌐 Frontend React: {orchestrator.app_info.frontend_url}")
        print(f"📊 Status endpoint: {orchestrator.app_info.backend_url}/status")
        print("=" * 50)
        
        # Tests d'intégration optionnels
        if not args.skip_tests:
            print("🧪 Exécution des tests d'intégration...")
            test_success = await orchestrator.full_integration_test(
                headless=orchestrator.headless,
                frontend_enabled=True
            )
            
            if test_success:
                print("✅ Tests d'intégration réussis")
            else:
                print("⚠️ Certains tests ont échoué (services toujours actifs)")
        
        # Surveillance continue
        print("\n💡 Services actifs - Utilisez stop_all_services.py pour arrêter")
        print("💡 Utilisez health_check.py pour vérifier l'état")
        
        # Ouverture optionnelle du navigateur
        try:
            open_browser = input("\nOuvrir le navigateur sur l'interface? (o/N): ").strip().lower()
            if open_browser in ['o', 'oui', 'y', 'yes']:
                import webbrowser
                webbrowser.open(orchestrator.app_info.frontend_url)
                print(f"🌐 Navigateur ouvert sur {orchestrator.app_info.frontend_url}")
        except KeyboardInterrupt:
            print("\nInterruption détectée")
        
        # Maintien des services actifs
        print("\n⏸️ Services en cours d'exécution. Appuyez sur Ctrl+C pour arrêter...")
        try:
            while True:
                await asyncio.sleep(30)
                # Health check périodique
                backend_healthy = await orchestrator.backend_manager.health_check()
                print(f"[{asyncio.get_event_loop().time():.0f}s] Backend: {'✅' if backend_healthy else '❌'}")
        except KeyboardInterrupt:
            print("\n🛑 Arrêt demandé par l'utilisateur")
        
        return True
        
    except KeyboardInterrupt:
        print("\n🛑 Interruption utilisateur")
        return False
    except Exception as e:
        print(f"❌ Erreur critique: {e}")
        return False
    finally:
        print("🔄 Arrêt des services...")
        await orchestrator.stop_webapp()
        print("✅ Services arrêtés proprement")

if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n🏁 Script terminé - {'Succès' if success else 'Échec'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n🛑 Interruption finale")
        sys.exit(1)