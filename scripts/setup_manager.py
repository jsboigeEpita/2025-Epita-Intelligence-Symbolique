import argparse
import sys
from pathlib import Path

# Ajouter la racine du projet au sys.path pour permettre les imports absolus
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from project_core.core_from_scripts.environment_manager import EnvironmentManager
from project_core.core_from_scripts.project_setup import ProjectSetup

def main():
    """Point d'entrée principal pour la façade CLI de setup."""
    parser = argparse.ArgumentParser(
        description="Façade CLI pour gérer le setup et la configuration de l'environnement du projet.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles", required=True)

    # --- Commande pour réparer les dépendances ---
    fix_deps_parser = subparsers.add_parser(
        "fix-deps", 
        help="Répare les dépendances Python, soit par paquet, soit depuis un fichier."
    )
    group = fix_deps_parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--package",
        nargs='+',
        metavar='PACKAGE',
        help="Un ou plusieurs paquets à réinstaller de force (ex: numpy pandas)."
    )
    group.add_argument(
        "--from-requirements",
        metavar='FILE_PATH',
        help="Chemin vers le fichier requirements.txt à utiliser pour l'installation."
    )

    # --- Commande pour configurer le PYTHONPATH via un fichier .pth ---
    set_path_parser = subparsers.add_parser(
        "set-path",
        help="Configure le PYTHONPATH en créant un .pth dans site-packages."
    )
    
    args = parser.parse_args()

    env_manager = EnvironmentManager()
    exit_code = 0

    if args.command == "fix-deps":
        if args.package:
            print(f"Tentative de réparation des paquets : {', '.join(args.package)}")
            if not env_manager.fix_dependencies(packages=args.package):
                print("La réparation des dépendances par paquet a échoué.", file=sys.stderr)
                exit_code = 1
            else:
                print("Réparation des dépendances par paquet terminée avec succès.")
        elif args.from_requirements:
            print(f"Tentative de réparation depuis le fichier : {args.from_requirements}")
            if not env_manager.fix_dependencies(requirements_file=args.from_requirements):
                print(f"La réparation depuis le fichier '{args.from_requirements}' a échoué.", file=sys.stderr)
                exit_code = 1
            else:
                print(f"Réparation depuis le fichier '{args.from_requirements}' terminée avec succès.")
    
    elif args.command == "set-path":
        print("Tentative de configuration du fichier .pth pour le PYTHONPATH...")
        setup_manager = ProjectSetup()
        if not setup_manager.set_project_path_file():
            print("La configuration du fichier .pth a échoué.", file=sys.stderr)
            exit_code = 1
        else:
            print("Configuration du fichier .pth terminée avec succès.")


    sys.exit(exit_code)

if __name__ == "__main__":
    main()