import subprocess
import os
import tempfile
from pathlib import Path

PROVER9_BIN_DIR = Path(__file__).parent.parent.parent / "libs" / "prover9" / "bin"
PROVER9_EXECUTABLE = PROVER9_BIN_DIR / "prover9.bat"

def run_prover9(input_content: str) -> str:
    # --- Bloc de débogage pour inspecter l'entrée de Prover9 ---
    import logging
    logger = logging.getLogger(__name__)
    debug_log_path = PROVER9_BIN_DIR / "prover9_input_debug.log"
    try:
        with open(debug_log_path, "w", encoding="utf-8") as f:
            f.write(input_content)
        logger.info(f"Prover9 input content logged to: {debug_log_path}")
    except Exception as e:
        logger.error(f"Failed to write Prover9 debug log: {e}")
    # --- Fin du bloc de débogage ---
    """
    Exécute Prover9 dans un processus externe avec le contenu d'entrée fourni.
    Utilise désormais un fichier temporaire pour passer l'entrée, conformément
    au fonctionnement du wrapper prover9.bat.

    Args:
        input_content: Une chaîne de caractères contenant la logique à envoyer à Prover9.

    Returns:
        La sortie combinée (stdout + stderr) de Prover9.

    Raises:
        FileNotFoundError: Si l'exécutable de Prover9 n'est pas trouvé.
        subprocess.CalledProcessError: Si Prover9 retourne un code d'erreur non nul (sauf pour les cas de succès attendus).
    """
    if not PROVER9_EXECUTABLE.is_file():
        raise FileNotFoundError(f"Prover9 executable not found at {PROVER9_EXECUTABLE}")

    try:
        with tempfile.NamedTemporaryFile(
            mode='w+',
            delete=False,
            suffix=".in",
            encoding='ascii',
            newline='\n'
        ) as temp_input_file:
            temp_input_file.write(input_content)
            temp_input_path = temp_input_file.name

        executable_path = os.path.normpath(os.path.abspath(PROVER9_EXECUTABLE))
        executable_path_quoted = f'"{executable_path}"'
        temp_input_path_quoted = f'"{temp_input_path}"'
        command_str = f"{executable_path_quoted} -f {temp_input_path_quoted}"

        process = subprocess.run(
            command_str,
            capture_output=True,
            text=True,
            cwd=str(PROVER9_BIN_DIR),
            encoding='cp1252',
            shell=True
        )

        logger.debug("Prover9 stdout:\n%s", process.stdout)
        if process.stderr:
            logger.debug("Prover9 stderr:\n%s", process.stderr)

        # Prover9 peut retourner des codes de sortie non nuls même en cas de succès
        # (ex: preuve trouvée, temps écoulé). On ne lève une exception que pour les vraies erreurs.
        # Ici, nous retournons toujours la sortie pour que l'appelant puisse décider.
        return process.stdout + "\n" + process.stderr

    except subprocess.CalledProcessError as e:
        logger.error("Prover9 a échoué avec le code de retour %s", e.returncode, exc_info=True)
        # Renvoyer une exception avec toutes les informations
        e.stderr = e.stderr if e.stderr else ""
        e.stdout = e.stdout if e.stdout else ""
        raise e

    finally:
        if 'temp_input_path' in locals() and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
