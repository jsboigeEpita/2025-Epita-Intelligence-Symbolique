import argparse
from project_core.environment.orchestrator import EnvironmentOrchestrator

def main():
    """
    Point d'entrée principal pour lancer l'orchestrateur d'environnement.
    """
    parser = argparse.ArgumentParser(
        description="Lanceur pour l'orchestrateur d'environnement."
    )
    parser.add_argument(
        '--tools',
        nargs='*',
        default=[],
        help="Liste des outils à installer ou à vérifier (ex: jdk, octave)."
    )
    parser.add_argument(
        '--requirements',
        nargs='*',
        default=[],
        help="Liste des fichiers de dépendances pip à traiter (ex: requirements.txt)."
    )
    # Ajoutez ici d'autres arguments si nécessaire pour EnvironmentOrchestrator.setup_environment

    args = parser.parse_args()

    orchestrator = EnvironmentOrchestrator()
    
    # Assurez-vous que la méthode setup_environment accepte ces arguments
    # ou adaptez les noms/la structure des arguments passés.
    orchestrator.setup_environment(
        tools_to_setup=args.tools,
        requirements_files=args.requirements
        # Passez d'autres arguments parsés ici si nécessaire
    )

if __name__ == "__main__":
    main()