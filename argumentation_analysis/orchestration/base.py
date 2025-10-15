# argumentation_analysis/orchestration/base.py
"""Module contenant les classes de base pour l'orchestration multi-agents."""

from abc import ABC, abstractmethod
from typing import List
from semantic_kernel.contents import ChatMessageContent
from pydantic import BaseModel


class Agent(BaseModel, ABC):
    """Classe de base abstraite pour un agent conversationnel."""

    name: str

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def invoke(self, history: List[ChatMessageContent]) -> ChatMessageContent:
        """Méthode principale pour invoquer l'agent."""
        pass


class SelectionStrategy(BaseModel, ABC):
    """Classe de base pour les stratégies de sélection d'agent."""

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def next(
        self, agents: List[Agent], history: List[ChatMessageContent]
    ) -> Agent:
        """Sélectionne le prochain agent."""
        pass

    def reset(self) -> None:
        """Remet à zéro l'état de la stratégie."""
        pass


class TerminationStrategy(BaseModel, ABC):
    """Classe de base pour les stratégies de terminaison de conversation."""

    class Config:
        arbitrary_types_allowed = True

    @abstractmethod
    async def should_terminate(
        self, agent: Agent, history: List[ChatMessageContent]
    ) -> bool:
        """Détermine si la conversation doit se terminer."""
        pass

    def reset(self) -> None:
        """Remet à zéro l'état de la stratégie."""
        pass
