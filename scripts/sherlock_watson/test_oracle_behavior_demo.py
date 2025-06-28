import sys
from argumentation_analysis.core.bootstrap import initialize_project_environment
from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
from argumentation_analysis.core.bootstrap import initialize_project_environment
import asyncio

async def run_demo():
    print("--- Début de la démo du comportement de l'oracle ---")
    # Forcer l'utilisation du LLM mocké est crucial pour les tests
    project_context = initialize_project_environment(force_mock_llm=True)
    agent = SherlockJTMSAgent(kernel=project_context.kernel)
    # Remplacer l'appel obsolète par l'appel à une méthode principale comme analyze_clues
    clues = [
        {'type': 'arme', 'description': 'Couteau ensanglanté trouvé dans la cuisine.', 'reliability': 0.9},
        {'type': 'témoignage', 'description': 'Un cri a été entendu vers 22h.', 'reliability': 0.6}
    ]
    analysis_result = await agent.analyze_clues(clues)
    if isinstance(analysis_result, dict) and 'error' in analysis_result:
        print(f"---AGENT_ERROR_START---")
        print(f"L'agent a retourné une erreur contrôlée: {analysis_result['error']}")
        print(f"---AGENT_ERROR_END---")
    else:
        print(f"Résultat de l'analyse des indices: {analysis_result}")
    print("--- Fin de la démo de l'oracle ---")



if __name__ == "__main__":
    # Gestion de la boucle d'événements pour exécution autonome ou via un runner
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if loop.is_running():
        loop.create_task(run_demo())
    else:
        loop.run_until_complete(run_demo())