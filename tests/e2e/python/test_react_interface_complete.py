#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test complet de l'interface React avec démarrage automatique
===========================================================

Ce script démarre automatiquement l'API backend et l'interface React,
puis exécute les tests Playwright des 6 onglets.
"""

import subprocess
import time
import sys
import os
import requests
import signal
from pathlib import Path
from project_core.utils.shell import run_in_activated_env, ShellCommandError

# Configuration d'encodage pour Windows
if sys.platform == "win32":
    import locale

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        print("Configuration UTF-8 chargée automatiquement")
    except:
        print("Configuration encodage chargée automatiquement")


def wait_for_service(url, name, timeout=30):
    """Attend qu'un service soit disponible"""
    print(f"Attente de {name} sur {url}...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"[OK] {name} disponible après {time.time() - start_time:.1f}s")
                return True
        except Exception:
            pass
        time.sleep(1)

    print(f"[ERROR] {name} non disponible après {timeout}s")
    return False


def start_backend_api():
    """Démarre l'API backend via l'orchestrateur unifié"""
    print("============================================================")
    print("DÉMARRAGE API BACKEND VIA ORCHESTRATEUR")
    print("============================================================")

    # Vérifier si l'API est déjà démarrée
    try:
        response = requests.get("http://localhost:8095/api/health", timeout=2)
        if response.status_code == 200:
            print("[INFO] API backend déjà démarrée sur port 8095")
            return None
    except:
        pass

    # Utiliser l'orchestrateur unifié pour démarrer l'API
    project_root = Path(__file__).parent.parent.parent
    orchestrator_cmd = [
        sys.executable,
        "-c",
        "from project_core.webapp_from_scripts import UnifiedWebOrchestrator; "
        "import asyncio; "
        "orchestrator = UnifiedWebOrchestrator(); "
        "asyncio.run(orchestrator.start_webapp(headless=True, frontend_enabled=False)); "
        "import time; "
        "time.sleep(300);",  # Maintenir l'API active
    ]

    print("Démarrage API via orchestrateur unifié...")
    print("Initialisation en cours (15-30s)...")

    try:
        # Note: run_in_activated_env est synchrone, mais nous le lançons
        # et vérifions simplement que le service est démarré.
        # Le processus parent (ce script) ne gérera pas l'enfant.
        run_in_activated_env(
            command=orchestrator_cmd,
            env_name="projet-is",
            cwd=str(project_root),
            check_errors=False,  # Ne pas bloquer si le script continue en arrière-plan
        )
    except ShellCommandError as e:
        print(f"[ERROR] Échec du lancement de l'orchestrateur: {e}")
        return None

    # Le processus est maintenant détaché. Nous nous fions à wait_for_service.
    # Il n'y a plus d'objet 'process' à retourner.
    process = None

    # Attendre que l'API soit prête
    if wait_for_service("http://localhost:5003/api/health", "API Backend", timeout=60):
        print("[SUCCESS] API backend démarrée sur port 5003")
        return process
    else:
        print("[ERROR] Échec démarrage API backend")
        process.terminate()
        return None


def start_react_interface():
    """Démarre l'interface React sur le port 3000"""
    print("============================================================")
    print("DÉMARRAGE INTERFACE REACT")
    print("============================================================")

    # Vérifier si React est déjà démarré
    try:
        response = requests.get("http://localhost:8085/", timeout=2)
        if response.status_code == 200:
            print("[INFO] Interface React déjà démarrée")
            return None
    except:
        pass

    # Installer les dépendances si nécessaire
    react_dir = (
        Path(__file__).parent.parent.parent
        / "services"
        / "web_api"
        / "interface-web-argumentative"
    )
    node_modules = react_dir / "node_modules"

    if not node_modules.exists():
        print("Installation des dépendances npm...")
        install_result = subprocess.run(
            "npm install",
            cwd=str(react_dir),
            capture_output=True,
            text=True,
            shell=True,
        )
        if install_result.returncode != 0:
            print(f"[ERROR] Échec installation npm: {install_result.stderr}")
            return None
        print("[OK] Dépendances npm installées")

    # Démarrer React
    print("Démarrage interface React...")
    env = os.environ.copy()
    env["BROWSER"] = "none"  # Éviter l'ouverture automatique du navigateur
    env["PORT"] = "3000"

    process = subprocess.Popen(
        "npm start",
        cwd=str(react_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        shell=True,
    )

    # Attendre que React soit prêt
    if wait_for_service("http://localhost:3000/", "Interface React", timeout=60):
        print("[SUCCESS] Interface React démarrée")
        return process
    else:
        print("[ERROR] Échec démarrage interface React")
        process.terminate()
        return None


def run_tests():
    """Exécute les tests Playwright"""
    print("============================================================")
    print("EXÉCUTION TESTS PLAYWRIGHT")
    print("============================================================")

    project_root = Path(__file__).parent.parent.parent

    test_files = [
        "tests/functional/test_argument_analyzer.py",
        "tests/functional/test_fallacy_detector.py",
        "tests/functional/test_argument_reconstructor.py",
        "tests/functional/test_logic_graph.py",
        "tests/functional/test_validation_form.py",
        "tests/functional/test_framework_builder.py",
    ]

    cmd = [sys.executable, "-m", "pytest", "-v", "--tb=short"] + test_files

    print(f"Commande test: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(project_root))
    return result.returncode == 0


def cleanup_processes(processes):
    """Nettoie les processus démarrés"""
    print("============================================================")
    print("NETTOYAGE")
    print("============================================================")

    for name, process in processes:
        if process:
            print(f"Arrêt {name}...")
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"Force kill {name}")


def main():
    """Fonction principale"""
    print("MISSION: TESTS INTERFACE WEB REACT")
    print("=" * 60)

    processes = []
    success = False

    try:
        # Démarrer l'API backend
        api_process = start_backend_api()
        processes.append(("API Backend", api_process))

        if (
            api_process is not None
            or requests.get("http://localhost:5003/api/health", timeout=2).status_code
            == 200
        ):
            # Démarrer l'interface React
            react_process = start_react_interface()
            processes.append(("Interface React", react_process))

            if (
                react_process is not None
                or requests.get("http://localhost:3000/", timeout=2).status_code == 200
            ):
                # Exécuter les tests
                success = run_tests()
            else:
                print("[ERROR] Impossible de démarrer l'interface React")
        else:
            print("[ERROR] Impossible de démarrer l'API backend")

    except KeyboardInterrupt:
        print("\n[INFO] Interruption utilisateur")
    except Exception as e:
        print(f"[ERROR] Erreur inattendue: {e}")
    finally:
        # Nettoyage
        cleanup_processes(processes)

    # Résultat final
    print("============================================================")
    if success:
        print("RÉSULTAT FINAL: SUCCESS - TESTS INTERFACE WEB OK")
        sys.exit(0)
    else:
        print("RÉSULTAT FINAL: FAILED - TESTS INTERFACE WEB ÉCHOUÉS")
        sys.exit(1)


if __name__ == "__main__":
    main()
