import asyncio
from typing import List, Dict, Any, Optional

import semantic_kernel as sk
from semantic_kernel.kernel import Kernel
from semantic_kernel.agents import Agent
from semantic_kernel.agents.group_chat.agent_group_chat import AgentGroupChat
from semantic_kernel.agents.strategies.selection.sequential_selection_strategy import SequentialSelectionStrategy
from semantic_kernel.agents.strategies.termination.termination_strategy import TerminationStrategy
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from pydantic import Field
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.filters.functions.function_invocation_context import FunctionInvocationContext
from semantic_kernel.filters.filter_types import FilterTypes


class CluedoTerminationStrategy(TerminationStrategy):
    """Stratégie de terminaison personnalisée pour le Cluedo."""
    max_total_messages: int = Field(default=20) # Augmentation pour laisser plus de place à la conversation
    is_solution_proposed: bool = Field(default=False, exclude=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def should_terminate(self, agent: Agent, history: List[ChatMessageContent]) -> bool:
        if len(history) >= self.max_total_messages:
            return True

        if not history:
            return False

        last_message = history[-1]
        
        # Vérifier si la solution a été proposée via l'état du plugin
        # C'est une approche plus robuste que de parser le message.
        # Accéder au plugin par son nom via la collection de plugins du kernel de l'agent.
        if agent.kernel.plugins.get("EnqueteStatePlugin"):
            enquete_state_plugin = agent.kernel.plugins["EnqueteStatePlugin"]
            if hasattr(enquete_state_plugin, "_state") and enquete_state_plugin._state.is_solution_proposed:
                self.is_solution_proposed = True
                return True

        # Garder une vérification sur le contenu du message comme fallback
        last_message_content = str(last_message.content).lower()
        sherlock_conclusion_keywords = ["conclusion finale:", "l'affaire est résolue", "le coupable est"]
        if last_message.name == "Sherlock" and any(keyword in last_message_content for keyword in sherlock_conclusion_keywords):
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
    max_messages: Optional[int] = 15
) -> (List[Dict[str, Any]], EnqueteCluedoState):
    """Exécute une partie de Cluedo avec des agents et retourne l'historique et l'état final."""
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

    # Ajout du filtre de journalisation
    kernel.add_filter(FilterTypes.FUNCTION_INVOCATION, logging_filter)

    # Préparer les constantes pour l'agent logique
    elements = enquete_state.elements_jeu_cluedo
    all_constants = [
        name.replace(" ", "") for name in elements.get("suspects", [])
    ] + [
        name.replace(" ", "") for name in elements.get("armes", [])
    ] + [
        name.replace(" ", "") for name in elements.get("lieux", [])
    ]

    sherlock = SherlockEnqueteAgent(kernel=kernel, agent_name="Sherlock")
    watson = WatsonLogicAssistant(kernel=kernel, agent_name="Watson", constants=all_constants)

    termination_strategy = CluedoTerminationStrategy(
        max_total_messages=max_messages,
        termination_keywords=["en effet", "c'est une excellente déduction", "cela semble correct"]
    )

    group_chat = AgentGroupChat(
        agents=[sherlock, watson],
        selection_strategy=SequentialSelectionStrategy(),
        termination_strategy=termination_strategy,
    )

    initial_message = ChatMessageContent(role="user", content=initial_question, name="System")
    
    # N'ajoutez le message système à l'historique que s'il est destiné à être conservé.
    # Pour le test fonctionnel, nous voulons un historique propre des échanges d'agents.
    # history.append(initial_message)
    
    await group_chat.add_chat_message(message=initial_message)

    # La boucle invoke va maintenant s'arrêter en fonction de max_messages
    async for message in group_chat.invoke():
        history.append(message)

    # L'appel final à Sherlock est supprimé. La conclusion doit émerger de la conversation.

    # Retourne uniquement les messages des agents, en excluant le message système initial
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