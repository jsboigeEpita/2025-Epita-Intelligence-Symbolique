import subprocess
import sys
import os

def run_tests():
    """
    Lance les tests pytest dans un sous-processus pour isoler l'environnement.
    """
    try:
        # Assurer que l'environnement est correctement configuré si nécessaire
        env = os.environ.copy()
        
        # Commande pour exécuter pytest
        command = [
            sys.executable,  # Utilise le même interpréteur python
            "-m",
            "pytest",
            "tests/e2e/python/"
        ]

        print(f"Executing command: {' '.join(command)}")

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )

        stdout, stderr = process.communicate()

        print("--- STDOUT ---")
        print(stdout)
        print("--- STDERR ---")
        print(stderr)

        return process.returncode

    except Exception as e:
        print(f"An error occurred: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)