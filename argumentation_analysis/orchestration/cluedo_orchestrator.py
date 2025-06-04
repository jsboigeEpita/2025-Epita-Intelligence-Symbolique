import asyncio
import semantic_kernel as sk
from semantic_kernel.kernel import Kernel

from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant

# Correction du chemin d'import pour AgentGroupChat et les stratégies
from semantic_kernel.experimental.group_chat import (
    AgentGroupChat,
    BalancedParticipationStrategy,
    SimpleTerminationStrategy,
    Agent,
)

# Définition d'une classe wrapper simple pour les agents si nécessaire pour AgentGroupChat
# Si SherlockEnqueteAgent et WatsonLogicAssistant n'héritent pas déjà de Agent ou n'ont pas la bonne interface
# Cette partie pourrait nécessiter un ajustement en fonction de la définition réelle des classes Agent.
# Pour l'instant, on suppose qu'elles sont compatibles ou qu'AgentGroupChat peut les gérer.

async def main():
    # 1. Initialisation du Kernel Semantic Kernel
    kernel = Kernel()

    # TODO: Ajouter la configuration du service LLM au kernel si ce n'est pas déjà géré
    # par les agents eux-mêmes ou globalement.
    # Exemple:
    # from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatCompletion
    # service_id = "default"
    # kernel.add_service(
    #     OpenAIChatCompletion(
    #         service_id=service_id,
    #         ai_model_id="gpt-3.5-turbo",
    #         api_key="YOUR_OPENAI_API_KEY" # Gérer les clés API de manière sécurisée
    #     )
    # )
    # Pour cet exemple, nous supposons que les agents sont configurés pour utiliser un service LLM.

    # 2. Création d'une instance de EnqueteCluedoState
    enquete_state = EnqueteCluedoState(
        nom_enquete_cluedo="Le Mystère du Manoir Tudor",
        elements_jeu_cluedo={
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose"],
            "armes": ["Poignard", "Chandelier", "Revolver"],
            "lieux": ["Salon", "Cuisine", "Bureau"]
        },
        description_cas="Un meurtre a été commis au Manoir Tudor. Qui est le coupable, avec quelle arme et dans quel lieu ?",
        auto_generate_solution=True
    )
    print(f"Solution générée pour l'enquête: {enquete_state.solution_enquete}")

    # 3. Création et enregistrement de EnqueteStateManagerPlugin
    enquete_state_plugin_name = "EnqueteStatePlugin"
    enquete_manager_plugin = EnqueteStateManagerPlugin(enquete_state)
    kernel.add_plugin(enquete_manager_plugin, enquete_state_plugin_name)
    print(f"Plugin '{enquete_state_plugin_name}' enregistré dans le kernel.")

    # 4. Instanciation de SherlockEnqueteAgent et WatsonLogicAssistant
    # Les constructeurs peuvent varier. Adapté selon la consigne.
    # Supposons qu'ils prennent le kernel, un service_id (si nécessaire pour le LLM)
    # et le nom du plugin d'état.
    # Si les agents gèrent leur propre client LLM, le kernel peut ne pas avoir besoin d'un service LLM global.
    
    # Pour cet exemple, nous allons supposer que les agents peuvent être initialisés
    # sans `service_id` explicite ici s'ils sont configurés pour utiliser un service par défaut du kernel
    # ou s'ils ont leur propre configuration LLM interne.
    # Le paramètre `name` est souvent requis pour les agents dans AgentGroupChat.
    sherlock_agent = SherlockEnqueteAgent(
        kernel=kernel,
        name="Sherlock",
        instructions="Vous êtes Sherlock Holmes, le détective consultant. Votre rôle est de mener l'enquête, de poser des questions pertinentes et de déduire la solution du Cluedo.",
        plugin_name=enquete_state_plugin_name
    )
    watson_assistant = WatsonLogicAssistant(
        kernel=kernel,
        name="Watson",
        instructions="Vous êtes le Dr. Watson, l'assistant logique de Sherlock. Votre rôle est d'aider Sherlock à structurer ses pensées, à vérifier la logique des hypothèses et à gérer les informations de l'enquête.",
        plugin_name=enquete_state_plugin_name
    )
    print("Agents Sherlock et Watson instanciés.")

    # 5. Configuration de AgentGroupChat
    # Assurez-vous que SherlockEnqueteAgent et WatsonLogicAssistant sont compatibles avec AgentGroupChat.
    # Ils pourraient avoir besoin d'hériter de semantic_kernel.experimental.group_chat.Agent
    # ou d'implémenter une interface similaire.
    # Pour l'instant, on les passe directement.
    
    # Si les agents ne sont pas directement compatibles, il faudra peut-être les wrapper.
    # Exemple de wrapper simple (si AgentGroupChat attend une méthode invoke spécifique):
    # class SKAgentWrapper(Agent):
    #     def __init__(self, sk_agent_instance, agent_name: str):
    #         self._sk_agent = sk_agent_instance
    #         super().__init__(name=agent_name, instructions=sk_agent_instance.instructions) # ou équivalent
    #
    #     async def invoke(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
    #         # Adapter l'appel à la méthode d'invocation réelle de vos agents
    #         # Ceci est une simplification et dépendra de l'API de vos agents
    #         last_message_content = messages[-1]["content"]
    #         response_content = await self._sk_agent.some_invoke_method(last_message_content) 
    #         return [{"role": "assistant", "name": self.name, "content": response_content}]

    # Pour cet exemple, nous allons supposer que les agents sont directement utilisables
    # ou que AgentGroupChat est flexible.
    
    group_chat = AgentGroupChat(
        agents=[sherlock_agent, watson_assistant], # ou [SKAgentWrapper(sherlock_agent, "Sherlock"), SKAgentWrapper(watson_assistant, "Watson")]
        kernel=kernel # AgentGroupChat peut aussi avoir besoin du kernel
    )
    print("AgentGroupChat créé.")

    # Configuration des stratégies
    # BalancedParticipationStrategy: chaque agent a un nombre égal de tours.
    # max_turns=2 signifie que chaque agent parlera au plus 2 fois.
    # La conversation totale pourrait donc avoir jusqu'à 4 messages (ou plus selon l'implémentation exacte).
    group_chat.add_hook(BalancedParticipationStrategy(max_turns=2, agents=[sherlock_agent, watson_assistant]))
    
    # SimpleTerminationStrategy: termine après un nombre total de messages ou sur un mot-clé.
    # max_messages=3 signifie que la conversation s'arrêtera après 3 messages au total échangés dans le chat.
    # Ou, si un agent dit "L'affaire est résolue."
    termination_keywords = ["L'affaire est résolue.", "FIN_ENQUETE"]
    group_chat.add_hook(SimpleTerminationStrategy(
        max_messages=5, # Augmenté pour permettre plus d'échanges
        termination_keywords=termination_keywords
    ))
    print("Stratégies de participation et de terminaison configurées.")

    # 6. Exécution
    initial_message = "L'enquête sur le meurtre au Manoir Tudor commence maintenant. Qui a des premières pistes ?"
    print(f"\nDébut de la conversation avec le message initial: '{initial_message}'")
    
    history = await group_chat.invoke(initial_prompt=initial_message)

    # 7. Affichage de l'historique de la conversation
    print("\n--- Historique de la Conversation ---")
    if history:
        for message in history:
            sender_name = message.get("name", message.get("role", "Inconnu"))
            print(f"{sender_name}: {message['content']}")
    else:
        print("Aucun historique de conversation disponible.")
    print("--- Fin de la Conversation ---")

if __name__ == "__main__":
    # Note: Les appels asynchrones nécessitent une boucle d'événements.
    # Si vous exécutez cela depuis un environnement qui ne gère pas déjà asyncio (comme un script simple),
    # vous devrez utiliser asyncio.run().
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Une erreur est survenue: {e}")
        import traceback
        traceback.print_exc()