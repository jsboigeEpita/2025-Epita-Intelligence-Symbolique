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

def get_conda_env_name(project_root: Path) -> str:
    """
    Détecte le nom de l'environnement Conda à partir du fichier .env.

    Retourne le nom de l'environnement ou une valeur par défaut.
    """
    try:
        from dotenv import load_dotenv
        dotenv_path = project_root / '.env'
        load_dotenv(dotenv_path=dotenv_path)
    except ImportError:
        print("Warning: python-dotenv not found. Install it with 'pip install python-dotenv' for .env file support.", file=sys.stderr)
    
    default_env_name = "projet-is"
    env_name = os.environ.get("CONDA_ENV_NAME", default_env_name)

    print(f"Nom de l'environnement utilisé : {env_name}", file=sys.stderr)
    return env_name

def find_conda_env_path(env_name: str) -> Path:
    """
    Trouve le chemin complet de l'environnement Conda spécifié.
    Lève une FileNotFoundError si l'environnement n'est pas trouvé.
    """
    try:
        result = subprocess.run(
            ["conda", "info", "--envs"],
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8'
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Erreur lors de l'exécution de 'conda info --envs'. Conda est-il installé et dans le PATH?", file=sys.stderr)
        raise e

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
        # 1. Obtenir le nom de l'environnement Conda
        conda_env_name = get_conda_env_name(project_root)

        # 2. Trouver le chemin de l'environnement
        conda_env_path = find_conda_env_path(conda_env_name)

        # 3. Préparer l'environnement (PYTHONPATH)
        # Ajoute la racine du projet au début du PYTHONPATH
        python_path = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = f"{project_root}{os.pathsep}{python_path}"
        print(f"PYTHONPATH mis à jour : {os.environ['PYTHONPATH']}", file=sys.stderr)

        # 4. Trouver le chemin de l'exécutable
        executable_name = args.command_args[0]
        executable_path = find_executable_in_env(conda_env_path, executable_name)
        
        # Cas spécial: si la commande est 'python', on s'assure d'utiliser le python de l'env
        if executable_name.lower() == 'python':
            command_to_run = [str(executable_path)] + args.command_args[1:]
        else:
            # Pour les autres commandes (pytest, etc.), on utilise leur chemin direct
            command_to_run = [str(executable_path)] + args.command_args[1:]


        # 5. Exécuter la commande
        print(f"Exécution de la commande : {' '.join(command_to_run)}", file=sys.stderr)
        
        #subprocess.run exécute la commande et attend qu'elle se termine.
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