#!/usr/bin/env python3
"""
Script Python Asynchrone - Investigation Playwright Textes Variés
Alternative non bloquante au script PowerShell
"""

import asyncio
import json
import subprocess
import time
import aiohttp
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configuration
PROJECT_ROOT = Path("c:/dev/2025-Epita-Intelligence-Symbolique")
PLAYWRIGHT_DIR = PROJECT_ROOT / "tests_playwright"
TEMP_DIR = PROJECT_ROOT / "_temp" / "investigation_playwright"


class NonBlockingPlaywrightInvestigator:
    def __init__(self, mode: str = "investigation"):
        self.mode = mode
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.temp_dir = TEMP_DIR
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.report_file = (
            self.temp_dir / f"investigation_async_report_{self.timestamp}.json"
        )

        # Configuration des services
        self.services = {
            "API Backend": {"url": "http://localhost:5003/api/health", "port": 5003},
            "Interface Web": {"url": "http://localhost:3000/status", "port": 3000},
        }

        self.results = {
            "timestamp": self.timestamp,
            "mode": mode,
            "services": {},
            "tests": {"total": 0, "success": 0, "results": []},
            "duration": 0,
            "start_time": time.time(),
        }

    async def check_service(
        self, session: aiohttp.ClientSession, name: str, config: Dict
    ) -> Dict[str, Any]:
        """Vérifier l'état d'un service de manière asynchrone"""
        try:
            timeout = aiohttp.ClientTimeout(total=3)
            async with session.get(config["url"], timeout=timeout) as response:
                if response.status == 200:
                    print(f"✅ {name} - Opérationnel")
                    return {"status": "OK", "code": response.status}
                else:
                    print(f"⚠️ {name} - Status {response.status}")
                    return {"status": "WARNING", "code": response.status}
        except Exception as e:
            print(f"❌ {name} - Non accessible: {str(e)}")
            return {"status": "ERROR", "error": str(e)}

    async def check_all_services(self) -> Dict[str, Any]:
        """Vérifier tous les services en parallèle"""
        print("\n🔍 VÉRIFICATION DES SERVICES")

        async with aiohttp.ClientSession() as session:
            tasks = [
                self.check_service(session, name, config)
                for name, config in self.services.items()
            ]
            service_results = await asyncio.gather(*tasks, return_exceptions=True)

            return dict(zip(self.services.keys(), service_results))

    def start_service_if_needed(
        self, name: str, port: int, command: str
    ) -> Optional[subprocess.Popen]:
        """Démarrer un service si nécessaire"""
        try:
            # Vérifier si le port est utilisé
            result = subprocess.run(
                ["netstat", "-an"], capture_output=True, text=True, shell=True
            )
            if f":{port}" in result.stdout:
                print(f"✅ {name} déjà actif sur port {port}")
                return None

            print(f"🚀 Démarrage {name} sur port {port}...")

            # Démarrer le service en arrière-plan
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=PROJECT_ROOT,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            print(f"⏳ Service {name} démarré (PID {process.pid})")
            time.sleep(3)  # Temps de démarrage

            return process

        except Exception as e:
            print(f"❌ Erreur démarrage {name}: {e}")
            return None

    async def setup_services(self) -> List[subprocess.Popen]:
        """Configuration et démarrage des services"""
        print("\n🏗️ GESTION DES SERVICES")

        services_commands = {
            "API Backend": "python -m uvicorn api.main_simple:app --host 0.0.0.0 --port 5003",
            "Interface Web": "python interface_web/app.py",
        }

        started_processes = []

        for name, config in self.services.items():
            if name in services_commands:
                process = self.start_service_if_needed(
                    name, config["port"], services_commands[name]
                )
                if process:
                    started_processes.append(process)

        # Attendre que les services soient prêts
        if started_processes:
            print("⏳ Attente de la préparation des services...")
            await asyncio.sleep(5)

        return started_processes

    def get_test_commands(self) -> List[str]:
        """Obtenir les commandes de test selon le mode"""
        base_cmd = "npx playwright test"

        commands = {
            "complet": [
                f"{base_cmd} investigation-textes-varies.spec.js --reporter=json",
                f"{base_cmd} api-backend.spec.js --reporter=json",
                f"{base_cmd} flask-interface.spec.js --reporter=json",
            ],
            "investigation": [
                f"{base_cmd} investigation-textes-varies.spec.js --reporter=json"
            ],
            "rapide": [
                f"{base_cmd} investigation-textes-varies.spec.js --grep='API - Test complet' --reporter=json"
            ],
        }

        return commands.get(self.mode, commands["investigation"])

    async def run_test_async(self, command: str) -> Dict[str, Any]:
        """Exécuter un test de manière asynchrone"""
        print(f"\n▶️ Exécution: {command}")

        start_time = time.time()

        try:
            # Utiliser asyncio.subprocess pour exécution non bloquante
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=PLAYWRIGHT_DIR,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Attendre avec timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=60.0
                )

                duration = time.time() - start_time

                result = {
                    "command": command,
                    "status": "SUCCESS" if process.returncode == 0 else "FAILURE",
                    "exit_code": process.returncode,
                    "duration": duration,
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                }

                status_emoji = "✅" if process.returncode == 0 else "❌"
                print(
                    f"{status_emoji} Test terminé: {result['status']} ({duration:.2f}s)"
                )

                return result

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

                return {
                    "command": command,
                    "status": "TIMEOUT",
                    "duration": time.time() - start_time,
                    "error": "Test interrompu (timeout 60s)",
                }

        except Exception as e:
            return {
                "command": command,
                "status": "ERROR",
                "duration": time.time() - start_time,
                "error": str(e),
            }

    async def run_all_tests(self) -> List[Dict[str, Any]]:
        """Exécuter tous les tests en parallèle"""
        print("\n🧪 EXÉCUTION DES TESTS")

        commands = self.get_test_commands()
        print(f"🎯 Mode {self.mode.upper()} - {len(commands)} test(s)")

        # Exécuter les tests en parallèle avec limitation
        semaphore = asyncio.Semaphore(2)  # Max 2 tests simultanés

        async def run_with_semaphore(cmd):
            async with semaphore:
                return await self.run_test_async(cmd)

        tasks = [run_with_semaphore(cmd) for cmd in commands]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Traiter les exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "command": commands[i],
                        "status": "EXCEPTION",
                        "error": str(result),
                    }
                )
            else:
                processed_results.append(result)

        return processed_results

    def setup_playwright(self):
        """Préparer l'environnement Playwright"""
        print("\n🎭 PRÉPARATION PLAYWRIGHT")

        if not (PLAYWRIGHT_DIR / "node_modules").exists():
            print("📦 Installation des dépendances npm...")
            subprocess.run(["npm", "install"], cwd=PLAYWRIGHT_DIR, capture_output=True)

    async def generate_report(self):
        """Générer le rapport final"""
        print("\n📊 GÉNÉRATION DU RAPPORT")

        self.results["duration"] = time.time() - self.results["start_time"]
        self.results["tests"]["total"] = len(self.results["tests"]["results"])
        self.results["tests"]["success"] = sum(
            1 for r in self.results["tests"]["results"] if r.get("status") == "SUCCESS"
        )

        if self.results["tests"]["total"] > 0:
            self.results["tests"]["success_rate"] = round(
                (self.results["tests"]["success"] / self.results["tests"]["total"])
                * 100,
                2,
            )
        else:
            self.results["tests"]["success_rate"] = 0

        # Sauvegarder le rapport
        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)

        print(f"💾 Rapport sauvegardé: {self.report_file}")

    def display_summary(self):
        """Afficher le résumé final"""
        print("\n📋 RÉSUMÉ FINAL")
        print("===============")
        print(f"🎯 Mode: {self.mode}")
        print(f"⏱️ Durée totale: {self.results['duration']:.2f}s")
        print(
            f"🧪 Tests: {self.results['tests']['success']}/{self.results['tests']['total']} réussis ({self.results['tests']['success_rate']}%)"
        )

        for name, status in self.results["services"].items():
            emoji = {"OK": "✅", "WARNING": "⚠️", "ERROR": "❌"}.get(
                status.get("status", "ERROR"), "❓"
            )
            print(f"🔧 {name}: {emoji} {status.get('status', 'UNKNOWN')}")

    async def run_investigation(self):
        """Exécuter l'investigation complète"""
        print("🚀 INVESTIGATION PLAYWRIGHT - TEXTES VARIÉS")
        print("=" * 45)

        try:
            # 1. Vérifier et démarrer les services
            await self.setup_services()

            # 2. Vérifier l'état des services
            self.results["services"] = await self.check_all_services()

            # 3. Préparer Playwright
            self.setup_playwright()

            # 4. Exécuter les tests
            test_results = await self.run_all_tests()
            self.results["tests"]["results"] = test_results

            # 5. Générer le rapport
            await self.generate_report()

            # 6. Afficher le résumé
            self.display_summary()

            print("\n🏁 Investigation terminée!")
            print(f"📁 Résultats dans: {self.temp_dir}")

            return True

        except KeyboardInterrupt:
            print("\n⏹️ Investigation interrompue par l'utilisateur")
            return False
        except Exception as e:
            print(f"\n💥 Erreur lors de l'investigation: {e}")
            return False


async def main():
    """Point d'entrée principal"""
    import argparse

    parser = argparse.ArgumentParser(description="Investigation Playwright Asynchrone")
    parser.add_argument(
        "--mode",
        choices=["complet", "investigation", "rapide"],
        default="investigation",
        help="Mode d'exécution",
    )
    parser.add_argument(
        "--report", action="store_true", help="Ouvrir le rapport après exécution"
    )

    args = parser.parse_args()

    investigator = NonBlockingPlaywrightInvestigator(args.mode)
    success = await investigator.run_investigation()

    if args.report and success:
        import webbrowser

        webbrowser.open(str(investigator.report_file))

    return 0 if success else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Script interrompu")
        sys.exit(1)
