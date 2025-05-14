"""
Interfaces pour les canaux de communication du système multi-canal.

Ce module définit les interfaces abstraites que tous les canaux de communication
doivent implémenter, ainsi que les types de canaux supportés.
"""

import enum
import abc
from typing import Dict, Any, Optional, List, Callable, Union
from .message import Message, MessageType, MessagePriority

from argumentiation_analysis.paths import DATA_DIR



class ChannelType(enum.Enum):
    """Types de canaux supportés par le système."""
    HIERARCHICAL = "hierarchical"  # Communication verticale entre niveaux hiérarchiques
    COLLABORATION = "collaboration"  # Communication horizontale entre agents de même niveau
    DATA = DATA_DIR  # Transfert de données volumineuses
    NEGOTIATION = "negotiation"  # Résolution de conflits et allocation de ressources
    FEEDBACK = "feedback"  # Remontée d'informations et suggestions
    SYSTEM = "system"  # Messages de contrôle du système


class Channel(abc.ABC):
    """
    Interface abstraite pour tous les canaux de communication.
    
    Tous les canaux doivent implémenter cette interface pour assurer
    l'interopérabilité avec le middleware de messagerie.
    """
    
    def __init__(self, channel_id: str, channel_type: ChannelType, config: Optional[Dict[str, Any]] = None):
        """
        Initialise un nouveau canal.
        
        Args:
            channel_id: Identifiant unique du canal
            channel_type: Type du canal
            config: Configuration spécifique au canal (optionnel)
        """
        self.id = channel_id
        self.type = channel_type
        self.config = config or {}
        self.subscribers = {}  # Dictionnaire des abonnés avec leurs filtres
    
    @abc.abstractmethod
    def send_message(self, message: Message) -> bool:
        """
        Envoie un message via ce canal.
        
        Args:
            message: Le message à envoyer
            
        Returns:
            True si le message a été envoyé avec succès, False sinon
        """
        pass
    
    @abc.abstractmethod
    def receive_message(self, recipient_id: str, timeout: Optional[float] = None) -> Optional[Message]:
        """
        Reçoit un message de ce canal pour un destinataire spécifique.
        
        Args:
            recipient_id: Identifiant du destinataire
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)
            
        Returns:
            Le message reçu ou None si timeout
        """
        pass
    
    @abc.abstractmethod
    def subscribe(self, subscriber_id: str, callback: Optional[Callable[[Message], None]] = None, 
                 filter_criteria: Optional[Dict[str, Any]] = None) -> str:
        """
        Abonne un agent à ce canal.
        
        Args:
            subscriber_id: Identifiant de l'abonné
            callback: Fonction de rappel à appeler lors de la réception d'un message (optionnel)
            filter_criteria: Critères de filtrage des messages (optionnel)
            
        Returns:
            Un identifiant d'abonnement
        """
        pass
    
    @abc.abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Désabonne un agent de ce canal.
        
        Args:
            subscription_id: Identifiant d'abonnement
            
        Returns:
            True si désabonnement réussi, False sinon
        """
        pass
    
    @abc.abstractmethod
    def get_pending_messages(self, recipient_id: str, max_count: Optional[int] = None) -> List[Message]:
        """
        Récupère les messages en attente pour un destinataire spécifique.
        
        Args:
            recipient_id: Identifiant du destinataire
            max_count: Nombre maximum de messages à récupérer (None pour tous)
            
        Returns:
            Liste des messages en attente
        """
        pass
    
    @abc.abstractmethod
    def get_channel_info(self) -> Dict[str, Any]:
        """
        Récupère des informations sur ce canal.
        
        Returns:
            Un dictionnaire d'informations sur le canal
        """
        pass
    
    def matches_filter(self, message: Message, filter_criteria: Dict[str, Any]) -> bool:
        """
        Vérifie si un message correspond aux critères de filtrage.
        
        Args:
            message: Le message à vérifier
            filter_criteria: Les critères de filtrage
            
        Returns:
            True si le message correspond aux critères, False sinon
        """
        if not filter_criteria:
            return True
        
        # Vérifier les critères de base
        for key, value in filter_criteria.items():
            if key == "message_type":
                if isinstance(value, list):
                    if message.type.value not in value:
                        return False
                elif message.type.value != value:
                    return False
            elif key == "sender":
                if isinstance(value, list):
                    if message.sender not in value:
                        return False
                elif message.sender != value:
                    return False
            elif key == "priority":
                if isinstance(value, list):
                    if message.priority.value not in value:
                        return False
                elif message.priority.value != value:
                    return False
            elif key == "sender_level":
                if isinstance(value, list):
                    if message.sender_level.value not in value:
                        return False
                elif message.sender_level.value != value:
                    return False
        
        # Vérifier les critères de contenu
        if "content" in filter_criteria:
            content_filter = filter_criteria["content"]
            for content_key, content_value in content_filter.items():
                if content_key not in message.content:
                    return False
                if isinstance(content_value, list):
                    if message.content[content_key] not in content_value:
                        return False
                elif message.content[content_key] != content_value:
                    return False
        
        return True


class ChannelException(Exception):
    """Exception de base pour les erreurs liées aux canaux."""
    pass


class ChannelFullException(ChannelException):
    """Exception levée lorsqu'un canal est plein."""
    pass


class ChannelTimeoutException(ChannelException):
    """Exception levée lorsqu'une opération sur un canal expire."""
    pass


class ChannelClosedException(ChannelException):
    """Exception levée lorsqu'une opération est tentée sur un canal fermé."""
    pass


class InvalidMessageException(ChannelException):
    """Exception levée lorsqu'un message invalide est envoyé sur un canal."""
    pass


class UnauthorizedAccessException(ChannelException):
    """Exception levée lorsqu'un accès non autorisé est tenté sur un canal."""
    pass