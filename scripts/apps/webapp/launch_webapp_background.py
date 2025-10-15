#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path
import subprocess
import time

# --- Correction du PYTHONPATH ---
# Ajoute la racine du projet au PYTHONPATH pour permettre les imports 'argumentation_analysis'
# Doit être fait avant tout import du projet.
project_root_path = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root_path))


# --- Garde-fou pour l'environnement ---
# Cet import est crucial. Il assure que le script s'exécute dans l'environnement
# Conda et avec les variables (JAVA_HOME, etc.) correctement configurés.
# Si l'environnement n'est pas bon, il lèvera une exception claire.
import argumentation_analysis.core.environment


"""
Lance le serveur backend de l'application en processus d'arrière-plan.

Ce script gère le cycle de vie du serveur Uvicorn pour l'API :
- 'start': Lance le serveur après avoir nettoyé les instances précédentes.
- 'status': Vérifie si le serveur répond correctement.
- 'kill': Termine tous les processus serveur correspondants.

Utilisation impérative via le wrapper d'environnement pour garantir que
l'environnement Conda ('projet-is') et les variables critiques sont chargés.
Exemple:
  powershell -File ./activate_project_env.ps1 -CommandToRun "python scripts/apps/webapp/launch_webapp_background.py start"
"""


def launch_backend_detached():
    """Lance le backend Uvicorn en arrière-plan complet"""
    # Le garde-fou garantit que sys.executable est le bon python
    python_exe = sys.executable
    project_root = str(Path(__file__).parent.parent.absolute())

    # Rendre le port configurable, avec une valeur par défaut
    port = os.environ.get("WEB_API_PORT", "5003")

    cmd = [
        python_exe,
        "-m",
        "uvicorn",
        "argumentation_analysis.services.web_api.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        port,
    ]

    # os.environ est déjà correctement configuré par le wrapper activate_project_env.ps1

    print(f"[LAUNCH] Lancement du backend détaché...")
    print(f"[DIR] Répertoire de travail: {project_root}")
    print(f"[PYTHON] Exécutable Python: {python_exe}")
    print(f"[URL] URL prevue: http://127.0.0.1:{port}/api/health")

    try:
        # Windows: DETACHED_PROCESS pour vraie indépendance
        if os.name == "nt":
            stdout_log = open("backend_stdout.log", "w")
            stderr_log = open("backend_stderr.log", "w")
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                env=os.environ,
                creationflags=subprocess.DETACHED_PROCESS,
                stdout=stdout_log,
                stderr=stderr_log,
                stdin=subprocess.DEVNULL,
            )
        else:
            # Unix: nohup équivalent
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                env=os.environ,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                preexec_fn=os.setsid,
            )

        print(f"[SUCCESS] Backend lance en arriere-plan (PID: {process.pid})")
        print(
            f"[WAIT] Attendre 10-15s puis tester: curl http://localhost:5003/api/health"
        )
        return True, process.pid

    except Exception as e:
        print(f"[ERROR] Erreur lancement: {e}")
        return False, None


def check_backend_status():
    """
    Vérifie rapidement si le backend répond (non-bloquant).

    Notes:
        Cette fonction requiert le module 'requests'. Si non disponible,
        le statut sera indeterminé.
    """
    try:
        import requests

        port = os.environ.get("WEB_API_PORT", "5003")
        response = requests.get(f"http://localhost:{port}/api/health", timeout=2)
        if response.status_code == 200:
            print(f"[OK] Backend actif et répond: {response.json()}")
            return True
        else:
            print(
                f"[WARN] Backend répond mais avec un statut inattendu: {response.status_code}"
            )
            return False
    except requests.exceptions.RequestException:
        print("[INFO] Backend pas encore prêt ou non démarré.")
        return False
    except ImportError:
        print(
            "[WARN] Le module 'requests' n'est pas installé. Test de statut impossible."
        )
        return None


def kill_existing_backends():
    """
    Tue les processus backend (Uvicorn) existants liés à ce projet.

    Notes:
        Cette fonction requiert le module 'psutil'. Si non disponible,
        le nettoyage ne pourra pas être effectué.
    """
    try:
        import psutil

        killed = 0
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = " ".join(proc.info["cmdline"] or [])
                if "uvicorn" in cmdline and "argumentation_analysis" in cmdline:
                    proc.terminate()
                    killed += 1
                    print(f"[KILL] Processus backend terminé: PID {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if killed > 0:
            time.sleep(2)  # Délai pour nettoyage
            print(f"[INFO] {killed} processus backend nettoyé(s).")
        else:
            print("[INFO] Aucun processus backend à nettoyer.")

        return killed
    except ImportError:
        print("[WARN] Le module 'psutil' n'est pas installé. Nettoyage impossible.")
        return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "start"

    if action == "start":
        # Nettoyage préventif
        kill_existing_backends()

        # Lancement détaché
        success, pid = launch_backend_detached()
        if success:
            print(f"[SUCCESS] Backend lance en arriere-plan (PID: {pid})")
            sys.exit(0)
        else:
            print("[FAILED] Echec lancement backend")
            sys.exit(1)

    elif action == "status":
        status = check_backend_status()
        if status is True:
            print("[OK] Backend OK")
            sys.exit(0)
        elif status is False:
            print("[KO] Backend KO")
            sys.exit(1)
        else:
            print("[UNKNOWN] Status indetermine")
            sys.exit(2)

    elif action == "kill":
        killed = kill_existing_backends()
        print(f"[CLEANUP] Nettoyage termine: {killed} processus")
        sys.exit(0)

    else:
        print("Usage: python launch_webapp_background.py [start|status|kill]")
        sys.exit(1)
