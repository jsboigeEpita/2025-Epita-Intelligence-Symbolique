# examples/cluedo_demo/demo_cluedo_workflow.py
import asyncio
import os
from dotenv import load_dotenv

import logging
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.orchestration.cluedo_orchestrator import run_cluedo_game
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging

async def main():
    """Point d'entrée pour exécuter le script de manière autonome."""
    setup_logging()
    load_dotenv()

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_CHAT_MODEL_ID = os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini")

    if not OPENAI_API_KEY:
        print("Erreur: La variable d'environnement OPENAI_API_KEY n'est pas définie.")
        return

    kernel = Kernel()
    kernel.add_service(
        OpenAIChatCompletion(
            service_id="default",
            api_key=OPENAI_API_KEY,
            ai_model_id=OPENAI_CHAT_MODEL_ID
        )
    )

    initial_question = "L'enquête commence. Sherlock, à vous de jouer. Qui a commis le meurtre, avec quelle arme et dans quel lieu ?"
    final_history, final_state = await run_cluedo_game(kernel, initial_question)
    
    print("\n--- Historique Final de la partie de Cluedo ---")
    for entry in final_history:
        # S'assurer que 'entry' est bien un dictionnaire avant d'accéder aux clés
        if isinstance(entry, dict):
            sender = entry.get('sender', 'N/A')
            message = entry.get('message', '')
            print(f"  {sender}: {message}")
    print("--- Fin de la partie ---")

    print("\n--- État Final de l'Enquête ---")
    print(f"Solution proposée: {final_state.final_solution}")
    print(f"Solution correcte: {final_state.solution_secrete_cluedo}")
    print("\nHypothèses:")
    if final_state.hypotheses_enquete:
        for hypo in final_state.hypotheses_enquete:
            print(f"  - {hypo.get('text')} (Confiance: {hypo.get('confidence_score')}, Statut: {hypo.get('status')})")
    else:
        print("  Aucune hypothèse enregistrée.")
    print("\nTâches:")
    if final_state.tasks:
        for task in final_state.tasks.values():
            print(f"  - ID: {task.get('id', 'N/A')}, Description: {task.get('description', '')}, Assigné à: {task.get('assignee', 'N/A')}, Statut: {task.get('status', 'N/A')}")
    else:
        print("  Aucune tâche enregistrée.")
    print("--- Fin de l'État ---")


if __name__ == "__main__":
    try:
        print("Lancement de la démonstration du workflow Cluedo...")
        asyncio.run(main())
        print("Démonstration terminée.")
    except Exception as e:
        print(f"Une erreur est survenue lors de la démonstration: {e}")
        import traceback
        traceback.print_exc()