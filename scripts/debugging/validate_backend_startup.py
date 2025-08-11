#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de validation pour le démarrage du backend API.

Ce script sert à diagnostiquer les problèmes de démarrage du serveur, en particulier
ceux liés à l'initialisation de la JVM, qui se sont avérés causer des deadlocks
lorsqu'ils sont lancés avec le serveur de développement Flask (Werkzeug).

Principe de fonctionnement :
1.  **Lance le serveur Uvicorn** : Utilise le script `run_e2e_backend.py`, qui
    démarre un serveur Uvicorn, plus robuste pour ce cas d'usage.
2.  **Utilise un Thread** : Le serveur est démarré dans un thread "démon" séparé
    pour ne pas bloquer le script principal.
3.  **Sondage (Health Check)** : Le script principal sonde en boucle l'endpoint
    `/api/health` pour vérifier si le serveur est devenu opérationnel.
4.  **Mode Mock** : Il active le mode `INTEGRATION_TEST_MODE` pour que les services
    externes (comme le LLM) soient mockés, permettant un test de démarrage pur
    sans dépendre de clés API.
5.  **Nettoyage de Port** : Avant de démarrer, il s'assure que le port cible est
    libre et tue tout processus qui l'occuperait.

Ce script est l'outil à utiliser pour vérifier que l'architecture de démarrage
lazy-loading de la JVM fonctionne correctement après une modification majeure.
"""
import os
import sys
import time
import requests
import threading
import psutil
from pathlib import Path

# --- Configuration et Setup du Path ---
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.run_e2e_backend import start_server

# --- Configuration du Test ---
HOST = "127.0.0.1"
PORT = 8095
HEALTH_CHECK_URL = f"http://{HOST}:{PORT}/api/health"
STARTUP_TIMEOUT = 240  # Secondes

# --- Fonctions de Gestion de Processus ---
def find_process_by_port(port):
    """Trouve le processus qui utilise un port donné."""
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.status == 'LISTEN':
            try:
                proc = psutil.Process(conn.pid)
                return {'pid': conn.pid, 'name': proc.name()}
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    return None

def kill_process_by_pid(pid):
    """Tue un processus par son PID de manière ciblée."""
    try:
        proc = psutil.Process(pid)
        proc.kill()
        proc.wait(timeout=5)
        print(f"INFO: Processus {pid} ({proc.name()}) terminé avec succès.")
        return True
    except psutil.NoSuchProcess:
        return True # Le but est atteint si le processus n'existe plus.
    except (psutil.AccessDenied, psutil.TimeoutExpired, Exception) as e:
        print(f"AVERTISSEMENT: N'a pas pu tuer le processus {pid}. Raison: {e}")
        return False

# --- Logique Principale ---
def main():
    """
    Lance le backend dans un thread et vérifie s'il démarre correctement.
    """
    # 1. Nettoyage du port avant le démarrage
    proc_info = find_process_by_port(PORT)
    if proc_info:
        print(f"INFO: Le port {PORT} est déjà utilisé par {proc_info['name']} (PID: {proc_info['pid']}). Tentative de nettoyage...")
        kill_process_by_pid(proc_info['pid'])
        time.sleep(2)

    # 2. Configuration de l'environnement pour le mode mock
    print("INFO: Activation du mode mock pour le service LLM (INTEGRATION_TEST_MODE=true).")
    os.environ['INTEGRATION_TEST_MODE'] = 'true'

    # 3. Démarrage du serveur dans un thread séparé
    print("INFO: Démarrage du serveur backend Uvicorn dans un thread...")
    # Un thread "démon" s'arrêtera automatiquement lorsque le script principal se terminera.
    # C'est idéal pour un processus d'arrière-plan que nous n'avons pas besoin de joindre.
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    # 4. Attente et sondage du serveur
    print(f"INFO: En attente du backend sur {HEALTH_CHECK_URL} (timeout: {STARTUP_TIMEOUT}s)...")
    start_time = time.time()
    backend_ready = False

    while time.time() - start_time < STARTUP_TIMEOUT:
        if not server_thread.is_alive():
            print("\n--- ERREUR CRITIQUE ---")
            print("Le thread du serveur s'est terminé de manière inattendue. Le serveur a probablement crashé au démarrage.")
            break
        try:
            response = requests.get(HEALTH_CHECK_URL, timeout=1)
            if response.status_code == 200:
                print("\n\n--- SUCCÈS ---")
                print("Le backend est prêt et répond au health check.")
                backend_ready = True
                break
            else:
                print(f"\nAVERTISSEMENT: Le health check a répondu avec le statut {response.status_code}. Nouvel essai...")
        except requests.ConnectionError:
            sys.stdout.write('.')
            sys.stdout.flush()
        except requests.Timeout:
             print("\nAVERTISSEMENT: Timeout du health check. Nouvel essai...")
        
        time.sleep(2)

    if not backend_ready:
        print("\n\n--- ÉCHEC ---")
        print("Le serveur n'est pas devenu prêt dans le temps imparti.")

    print("INFO: Fin du script de validation.")
    
    if backend_ready:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()