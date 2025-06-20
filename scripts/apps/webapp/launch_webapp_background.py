#!/usr/bin/env python
# -*- coding: utf-8 -*-

# --- Garde-fou pour l'environnement ---
# Cet import est crucial. Il assure que le script s'exécute dans l'environnement
# Conda et avec les variables (JAVA_HOME, etc.) correctement configurés.
# Si l'environnement n'est pas bon, il lèvera une exception claire.
import argumentation_analysis.core.environment
import argumentation_analysis.core.environment
#!/usr/bin/env python3
"""
Launcher webapp 100% détaché - lance et retourne immédiatement
Utilise subprocess.DETACHED_PROCESS sur Windows pour vraie indépendance
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def launch_backend_detached():
    """Lance le backend Uvicorn en arrière-plan complet"""
    # Le garde-fou garantit que sys.executable est le bon python
    python_exe = sys.executable
    project_root = str(Path(__file__).parent.parent.absolute())
    
    # Rendre le port configurable, avec une valeur par défaut
    port = os.environ.get("WEB_API_PORT", "5003")
    
    cmd = [
        python_exe,
        "-m", "uvicorn",
        "argumentation_analysis.services.web_api.app:app",
        "--host", "0.0.0.0",
        "--port", port
    ]
    
    # os.environ est déjà correctement configuré par le wrapper activate_project_env.ps1
    
    print(f"[LAUNCH] Lancement du backend détaché...")
    print(f"[DIR] Répertoire de travail: {project_root}")
    print(f"[PYTHON] Exécutable Python: {python_exe}")
    print(f"[URL] URL prevue: http://localhost:{port}/api/health")
    
    try:
        # Windows: DETACHED_PROCESS pour vraie indépendance
        if os.name == 'nt':
            stdout_log = open("backend_stdout.log", "w")
            stderr_log = open("backend_stderr.log", "w")
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                env=os.environ,
                creationflags=subprocess.DETACHED_PROCESS,
                stdout=stdout_log,
                stderr=stderr_log,
                stdin=subprocess.DEVNULL
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
                preexec_fn=os.setsid
            )
        
        print(f"[SUCCESS] Backend lance en arriere-plan (PID: {process.pid})")
        print(f"[WAIT] Attendre 10-15s puis tester: curl http://localhost:5003/api/health")
        return True, process.pid
        
    except Exception as e:
        print(f"[ERROR] Erreur lancement: {e}")
        return False, None

def check_backend_status():
    """Vérifie rapidement si le backend répond (non-bloquant)"""
    try:
        import requests
        port = os.environ.get("WEB_API_PORT", "5003")
        response = requests.get(f"http://localhost:{port}/api/health", timeout=2)
        if response.status_code == 200:
            print(f"[OK] Backend actif et repond: {response.json()}")
            return True
        else:
            print(f"[WARN] Backend repond mais status {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("[INFO] Backend pas encore pret ou non demarre")
        return False
    except ImportError:
        print("[INFO] Module requests non disponible pour test")
        return None

def kill_existing_backends():
    """Tue les processus backend existants"""
    try:
        import psutil
        killed = 0
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'uvicorn' in cmdline and 'argumentation_analysis' in cmdline:
                    proc.terminate()
                    killed += 1
                    print(f"[KILL] Processus backend termine: PID {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if killed > 0:
            time.sleep(2)  # Délai pour nettoyage
            print(f"[CLEAN] {killed} processus backend nettoyes")
        else:
            print("[INFO] Aucun processus backend a nettoyer")
            
        return killed
    except ImportError:
        print("[WARN] Module psutil non disponible pour nettoyage")
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