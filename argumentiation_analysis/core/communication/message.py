"""
Structures de données pour les messages échangés dans le système de communication multi-canal.

Ce module définit le format commun pour tous les messages, ainsi que les types
de messages spécifiques et les priorités.
"""

import uuid
import enum
from datetime import datetime
from typing import Dict, Any, Optional, List, Union


class MessageType(enum.Enum):
    """Types de messages supportés par le système."""
    COMMAND = "command"  # Directives, tâches, instructions
    INFORMATION = "information"  # Informations, résultats, états
    REQUEST = "request"  # Demandes d'informations ou d'actions
    RESPONSE = "response"  # Réponses aux requêtes
    EVENT = "event"  # Notifications d'événements
    CONTROL = "control"  # Messages de contrôle du système
    PUBLICATION = "publication"  # Publications (pour pub/sub)
    SUBSCRIPTION = "subscription"  # Abonnements (pour pub/sub)


class MessagePriority(enum.Enum):
    """Niveaux de priorité pour les messages."""
    LOW = "low"  # Priorité basse
    NORMAL = "normal"  # Priorité normale (par défaut)
    HIGH = "high"  # Priorité haute
    CRITICAL = "critical"  # Priorité critique


class AgentLevel(enum.Enum):
    """Niveaux des agents dans l'architecture hiérarchique."""
    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    OPERATIONAL = "operational"
    SYSTEM = "system"


class Message:
    """
    Représentation d'un message dans le système de communication multi-canal.
    
    Tous les messages suivent un format commun avec des champs obligatoires et optionnels.
    """
    
    def __init__(
        self,
        message_type: MessageType,
        sender: str,
        sender_level: AgentLevel,
        content: Dict[str, Any],
        recipient: Optional[str] = None,
        channel: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        """
        Initialise un nouveau message.
        
        Args:
            message_type: Type du message
            sender: Identifiant de l'émetteur
            sender_level: Niveau de l'émetteur (stratégique, tactique, opérationnel)
            content: Contenu spécifique au type de message
            recipient: Identifiant du destinataire (None pour broadcast)
            channel: Canal utilisé (peut être déterminé automatiquement)
            priority: Priorité du message (par défaut: NORMAL)
            metadata: Métadonnées additionnelles
            message_id: Identifiant unique du message (généré automatiquement si None)
            timestamp: Horodatage de création du message (généré automatiquement si None)
        """
        self.id = message_id or f"{message_type.value}-{uuid.uuid4().hex[:8]}"
        self.type = message_type
        self.sender = sender
        self.sender_level = sender_level
        self.recipient = recipient
        self.channel = channel
        self.priority = priority
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convertit le message en dictionnaire pour la sérialisation.
        
        Returns:
            Un dictionnaire représentant le message
        """
        return {
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "sender_level": self.sender_level.value,
            "recipient": self.recipient,
            "channel": self.channel,
            "priority": self.priority.value,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        Crée un message à partir d'un dictionnaire.
        
        Args:
            data: Dictionnaire contenant les données du message
            
        Returns:
            Une instance de Message
        """
        return cls(
            message_type=MessageType(data["type"]),
            sender=data["sender"],
            sender_level=AgentLevel(data["sender_level"]),
            content=data["content"],
            recipient=data.get("recipient"),
            channel=data.get("channel"),
            priority=MessagePriority(data.get("priority", "normal")),
            metadata=data.get("metadata", {}),
            message_id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"])
        )
    
    def is_response_to(self, request_id: str) -> bool:
        """
        Vérifie si ce message est une réponse à une requête spécifique.
        
        Args:
            request_id: Identifiant de la requête
            
        Returns:
            True si ce message est une réponse à la requête spécifiée, False sinon
        """
        return (
            self.type == MessageType.RESPONSE and
            self.metadata.get("reply_to") == request_id
        )
    
    def requires_acknowledgement(self) -> bool:
        """
        Vérifie si ce message nécessite un accusé de réception.
        
        Returns:
            True si un accusé de réception est requis, False sinon
        """
        return self.metadata.get("requires_ack", False)
    
    def create_response(
        self,
        content: Dict[str, Any],
        priority: Optional[MessagePriority] = None
    ) -> 'Message':
        """
        Crée un message de réponse à ce message.
        
        Args:
            content: Contenu de la réponse
            priority: Priorité de la réponse (par défaut: même priorité que la requête)
            
        Returns:
            Un nouveau message de type RESPONSE
        """
        return Message(
            message_type=MessageType.RESPONSE,
            sender=self.recipient,
            sender_level=AgentLevel.SYSTEM,  # À remplacer par le niveau réel de l'agent
            content=content,
            recipient=self.sender,
            channel=self.channel,
            priority=priority or self.priority,
            metadata={
                "reply_to": self.id,
                "conversation_id": self.metadata.get("conversation_id")
            }
        )
    
    def create_acknowledgement(self) -> 'Message':
        """
        Crée un accusé de réception pour ce message.
        
        Returns:
            Un nouveau message d'accusé de réception
        """
        return Message(
            message_type=MessageType.RESPONSE,
            sender=self.recipient,
            sender_level=AgentLevel.SYSTEM,  # À remplacer par le niveau réel de l'agent
            content={"status": "acknowledged", "message_id": self.id},
            recipient=self.sender,
            channel=self.channel,
            priority=self.priority,
            metadata={
                "reply_to": self.id,
                "conversation_id": self.metadata.get("conversation_id"),
                "acknowledgement": True
            }
        )


# Classes spécialisées pour les différents types de messages

class CommandMessage(Message):
    """Message de commande pour transmettre des directives, des tâches ou des instructions."""
    
    def __init__(
        self,
        sender: str,
        sender_level: AgentLevel,
        command_type: str,
        parameters: Dict[str, Any],
        recipient: str,
        constraints: Optional[Dict[str, Any]] = None,
        priority: MessagePriority = MessagePriority.HIGH,
        requires_ack: bool = True,
        **kwargs
    ):
        """
        Initialise un nouveau message de commande.
        
        Args:
            sender: Identifiant de l'émetteur
            sender_level: Niveau de l'émetteur
            command_type: Type de commande (execute_analysis, allocate_resources, etc.)
            parameters: Paramètres de la commande
            recipient: Destinataire de la commande
            constraints: Contraintes d'exécution (optionnel)
            priority: Priorité du message (par défaut: HIGH)
            requires_ack: Indique si un accusé de réception est requis (par défaut: True)
            **kwargs: Arguments supplémentaires pour la classe Message
        """
        content = {
            "command_type": command_type,
            "parameters": parameters
        }
        
        if constraints:
            content["constraints"] = constraints
        
        metadata = kwargs.pop("metadata", {})
        metadata["requires_ack"] = requires_ack
        
        super().__init__(
            message_type=MessageType.COMMAND,
            sender=sender,
            sender_level=sender_level,
            content=content,
            recipient=recipient,
            priority=priority,
            metadata=metadata,
            **kwargs
        )


class InformationMessage(Message):
    """Message d'information pour partager des informations, des résultats ou des états."""
    
    def __init__(
        self,
        sender: str,
        sender_level: AgentLevel,
        info_type: str,
        data: Dict[str, Any],
        recipient: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs
    ):
        """
        Initialise un nouveau message d'information.
        
        Args:
            sender: Identifiant de l'émetteur
            sender_level: Niveau de l'émetteur
            info_type: Type d'information (analysis_result, status_update, etc.)
            data: Données de l'information
            recipient: Destinataire de l'information (None pour broadcast)
            priority: Priorité du message (par défaut: NORMAL)
            **kwargs: Arguments supplémentaires pour la classe Message
        """
        content = {
            "info_type": info_type,
            "data": data
        }
        
        super().__init__(
            message_type=MessageType.INFORMATION,
            sender=sender,
            sender_level=sender_level,
            content=content,
            recipient=recipient,
            priority=priority,
            **kwargs
        )


class RequestMessage(Message):
    """Message de requête pour demander des informations ou des actions."""
    
    def __init__(
        self,
        sender: str,
        sender_level: AgentLevel,
        request_type: str,
        description: str,
        context: Dict[str, Any],
        recipient: str,
        response_format: Optional[str] = None,
        timeout: Optional[int] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        **kwargs
    ):
        """
        Initialise un nouveau message de requête.
        
        Args:
            sender: Identifiant de l'émetteur
            sender_level: Niveau de l'émetteur
            request_type: Type de requête (get_analysis, assistance, etc.)
            description: Description de la requête
            context: Contexte de la requête
            recipient: Destinataire de la requête
            response_format: Format de réponse attendu (optionnel)
            timeout: Délai d'attente en secondes (optionnel)
            priority: Priorité du message (par défaut: NORMAL)
            **kwargs: Arguments supplémentaires pour la classe Message
        """
        content = {
            "request_type": request_type,
            "description": description,
            "context": context
        }
        
        if response_format:
            content["response_format"] = response_format
        
        if timeout:
            content["timeout"] = timeout
        
        super().__init__(
            message_type=MessageType.REQUEST,
            sender=sender,
            sender_level=sender_level,
            content=content,
            recipient=recipient,
            priority=priority,
            **kwargs
        )


class EventMessage(Message):
    """Message d'événement pour notifier des événements importants dans le système."""
    
    def __init__(
        self,
        sender: str,
        sender_level: AgentLevel,
        event_type: str,
        description: str,
        details: Dict[str, Any],
        recommended_action: Optional[str] = None,
        priority: MessagePriority = MessagePriority.HIGH,
        **kwargs
    ):
        """
        Initialise un nouveau message d'événement.
        
        Args:
            sender: Identifiant de l'émetteur
            sender_level: Niveau de l'émetteur
            event_type: Type d'événement (resource_warning, error, etc.)
            description: Description de l'événement
            details: Détails de l'événement
            recommended_action: Action recommandée (optionnel)
            priority: Priorité du message (par défaut: HIGH)
            **kwargs: Arguments supplémentaires pour la classe Message
        """
        content = {
            "event_type": event_type,
            "description": description,
            "details": details
        }
        
        if recommended_action:
            content["recommended_action"] = recommended_action
        
        super().__init__(
            message_type=MessageType.EVENT,
            sender=sender,
            sender_level=sender_level,
            content=content,
            recipient=None,  # Les événements sont généralement diffusés
            priority=priority,
            **kwargs
        )