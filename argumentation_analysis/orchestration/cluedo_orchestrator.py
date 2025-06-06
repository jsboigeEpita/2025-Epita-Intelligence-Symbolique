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

from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant


class CluedoTerminationStrategy(TerminationStrategy):
    """Stratégie de terminaison personnalisée pour le Cluedo."""
    max_total_messages: int = Field(default=10)
    termination_keywords: List[str] = Field(default_factory=list)

    async def should_terminate(self, agents: List[Agent], history: List[ChatMessageContent]) -> bool:
        if len(history) >= self.max_total_messages:
            return True

        if not history:
            return False

        last_message = history[-1]
        last_message_content = str(last_message.content).lower()

        # La boucle s'arrête si le dernier message vient de Watson et contient un mot-clé d'accord.
        if last_message.name == "Watson" and any(keyword.lower() in last_message_content for keyword in self.termination_keywords):
            return True
        
        # Condition de sortie pour la conclusion de Sherlock.
        sherlock_conclusion_keywords = ["l'affaire est résolue", "le coupable est"]
        if last_message.name == "Sherlock" and any(keyword in last_message_content for keyword in sherlock_conclusion_keywords):
            return True

        return False


async def run_cluedo_game(
    kernel: Kernel,
    initial_question: str,
    history: List[ChatMessageContent] = None,
    max_messages: Optional[int] = 15
) -> List[Dict[str, Any]]:
    """Exécute une partie de Cluedo avec des agents et retourne l'historique."""
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

    sherlock = SherlockEnqueteAgent(kernel=kernel, agent_name="Sherlock")
    watson = WatsonLogicAssistant(kernel=kernel, agent_name="Watson")

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

    # Ajout d'un appel final à Sherlock pour la conclusion
    conclusion_prompt = "Sherlock, veuillez résumer vos conclusions."
    # Invoquer directement Sherlock pour la conclusion
    final_responses = []
    async for response in sherlock.invoke(conclusion_prompt):
        final_responses.append(response)
    
    # La méthode invoke d'un agent retourne un générateur asynchrone de ChatMessageContent
    if final_responses:
        history.extend(final_responses)


    # Retourne uniquement les messages des agents, en excluant le message système initial
    return [
        {"sender": msg.name, "message": str(msg.content)} for msg in history if msg.name != "System"
    ]


async def main():
    """Point d'entrée pour exécuter le script de manière autonome."""
    kernel = Kernel()
    # NOTE: Ajoutez ici la configuration du service LLM (ex: OpenAI, Azure) au kernel.
    # from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
    # kernel.add_service(OpenAIChatCompletion(service_id="default", ...))

    final_history = await run_cluedo_game(kernel, "L'enquête commence. Sherlock, à vous.")
    
    print("\n--- Historique Final ---")
    for entry in final_history:
        print(f"  {entry['sender']}: {entry['message']}")
    print("--- Fin ---")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
        import traceback
        traceback.print_exc()