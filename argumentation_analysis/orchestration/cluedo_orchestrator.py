import asyncio
import logging
from typing import List, Dict, Any, Optional

import semantic_kernel as sk
from semantic_kernel.functions import kernel_function
from semantic_kernel.kernel import Kernel
# CORRECTIF COMPATIBILITÉ: Utilisation du module de compatibilité pour agents et filters
from argumentation_analysis.utils.semantic_kernel_compatibility import (
    Agent, AgentGroupChat, SequentialSelectionStrategy, TerminationStrategy,
    FunctionInvocationContext, FilterTypes
)
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.functions.kernel_arguments import KernelArguments
from pydantic import Field

# Configuration du logging en premier
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from .base import Agent, TerminationStrategy
from .cluedo_extended_orchestrator import CyclicSelectionStrategy

from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant


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


async def logging_filter(context: FunctionInvocationContext, next):
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
    kernel.add_filter(FilterTypes.FUNCTION_INVOCATION, logging_filter)

    elements = enquete_state.elements_jeu_cluedo
    all_constants = [name.replace(" ", "") for category in elements.values() for name in category]

    sherlock = SherlockEnqueteAgent(kernel=kernel, agent_name="Sherlock")
    watson = WatsonLogicAssistant(kernel=kernel, agent_name="Watson", constants=all_constants)

    termination_strategy = CluedoTerminationStrategy(max_turns=max_turns, enquete_plugin=plugin)
    
    group_chat = AgentGroupChat(
        agents=[sherlock, watson],
        selection_strategy=SequentialSelectionStrategy(),
        termination_strategy=termination_strategy,
    )

    # Ajout du message initial au chat pour démarrer la conversation
    initial_message = ChatMessageContent(role="user", content=initial_question, name="System")
    await group_chat.add_chat_message(message=initial_message)
    history.append(initial_message)

    logger.info("Début de la boucle de jeu gérée par AgentGroupChat.invoke...")
    async for message in group_chat.invoke():
        history.append(message)
        logger.info(f"Message de {message.name}: {message.content}")

    logger.info("Jeu terminé.")
    return [
        {"sender": msg.name, "message": str(msg.content)} for msg in history if msg.name != "System"
    ], enquete_state


async def main():
    """Point d'entrée pour exécuter le script de manière autonome."""
    kernel = Kernel()
    # NOTE: Ajoutez ici la configuration du service LLM (ex: OpenAI, Azure) au kernel.
    # from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    # kernel.add_service(OpenAIChatCompletion(service_id="default", ...))

    final_history, final_state = await run_cluedo_game(kernel, "L'enquête commence. Sherlock, à vous.")
    
    print("\n--- Historique Final de la Conversation ---")
    for entry in final_history:
        print(f"  {entry['sender']}: {entry['message']}")
    print("--- Fin de la Conversation ---")

    print("\n--- État Final de l'Enquête ---")
    print(f"Nom de l'enquête: {final_state.nom_enquete}")
    print(f"Description: {final_state.description_cas}")
    print(f"Solution proposée: {final_state.solution_proposee}")
    print(f"Solution correcte: {final_state.solution_correcte}")
    print("\nHypothèses:")
    for hypo in final_state.hypotheses.values():
        print(f"  - ID: {hypo['id']}, Text: {hypo['text']}, Confiance: {hypo['confidence_score']}, Statut: {hypo['status']}")
    print("\nTâches:")
    for task in final_state.tasks.values():
        print(f"  - ID: {task['id']}, Description: {task['description']}, Assigné à: {task['assignee']}, Statut: {task['status']}")
    print("--- Fin de l'État ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
        import traceback
        traceback.print_exc()
