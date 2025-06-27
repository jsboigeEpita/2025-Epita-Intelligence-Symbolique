import argparse
import sys
import os

# Assurez-vous que le répertoire racine du projet est dans le sys.path
# pour que les imports depuis project_core fonctionnent.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

from project_core.core_from_scripts.environment_manager import EnvironmentManager

def fix_deps_command(args):
    """
    Fonction pour gérer la commande fix-deps.
    """
    if not args.package:
        print("Erreur : La commande fix-deps nécessite au moins un paquet.", file=sys.stderr)
        sys.exit(1)
    
    print(f"Lancement de la réparation des dépendances pour les paquets : {', '.join(args.package)}")
    try:
        manager = EnvironmentManager()
        manager.fix_dependencies(args.package)
        print("Réparation des dépendances terminée avec succès.")
    except Exception as e:
        print(f"Une erreur est survenue lors de la réparation des dépendances : {e}", file=sys.stderr)
        sys.exit(1)

def main():
    """
    Fonction principale pour l'analyse des arguments de la ligne de commande.
    """
    parser = argparse.ArgumentParser(description="Gestionnaire de configuration de l'environnement.")
    subparsers = parser.add_subparsers(dest='command', help='Commandes disponibles')

    # Création du parser pour la commande "fix-deps"
    fix_deps_parser = subparsers.add_parser('fix-deps', help='Répare les dépendances pour un ou plusieurs paquets.')
    fix_deps_parser.add_argument(
        '--package',
        nargs='+',
        required=True,
        help='Un ou plusieurs noms de paquets à réparer.'
    )
    fix_deps_parser.set_defaults(func=fix_deps_command)

    args = parser.parse_args()

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()