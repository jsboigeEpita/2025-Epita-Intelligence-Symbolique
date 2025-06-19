import asyncio
import sys
import os
import subprocess
from pathlib import Path
import time

async def stream_output(stream, prefix):
    """Lit et affiche les lignes d'un flux en temps réel."""
    while True:
        try:
            line = await stream.readline()
            if not line:
                break
            decoded_line = line.decode('utf-8', errors='replace').strip()
            print(f"[{prefix}] {decoded_line}")
        except Exception as e:
            print(f"Error in stream_output for {prefix}: {e}")
            break

async def run_pytest_with_timeout(timeout: int, pytest_args: list):
    """
    Exécute pytest en tant que sous-processus avec un timeout strict,
    en utilisant asyncio.
    """
    command = [sys.executable, "-m", "pytest"] + pytest_args

    print(f"--- Lancement de la commande : {' '.join(command)}")
    print(f"--- Timeout réglé à : {timeout} secondes")

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

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    os.chdir(Path(__file__).parent)
    
    TEST_TIMEOUT = 300 # 5 minutes
    PYTEST_ARGS = ["-v", "-s", "--headed", "tests/e2e/python/test_webapp_homepage.py"]

    exit_code = asyncio.run(run_pytest_with_timeout(TEST_TIMEOUT, PYTEST_ARGS))
    
    print(f"Script terminé avec le code de sortie : {exit_code}")
    sys.exit(exit_code)