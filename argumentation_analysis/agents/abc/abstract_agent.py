# Fichier : argumentation_analysis/agents/abc/abstract_agent.py

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterable, List

from semantic_kernel import Kernel
from semantic_kernel.agents import Agent
from semantic_kernel.agents.agent import AgentResponseItem
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.functions.kernel_arguments import KernelArguments

class AbstractAgent(Agent, ABC):
    """
    Classe de base abstraite pour tous les agents du système.
    Garantit la compatibilité avec AgentGroupChat et standardise la configuration.
    """

    def __init__(
        self,
        kernel: Kernel,
        name: Optional[str] = None,
        description: Optional[str] = None,
        instructions: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Initialise une instance d'AbstractAgent."""
        super().__init__(
            name=name,
            description=description,
            instructions=instructions,
            kernel=kernel,
            **kwargs,
        )
        self.logger = logging.getLogger(f"agent.{self.__class__.__name__}.{self.name}")
        self.llm_service_id: Optional[str] = None

    @abstractmethod
    def setup_agent_components(self, llm_service_id: str, correction_attempts: int = 3) -> None:
        """
        Configuration post-initialisation pour charger les plugins et dépendances.
        """
        self.llm_service_id = llm_service_id
        self.correction_attempts = correction_attempts
        self.logger.info(f"Composants configurés pour '{self.name}' avec le service LLM '{llm_service_id}'.")

    @abstractmethod
    def get_agent_capabilities(self) -> Dict[str, Any]:
        """
        Retourne un dictionnaire décrivant les 'pouvoirs' de l'agent (plugins, etc.).
        """
        pass

    @abstractmethod
    async def get_response(
        self,
        messages: List[ChatMessageContent],
        arguments: KernelArguments,
        **kwargs: Any,
    ) -> AgentResponseItem[ChatMessageContent]:
        """Contient la logique métier principale de l'agent."""
        raise NotImplementedError

    async def invoke(
        self,
        messages: List[ChatMessageContent],
        arguments: Optional[KernelArguments] = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseItem[ChatMessageContent]]:
        """Point d'entrée standardisé pour AgentGroupChat."""
        if arguments is None:
            arguments = KernelArguments()
        
        self.logger.debug(f"Agent '{self.name}' invoqué.")
        response = await self.get_response(messages, arguments, **kwargs)
        self.logger.debug(f"Agent '{self.name}' a produit une réponse.")
        yield response

    async def invoke_stream(
        self,
        messages: List[ChatMessageContent],
        arguments: Optional[KernelArguments] = None,
        **kwargs: Any,
    ) -> AsyncIterable[AgentResponseItem[ChatMessageContent]]:
        """Implémentation du streaming, qui délègue à `invoke`."""
        async for message in self.invoke(messages, arguments, **kwargs):
            yield message