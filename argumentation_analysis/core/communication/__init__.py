"""
Module de communication multi-canal pour les agents d'analyse rhétorique.

Ce module implémente un système de communication flexible permettant aux agents
de différents niveaux (stratégique, tactique, opérationnel) d'échanger des messages
via différents canaux spécialisés.

Composants principaux:
- Middleware de messagerie: Composant central qui gère tous les aspects de la communication
- Canaux de communication: Canaux spécialisés pour différents types d'interactions
- Protocoles de communication: Différents protocoles comme requête-réponse et publication-abonnement
- Structures de messages: Format commun pour tous les messages avec des extensions spécifiques
- Adaptateurs d'agents: Interfaces entre les agents et le middleware
"""

from .message import Message, MessageType, MessagePriority, AgentLevel
from .channel_interface import (
    Channel,
    ChannelType,
    LocalChannel,
)  # Ajout de LocalChannel
from .middleware import MessageMiddleware
from .request_response import RequestResponseProtocol
from .pub_sub import PublishSubscribeProtocol
from .hierarchical_channel import HierarchicalChannel
from .collaboration_channel import CollaborationChannel
from .data_channel import DataChannel
from .strategic_adapter import StrategicAdapter
from .tactical_adapter import TacticalAdapter
from .operational_adapter import OperationalAdapter

# Importer le patch pour ajouter la méthode get_adapter à MessageMiddleware
from .middleware_patch import *

__all__ = [
    "Message",
    "MessageType",
    "MessagePriority",
    "AgentLevel",
    "Channel",
    "ChannelType",
    "LocalChannel",  # Ajout de LocalChannel
    "MessageMiddleware",
    "RequestResponseProtocol",
    "PublishSubscribeProtocol",
    "HierarchicalChannel",
    "CollaborationChannel",
    "DataChannel",
    "StrategicAdapter",
    "TacticalAdapter",
    "OperationalAdapter",
]
