import asyncio
from argumentation_analysis.core.bootstrap import initialize_project_environment
from argumentation_analysis.orchestration.logique_complexe_orchestrator import LogiqueComplexeOrchestrator

def main():
    print("Initialisation de l'environnement pour le puzzle d'Einstein...")
    project_context = initialize_project_environment()
    orchestrator = LogiqueComplexeOrchestrator(project_context)
    print("Lancement de la résolution du puzzle...")
    result = asyncio.run(orchestrator.run_einstein_puzzle(puzzle_data={'test_mode': True, 'max_hints': 2}))
    success = result.get('success', False)
    print(f"Résultat du puzzle Einstein (succès: {success}): {result}")
    if not success:
        print(f"ERREUR: {result.get('details')}")
        exit(1)

if __name__ == "__main__":
    main()