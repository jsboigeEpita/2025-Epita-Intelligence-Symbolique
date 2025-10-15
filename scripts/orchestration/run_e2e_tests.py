# -*- coding: utf-8 -*-
"""
Orchestrateur de tests E2E asynchrone et non bloquant.

Ce script utilise asyncio pour gérer de manière robuste le cycle de vie des tests E2E :
- Démarrage et surveillance des services backend et frontend.
- Redirection en temps réel des logs des services.
- Health checks non bloquants pour attendre que les services soient prêts.
- Lancement de la suite de tests pytest.
- Nettoyage et terminaison garantis de tous les processus.
"""

import asyncio
import os
import sys
from pathlib import Path
import psutil
import signal
import platform

# Configuration des chemins
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
API_DIR = ROOT_DIR
FRONTEND_DIR = ROOT_DIR / "services" / "web_api" / "interface-web-argumentative"
LOG_DIR = ROOT_DIR / "_e2e_logs"

# Configuration des services
API_PORT = 5004
FRONTEND_PORT = 3000
API_HOST = "127.0.0.1"
FRONTEND_HOST = "127.0.0.1"


def get_uvicorn_command():
    """Construit la commande pour lancer le serveur backend API avec uvicorn."""
    return [
        sys.executable,
        "-m",
        "uvicorn",
        "services.web_api_from_libs.app:app_asgi",
        "--host",
        API_HOST,
        "--port",
        str(API_PORT),
        "--log-level",
        "info",
    ]


def get_npm_command():
    """Construit la commande pour lancer le serveur de développement frontend."""
    npm_executable = "npm.cmd" if sys.platform == "win32" else "npm"
    return [npm_executable, "start"]


async def stream_logs(stream, log_file_path):
    """Lit le flux (stdout/stderr) d'un processus et l'écrit dans un fichier de log."""
    with open(
        log_file_path, "ab"
    ) as f:  # Ouvre en mode binaire pour éviter les problèmes d'encodage
        while True:
            line = await stream.readline()
            if not line:
                break
            f.write(line)
            f.flush()


async def start_service(command, cwd, log_file_path):
    """
    Démarre un service en tant que sous-processus et redirige ses logs.
    Retourne le processus et les tâches de logging.
    """
    print(f"Lancement de la commande: {' '.join(command)} dans {cwd}")

    # Configuration de l'environnement avec variables React pour le frontend
    env = os.environ.copy()
    if "npm" in " ".join(command):  # Si c'est le frontend React
        env["REACT_APP_BACKEND_URL"] = f"http://{API_HOST}:{API_PORT}"

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )

    # Création des tâches pour la redirection des logs
    stdout_log_task = asyncio.create_task(stream_logs(process.stdout, log_file_path))
    stderr_log_task = asyncio.create_task(stream_logs(process.stderr, log_file_path))

    print(f"Service démarré avec le PID: {process.pid}. Logs dans: {log_file_path}")
    return process, stdout_log_task, stderr_log_task


async def wait_for_service(host, port, service_name, timeout=90):
    """Attend qu'un service soit disponible sur un port TCP donné."""
    print(f"Attente de la disponibilité du service {service_name} sur {host}:{port}...")
    start_time = asyncio.get_event_loop().time()

    while True:
        current_time = asyncio.get_event_loop().time()
        if current_time - start_time > timeout:
            raise TimeoutError(
                f"Timeout ({timeout}s) atteint pour le service {service_name}."
            )

        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            print(f"Service {service_name} est prêt !")
            return True
        except ConnectionRefusedError:
            await asyncio.sleep(2)  # Attente non bloquante
        except asyncio.CancelledError:
            print(f"L'attente pour le service {service_name} a été annulée.")
            raise


def get_pytest_command():
    """Construit la commande pour lancer pytest."""
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-vv",
        "-s",
        "--capture=no",
        "--durations=10",
        "tests/e2e",
        "--backend-url",
        f"http://{API_HOST}:{API_PORT}",
        "--frontend-url",
        f"http://{FRONTEND_HOST}:{FRONTEND_PORT}",
        "--browser",
        "chromium",  # Peut être paramétré plus tard
    ]
    return command


async def run_pytest():
    """Lance la suite de tests pytest et attend sa complétion."""
    command = get_pytest_command()
    print(f"Lancement de pytest avec la commande: {' '.join(command)}")

    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=ROOT_DIR,
        stdout=sys.stdout,  # Affiche la sortie pytest directement sur la console
        stderr=sys.stderr,
    )

    return_code = await process.wait()

    if return_code != 0:
        print(f"Pytest a terminé avec un code d'erreur: {return_code}")
        return False

    print("Pytest a terminé avec succès.")
    return True


def kill_process_on_port(port):
    """Trouve et tue le processus qui écoute sur un port donné en utilisant psutil."""
    print(f"Vérification et nettoyage du port {port}...")
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            connections = proc.connections(kind="inet")
            for conn in connections:
                if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                    print(
                        f"  > Port {port} utilisé par le processus {proc.info['name']} (PID: {proc.info['pid']}). Terminaison..."
                    )
                    process = psutil.Process(proc.info["pid"])
                    process.terminate()
                    process.wait()
                    print(f"  > Processus {proc.info['pid']} terminé.")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    print(f"Nettoyage du port {port} terminé.")


async def main():
    """Point d'entrée principal de l'orchestrateur."""
    print("Démarrage de l'orchestrateur de tests E2E asynchrone...")

    # Nettoyage des ports avant de démarrer les services
    kill_process_on_port(API_PORT)
    kill_process_on_port(FRONTEND_PORT)

    backend_process, backend_stdout_task, backend_stderr_task = (None, None, None)
    frontend_process, frontend_stdout_task, frontend_stderr_task = (None, None, None)

    test_success = False
    try:
        # Démarrage des services
        backend_process, backend_stdout_task, backend_stderr_task = await start_service(
            get_uvicorn_command(), API_DIR, LOG_DIR / "backend.log"
        )

        (
            frontend_process,
            frontend_stdout_task,
            frontend_stderr_task,
        ) = await start_service(
            get_npm_command(), FRONTEND_DIR, LOG_DIR / "frontend.log"
        )

        # Attendre que les services soient prêts
        await asyncio.gather(
            wait_for_service(API_HOST, API_PORT, "Backend API"),
            wait_for_service(FRONTEND_HOST, FRONTEND_PORT, "Frontend"),
        )

        print("Tous les services sont prêts. Lancement des tests...")
        print("--- DEBUT DE L'EXECUTION PYTEST ---")

        test_success = await run_pytest()

        print("--- FIN DE L'EXECUTION PYTEST ---")

    finally:
        print("Nettoyage des processus...")
        if backend_process:
            if platform.system() == "Windows":
                backend_process.terminate()
            else:
                backend_process.send_signal(signal.SIGTERM)
        if frontend_process:
            if platform.system() == "Windows":
                frontend_process.terminate()
            else:
                # Le processus npm start peut avoir des enfants, nous les gérons
                try:
                    parent = psutil.Process(frontend_process.pid)
                    for child in parent.children(recursive=True):
                        child.terminate()
                    parent.terminate()
                except psutil.NoSuchProcess:
                    pass  # Le processus est peut-être déjà terminé

        # Attendre que les processus se terminent réellement
        tasks_to_wait = []
        if backend_process:
            tasks_to_wait.append(backend_process.wait())
        if frontend_process:
            tasks_to_wait.append(frontend_process.wait())
        if tasks_to_wait:
            await asyncio.gather(*tasks_to_wait)

        # Annuler les tâches de logging pour qu'elles se terminent proprement
        tasks_to_cancel = [
            t
            for t in [
                backend_stdout_task,
                backend_stderr_task,
                frontend_stdout_task,
                frontend_stderr_task,
            ]
            if t
        ]
        for task in tasks_to_cancel:
            task.cancel()

        if tasks_to_cancel:
            await asyncio.gather(*tasks_to_cancel, return_exceptions=True)

        print("Nettoyage terminé.")

    if not test_success:
        print("Au moins un test a échoué.")
        sys.exit(1)


if __name__ == "__main__":
    # Création du répertoire de logs s'il n'existe pas
    LOG_DIR.mkdir(exist_ok=True)

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, TimeoutError) as e:
        print(f"\nOrchestrateur interrompu ou a échoué: {e}")
        # Une terminaison propre est déjà gérée dans le `finally` de `main`
        sys.exit(1)
