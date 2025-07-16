import asyncio
import logging
from typing import List, Dict, Any, Optional

import semantic_kernel as sk
from semantic_kernel.functions import kernel_function
from semantic_kernel.kernel import Kernel
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.functions import KernelArguments
from pydantic import Field

# Configuration du logging en premier
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from .base import Agent, TerminationStrategy
from .cluedo_extended_orchestrator import CyclicSelectionStrategy

from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from argumentation_analysis.agents.factory import AgentFactory


class CluedoTerminationStrategy(TerminationStrategy):
    """Stratégie de terminaison personnalisée pour le Cluedo."""
    max_turns: int = Field(default=10)
    turn_count: int = Field(default=0, exclude=True)
    is_solution_found: bool = Field(default=False, exclude=True)
    enquete_plugin: EnqueteStateManagerPlugin = Field(...)

    async def should_terminate(self, agent: Agent, history: List[ChatMessageContent]) -> bool:
        """Termine si la solution est trouvée ou si le nombre max de tours est atteint."""
        # Un "tour" est défini comme une intervention de Sherlock.
        if agent.name == "Sherlock":
            self.turn_count += 1
            logger.info(f"\n--- TOUR {self.turn_count}/{self.max_turns} ---")

        if self.enquete_plugin and isinstance(self.enquete_plugin._state, EnqueteCluedoState) and self.enquete_plugin._state.is_solution_proposed:
            solution_proposee = self.enquete_plugin._state.final_solution
            solution_correcte = self.enquete_plugin._state.get_solution_secrete()
            if solution_proposee == solution_correcte:
                self.is_solution_found = True
                logger.info("Solution correcte proposée. Terminaison.")
                return True

        if self.turn_count >= self.max_turns:
            logger.info("Nombre maximum de tours atteint. Terminaison.")
            return True
            
        return False


async def logging_filter(context: Any, next):
    """Filtre pour logger les appels de fonction."""
    logger.info(f"[FILTER PRE] Appel de: {context.function.plugin_name}-{context.function.name}")
    logger.info(f"[FILTER PRE] Arguments: {context.arguments}")
    
    await next(context)
    
    logger.info(f"[FILTER POST] Resultat de: {context.function.plugin_name}-{context.function.name}")
    logger.info(f"[FILTER POST] Resultat: {context.result}")

async def run_cluedo_game(
    kernel: Kernel,
    initial_question: str,
    history: List[ChatMessageContent] = None,
    max_turns: Optional[int] = 10
) -> (List[Dict[str, Any]], EnqueteCluedoState):
    """Exécute une partie de Cluedo avec une logique de tours de jeu."""
    if history is None:
        history = []

    enquete_state = EnqueteCluedoState(
        nom_enquete_cluedo="Le Mystère du Manoir Tudor",
        elements_jeu_cluedo={
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
            "armes": ["Poignard", "Chandelier", "Revolver"],
            "lieux": ["Salon", "Cuisine", "Bureau"]
        },
        description_cas="Un meurtre a été commis. Qui, où, et avec quoi ?",
        initial_context="L'enquête débute.",
        auto_generate_solution=True
    )

    plugin = EnqueteStateManagerPlugin(enquete_state)
    kernel.add_plugin(plugin, "EnqueteStatePlugin")
    if hasattr(kernel, 'auto_function_invocation_filters'):
        kernel.auto_function_invocation_filters.append(logging_filter)
    elif hasattr(kernel, 'add_function_invocation_filter'): # Fallback pour les anciennes versions
         kernel.add_function_invocation_filter(logging_filter)

    elements = enquete_state.elements_jeu_cluedo
    all_constants = [name.replace(" ", "") for category in elements.values() for name in category]

    # Récupération du service_id depuis les settings
    from argumentation_analysis.config.settings import settings
    service_id = settings.openai.chat_model_id if settings.openai else "default"

    factory = AgentFactory(kernel, service_id)
    sherlock = factory.create_sherlock_agent(agent_name="Sherlock")
    watson = factory.create_watson_agent(agent_name="Watson")

    termination_strategy = CluedoTerminationStrategy(max_turns=max_turns, enquete_plugin=plugin)
    selection_strategy = CyclicSelectionStrategy(agents=[sherlock, watson])
    
    # Ajout du message initial au chat pour démarrer la conversation
    initial_message = ChatMessageContent(role="user", content=initial_question, name="System")
    history.append(initial_message)

    logger.info("Début de la boucle de jeu...")
    
    current_agent = sherlock # Démarrer avec Sherlock
    while not await termination_strategy.should_terminate(agent=current_agent, history=history):
        current_agent = await selection_strategy.next(agents=[sherlock, watson], history=history)
        
        logger.info(f"--- Tour de {current_agent.name} ---")
        
        response = await current_agent.invoke(history)
        
        message_content = response[0] if isinstance(response, list) and response else ChatMessageContent(role="assistant", content=str(response), name=current_agent.name)

        history.append(message_content)
        logger.info(f"Message de {message_content.name}: {message_content.content}")

    logger.info("Jeu terminé.")
    return [
        {"sender": msg.name, "message": str(msg.content)} for msg in history if msg.name != "System"
    ], enquete_state


async def main():
    """Point d'entrée pour exécuter le script de manière autonome."""
    from argumentation_analysis.config.settings import settings
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

    kernel = Kernel()
    
    if not settings.use_mock_llm and settings.openai.api_key:
        kernel.add_service(
            OpenAIChatCompletion(
                service_id=settings.openai.chat_model_id,
                ai_model_id=settings.openai.chat_model_id,
                api_key=settings.openai.api_key.get_secret_value(),
            )
        )
    else:
        logger.warning("Aucun service LLM configuré ou utilisation de mock activée. L'exécution peut échouer ou être limitée.")


    final_history, final_state = await run_cluedo_game(kernel, "L'enquête commence. Sherlock, à vous.")
    
    print("\n--- Historique Final de la Conversation ---")
    for entry in final_history:
        print(f"  {entry['sender']}: {entry['message']}")
    print("--- Fin de la Conversation ---")

    print("\n--- État Final de l'Enquête ---")
    print(f"Nom de l'enquête: {final_state.nom_enquete_cluedo}")
    print(f"Description: {final_state.description_cas}")
    print(f"Solution proposée: {final_state.final_solution}")
    print(f"Solution correcte: {final_state.solution_secrete_cluedo}")
    print("\nHypothèses:")
    for hypo in final_state.get_hypotheses():
        print(f"  - ID: {hypo['id']}, Text: {hypo['text']}, Confiance: {hypo['confidence_score']}, Statut: {hypo['status']}")
    print("\nTâches:")
    for task in final_state.tasks:
        print(f"  - ID: {task['id']}, Description: {task['description']}, Assigné à: {task['assignee']}, Statut: {task['status']}")
    print("--- Fin de l'État ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
        import traceback
        traceback.print_exc()
