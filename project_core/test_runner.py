# -*- coding: utf-8 -*-
"""
Orchestrateur de test unifié pour le projet.

Ce script gère le cycle de vie complet des tests, y compris :
- Le démarrage et l'arrêt des services dépendants (backend, frontend).
- L'exécution des suites de tests (unit, functional, e2e) via pytest.
- La gestion propre des processus et des ressources.

Utilisation :
    python project_core/test_runner.py --type [unit|functional|e2e|all] [--path <path>] [--browser <name>]
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

# Configuration des chemins et des commandes
ROOT_DIR = Path(__file__).parent.parent
API_DIR = ROOT_DIR
FRONTEND_DIR = ROOT_DIR / "interface_web"


class ServiceManager:
    """Gère le démarrage et l'arrêt des services web (API et Frontend)."""

    def __init__(self):
        self.processes = []
        self.log_files = {}

    def start_services(self):
        """Démarre l'API backend et le frontend React en arrière-plan."""
        print("Démarrage des services pour les tests E2E...")

        # Démarrer le backend API (Uvicorn sur le port 5004)
        print("Démarrage du service API sur le port 5004...")
        api_log_out = open("api_server.log", "w")
        api_log_err = open("api_server.error.log", "w")
        self.log_files["api_out"] = api_log_out
        self.log_files["api_err"] = api_log_err
        
        api_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "argumentation_analysis.services.web_api.app:app", "--port", "5004"],
            cwd=API_DIR,
            stdout=api_log_out,
            stderr=api_log_err
        )
        self.processes.append(api_process)
        print(f"Service API démarré avec le PID: {api_process.pid}")

        # Démarrer le frontend Starlette (uvicorn sur le port 3000)
        print("Démarrage du service Frontend (Starlette) sur le port 3000...")
        frontend_log_out = open("frontend_server.log", "w")
        frontend_log_err = open("frontend_server.error.log", "w")
        self.log_files["frontend_out"] = frontend_log_out
        self.log_files["frontend_err"] = frontend_log_err
        
        frontend_process = subprocess.Popen(
            [sys.executable, str(FRONTEND_DIR / "app.py"), "--port", "3000"],
            cwd=ROOT_DIR,
            stdout=frontend_log_out,
            stderr=frontend_log_err
        )
        self.processes.append(frontend_process)
        print(f"Service Frontend démarré avec le PID: {frontend_process.pid}")

        # Laisser le temps aux serveurs de démarrer
        print("Attente du démarrage des services (60 secondes)...")
        time.sleep(60)
        print("Services probablement démarrés.")

    def stop_services(self):
        """Arrête proprement tous les services démarrés."""
        print("Arrêt des services...")
        for process in self.processes:
            try:
                process.terminate()
                process.wait(timeout=10)
                print(f"Processus {process.pid} arrêté.")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"Processus {process.pid} forcé à s'arrêter.")
        self.processes = []

        # Fermer les fichiers de log
        for log_file in self.log_files.values():
            log_file.close()
        self.log_files = {}


class TestRunner:
    """Orchestre l'exécution des tests."""

    def __init__(self, test_type, test_path, browser):
        self.test_type = test_type
        self.test_path = test_path
        self.browser = browser
        self.service_manager = ServiceManager()

    def run(self):
        """Exécute le cycle de vie complet des tests."""
        needs_services = self.test_type in ["functional", "e2e", "all"]

        if needs_services:
            self.service_manager.start_services()

        try:
            self._run_pytest()
            if self.test_type in ["e2e", "all"]:
                self._run_playwright()
        finally:
            if needs_services:
                self.service_manager.stop_services()

    def _get_test_paths(self):
        """Détermine les chemins de test à utiliser."""
        if self.test_path:
            return [self.test_path]
        
        paths = {
            "unit": "tests/unit",
            "functional": "tests/functional",
            "e2e": "tests/e2e",
            "all": ["tests/unit", "tests/functional", "tests/e2e"],
        }
        
        path_or_paths = paths.get(self.test_type)
        if isinstance(path_or_paths, list):
            return path_or_paths
        return [path_or_paths] if path_or_paths else []


    def _run_pytest(self):
        """Lance pytest avec les arguments appropriés."""
        test_paths = self._get_test_paths()
        if not test_paths:
            print(f"Type de test '{self.test_type}' non reconnu pour pytest.")
            return

        command = [sys.executable, "-m", "pytest"] + test_paths
        
        # Ne lance pas les tests e2e avec pytest, ils sont gérés par playwright
        if self.test_type == "e2e":
            return

        print(f"Lancement de pytest avec la commande : {' '.join(command)}")
        result = subprocess.run(command, cwd=ROOT_DIR)

        if result.returncode != 0:
            print("Pytest a rencontré des erreurs.")
            # sys.exit(result.returncode) # On peut décider de stopper ici ou de continuer

    def _run_playwright(self):
        """Lance les tests Playwright."""
        test_paths = self._get_test_paths()
        if not test_paths:
            print("Aucun chemin de test trouvé pour Playwright.")
            return

        command = ["npx", "playwright", "test"] + test_paths
        if self.browser:
            command.extend(["--browser", self.browser])

        print("Lancement de 'npm install' pour s'assurer que les dépendances Playwright sont installées...")
        install_command = ["npm", "install"]
        install_result = subprocess.run(install_command, cwd=ROOT_DIR, shell=True, capture_output=True, text=True)
        if install_result.returncode != 0:
            print("Erreur pendant 'npm install'.")
            print(f"STDOUT:\n{install_result.stdout}")
            print(f"STDERR:\n{install_result.stderr}")
            return # Arrêter si l'installation échoue

        print(f"Lancement de Playwright avec la commande : {' '.join(command)}")
        # On exécute depuis la racine du projet pour que les chemins soient corrects
        result = subprocess.run(command, cwd=ROOT_DIR, shell=True)

        if result.returncode != 0:
            print("Playwright a rencontré des erreurs.")
            # sys.exit(result.returncode)


def main():
    """Point d'entrée principal du script."""
    parser = argparse.ArgumentParser(description="Orchestrateur de tests du projet.")
    parser.add_argument(
        "--type",
        required=True,
        choices=["unit", "functional", "e2e", "all"],
        help="Type de tests à exécuter."
    )
    parser.add_argument(
        "--path",
        help="Chemin spécifique vers un fichier ou dossier de test (optionnel)."
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        help="Navigateur pour les tests Playwright (optionnel)."
    )
    args = parser.parse_args()

    runner = TestRunner(args.type, args.path, args.browser)
    runner.run()


if __name__ == "__main__":
    main()