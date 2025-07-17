import subprocess
import os
import tempfile
from pathlib import Path

PROVER9_BIN_DIR = Path(__file__).parent.parent.parent / "libs" / "prover9" / "bin"
PROVER9_EXECUTABLE = PROVER9_BIN_DIR / "prover9.bat"

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

    try:
        # Créer un fichier temporaire pour l'entrée
        # Créer un fichier temporaire en ASCII avec des fins de ligne Unix (\n) pour Prover9
        with tempfile.NamedTemporaryFile(
            mode='w+',
            delete=False,
            suffix=".in",
            encoding='ascii',
            newline='\n'
        ) as temp_input_file:
            temp_input_file.write(input_content)
            temp_input_path = temp_input_file.name

        # La commande inclut maintenant le chemin du fichier d'entrée
        # Normaliser le chemin pour garantir la compatibilité avec Windows
        executable_path = os.path.normpath(os.path.abspath(PROVER9_EXECUTABLE))
        # Forcer les guillemets autour des chemins pour le shell
        executable_path_quoted = f'"{executable_path}"'
        temp_input_path_quoted = f'"{temp_input_path}"'
        command_str = f"{executable_path_quoted} -f {temp_input_path_quoted}"

        process = subprocess.run(
            command_str,
            capture_output=True,
            text=True,
            check=True,
            cwd=str(PROVER9_BIN_DIR),
            encoding='cp1252',
            shell=True
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        error_message = f"Prover9 failed with exit code {e.returncode}.\n"
        error_message += f"Input was:\n{input_content}\n"
        error_message += f"Stderr:\n{e.stderr}"
        raise subprocess.CalledProcessError(e.returncode, e.cmd, output=e.stdout, stderr=error_message)
    finally:
        # S'assurer que le fichier temporaire est supprimé
        if 'temp_input_path' in locals() and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
