"""
Fallback pour semantic_kernel.agents
Module de remplacement pour les composants agents manquants de semantic-kernel
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


class AuthorRole(Enum):
    """Rôles d'auteur pour les agents conversationnels"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    AGENT = "agent"
    FUNCTION = "function"


@dataclass
class ChatMessage:
    """Message de chat pour les agents"""
    content: str
    role: AuthorRole
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AgentChat:
    """Classe de base pour les chats d'agents"""
    
    def __init__(self, name: str = "Agent"):
        self.name = name
        self.messages: List[ChatMessage] = []
    
    def add_message(self, content: str, role: AuthorRole, metadata: Optional[Dict[str, Any]] = None):
        """Ajoute un message au chat"""
        message = ChatMessage(content=content, role=role, metadata=metadata)
        self.messages.append(message)
        return message
    
    def get_messages(self, role: Optional[AuthorRole] = None) -> List[ChatMessage]:
        """Récupère les messages filtrés par rôle"""
        if role is None:
            return self.messages.copy()
        return [msg for msg in self.messages if msg.role == role]
    
    def clear_messages(self):
        """Efface tous les messages"""
        self.messages.clear()


class ChatCompletion:
    """Classe pour les complétions de chat"""
    
    def __init__(self, content: str, role: AuthorRole = AuthorRole.ASSISTANT):
        self.content = content
        self.role = role
        self.metadata = {}
    
    @property
    def message(self) -> ChatMessage:
        """Retourne le message de la completion"""
        return ChatMessage(content=self.content, role=self.role, metadata=self.metadata)


# Aliases pour compatibilité
Author = AuthorRole
AgentMessage = ChatMessage
AgentChatCompletion = ChatCompletion


def get_available_roles() -> List[str]:
    """Retourne la liste des rôles disponibles"""
    return [role.value for role in AuthorRole]


def create_agent_chat(name: str = "DefaultAgent") -> AgentChat:
    """Factory pour créer un chat d'agent"""
    return AgentChat(name=name)


# Export pour import direct
__all__ = [
    'AuthorRole', 
    'ChatMessage', 
    'AgentChat', 
    'ChatCompletion',
    'Author',
    'AgentMessage', 
    'AgentChatCompletion',
    'get_available_roles',
    'create_agent_chat'
]