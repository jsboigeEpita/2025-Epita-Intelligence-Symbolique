import subprocess
import os
import tempfile
from pathlib import Path

PROVER9_BIN_DIR = Path(__file__).parent.parent.parent / "libs" / "prover9" / "bin"
PROVER9_EXECUTABLE = PROVER9_BIN_DIR / "prover9.bat"

import logging
logger = logging.getLogger(__name__)

def run_prover9(input_content: str) -> str:
    """
    Exécute Prover9 dans un processus externe avec le contenu d'entrée fourni.
    Utilise désormais un fichier temporaire pour passer l'entrée, conformément
    au fonctionnement du wrapper prover9.bat.

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

    temp_input_path = None
    try:
        # Créer un fichier temporaire pour l'entrée
        with tempfile.NamedTemporaryFile(
            mode='w+',
            delete=False,
            suffix=".in",
            encoding='ascii',
            newline='\n'
        ) as temp_input_file:
            temp_input_file.write(input_content)
            temp_input_path = temp_input_file.name

        # --- DEBUG LOGS ---
        logger.info(f"--- Prover9 Debug ---")
        logger.info(f"Input file created at: {temp_input_path}")
        logger.info(f"Input content:\n---\n{input_content}\n---")
        
        command = [str(PROVER9_EXECUTABLE), "-f", temp_input_path]
        logger.info(f"Executing command: {' '.join(command)}")
        logger.info(f"Working directory: {str(PROVER9_BIN_DIR)}")
        # --- END DEBUG LOGS ---

        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Set to False to handle errors manually
            cwd=str(PROVER9_BIN_DIR)
        )

        # --- DEBUG LOGS ---
        logger.info(f"Prover9 stdout:\n---\n{process.stdout}\n---")
        if process.stderr:
            logger.warning(f"Prover9 stderr:\n---\n{process.stderr}\n---")
        # --- END DEBUG LOGS ---

        if process.returncode != 0:
            error_message = f"Prover9 failed with exit code {process.returncode}.\n"
            error_message += f"Input was in file: {temp_input_path}\n"
            error_message += f"Stderr:\n{process.stderr}"
            logger.error(error_message)
            # We don't raise an exception here to see the test failure itself
            # raise subprocess.CalledProcessError(process.returncode, command, output=process.stdout, stderr=error_message)

        return process.stdout
    except Exception as e:
        logger.error(f"An unexpected error occurred in run_prover9: {e}", exc_info=True)
        raise
    finally:
        # Keep the temp file for inspection by commenting this out
        # if temp_input_path and os.path.exists(temp_input_path):
        #     logger.info(f"Temporarily keeping Prover9 input file for inspection: {temp_input_path}")
        #     # os.remove(temp_input_path)
        pass
