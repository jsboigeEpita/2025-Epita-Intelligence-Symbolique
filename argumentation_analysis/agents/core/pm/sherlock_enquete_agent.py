# argumentation_analysis/agents/core/pm/sherlock_enquete_agent.py
import logging
from typing import Optional, List, AsyncGenerator, ClassVar, Any

from semantic_kernel import Kernel
from semantic_kernel.agents import Agent
from semantic_kernel.agents.channels.agent_channel import AgentChannel
from semantic_kernel.contents import ChatMessageContent, StreamingChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory

from .pm_agent import ProjectManagerAgent
# from .pm_definitions import PM_INSTRUCTIONS # Remplacé par le prompt spécifique

SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT = """Vous êtes Sherlock Holmes, un détective consultant de renommée mondiale. Votre mission est de résoudre l'enquête en cours décrite dans l'état partagé.
Vous devez analyser les informations disponibles, formuler des hypothèses et diriger l'enquête.
Utilisez l'agent WatsonLogicAssistant pour effectuer des déductions logiques basées sur les faits et les règles établies.
Pour interagir avec l'état de l'enquête (géré par StateManagerPlugin), utilisez les fonctions disponibles pour :
- Lire la description du cas : `get_case_description()`
- Consulter les éléments identifiés : `get_identified_elements()`
- Consulter les hypothèses actuelles : `get_hypotheses()`
- Ajouter une nouvelle hypothèse : `add_hypothesis(hypothesis_text: str, confidence_score: float)`
- Mettre à jour une hypothèse : `update_hypothesis(hypothesis_id: str, new_text: str, new_confidence: float)`
- Demander une déduction à Watson : `query_watson(logical_query: str, belief_set_id: str)` (Watson mettra à jour l'état avec sa réponse)
- Consulter le log des requêtes à Watson : `get_query_log()`
- Marquer une tâche comme terminée : `complete_task(task_id: str)`
- Ajouter une nouvelle tâche : `add_task(description: str, assignee: str)`
- Consulter les tâches : `get_tasks()`
- Proposer une solution finale : `propose_final_solution(solution_details: dict)`

Votre objectif est de parvenir à une conclusion logique et bien étayée.
Dans le contexte d'une enquête Cluedo, vous devez identifier le coupable, l'arme et le lieu du crime."""

class CluedoChannel(AgentChannel):
    """Un canal de communication pour le jeu Cluedo."""
    async def get_history(self, **kwargs: Any) -> AsyncGenerator[List[ChatMessageContent], Any]:
        yield []
    async def invoke(self, agent: "Agent", **kwargs: Any) -> AsyncGenerator[List[ChatMessageContent], Any]:
        yield True, ChatMessageContent(role="user", content="test")
    async def invoke_stream(self, agent: "Agent", **kwargs: Any) -> AsyncGenerator[List[StreamingChatMessageContent], Any]:
        yield []
    async def receive(self, messages: List[ChatMessageContent], **kwargs: Any) -> None:
        pass
    async def reset(self, **kwargs: Any) -> None:
        pass

class SherlockEnqueteAgent(ProjectManagerAgent):
    channel_type: ClassVar[type[AgentChannel]] = CluedoChannel
    """
    Agent spécialisé dans la gestion d'enquêtes complexes, inspiré par Sherlock Holmes.
    Il planifie les étapes d'investigation, identifie les pistes à suivre et
    synthétise les informations pour résoudre l'affaire.
    """

    def __init__(self, kernel: Kernel, agent_name: str = "SherlockEnqueteAgent", system_prompt: Optional[str] = SHERLOCK_ENQUETE_AGENT_SYSTEM_PROMPT):
        """
        Initialise une instance de SherlockEnqueteAgent.

        Args:
            kernel: Le kernel Semantic Kernel à utiliser.
            agent_name: Le nom de l'agent.
            system_prompt: Le prompt système pour guider l'agent.
        """
        super().__init__(kernel, agent_name=agent_name, system_prompt=system_prompt)
        self.kernel = kernel  # Stocker la référence au kernel
        # self.logger = logging.getLogger(agent_name) # Assurer un logger spécifique - Géré par BaseAgent._logger
        self._logger.info(f"SherlockEnqueteAgent '{agent_name}' initialisé.")

    async def invoke(
        self,
        messages: List[ChatMessageContent],
        **kwargs,
    ) -> List[ChatMessageContent]:
        """Invoke the agent with a list of messages."""
        self._logger.info(f"--- SherlockEnqueteAgent INVOKED with {len(messages)} messages ---")
        chat_history = ChatHistory(messages=messages)
        chat_history.add_system_message(self.instructions)
        
        # Pass runtime to the kernel invocation
        runtime = kwargs.pop("runtime", None)
        if not runtime:
            raise ValueError("Runtime not provided in kwargs for agent invocation.")

        result = await self.kernel.invoke(
            prompt=str(chat_history),
            runtime=runtime,
            **kwargs,
        )
        # Assuming result is ChatMessageContent or similar
        response_message = result if isinstance(result, ChatMessageContent) else ChatMessageContent(role="assistant", content=str(result))
        return [response_message]

    async def invoke_stream(
        self,
        messages: List[ChatMessageContent],
        **kwargs,
    ) -> AsyncGenerator[List[ChatMessageContent], None]:
        """Invoke the agent with a stream of messages."""
        # Basic (non-streaming) implementation for now
        response = await self.invoke(messages, **kwargs)
        yield response

    async def get_response(
        self,
        messages: List[ChatMessageContent],
        **kwargs,
    ) -> List[ChatMessageContent]:
        """Get a response from the agent."""
        return await self.invoke(messages, **kwargs)

    async def get_current_case_description(self) -> str:
        """
        Récupère la description de l'affaire en cours via le EnqueteStateManagerPlugin.

        Returns:
            La description de l'affaire.
        """
        self._logger.info("Récupération de la description de l'affaire en cours.")
        try:
            result = await self.kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="get_case_description"
            )
            # La valeur réelle est souvent dans result.value ou directement result selon la config du kernel
            # Pour l'instant, supposons que 'result' est directement la chaîne ou a un attribut 'value'
            # Ceci pourrait nécessiter un ajustement basé sur le comportement réel de 'invoke'
            if hasattr(result, 'value'):
                return str(result.value)
            return str(result)
        except Exception as e:
            self._logger.error(f"Erreur lors de la récupération de la description de l'affaire: {e}")
            # Retourner une chaîne vide ou lever une exception spécifique pourrait être mieux
            return "Erreur: Impossible de récupérer la description de l'affaire."

    async def add_new_hypothesis(self, hypothesis_text: str, confidence_score: float) -> Optional[dict]:
        """
        Ajoute une nouvelle hypothèse à l'état de l'enquête.

        Args:
            hypothesis_text: Le texte de l'hypothèse.
            confidence_score: Le score de confiance de l'hypothèse.

        Returns:
            Le dictionnaire de l'hypothèse ajoutée ou None en cas d'erreur.
        """
        self._logger.info(f"Ajout d'une nouvelle hypothèse: '{hypothesis_text}' avec confiance {confidence_score}")
        try:
            result = await self.kernel.invoke(
                plugin_name="EnqueteStatePlugin",
                function_name="add_hypothesis",
                text=hypothesis_text, # type: ignore
                confidence_score=confidence_score # type: ignore
            )
            # Supposant que 'result' est le dictionnaire de l'hypothèse ou a un attribut 'value'
            if hasattr(result, 'value'):
                return result.value # type: ignore
            return result # type: ignore
        except Exception as e:
            self._logger.error(f"Erreur lors de l'ajout de l'hypothèse: {e}")
            return None

# Pourrait être étendu avec des capacités spécifiques à Sherlock plus tard
# def get_agent_capabilities(self) -> Dict[str, Any]:
#     base_caps = super().get_agent_capabilities()
#     sherlock_caps = {
#         "deduce_next_step": "Deduces the next logical step in the investigation based on evidence.",
#         "formulate_hypotheses": "Formulates hypotheses based on collected clues."
#     }
#     base_caps.update(sherlock_caps)
#     return base_caps