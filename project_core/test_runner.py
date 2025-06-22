# -*- coding: utf-8 -*-
print("[DEBUG] test_runner.py a démarré")
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
from datetime import datetime
from pathlib import Path

# Configuration des chemins et des commandes
ROOT_DIR = Path(__file__).parent.parent
API_DIR = ROOT_DIR
FRONTEND_DIR = ROOT_DIR / "interface_web"

def _log(message):
    """Affiche un message de log avec un timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


class ServiceManager:
    """Gère le démarrage et l'arrêt des services web (API et Frontend)."""

    def __init__(self):
        self.processes = []
        self.log_files = {}

    def start_services(self):
        """Démarre l'API backend et le frontend React en arrière-plan."""
        _log("Démarrage des services pour les tests E2E...")

        # Démarrer le backend API (Uvicorn sur le port 5003)
        _log(f"Démarrage du service API sur le port 5003 (CWD: {API_DIR})")
        api_log_out = open("api_server.log", "w", encoding="utf-8")
        api_log_err = open("api_server.error.log", "w", encoding="utf-8")
        self.log_files["api_out"] = api_log_out
        self.log_files["api_err"] = api_log_err
        
        api_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "argumentation_analysis.services.web_api.app:app", "--port", "5003"],
            cwd=API_DIR,
            stdout=api_log_out,
            stderr=api_log_err
        )
        self.processes.append(api_process)
        _log(f"Service API démarré avec le PID: {api_process.pid}")

        # Démarrer le frontend Starlette (uvicorn sur le port 3000)
        _log(f"Démarrage du service Frontend (Starlette) sur le port 3000 (CWD: {ROOT_DIR})")
        frontend_log_out = open("frontend_server.log", "w", encoding="utf-8")
        frontend_log_err = open("frontend_server.error.log", "w", encoding="utf-8")
        self.log_files["frontend_out"] = frontend_log_out
        self.log_files["frontend_err"] = frontend_log_err
        
        frontend_process = subprocess.Popen(
            [sys.executable, str(FRONTEND_DIR / "app.py"), "--port", "3000"],
            cwd=ROOT_DIR,
            stdout=frontend_log_out,
            stderr=frontend_log_err
        )
        self.processes.append(frontend_process)
        _log(f"Service Frontend démarré avec le PID: {frontend_process.pid}")

        # Laisser le temps aux serveurs de démarrer
        _log("Attente du démarrage des services (60 secondes)...")
        time.sleep(60)
        _log("Services probablement démarrés.")

    def stop_services(self):
        """Arrête proprement tous les services démarrés."""
        _log("Arrêt des services...")
        for process in self.processes:
            try:
                _log(f"Tentative d'arrêt du processus {process.pid}...")
                process.terminate()
                process.wait(timeout=10)
                _log(f"Processus {process.pid} arrêté avec succès.")
            except subprocess.TimeoutExpired:
                _log(f"Le processus {process.pid} ne s'est pas arrêté à temps, forçage...")
                process.kill()
                _log(f"Processus {process.pid} forcé à s'arrêter.")
        self.processes = []

        # Fermer les fichiers de log
        _log("Fermeture des fichiers de log...")
        for log_file in self.log_files.values():
            log_file.close()
        self.log_files = {}
        _log("Fichiers de log fermés.")


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
        """Lance pytest avec les arguments appropriés et une journalisation en temps réel."""
        test_paths = self._get_test_paths()
        if not test_paths:
            _log(f"Type de test '{self.test_type}' non reconnu ou aucun chemin de test trouvé.")
            return

        # Ajout de -v pour un output plus verbeux
        command = [sys.executable, "-m", "pytest", "-s", "-v"] + test_paths
        
        if self.browser:
            command.extend(["--browser", self.browser])
        
        _log(f"Lancement de pytest avec la commande: {' '.join(command)}")
        _log(f"Répertoire de travail: {ROOT_DIR}")

        process = subprocess.Popen(
            command,
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        # Lire et afficher la sortie en temps réel
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        # Gérer les erreurs
        stderr_output = process.stderr.read()
        if stderr_output:
            _log("Erreurs de pytest (stderr):")
            print(stderr_output.strip())

        if process.returncode != 0:
            _log(f"Pytest a terminé avec le code d'erreur {process.returncode}.")
            sys.exit(process.returncode)
        else:
            _log("Pytest a terminé avec succès.")


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