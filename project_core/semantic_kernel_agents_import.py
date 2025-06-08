"""
Module d'import automatique pour semantic_kernel.agents avec fallback
Gère l'import d'AuthorRole et des autres composants agents
"""

import sys
import warnings
from typing import TYPE_CHECKING

# Tentative d'import direct
try:
    from semantic_kernel.agents import AuthorRole, ChatMessage
    _USING_FALLBACK = False
    print("[SK-AGENTS] Import direct réussi depuis semantic_kernel.agents")
except ImportError:
    # Import du fallback
    try:
        from project_core.semantic_kernel_agents_fallback import (
            AuthorRole, 
            ChatMessage, 
            AgentChat, 
            ChatCompletion,
            get_available_roles,
            create_agent_chat
        )
        _USING_FALLBACK = True
        warnings.warn(
            "semantic_kernel.agents non disponible, utilisation du fallback", 
            UserWarning
        )
        print("[SK-AGENTS] Utilisation du fallback pour semantic_kernel.agents")
    except ImportError as e:
        raise ImportError(f"Impossible d'importer semantic_kernel.agents ou le fallback: {e}")

# Vérification des composants additionnels
try:
    from semantic_kernel.agents import AgentChat as SKAgentChat
    if not _USING_FALLBACK:
        AgentChat = SKAgentChat
except ImportError:
    if not _USING_FALLBACK:
        # Créer une classe de base simple si pas dans le fallback
        class AgentChat:
            def __init__(self, name="Agent"):
                self.name = name
                self.messages = []

try:
    from semantic_kernel.agents import ChatCompletion as SKChatCompletion
    if not _USING_FALLBACK:
        ChatCompletion = SKChatCompletion
except ImportError:
    if not _USING_FALLBACK:
        # Classe simple de remplacement
        class ChatCompletion:
            def __init__(self, content, role=None):
                self.content = content
                self.role = role or AuthorRole.ASSISTANT


def get_author_role_enum():
    """Retourne l'enum AuthorRole disponible"""
    return AuthorRole


def is_using_fallback():
    """Retourne True si on utilise le fallback"""
    return _USING_FALLBACK


def test_agents_import():
    """Test rapide des imports agents"""
    try:
        # Test des rôles de base
        user_role = AuthorRole.USER
        assistant_role = AuthorRole.ASSISTANT
        system_role = AuthorRole.SYSTEM
        
        # Test de création de message
        msg = ChatMessage(content="Test", role=user_role)
        
        print(f"✓ AuthorRole.USER: {user_role.value}")
        print(f"✓ AuthorRole.ASSISTANT: {assistant_role.value}")
        print(f"✓ AuthorRole.SYSTEM: {system_role.value}")
        print(f"✓ ChatMessage créé: {msg.content}")
        print(f"✓ Mode fallback: {is_using_fallback()}")
        
        return True
    except Exception as e:
        print(f"✗ Erreur test agents: {e}")
        return False


# Export pour utilisation
__all__ = [
    'AuthorRole',
    'ChatMessage', 
    'AgentChat',
    'ChatCompletion',
    'get_author_role_enum',
    'is_using_fallback',
    'test_agents_import'
]


# Test automatique à l'import
if __name__ == "__main__":
    print("=== Test semantic_kernel.agents import ===")
    success = test_agents_import()
    sys.exit(0 if success else 1)