import asyncio
import semantic_kernel as sk
from semantic_kernel.kernel import Kernel

from argumentation_analysis.core.enquete_states import EnqueteCluedoState
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant

# Correction du chemin d'import pour GroupChatOrchestration et les composants associés
from semantic_kernel.agents import (
    Agent,  # Agent reste pertinent
    GroupChatOrchestration,
    RoundRobinGroupChatManager,
    BooleanResult  # Utile pour should_terminate dans un manager customisé
)
from semantic_kernel.agents.runtime import InProcessRuntime
from typing import List, Dict, Optional, Any # Ajout pour typage
from pydantic import Field

# Définition d'une classe wrapper simple pour les agents si nécessaire pour AgentGroupChat
# Si SherlockEnqueteAgent et WatsonLogicAssistant n'héritent pas déjà de Agent ou n'ont pas la bonne interface
# Cette partie pourrait nécessiter un ajustement en fonction de la définition réelle des classes Agent.
# Pour l'instant, on suppose qu'elles sont compatibles ou qu'AgentGroupChat peut les gérer.

# Définition du GroupChatManager personnalisé pour Cluedo
class CluedoGroupChatManager(RoundRobinGroupChatManager):
    """
    Gestionnaire de chat personnalisé pour le Cluedo, implémentant la logique
    de participation équilibrée et de terminaison.
    """
    max_turns_per_agent: int = Field(default=2)
    max_total_messages: int = Field(default=10) # Augmenté par rapport à l'exemple pour plus de flexibilité
    termination_keywords: Optional[List[str]] = Field(default_factory=list)

    def __init__(
        self,
        members: List[Agent],
        max_turns_per_agent: int = 2,
        max_total_messages: int = 10, # Augmenté par rapport à l'exemple pour plus de flexibilité
        termination_keywords: Optional[List[str]] = None,
        **kwargs: Any, # Ajout pour accepter d'autres arguments de la classe parente
    ):
        # max_rounds dans RoundRobinGroupChatManager est le nombre total de tours,
        # pas le nombre total de messages. Un tour peut impliquer plusieurs messages
        # si l'agent sélectionné ne répond pas ou si le manager le décide.
        # Pour l'instant, on le lie à max_total_messages pour une approximation.
        super().__init__(members=members, max_rounds=max_total_messages, **kwargs) # Passer kwargs
        self.max_turns_per_agent = max_turns_per_agent
        self.max_total_messages = max_total_messages
        self.termination_keywords = termination_keywords if termination_keywords is not None else []
        self._agent_turn_count: Dict[str, int] = {agent.name: 0 for agent in members}
        self._total_messages_count = 0
        self._conversation_history: List[Dict[str, str]] = [] # Pour stocker l'historique

    async def select_next_agent(self, history: List[Dict[str, Any]]) -> Agent:
        """Sélectionne le prochain agent en mode round-robin, en respectant max_turns_per_agent."""
        # Implémentation de RoundRobinGroupChatManager gère déjà le round-robin de base.
        # On va surcharger pour ajouter la logique de max_turns_per_agent.
        
        # Trouver l'agent qui vient de parler
        last_speaker_name = history[-1]["name"] if history else None

        # Trouver l'index du dernier agent ayant parlé pour le round-robin
        current_agent_index = -1
        if last_speaker_name:
            for i, agent in enumerate(self.members):
                if agent.name == last_speaker_name:
                    current_agent_index = i
                    break
        
        # Sélectionner le prochain agent en round-robin
        # Si aucun agent n'a parlé, ou si on ne trouve pas le dernier, on commence par le premier.
        next_agent_index = (current_agent_index + 1) % len(self.members)
        selected_agent = self.members[next_agent_index]

        # Vérifier si cet agent a dépassé son nombre de tours
        # Si tous les agents ont atteint leur max_turns_per_agent, la terminaison devrait être gérée par should_terminate
        # Cette boucle est pour s'assurer qu'on ne sélectionne pas un agent qui a déjà trop parlé *dans ce tour de sélection*
        # et qu'il y a d'autres options.
        initial_next_agent_index = next_agent_index
        while self._agent_turn_count.get(selected_agent.name, 0) >= self.max_turns_per_agent:
            next_agent_index = (next_agent_index + 1) % len(self.members)
            selected_agent = self.members[next_agent_index]
            if next_agent_index == initial_next_agent_index:
                # On a fait un tour complet, tous les agents restants ont atteint leur max.
                # La terminaison sera gérée par should_terminate.
                # On retourne le premier agent disponible pour éviter une boucle infinie ici.
                # Ou on pourrait lever une exception si aucun agent ne peut parler.
                # Pour l'instant, on retourne l'agent sélectionné, should_terminate décidera.
                break
        
        return selected_agent

    async def should_terminate(self, history: List[Dict[str, Any]]) -> BooleanResult:
        """Détermine si la conversation doit se terminer."""
        self._total_messages_count = len(history)
        
        if history:
            last_message_content = str(history[-1].get("content", "")).strip()
            if any(keyword.lower() in last_message_content.lower() for keyword in self.termination_keywords):
                return BooleanResult(value=True, rationale="Termination keyword detected.")

        if self._total_messages_count >= self.max_total_messages:
            return BooleanResult(value=True, rationale=f"Max total messages ({self.max_total_messages}) reached.")

        # Mettre à jour le compteur de tours pour l'agent qui vient de parler
        if history:
            last_speaker_name = history[-1]["name"]
            if last_speaker_name in self._agent_turn_count:
                 # On ne met à jour que si c'est un nouveau message de cet agent
                 # (pour éviter de compter plusieurs fois si l'historique est passé plusieurs fois)
                 # Ceci est une simplification; une gestion plus robuste de l'historique serait nécessaire
                 # pour s'assurer qu'on compte bien les "tours" et non les messages.
                 # Pour l'instant, on assume qu'un message dans l'historique = un tour pour cet agent.
                pass # La mise à jour se fera après l'invocation de l'agent

        # Vérifier si tous les agents ont atteint leur max_turns_per_agent
        # Cette condition est délicate car un agent peut être sélectionné mais ne pas répondre.
        # On se base sur le nombre de fois qu'un agent a été *sélectionné et a parlé*.
        # La logique de RoundRobinGroupChatManager peut déjà gérer une partie de cela.
        # Pour l'instant, on se fie à max_total_messages et aux mots-clés.
        # Une logique plus fine de max_turns_per_agent nécessiterait de compter après chaque invocation réussie.

        return BooleanResult(value=False)

    def record_agent_turn(self, agent_name: str):
        """Appelée après qu'un agent a effectivement parlé."""
        if agent_name in self._agent_turn_count:
            self._agent_turn_count[agent_name] += 1
        else:
            self._agent_turn_count[agent_name] = 1

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
    
    # Création des agents (sherlock_agent et watson_assistant sont créés plus haut)
    # Assurez-vous que self.current_case_description est disponible si vous l'utilisez.
    # Pour cet exemple dans main(), nous allons utiliser la description de enquete_state.
    current_case_description = enquete_state.description_cas

    # Configuration du CluedoGroupChatManager
    print("Configuration du CluedoGroupChatManager...") # Remplacement de self.logger.info pour main()
    termination_keywords = ["L'affaire est résolue.", "FIN_ENQUETE", "Le coupable est", "Nous avons trouvé"]
    cluedo_manager = CluedoGroupChatManager(
        members=[sherlock_agent, watson_assistant],
        max_turns_per_agent=3, # Nombre de fois que chaque agent peut parler
        max_total_messages=15, # Nombre total de messages dans la conversation
        termination_keywords=termination_keywords
    )

    print("Configuration de GroupChatOrchestration...") # Remplacement de self.logger.info pour main()
    orchestration = GroupChatOrchestration(
        members=[sherlock_agent, watson_assistant], # Doit correspondre aux membres du manager
        manager=cluedo_manager,
        runtime=InProcessRuntime() # Nécessaire pour exécuter le chat
    )

    print("Lancement de l'orchestration du Cluedo...") # Remplacement de self.logger.info pour main()
    # L'historique initial peut contenir le message de démarrage
    initial_history = [{"role": "user", "name": "System", "content": f"Nouvelle enquête Cluedo : {current_case_description}. Sherlock, commencez."}]
    
    # La méthode invoke est asynchrone
    # Note: Dans la nouvelle API, invoke prend un seul argument, qui est l'entrée (souvent un dict ou une liste de messages)
    # et ne prend plus `initial_history` séparément ni `runtime` directement. Le runtime est configuré sur l'orchestration.
    # La méthode invoke de GroupChatOrchestration attend une List[Dict[str, Any]] ou un str.
    # Si c'est une List[Dict], elle est traitée comme l'historique initial.
    
    # Démarrage du runtime si nécessaire (InProcessRuntime est géré par l'orchestration)
    # await orchestration.runtime.start() # Pas nécessaire explicitement avec InProcessRuntime et la nouvelle API

    full_history = await orchestration.invoke(input=initial_history) # 'input' est le paramètre attendu
    
    # Enregistrer le tour de l'agent après chaque message dans l'historique réel
    # La logique de `record_agent_turn` devrait être appelée par le runtime ou l'orchestrateur
    # après qu'un agent a effectivement contribué.
    # Le RoundRobinGroupChatManager de base gère le comptage des tours pour sa propre logique de `max_rounds`.
    # Notre `record_agent_turn` est une méthode supplémentaire pour notre propre suivi si nécessaire,
    # mais son appel doit être intégré dans le flux d'exécution, ce qui est complexe sans modifier
    # le comportement interne de l'orchestrateur ou du runtime.
    # Pour l'instant, nous nous fions à la logique interne du manager et de l'orchestrateur.

    print("Orchestration du Cluedo terminée.") # Remplacement de self.logger.info pour main()
    print("Historique de la conversation Cluedo :") # Remplacement de self.logger.info pour main()
    
    final_chat_history = []
    if full_history: # full_history est maintenant la liste des messages
        for message in full_history: # full_history est déjà l'historique
            sender_name = message.get("name", "Inconnu") # Les messages de l'historique ont 'name'
            content = message.get("content", "")
            print(f"  {sender_name}: {content}") # Remplacement de self.logger.info pour main()
            final_chat_history.append({"sender": sender_name, "message": content})
    else:
        print("L'historique de la conversation est vide.") # Remplacement de self.logger.warning pour main()

    # await orchestration.runtime.stop_when_idle() # Pas nécessaire explicitement avec InProcessRuntime

    # La fonction main retournera l'historique pour correspondre à run_cluedo_game
    # Pour l'instant, on imprime juste, mais on pourrait retourner final_chat_history
    # si cette fonction main était appelée et son résultat utilisé.
    # Pour la tâche, l'important est que la logique soit adaptée.
    # La fonction `main` actuelle ne retourne rien, mais la logique de `run_cluedo_game` le ferait.
    # Nous allons laisser `main` imprimer pour la démo, et noter que `final_chat_history` est prêt.
    print("--- Fin de la Conversation ---")
    # return final_chat_history # Si main devait retourner comme run_cluedo_game

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