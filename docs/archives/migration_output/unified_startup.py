#!/usr/bin/env python3
"""
Script de démarrage unifié - remplace tous les scripts PowerShell/CMD
Généré automatiquement par migrate_to_service_manager.py
"""

import sys
import argparse
from pathlib import Path

# Ajout du chemin du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_core.service_manager import ServiceManager, create_default_configs
from project_core.test_runner import TestRunner


def main():
    parser = argparse.ArgumentParser(description="Script de démarrage unifié")
    parser.add_argument(
        "action",
        choices=[
            "start-backend",
            "start-frontend",
            "start-app",
            "test-integration",
            "test-unit",
            "stop-all",
        ],
    )
    parser.add_argument("--wait", action="store_true", help="Attendre après démarrage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")

    args = parser.parse_args()

    if args.action == "start-backend":
        sm = ServiceManager()
        for config in create_default_configs():
            if config.name == "backend-flask":
                sm.register_service(config)
                success, port = sm.start_service_with_failover("backend-flask")
                if success:
                    print(f"Backend démarré sur port {port}")
                    if args.wait:
                        input("Appuyez sur Entrée pour arrêter...")
                        sm.stop_all_services()
                return 0 if success else 1

    elif args.action == "start-frontend":
        sm = ServiceManager()
        for config in create_default_configs():
            if config.name == "frontend-react":
                sm.register_service(config)
                success, port = sm.start_service_with_failover("frontend-react")
                if success:
                    print(f"Frontend démarré sur port {port}")
                    if args.wait:
                        input("Appuyez sur Entrée pour arrêter...")
                        sm.stop_all_services()
                return 0 if success else 1

    elif args.action == "start-app":
        runner = TestRunner()
        results = runner.start_web_application(wait=args.wait)
        return 0 if all(success for success, _ in results.values()) else 1

    elif args.action == "test-integration":
        runner = TestRunner()
        return runner.run_tests("integration")

    elif args.action == "test-unit":
        runner = TestRunner()
        return runner.run_tests("unit")

    elif args.action == "stop-all":
        sm = ServiceManager()
        sm.stop_all_services()
        print("Tous les services arrêtés")
        return 0


if __name__ == "__main__":
    sys.exit(main())
