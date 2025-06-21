import subprocess
import sys
import os
from pathlib import Path

def main():
    """
    Lance les tests E2E avec pytest en utilisant subprocess.run pour
    fournir un timeout robuste qui peut tuer le processus si nécessaire.
    """
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    test_path = "tests/e2e/python/test_webapp_homepage.py"
    timeout_seconds = 300

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "-s",
        "--backend-url", "http://localhost:8000",
        "--frontend-url", "http://localhost:8000",
        test_path
    ]

    print(f"--- Lancement de la commande : {' '.join(command)}")
    print(f"--- Timeout réglé à : {timeout_seconds} secondes")

    try:
        result = subprocess.run(
            command,
            timeout=timeout_seconds,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

        print("--- STDOUT ---")
        print(result.stdout)
        print("--- STDERR ---")
        print(result.stderr)
        
        exit_code = result.returncode
        print(f"\n--- Pytest terminé avec le code de sortie : {exit_code}")

    except subprocess.TimeoutExpired as e:
        print(f"\n--- !!! TIMEOUT ATTEINT ({timeout_seconds}s) !!!")
        print("--- Le processus de test a été tué.")
        
        print("--- STDOUT (partiel) ---")
        print(e.stdout)
        print("--- STDERR (partiel) ---")
        print(e.stderr)

        exit_code = -99 # Code de sortie spécial pour le timeout

    sys.exit(exit_code)

if __name__ == "__main__":
    main()