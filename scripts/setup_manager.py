import argparse
import sys
from pathlib import Path

# Ajouter la racine du projet au sys.path pour permettre les imports absolus
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from project_core.core_from_scripts.environment_manager import EnvironmentManager
from project_core.core_from_scripts.project_setup import ProjectSetup
from project_core.core_from_scripts.validation_engine import ValidationEngine

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
    fix_deps_parser.add_argument(
        "--strategy",
        choices=['default', 'aggressive'],
        default='default',
        help="Stratégie de réparation à utiliser (default: simple réinstallation, aggressive: essaie plusieurs méthodes)."
    )

    # --- Commande pour configurer le PYTHONPATH via un fichier .pth ---
    set_path_parser = subparsers.add_parser(
        "set-path",
        help="Configure le PYTHONPATH en créant un .pth dans site-packages."
    )

    # --- Commande pour valider les composants ---
    validate_parser = subparsers.add_parser(
        "validate",
        help="Valide differents composants de l'environnement."
    )
    validate_parser.add_argument(
        "--component",
        choices=['jvm-bridge', 'build-tools'],
        required=True,
        help="Le composant a valider."
    )

    # --- Commande pour installer le projet ---
    install_parser = subparsers.add_parser(
        "install-project",
        help="Orchestre une installation complète et propre du projet."
    )
    install_parser.add_argument(
        "--requirements",
        default="requirements.txt",
        metavar="FILE_PATH",
        help="Chemin vers le fichier requirements.txt principal (défaut: requirements.txt)."
    )

    # --- Commande pour configurer l'environnement de test ---
    setup_test_env_parser = subparsers.add_parser(
        "setup-test-env",
        help="Prépare l'environnement pour l'exécution des tests."
    )
    setup_test_env_parser.add_argument(
        "--with-mocks",
        action="store_true",
        help="Active les mocks pour les dépendances comme JPype."
    )

    args = parser.parse_args()

    env_manager = EnvironmentManager()
    validation_engine = ValidationEngine()
    exit_code = 0

    if args.command == "fix-deps":
        if args.package:
            print(f"Tentative de réparation des paquets : {', '.join(args.package)} avec la stratégie '{args.strategy}'")
            if not env_manager.fix_dependencies(packages=args.package, strategy=args.strategy):
                print("La réparation des dépendances par paquet a échoué.", file=sys.stderr)
                exit_code = 1
            else:
                print("Réparation des dépendances par paquet terminée avec succès.")
        elif args.from_requirements:
            print(f"Tentative de réparation depuis le fichier : {args.from_requirements}")
            if not env_manager.fix_dependencies(requirements_file=args.from_requirements, strategy=args.strategy):
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

    elif args.command == "validate":
        print(f"Validation du composant : {args.component}...")
        if args.component == 'build-tools':
            result = validation_engine.validate_build_tools()
            print(result['message'])
            if result['status'] == 'failure':
                exit_code = 1
        elif args.component == 'jvm-bridge':
            result = validation_engine.validate_jvm_bridge()
            print(result['message'])
            if result['status'] == 'failure':
                exit_code = 1

    elif args.command == "install-project":
        print("Lancement de l'installation complète du projet...")
        setup_manager = ProjectSetup()
        if not setup_manager.install_project(requirements_file=args.requirements):
            print("L'installation du projet a échoué.", file=sys.stderr)
            exit_code = 1
        else:
            print("Installation du projet terminée avec succès.")

    elif args.command == "setup-test-env":
        print("Préparation de l'environnement de test...")
        setup_manager = ProjectSetup()
        if not setup_manager.setup_test_environment(with_mocks=args.with_mocks):
            print("La préparation de l'environnement de test a échoué.", file=sys.stderr)
            exit_code = 1
        else:
            print("Préparation de l'environnement de test terminée avec succès.")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()