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
import socket
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


class TestRunner:
    """Orchestre l'exécution des tests."""

    def __init__(self, test_type, test_path, browser, pytest_extra_args=None):
        self.test_type = test_type
        self.test_path = test_path
        self.browser = browser
        self.pytest_extra_args = pytest_extra_args if pytest_extra_args is not None else []

    def run(self):
        """Exécute le cycle de vie complet des tests."""
        self._run_pytest()

    def _get_test_paths(self):
        """Détermine les chemins de test à utiliser."""
        if self.test_path:
            return [self.test_path]
        
        paths = {
            "unit": "tests/unit",
            "functional": "tests/functional",
            "e2e": "tests/e2e",
            "all": ["tests/unit"],
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

        command = ["python", "-m", "pytest", "-s", "-vv"] + test_paths
        
        if self.browser:
            command.extend(["--browser", self.browser])

        if self.pytest_extra_args:
            command.extend(self.pytest_extra_args)
        
        _log(f"Lancement de pytest avec la commande: {' '.join(command)}")
        _log(f"Répertoire de travail: {ROOT_DIR}")

        process = subprocess.run(
            command,
            cwd=ROOT_DIR,
            text=True,
            encoding='utf-8'
        )

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
    args, unknown_args = parser.parse_known_args()
 
    runner = TestRunner(args.type, args.path, args.browser, pytest_extra_args=unknown_args)
    runner.run()


if __name__ == "__main__":
    main()