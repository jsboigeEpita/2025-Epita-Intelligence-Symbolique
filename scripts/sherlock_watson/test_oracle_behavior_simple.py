import asyncio
import sys
from argumentation_analysis.core.bootstrap import initialize_project_environment
from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
from argumentation_analysis.core.bootstrap import initialize_project_environment

async def main():
    print("Initialisation simple du test de l'oracle...")
    # Forcer l'utilisation du LLM mocké est crucial pour les tests
    project_context = initialize_project_environment(force_mock_llm=True)
    agent = SherlockJTMSAgent(kernel=project_context.kernel)
    summary = agent.get_investigation_summary()
    print(f"Résumé de l'investigation de l'agent: {summary}")
    # Remplacer l'ancienne méthode par une nouvelle, comme l'ajout d'une évidence
    evidence_data = {
        'type': 'témoignage',
        'description': 'Le colonel Moutarde a été vu près de la scène de crime.',
        'reliability': 0.8
    }
    await agent.update_with_evidence(evidence_data)
    print("Le comportement simple de l'oracle a été validé.")

if __name__ == "__main__":
    # Cette construction permet de lancer le script de manière autonome
    # ou via un exécuteur de tests qui gère déjà une boucle d'événements.
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:  # 'RuntimeError: There is no current event loop...'
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        # Créer une tâche pour éviter de bloquer la boucle existante
        loop.create_task(main())
    else:
        # Lancer une nouvelle boucle si aucune n'est en cours
        loop.run_until_complete(main())