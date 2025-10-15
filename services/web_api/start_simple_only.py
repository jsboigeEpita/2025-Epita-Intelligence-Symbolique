#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de démarrage de l'interface simple uniquement
===================================================

Démarre uniquement l'interface simple Flask intégrée avec ServiceManager
en mode standalone. Utilise l'infrastructure Python existante.

Usage:
    python services/web_api/start_simple_only.py
    python services/web_api/start_simple_only.py --port 3000
    python services/web_api/start_simple_only.py --debug

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
    """Point d'entrée principal pour l'interface simple standalone."""
    parser = argparse.ArgumentParser(
        description="Démarrage interface simple Flask standalone",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python services/web_api/start_simple_only.py                    # Mode standard port 3000
  python services/web_api/start_simple_only.py --port 3001       # Port personnalisé
  python services/web_api/start_simple_only.py --debug           # Mode debug
        """,
    )

    # Options de configuration
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port de l'interface simple (défaut: 3000)",
    )
    parser.add_argument("--debug", action="store_true", help="Mode debug Flask")
    parser.add_argument(
        "--skip-servicemanager-check",
        action="store_true",
        help="Ignore la vérification du ServiceManager",
    )
    parser.add_argument(
        "--timeout", type=int, default=10, help="Timeout en minutes (défaut: 10)"
    )

    args = parser.parse_args()

    print("[INFO] DEMARRAGE INTERFACE SIMPLE STANDALONE")
    print("=" * 50)
    print(f"Interface: Flask Simple (port {args.port})")
    print(f"Mode: {'Debug' if args.debug else 'Production'}")
    print("=" * 50)

    # Configuration de l'orchestrateur
    config_path = PROJECT_ROOT / "scripts" / "webapp" / "config" / "webapp_config.yml"
    orchestrator = UnifiedWebOrchestrator(str(config_path))
    orchestrator.headless = True  # Mode headless pour interface simple
    orchestrator.timeout_minutes = args.timeout

    try:
        # Vérification des dépendances si demandé
        if not args.skip_servicemanager_check:
            print(
                "[VERIFICATION] Vérification de la disponibilité du ServiceManager..."
            )
            # Test d'import du ServiceManager
            try:
                from argumentation_analysis.orchestration.service_manager import (
                    ServiceManager,
                )

                print("[OK] ServiceManager disponible")
                servicemanager_available = True
            except ImportError as e:
                print(f"[WARNING] ServiceManager non disponible: {e}")
                print("   L'interface fonctionnera en mode dégradé")
                servicemanager_available = False

            # Test des analyseurs de sophismes
            try:
                from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import (
                    ComplexFallacyAnalyzer,
                )
                from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import (
                    ContextualFallacyAnalyzer,
                )

                print("[OK] Analyseurs de sophismes disponibles")
                fallacy_analyzers_available = True
            except ImportError as e:
                print(f"[WARNING] Analyseurs de sophismes non disponibles: {e}")
                fallacy_analyzers_available = False
        else:
            print("⏭️ Vérification des dépendances ignorée")
            servicemanager_available = False
            fallacy_analyzers_available = False

        # Démarrage de l'interface simple (backend seulement, pas de frontend React)
        print("[WEB] Démarrage de l'interface simple Flask...")

        success = await orchestrator.start_webapp(
            headless=True,
            frontend_enabled=False,  # Pas de frontend React, seulement Flask
        )

        if not success:
            print("[ERROR] Échec du démarrage de l'interface simple")
            return False

        # Affichage des informations de connexion
        print("\n" + "=" * 50)
        print("[SUCCESS] INTERFACE SIMPLE DÉMARRÉE AVEC SUCCÈS!")
        print("=" * 50)
        print(f"[WEB] Interface Web: {orchestrator.app_info.backend_url}")
        print(f"[STATS] Status endpoint: {orchestrator.app_info.backend_url}/status")
        print(
            f"[CONFIG] ServiceManager: {'Activé' if servicemanager_available else 'Mode dégradé'}"
        )
        print(
            f"[VERIFICATION] Analyseurs: {'Disponibles' if fallacy_analyzers_available else 'Fallback basique'}"
        )
        print("=" * 50)

        # Test de santé simple
        print("[TEST] Vérification de l'interface...")
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{orchestrator.app_info.backend_url}/"
                ) as response:
                    if response.status == 200:
                        print("[OK] Interface accessible")
                    else:
                        print(
                            f"[WARNING] Interface répond avec status {response.status}"
                        )

                # Test du endpoint status
                async with session.get(
                    f"{orchestrator.app_info.backend_url}/status"
                ) as response:
                    if response.status == 200:
                        status_data = await response.json()
                        print(
                            f"[STATS] Status de l'interface: {status_data.get('status', 'inconnu')}"
                        )
                        print(
                            f"[CONFIG] Mode: {status_data.get('webapp', {}).get('mode', 'inconnu')}"
                        )
                    else:
                        print("[WARNING] Endpoint /status non accessible")
        except ImportError:
            print("[WARNING] aiohttp non disponible, test de santé ignoré")
        except Exception as e:
            print(f"[WARNING] Erreur lors du test de santé: {e}")

        # Surveillance et contrôle interactif
        print("\n[INFO] Interface active - Utilisez stop_all_services.py pour arrêter")
        print("[INFO] Utilisez health_check.py pour vérifier l'état")

        # Ouverture optionnelle du navigateur
        try:
            open_browser = (
                input("\nOuvrir le navigateur sur l'interface? (o/N): ").strip().lower()
            )
            if open_browser in ["o", "oui", "y", "yes"]:
                import webbrowser

                webbrowser.open(orchestrator.app_info.backend_url)
                print(
                    f"[WEB] Navigateur ouvert sur {orchestrator.app_info.backend_url}"
                )
        except KeyboardInterrupt:
            print("\nInterruption détectée")

        # Maintien de l'interface active
        print("\n⏸️ Interface en cours d'exécution. Appuyez sur Ctrl+C pour arrêter...")
        try:
            while True:
                await asyncio.sleep(30)
                # Health check périodique simple
                backend_healthy = await orchestrator.backend_manager.health_check()
                timestamp = asyncio.get_event_loop().time()
                status_symbol = "[OK]" if backend_healthy else "[ERROR]"
                print(
                    f"[{timestamp:.0f}s] Interface: {status_symbol} | SM: {'[OK]' if servicemanager_available else '[WARNING]'} | FA: {'[OK]' if fallacy_analyzers_available else '[WARNING]'}"
                )
        except KeyboardInterrupt:
            print("\n[STOP] Arrêt demandé par l'utilisateur")

        return True

    except KeyboardInterrupt:
        print("\n[STOP] Interruption utilisateur")
        return False
    except Exception as e:
        print(f"[ERROR] Erreur critique: {e}")
        return False
    finally:
        print("[RESTART] Arrêt de l'interface...")
        await orchestrator.stop_webapp()
        print("[OK] Interface arrêtée proprement")


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n[FINISH] Script terminé - {'Succès' if success else 'Échec'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[STOP] Interruption finale")
        sys.exit(1)
