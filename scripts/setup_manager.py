import argparse
import sys
import os

# Assurez-vous que le répertoire racine du projet est dans le sys.path
# pour que les imports depuis project_core fonctionnent.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

from project_core.core_from_scripts.environment_manager import EnvironmentManager
from project_core.core_from_scripts.project_setup import ProjectSetup

def fix_deps_command(args):
    """
    Fonction pour gérer la commande fix-deps.
    """
    if not args.package and not args.from_requirements:
        print("Erreur : La commande fix-deps nécessite l'option --package ou --from-requirements.", file=sys.stderr)
        sys.exit(1)

    try:
        manager = EnvironmentManager()
        if args.from_requirements:
            print(f"Lancement de la réparation des dépendances depuis le fichier : {args.from_requirements}")
            manager.fix_dependencies(requirements_file=args.from_requirements)
        else:
            print(f"Lancement de la réparation des dépendances pour les paquets : {', '.join(args.package)}")
            manager.fix_dependencies(packages=args.package)
        print("Réparation des dépendances terminée avec succès.")
    except ValueError as e:
        print(f"Erreur d'argument : {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Une erreur est survenue lors de la réparation des dépendances : {e}", file=sys.stderr)
        sys.exit(1)

def set_path_command(args):
    """
    Fonction pour gérer la commande set-path.
    """
    print("Configuration du fichier .pth pour le PYTHONPATH...")
    try:
        setup = ProjectSetup()
        if setup.set_project_path_file():
            print("Configuration du PYTHONPATH terminée avec succès.")
        else:
            print("Échec de la configuration du PYTHONPATH.", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Une erreur est survenue lors de la configuration du PYTHONPATH : {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """
    Fonction principale pour l'analyse des arguments de la ligne de commande.
    """
    parser = argparse.ArgumentParser(description="Gestionnaire de configuration de l'environnement.")
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles', required=True)

    # Création du parser pour la commande "fix-deps"
    fix_deps_parser = subparsers.add_parser('fix-deps', help='Répare les dépendances depuis une liste de paquets ou un fichier requirements.')
    group = fix_deps_parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--package',
        nargs='+',
        help='Un ou plusieurs noms de paquets à réparer.'
    )
    group.add_argument(
        '--from-requirements',
        metavar='<file>',
        help='Chemin vers un fichier requirements.txt.'
    )
    fix_deps_parser.set_defaults(func=fix_deps_command)

    # Création du parser pour la commande "set-path"
    set_path_parser = subparsers.add_parser('set-path', help='Configure le PYTHONPATH en créant un fichier .pth.')
    set_path_parser.set_defaults(func=set_path_command)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()