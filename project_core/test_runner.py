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
import os
import subprocess
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

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
        # FORCER LE PORT 5000 car le frontend est en build statique
        self.api_port = 5000 
        self.frontend_port = 3000

    def start_services(self):
        """Démarre l'API backend qui sert également le frontend."""
        _log("Démarrage du service API pour les tests E2E...")

        # Démarrer le backend API
        _log(f"[RUNNER_DEBUG] Démarrage du service API sur le port {self.api_port} (CWD: {API_DIR})")
        api_log_out = open("api_server.log", "w", encoding="utf-8")
        api_log_err = open("api_server.error.log", "w", encoding="utf-8")
        self.log_files["api_out"] = api_log_out
        self.log_files["api_err"] = api_log_err
        
        uvicorn_command = [
            sys.executable, "-m", "uvicorn", 
            "argumentation_analysis.services.web_api.app:app",
            "--host", "0.0.0.0",
            "--port", str(self.api_port), 
            "--log-level", "debug"
        ]
        _log(f"[RUNNER_DEBUG] Commande Popen Uvicorn: {uvicorn_command}")
        
        # On s'assure de propager l'environnement actuel au sous-processus
        env = os.environ.copy()
        api_process = subprocess.Popen(
            uvicorn_command,
            cwd=API_DIR,
            stdout=api_log_out,
            stderr=api_log_err,
            env=env
        )
        self.processes.append(api_process)
        _log(f"[RUNNER_DEBUG] Service API démarré avec le PID: {api_process.pid}")

        # Le frontend est servi par le backend, pas de service séparé à démarrer.
        _log("[RUNNER_DEBUG] Début de l'attente de la disponibilité du service API...")
        self._wait_for_services(ports=[self.api_port])
        _log("[RUNNER_DEBUG] Fin de l'attente de la disponibilité du service API.")

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

    def _check_service_health(self):
        """Vérifie si les processus de service sont toujours en cours d'exécution."""
        for process in self.processes:
            if process.poll() is not None:
                _log(f"ERREUR: Le service avec le PID {process.pid} s'est arrêté de manière inattendue.")
                return False
        return True

    def _wait_for_services(self, ports, timeout=90):
        """Attend que les services soient prêts en vérifiant la disponibilité des ports."""
        start_time = time.time()
        interval = 5

        while time.time() - start_time < timeout:
            if not self._check_service_health():
                _log("Un service s'est arrêté prématurément. Annulation de l'attente.")
                raise RuntimeError("Échec du démarrage d'un service dépendant.")

            all_ports_ready = True
            for port in ports:
                if not self._check_port(port):
                    _log(f"Le port {port} n'est pas encore disponible. Prochaine vérification dans {interval}s.")
                    all_ports_ready = False
                    break
            
            if all_ports_ready:
                _log("[RUNNER_DEBUG] Tous les services sont opérationnels. Démarrage des tests.")
                return

            time.sleep(interval)

        _log(f"Dépassement du timeout de {timeout}s pour le démarrage des services.")
        raise RuntimeError("Timeout atteint lors de l'attente du démarrage des services.")

    def _check_port(self, port, host="127.0.0.1"):
        """Vérifie si un port est ouvert sur un hôte donné."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)  # Timeout court pour ne pas bloquer
            try:
                s.connect((host, port))
                return True
            except (socket.timeout, ConnectionRefusedError):
                return False

    def _find_free_port(self):
        """Trouve et retourne un port TCP libre sur la machine."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            return s.getsockname()[1]
class TestRunner:
    """Orchestre l'exécution des tests."""

    def __init__(self, test_type, test_path, browser, pytest_extra_args=None, collect_only_path=None):
        self.test_type = test_type
        self.test_path = test_path
        self.browser = browser
        self.pytest_extra_args = pytest_extra_args if pytest_extra_args is not None else []
        self.collect_only_path = collect_only_path
        self.service_manager = ServiceManager()

    def run(self):
        """Exécute le cycle de vie complet des tests."""
        needs_services = self.test_type in ["functional", "e2e"]

        try:
            if needs_services:
                self.service_manager.start_services()
            
            # Si les services ne sont pas nécessaires, ou s'ils ont démarré, on lance les tests.
            self._run_pytest()
        finally:
            # Assure l'affichage des logs et l'arrêt des services même si start_services échoue.
            if needs_services:
                self._show_service_logs()
                self.service_manager.stop_services()

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

        command = ["python", "-m", "pytest", "-v"] + test_paths
        
        # Ajout de l'option pour autoriser le chargement du .env
        command.append("--allow-dotenv")

        # Passer les URLs aux tests seulement si les services sont démarrés
        needs_services = self.test_type in ["functional", "e2e", "all"]
        if needs_services:
            backend_url = f"http://127.0.0.1:{self.service_manager.api_port}"
            # L'URL du frontend est la même que celle du backend car il sert les fichiers statiques
            frontend_url = backend_url
            command.extend(["--backend-url", backend_url])
            command.extend(["--frontend-url", frontend_url])

        if self.browser:
            command.extend(["--browser", self.browser])

        if self.pytest_extra_args:
            command.extend(self.pytest_extra_args)

        if self.collect_only_path:
            command.extend(["--collect-only"])
        
        _log(f"Lancement de pytest avec la commande: {' '.join(command)}")
        _log(f"Répertoire de travail: {ROOT_DIR}")

        # Définir l'environnement pour le sous-processus
        env = os.environ.copy()
        if self.test_type == "unit" or self.test_type == "all":
            _log("Activation du contournement de la JVM via la variable d'environnement SKIP_JVM_TESTS.")
            env["SKIP_JVM_TESTS"] = "1"

        # Utilisation de subprocess.Popen pour un affichage en temps réel
        _log("[RUNNER_DEBUG] --- APPEL DE SUBPROCESS.POPEN POUR PYTEST ---")
        process = subprocess.Popen(
            command,
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            # text=True, # On gère le décodage manuellement pour éviter les erreurs
            # encoding='utf-8',
            # bufsize=1,
            env=env
        )

        # Lire et afficher la sortie en temps réel
        collected_tests = []
        if self.collect_only_path:
            # For collection, we use quiet mode to get clean node IDs
            if "-q" not in command:
                command.insert(command.index("--collect-only"), "-q")
            raw_output = process.communicate()[0].decode('utf-8', errors='replace')
            
            for line in raw_output.splitlines():
                line_stripped = line.strip()
                # A valid pytest node ID must contain '::' and a python file extension
                if '::' in line_stripped and '.py' in line_stripped and not line_stripped.startswith('==') and 'warning' not in line_stripped.lower():
                    collected_tests.append(line_stripped)
        else:
             # Regular execution with real-time output
            if process.stdout:
                while True:
                    line_bytes = process.stdout.readline()
                    if not line_bytes:
                        break
                    line_str = line_bytes.decode('utf-8', errors='replace')
                    print(line_str, end='')

        if self.collect_only_path:
            _log(f"Sauvegarde de {len(collected_tests)} tests collectés dans {self.collect_only_path}")
            with open(self.collect_only_path, "w", encoding="utf-8") as f:
                f.write("\n".join(collected_tests))
        
        # Attendre que le processus se termine et obtenir le code de retour
        returncode = process.wait()
        _log(f"[RUNNER_DEBUG] --- PROCESSUS PYTEST TERMINÉ (Code: {returncode}) ---")

        if returncode != 0:
            _log(f"Pytest a terminé avec le code d'erreur {returncode}.")
            sys.exit(returncode)
        else:
            _log("Pytest a terminé avec succès.")

    def _show_service_logs(self):
        """Affiche le contenu des fichiers de log des services."""
        _log("Affichage des logs des services...")
        for log_name, log_path in [("API_OUT", "api_server.log"), ("API_ERR", "api_server.error.log")]:
            full_path = ROOT_DIR / log_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding="utf-8", errors='replace').strip()
                    if content:
                        _log(f"--- Contenu du log: {log_name} ({full_path}) ---")
                        print(content)
                        _log(f"--- Fin du log: {log_name} ---")
                    else:
                        _log(f"Le fichier de log {full_path} est vide.")
                except Exception as e:
                    _log(f"Impossible de lire le fichier de log {full_path}: {e}")
            else:
                _log(f"Le fichier de log {full_path} n'a pas été trouvé.")


def main():
    """Point d'entrée principal du script."""
    # Pour s'assurer que les tests (en particulier E2E) ont toujours accès aux variables
    # d'environnement nécessaires (comme la clé API), nous chargeons explicitement le fichier .env.
    # Cela rend le script de test autonome et résilient aux problèmes de propagation d'environnement
    # depuis les scripts de lancement (PowerShell, Conda, etc.).
    env_path = ROOT_DIR / '.env'
    if env_path.exists():
        _log(f"Chargement des variables d'environnement depuis {env_path}")
        # `override=True` garantit que les variables du .env priment sur celles
        # qui pourraient déjà exister dans l'environnement système.
        load_dotenv(dotenv_path=env_path, override=True)
    else:
        _log(f"[WARNING] Fichier .env non trouvé à {env_path}. Les tests risquent d'échouer si les variables requises ne sont pas déjà définies dans l'environnement.")

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
    parser.add_argument(
        "--collect-only",
        default=None,
        help="Collecte uniquement les noms des tests sans les exécuter et les enregistre dans le fichier spécifié."
    )
    args, unknown_args = parser.parse_known_args()
 
    runner = TestRunner(
        args.type,
        args.path,
        args.browser,
        pytest_extra_args=unknown_args,
        collect_only_path=args.collect_only
    )
    runner.run()


if __name__ == "__main__":
    main()