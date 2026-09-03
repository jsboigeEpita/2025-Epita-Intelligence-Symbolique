"""
Modèles de données étendus pour l'intégration JTMS.
Selon les spécifications du RAPPORT_ARCHITECTURE_INTEGRATION_JTMS.md - AXE A
"""

from .extended_belief_model import (
    ExtendedBeliefModel,
    BeliefMetadata,
    ModificationHistory,
)
from .agent_communication_model import (
    AgentMessage,
    CommunicationProtocol,
    SyncOperation,
)

__all__ = [
    "ExtendedBeliefModel",
    "BeliefMetadata",
    "ModificationHistory",
    "AgentMessage",
    "CommunicationProtocol",
    "SyncOperation",
]
