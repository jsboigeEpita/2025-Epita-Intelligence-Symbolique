# -*- coding: utf-8 -*-
"""
Module centralisé pour exécuter des commandes dans l'environnement Conda du projet.

Ce script est conçu pour être appelé par des wrappers shell (PowerShell, Bash)
et contient toute la logique de détection de l'environnement et d'exécution,
le rendant ainsi multiplateforme.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

def load_dotenv(project_root: Path):
    """
    Charge les variables d'environnement depuis le fichier .env à la racine du projet.
    """
    dotenv_path = project_root / ".env"
    if not dotenv_path.is_file():
        print("Fichier .env non trouvé.", file=sys.stderr)
        return

    print(f"Chargement des variables depuis : {dotenv_path}", file=sys.stderr)
    try:
        with dotenv_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                # Nettoyer les guillemets optionnels
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                else:
                    value = value.strip()
                
                # Ne pas écraser les variables existantes
                if key not in os.environ:
                    os.environ[key] = value

    except Exception as e:
        print(f"Erreur lors du chargement du fichier .env: {e}", file=sys.stderr)


def get_conda_env_name(project_root: Path) -> str:
    """
    Détecte le nom de l'environnement Conda à partir du fichier de configuration.

    Retourne le nom de l'environnement ou une valeur par défaut.
    """
    import re

    config_path = project_root / "argumentation_analysis" / "config" / "environment_config.py"
    default_env_name = "projet-is"

    if not config_path.is_file():
        print(f"Fichier de configuration non trouvé : {config_path}", file=sys.stderr)
        return default_env_name

    try:
        content = config_path.read_text(encoding="utf-8")
        match = re.search(r"""^CONDA_ENV_NAME\s*=\s*["']([^"']+)["']""", content, re.MULTILINE)
        if match:
            env_name = match.group(1)
            print(f"Nom de l'environnement trouvé dans la config : {env_name}", file=sys.stderr)
            return env_name
    except Exception as e:
        print(f"Erreur en lisant le fichier de configuration : {e}", file=sys.stderr)

    return default_env_name

def find_conda_env_path(env_name: str) -> Path:
    """
    Trouve le chemin complet de l'environnement Conda spécifié.
    Lève une FileNotFoundError si l'environnement n'est pas trouvé.
    """
    try:
        # Capture stdout et stderr pour un meilleur diagnostic
        result = subprocess.run(
            ["conda", "info", "--envs"],
            capture_output=True,
            text=True,
            check=False,  # On ne veut pas que ça lève une exception ici, on la gère nous-mêmes
            encoding='utf-8'
        )
        
        # Gestion manuelle de l'erreur pour un message plus clair
        if result.returncode != 0:
            print("--- ERREUR SUBPROCESS ---", file=sys.stderr)
            print(f"La commande 'conda info --envs' a échoué avec le code {result.returncode}.", file=sys.stderr)
            print("STDOUT:", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            print("STDERR:", file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            print("-------------------------", file=sys.stderr)
            raise FileNotFoundError("Impossible d'exécuter 'conda info --envs'. Assurez-vous que Conda est installé et accessible dans le PATH.")

    except FileNotFoundError:
        print("ERREUR CRITIQUE: La commande 'conda' n'est pas trouvée. Assurez-vous que Conda est installé et que son chemin est dans le PATH de l'environnement qui exécute ce script.", file=sys.stderr)
        raise

    for line in result.stdout.splitlines():
        if line.startswith("#"):
            continue
        parts = line.split()
        if not parts:
            continue
        
        name = parts[0]
        path_str = parts[-1]

        if name == env_name:
            env_path = Path(path_str)
            if env_path.exists():
                print(f"Chemin de l'environnement '{env_name}' trouvé : {env_path}", file=sys.stderr)
                return env_path
    
    raise FileNotFoundError(f"L'environnement Conda '{env_name}' n'a pas été trouvé.")

def find_executable_in_env(env_path: Path, executable_name: str) -> Path:
    """
    Trouve un exécutable (comme python, pytest) dans l'environnement Conda.
    Gère les différences d'OS pour les chemins (bin/ vs Scripts/).
    """
    if sys.platform == "win32":
        # Sur Windows, les exécutables sont dans Scripts et ont souvent .exe
        bin_dir = env_path / "Scripts"
        exe_path = bin_dir / f"{executable_name}.exe"
        if exe_path.is_file():
            return exe_path
        # Fallback pour les commandes qui ne sont pas des .exe
        exe_path = bin_dir / executable_name
        if exe_path.is_file():
            return exe_path
    else:
        # Sur Linux/macOS, les exécutables sont dans bin/
        bin_dir = env_path / "bin"
        exe_path = bin_dir / executable_name
        if exe_path.is_file():
            return exe_path

    # Si on cherche "python" et qu'on ne l'a pas trouvé avec une extension,
    # on vérifie le nom de base.
    if executable_name == "python" and sys.platform == "win32":
        python_path = env_path / "python.exe"
        if python_path.is_file():
            return python_path
    elif executable_name == "python":
        python_path = env_path / "python"
        if python_path.is_file():
            return python_path

    raise FileNotFoundError(f"L'exécutable '{executable_name}' n'a pas été trouvé dans '{bin_dir}'.")

def main():
    """
    Point d'entrée principal du script.
    """
    parser = argparse.ArgumentParser(
        description="Exécute une commande dans l'environnement Conda du projet.",
        # Utilisons REMAINDER pour capturer toute la commande.
        # Le parsing s'arrête à la première option non reconnue.
    )
    parser.add_argument(
        "command_args",
        nargs=argparse.REMAINDER,
        help="La commande à exécuter et ses arguments (ex: pytest --version)."
    )

    args = parser.parse_args()

    if not args.command_args:
        print("Erreur: Aucune commande spécifiée.", file=sys.stderr)
        sys.exit(1)

    project_root = Path(__file__).parent.parent.resolve()
    
    try:
        # 1. Charger les variables d'environnement depuis le .env
        load_dotenv(project_root)

        # 2. Obtenir le nom de l'environnement Conda
        conda_env_name = get_conda_env_name(project_root)

        # 3. Trouver le chemin de l'environnement
        conda_env_path = find_conda_env_path(conda_env_name)

        # 4. Préparer l'environnement (PYTHONPATH)
        # Ajoute la racine du projet au début du PYTHONPATH
        python_path = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = f"{project_root}{os.pathsep}{python_path}"
        print(f"PYTHONPATH mis à jour : {os.environ['PYTHONPATH']}", file=sys.stderr)

        # 5. Trouver le chemin de l'exécutable
        executable_name = args.command_args[0]
        executable_path = find_executable_in_env(conda_env_path, executable_name)
        
        # Cas spécial: si la commande est 'python', on s'assure d'utiliser le python de l'env
        # La logique de construction est la même dans les deux cas.
        command_to_run = [str(executable_path)] + args.command_args[1:]

        # 6. Exécuter la commande
        print(f"Exécution de la commande : {' '.join(map(str, command_to_run))}", file=sys.stderr)
        
        if not command_to_run:
            print("Erreur: La commande à exécuter est vide.", file=sys.stderr)
            sys.exit(1)

        result = subprocess.run(command_to_run, check=False)

        # Propager le code de sortie
        sys.exit(result.returncode)

    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"ERREUR CRITIQUE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Une erreur inattendue est survenue: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()