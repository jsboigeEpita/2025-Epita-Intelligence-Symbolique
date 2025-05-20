"""
Patch pour le middleware de messagerie.

Ce module étend la classe MessageMiddleware pour ajouter des fonctionnalités
nécessaires aux tests d'interface tactique-opérationnelle.
"""

from typing import Optional
from .middleware import MessageMiddleware
from .tactical_adapter import TacticalAdapter
from .operational_adapter import OperationalAdapter
from .message import AgentLevel

# Patch pour la classe MessageMiddleware
def get_adapter(self, agent_id: str, level: AgentLevel):
    """
    Récupère l'adaptateur approprié pour un agent et un niveau donnés.
    
    Args:
        agent_id: Identifiant de l'agent
        level: Niveau de l'agent (STRATEGIC, TACTICAL, OPERATIONAL)
        
    Returns:
        L'adaptateur approprié ou None si le niveau n'est pas reconnu
    """
    if level == AgentLevel.TACTICAL:
        return TacticalAdapter(agent_id, self)
    elif level == AgentLevel.OPERATIONAL:
        return OperationalAdapter(agent_id, self)
    else:
        # Pour les autres niveaux, on pourrait ajouter d'autres adaptateurs
        return None

# Appliquer le patch à la classe MessageMiddleware
MessageMiddleware.get_adapter = get_adapter