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
    final_history = await run_cluedo_game(kernel, initial_question)
    
    print("\n--- Historique Final de la partie de Cluedo ---")
    for entry in final_history:
        print(f"  {entry['sender']}: {entry['message']}")
    print("--- Fin de la partie ---")


if __name__ == "__main__":
    try:
        print("Lancement de la démonstration du workflow Cluedo...")
        asyncio.run(main())
        print("Démonstration terminée.")
    except Exception as e:
        print(f"Une erreur est survenue lors de la démonstration: {e}")
        import traceback
        traceback.print_exc()