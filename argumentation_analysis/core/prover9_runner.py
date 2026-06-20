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
        La sortie de Prover9 (stdout), whether or not a proof was found. A
        non-zero exit code is SEMANTIC (exit 2 = "SEARCH FAILED" on a consistent
        KB) and is NOT treated as an error — the caller inspects the stdout
        markers ("THEOREM PROVED" vs "SEARCH FAILED") to decide.

    Raises:
        FileNotFoundError: Si l'exécutable de Prover9 n'est pas trouvé.
        RuntimeError: Si Prover9 signale une erreur fatale (input mal formé).
    """
    if not PROVER9_EXECUTABLE.is_file():
        raise FileNotFoundError(f"Prover9 executable not found at {PROVER9_EXECUTABLE}")

    try:
        # Créer un fichier temporaire pour l'entrée
        # Créer un fichier temporaire en ASCII avec des fins de ligne Unix (\n) pour Prover9
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".in", encoding="ascii", newline="\n"
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
            cwd=str(PROVER9_BIN_DIR),
            encoding="cp1252",
            shell=True,
        )
        # FP-8 verify-the-verification: Prover9's exit code is SEMANTIC, not a
        # success/failure signal. Exit 2 with "SEARCH FAILED" is the NORMAL
        # outcome for a consistency check on a CONSISTENT KB (no proof of $F
        # found) — using ``check=True`` made the runner raise on exactly the
        # case the caller wants, so a consistent KB could never be reported.
        # Only a *parser* failure is a real error: it carries the "Fatal error"
        # marker in stdout and must be surfaced (anti-théâtre #1019: a malformed
        # input must not masquerade as a consistency verdict). Everything else
        # (proof found / search failed) is returned to the caller, which
        # interprets the proof markers.
        stdout = process.stdout
        if "Fatal error" in stdout:
            raise RuntimeError(
                "Prover9 reported a fatal error (likely malformed input):\n"
                f"{stdout}"
            )
        return stdout
    finally:
        # S'assurer que le fichier temporaire est supprimé
        if "temp_input_path" in locals() and os.path.exists(temp_input_path):
            os.remove(temp_input_path)
