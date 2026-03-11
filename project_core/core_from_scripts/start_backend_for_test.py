# -*- coding: utf-8 -*-
"""
Utilitaire pour lancer le backend de l'application en arrière-plan,
spécifiquement pour les besoins des tests automatisés.

Ce script est conçu pour être appelé depuis un script shell (ex: PowerShell)
qui orchestre les tests. Il démarre le serveur webapp, écrit son PID dans
un fichier pour permettre au script appelant de le gérer (attendre, ou
terminer le processus), et redirige stdout/stderr vers des fichiers de log.
"""

import os
import sys
import subprocess
from pathlib import Path


def main():
    """
    Point d'entrée principal du script.
    """
    # Déterminer la racine du projet à partir de l'emplacement de ce script
    # project_core/core_from_scripts/start_backend_for_test.py -> project_root
    project_root = Path(__file__).parent.parent.parent.absolute()

    # Valider que nous sommes bien à la racine attendue
    if not (project_root / "pyproject.toml").exists():
        print(
            f"ERREUR: Impossible de trouver la racine du projet. Attendu un 'pyproject.toml' dans {project_root}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Configuration des chemins
    log_dir = project_root / "_temp"
    log_dir.mkdir(exist_ok=True)  # S'assurer que le répertoire de log existe

    backend_stdout_log = log_dir / "backend_stdout.log"
    backend_stderr_log = log_dir / "backend_stderr.log"
    pid_file = log_dir / "backend.pid"

    # S'assurer que la racine du projet est dans le PYTHONPATH
    sys.path.insert(0, str(project_root))

    # Construction de la commande de lancement
    uvicorn_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",  # Point d'entrée corrigé
        "--host",
        "127.0.0.1",
        "--port",
        "8004",  # Port fixe pour les tests
        "--log-level",
        "info",
    ]

    print(f"--- Lancement du Backend pour les tests (via {__file__}) ---")
    print(f"  - Commande: {' '.join(uvicorn_cmd)}")
    print(f"  - PID file: {pid_file}")
    print(f"  - Logs: {backend_stdout_log} / {backend_stderr_log}")

    try:
        # Ouvrir les fichiers de log pour la redirection
        stdout_log = open(backend_stdout_log, "w", encoding="utf-8")
        stderr_log = open(backend_stderr_log, "w", encoding="utf-8")

        # Démarrer le processus en arrière-plan
        process = subprocess.Popen(
            uvicorn_cmd,
            cwd=project_root,
            stdout=stdout_log,
            stderr=stderr_log,
            env=os.environ.copy(),
        )
    except Exception as e:
        print(f"ERREUR CRITIQUE: subprocess.Popen a échoué: {e}", file=sys.stderr)
        sys.exit(1)

    # Écrire le PID dans le fichier pour que le script appelant puisse le tuer
    try:
        with open(pid_file, "w", encoding="utf-8") as f:
            f.write(str(process.pid))
        print(
            f"Backend lancé avec succès. PID: {process.pid}. En attente de la fin du processus..."
        )
    except IOError as e:
        print(
            f"ERREUR: Impossible d'écrire dans le fichier PID '{pid_file}': {e}",
            file=sys.stderr,
        )
        # Tenter de tuer le processus qu'on vient de lancer pour ne pas le laisser zombie
        process.kill()
        sys.exit(1)

    # Le script doit maintenant attendre que le processus uvicorn se termine.
    # C'est ce qui maintient le script "en cours d'exécution" et donc le Job PowerShell
    # à l'état "Running". Le processus sera tué de l'extérieur par le script de test.
    try:
        process.wait()
    except KeyboardInterrupt:
        print("Interruption manuelle reçue. Le backend s'arrête.")
        process.terminate()
    finally:
        # Nettoyage au cas où le processus se terminerait de manière inattendue
        if os.path.exists(pid_file):
            os.remove(pid_file)


if __name__ == "__main__":
    main()
