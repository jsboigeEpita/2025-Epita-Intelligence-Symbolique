import subprocess
import os
from pathlib import Path

PROVER9_BIN_DIR = Path(__file__).parent.parent.parent / "libs" / "prover9" / "bin"
PROVER9_EXECUTABLE = PROVER9_BIN_DIR / "prover9.bat"

def run_prover9(input_content: str) -> str:
    """
    Exécute Prover9 dans un processus externe avec le contenu d'entrée fourni.

    Args:
        input_content: Une chaîne de caractères contenant la logique à envoyer à Prover9.

    Returns:
        La sortie de Prover9.

    Raises:
        FileNotFoundError: Si l'exécutable de Prover9 n'est pas trouvé.
        subprocess.CalledProcessError: Si Prover9 retourne un code d'erreur.
    """
    if not PROVER9_EXECUTABLE.is_file():
        raise FileNotFoundError(f"Prover9 executable not found at {PROVER9_EXECUTABLE}")

    command = [str(PROVER9_EXECUTABLE)]

    try:
        process = subprocess.run(
            command,
            input=input_content,
            capture_output=True,
            text=True,
            check=True,
            cwd=str(PROVER9_BIN_DIR)
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        error_message = f"Prover9 failed with exit code {e.returncode}.\n"
        error_message += f"Stderr:\n{e.stderr}"
        raise subprocess.CalledProcessError(e.returncode, e.cmd, output=e.stdout, stderr=error_message)
