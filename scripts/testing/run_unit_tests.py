import pytest
import sys
import subprocess

if __name__ == "__main__":
    # La redirection de la sortie de pytest est complexe car il modifie les flux sys.stdout/sys.stderr.
    # L'approche la plus robuste est de lancer pytest dans un sous-processus
    # et de capturer sa sortie.

    command = [sys.executable, "-m", "pytest", "-v", "tests/unit/"]

    try:
        # On utilise subprocess.run pour exécuter la commande et attendre sa complétion.
        # stdout et stderr sont redirigés vers un fichier log.
        with open("unit_test_output.log", "w", encoding="utf-8") as f:
            result = subprocess.run(
                command,
                stdout=f,
                stderr=subprocess.STDOUT,
                check=False,  # On ne lève pas d'exception si le code de sortie est non-nul
                text=True,
                encoding="utf-8",
            )

        # On propage le code de sortie de pytest
        sys.exit(result.returncode)

    except Exception as e:
        print(f"Une erreur est survenue lors du lancement de pytest : {e}")
        sys.exit(1)
