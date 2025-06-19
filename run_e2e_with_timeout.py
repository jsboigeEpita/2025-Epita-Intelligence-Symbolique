import asyncio
import sys
import os
import subprocess
from pathlib import Path
import time
import uvicorn

# --- Configuration des chemins ---
# --- Configuration des chemins ---
SERVER_SCRIPT = "tests/e2e/util_start_servers.py"
ENVIRONMENT_MANAGER_SCRIPT = "project_core/core_from_scripts/environment_manager.py"
SERVER_READY_SENTINEL = "SERVER_READY.tmp"

async def stream_output(stream, prefix):
    """Lit et affiche les lignes d'un flux en temps réel."""
    while True:
        try:
            line = await stream.readline()
            if not line:
                break
            # Force UTF-8 encoding to handle special characters
            decoded_line = line.decode('utf-8', errors='replace').strip()
            print(f"[{prefix}] {decoded_line}")
        except Exception as e:
            print(f"Error in stream_output for {prefix}: {e}")
            break

async def run_pytest_with_timeout(timeout: int, pytest_args: list):
    """
    Exécute pytest en tant que sous-processus avec un timeout strict,
    en utilisant asyncio et conda run.
    """
    # Construire la commande pytest en utilisant le script d'activation centralisé
    # On appelle directement le manager d'environnement Python.
    # C'est la configuration la plus simple.
    raw_pytest_command = f"python -m pytest {' '.join(pytest_args)}"
    command = [
        "python",
        ENVIRONMENT_MANAGER_SCRIPT,
        "--command",
        raw_pytest_command,
    ]

    print(f"--- Lancement de la commande : {' '.join(command)}")
    print(f"--- Timeout réglé à : {timeout} secondes")

    # On exécute depuis la racine, sans changer le CWD.
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
    )

    stdout_task = asyncio.create_task(stream_output(process.stdout, "STDOUT"))
    stderr_task = asyncio.create_task(stream_output(process.stderr, "STDERR"))

    exit_code = -1
    try:
        await asyncio.wait_for(process.wait(), timeout=timeout)
        exit_code = process.returncode
        print(f"\n--- Pytest s'est terminé avec le code de sortie : {exit_code}")

    except asyncio.TimeoutError:
        print(f"\n--- !!! TIMEOUT ATTEINT ({timeout}s) !!!")
        
        try:
            if sys.platform == "win32":
                os.kill(process.pid, subprocess.CTRL_BREAK_EVENT)
            else:
                os.killpg(os.getpgid(process.pid), 15) # signal.SIGTERM
            
            await asyncio.wait_for(process.wait(), timeout=10)
        except (asyncio.TimeoutError, ProcessLookupError):
            process.kill()
            await process.wait()
        
        print("--- Processus pytest terminé.")
        exit_code = -99 # Special exit code for timeout

    finally:
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

    return exit_code

async def main():

    # Nettoyer un éventuel fichier sentinelle précédent
    sentinel_path = Path(SERVER_READY_SENTINEL)
    if sentinel_path.exists():
        sentinel_path.unlink()

    # Pour le serveur, on revient à conda run.
    # La méthode via le script d'activation ne fonctionne pas car environment_manager
    # attend la fin de la commande, ce qui n'arrive jamais pour un serveur.
    # Conda run, lui, lance juste le processus et continue.
    server_command = [
        "conda",
        "run",
        "-n",
        "projet-is",
        "python",
        SERVER_SCRIPT,
    ]
    server_process = await asyncio.create_subprocess_exec(
        *server_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Lancer les tâches pour lire la sortie du serveur
    server_stdout_task = asyncio.create_task(stream_output(server_process.stdout, "SERVER_STDOUT"))
    server_stderr_task = asyncio.create_task(stream_output(server_process.stderr, "SERVER_STDERR"))

    exit_code = 1
    try:
        # Attendre que le serveur soit prêt en sondant le port
        host = "127.0.0.1"
        port = 8000
        print(f"--- En attente du démarrage du serveur sur {host}:{port}...")
        for _ in range(60):  # 60 secondes timeout
            try:
                reader, writer = await asyncio.open_connection(host, port)
                writer.close()
                await writer.wait_closed()
                print(f"--- Serveur détecté sur {host}:{port}. Il est prêt.")
                break
            except ConnectionRefusedError:
                # Vérifier si le processus serveur ne s'est pas terminé prématurément
                if server_process.returncode is not None:
                    print("--- Le processus serveur s'est arrêté de manière inattendue.")
                    if Path("server_startup_error.log").exists():
                        error_log = Path("server_startup_error.log").read_text()
                        print(f"--- Erreur de démarrage du serveur:\n{error_log}")
                        Path("server_startup_error.log").unlink()
                    return 1
                await asyncio.sleep(1)
        else:
            print(f"--- Timeout: Le serveur n'a pas démarré sur {host}:{port} dans le temps imparti.")
            return 1

        # Configurer les arguments pour pytest
        TEST_TIMEOUT = 300 # 5 minutes
        
        # Supprimer l'ancien rapport s'il existe pour éviter la confusion
        report_dir = Path(__file__).parent / "playwright-report"
        if report_dir.exists():
            import shutil
            shutil.rmtree(report_dir)

        # On supprime les arguments HTML qui causent l'erreur.
        # L'objectif est d'abord de faire tourner les tests.
        PYTEST_ARGS = [
            "--output=playwright-report/test-results.zip", # Chemin relatif à la racine
            # "--html=playwright-report/report.html", # Supprimé
            # "--self-contained-html", # Supprimé
            "-v",
            "-s",
            # "--headed", # Supprimé pour le moment pour voir si le test se débloque
            "--backend-url", "http://localhost:8000",
            "--frontend-url", "http://localhost:8000",
            "tests/e2e/python/test_webapp_homepage.py" # On isole un seul test pour le debug
        ]

        # Lancer pytest
        exit_code = await run_pytest_with_timeout(TEST_TIMEOUT, PYTEST_ARGS)

    finally:
        # Assurer l'arrêt propre du serveur et le nettoyage
        print("--- Arrêt du processus serveur...")
        if server_process.returncode is None:
            server_process.terminate()
            try:
                await asyncio.wait_for(server_process.wait(), timeout=10)
            except asyncio.TimeoutError:
                server_process.kill()
                await server_process.wait()

        # Attendre que les tâches de streaming se terminent
        await asyncio.gather(server_stdout_task, server_stderr_task, return_exceptions=True)

        if Path("server_startup_error.log").exists():
            Path("server_startup_error.log").unlink()
        if sentinel_path.exists():
            sentinel_path.unlink()

        print(f"--- Processus serveur terminé avec le code {server_process.returncode}.")

    return exit_code

if __name__ == "__main__":
    # La ligne os.environ['E2E_TEST_RUNNING'] = 'true' est supprimée.
    # Nous voulons que la vérification de l'environnement dans auto_env.py s'exécute normalement,
    # car le script d'activation est censé le configurer correctement.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    os.chdir(Path(__file__).parent)
    
    exit_code = asyncio.run(main())
    
    print(f"Script terminé avec le code de sortie : {exit_code}")
    sys.exit(exit_code)