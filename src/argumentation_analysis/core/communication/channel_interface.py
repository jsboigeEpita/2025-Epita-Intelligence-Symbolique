"""
Interfaces pour les canaux de communication du système multi-canal.

Ce module définit les interfaces abstraites que tous les canaux de communication
doivent implémenter, ainsi que les types de canaux supportés.
"""

import enum
import abc
from typing import Dict, Any, Optional, List, Callable, Union
import logging # Ajout pour LocalChannel
from .message import Message, MessageType, MessagePriority

from argumentation_analysis.paths import DATA_DIR


logger_channel = logging.getLogger(__name__) # Logger pour ce module

class ChannelType(enum.Enum):
    """Types de canaux supportés par le système."""
    HIERARCHICAL = "hierarchical"
    COLLABORATION = "collaboration"
    DATA = DATA_DIR 
    NEGOTIATION = "negotiation"
    FEEDBACK = "feedback"
    SYSTEM = "system"
    LOCAL = "local" # Ajout pour LocalChannel


class Channel(abc.ABC):
    """
    Interface abstraite pour tous les canaux de communication.
    """
    
    def __init__(self, channel_id: str, channel_type: ChannelType, config: Optional[Dict[str, Any]] = None):
        self.id = channel_id
        self.type = channel_type
        self.config = config or {}
        self.subscribers: Dict[str, Dict[str, Any]] = {} # subscriber_id -> {"callback": callback, "filter": filter}
        self._message_queue: List[Message] = [] # Simple file d'attente en mémoire pour LocalChannel
    
    @abc.abstractmethod
    def send_message(self, message: Message) -> bool:
        pass
    
    @abc.abstractmethod
    def receive_message(self, recipient_id: str, timeout: Optional[float] = None) -> Optional[Message]:
        pass
    
    @abc.abstractmethod
    def subscribe(self, subscriber_id: str, callback: Optional[Callable[[Message], None]] = None, 
                 filter_criteria: Optional[Dict[str, Any]] = None) -> str:
        pass
    
    @abc.abstractmethod
    def unsubscribe(self, subscription_id: str) -> bool:
        pass
    
    @abc.abstractmethod
    def get_pending_messages(self, recipient_id: str, max_count: Optional[int] = None) -> List[Message]:
        pass
    
    @abc.abstractmethod
    def get_channel_info(self) -> Dict[str, Any]:
        pass
    
    def matches_filter(self, message: Message, filter_criteria: Dict[str, Any]) -> bool:
        if not filter_criteria:
            return True
        for key, value in filter_criteria.items():
            if key == "message_type":
                if isinstance(value, list):
                    if message.type.value not in value: return False
                elif message.type.value != value: return False
            elif key == "sender":
                if isinstance(value, list):
                    if message.sender not in value: return False
                elif message.sender != value: return False
            elif key == "priority":
                if isinstance(value, list):
                    if message.priority.value not in value: return False
                elif message.priority.value != value: return False
            elif key == "sender_level":
                if isinstance(value, list):
                    if message.sender_level.value not in value: return False # Assumant que sender_level a .value
                elif message.sender_level.value != value: return False # Assumant que sender_level a .value
            elif key == "content": # Filtre de contenu simple
                content_filter = value
                for content_key, content_val in content_filter.items():
                    if content_key not in message.content or message.content[content_key] != content_val:
                        return False
            # Ajouter d'autres logiques de filtrage si nécessaire
        return True

# Implémentation simple de LocalChannel pour les tests
class LocalChannel(Channel):
    """
    Un canal de communication simple en mémoire pour les tests ou la communication locale.
    """
    def __init__(self, channel_id: str, middleware: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        # Le middleware n'est pas directement utilisé par ce canal simple, mais l'API est conservée.
        # Le type est défini comme LOCAL.
        super().__init__(channel_id, ChannelType.LOCAL, config)
        self._middleware = middleware # Peut être utilisé pour des interactions plus complexes si nécessaire
        logger_channel.info(f"Canal local '{channel_id}' créé.")

    def send_message(self, message: Message) -> bool:
        logger_channel.debug(f"Canal '{self.id}': Envoi du message {message.id} de {message.sender} à {message.recipient}")
        # Pour un canal local simple, on pourrait directement appeler les callbacks des abonnés
        # ou ajouter à une file d'attente que les destinataires peuvent interroger.
        
        # Version simple: ajouter à une file et notifier les abonnés qui correspondent au filtre
        self._message_queue.append(message) # Pour receive_message
        
        for sub_id, sub_info in list(self.subscribers.items()): # list() pour permettre la désinscription pendant l'itération
            callback = sub_info.get("callback")
            filter_criteria = sub_info.get("filter")
            
            if self.matches_filter(message, filter_criteria or {}):
                if callback:
                    try:
                        logger_channel.debug(f"Canal '{self.id}': Notification de l'abonné {sub_id} pour le message {message.id}")
                        callback(message)
                    except Exception as e:
                        logger_channel.error(f"Canal '{self.id}': Erreur lors de l'appel du callback pour {sub_id}: {e}")
                # Si pas de callback, l'abonné doit utiliser receive_message ou get_pending_messages
        return True

    def receive_message(self, recipient_id: str, timeout: Optional[float] = None) -> Optional[Message]:
        # Implémentation simple: retourne le premier message pour ce destinataire
        # Pas de gestion de timeout ou de blocage réel ici pour la simplicité
        for i, msg in enumerate(self._message_queue):
            if msg.recipient == recipient_id or recipient_id == "*": # "*" pour écouter tous les messages
                logger_channel.debug(f"Canal '{self.id}': Message {msg.id} reçu par {recipient_id}")
                return self._message_queue.pop(i)
        return None

    def subscribe(self, subscriber_id: str, callback: Optional[Callable[[Message], None]] = None, 
                 filter_criteria: Optional[Dict[str, Any]] = None) -> str:
        subscription_id = f"{self.id}_{subscriber_id}_{len(self.subscribers)}" # ID d'abonnement simple
        self.subscribers[subscription_id] = {
            "callback": callback,
            "filter": filter_criteria or {},
            "subscriber_id": subscriber_id # Garder une trace de qui est l'abonné
        }
        logger_channel.info(f"Canal '{self.id}': Abonné {subscriber_id} enregistré avec ID {subscription_id}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        if subscription_id in self.subscribers:
            del self.subscribers[subscription_id]
            logger_channel.info(f"Canal '{self.id}': Abonnement {subscription_id} supprimé")
            return True
        logger_channel.warning(f"Canal '{self.id}': Tentative de désabonnement pour ID inexistant {subscription_id}")
        return False

    def get_pending_messages(self, recipient_id: str, max_count: Optional[int] = None) -> List[Message]:
        pending = []
        remaining_messages = []
        count = 0
        for msg in self._message_queue:
            if msg.recipient == recipient_id or recipient_id == "*":
                if max_count is None or count < max_count:
                    pending.append(msg)
                    count += 1
                else:
                    remaining_messages.append(msg) # Garder les messages non récupérés
            else:
                remaining_messages.append(msg)
        self._message_queue = remaining_messages # Mettre à jour la file
        logger_channel.debug(f"Canal '{self.id}': {len(pending)} messages en attente récupérés par {recipient_id}")
        return pending

    def get_channel_info(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "config": self.config,
            "subscriber_count": len(self.subscribers),
            "pending_message_count": len(self._message_queue)
        }

class ChannelException(Exception):
    """Exception de base pour les erreurs liées aux canaux."""
    pass

class ChannelFullException(ChannelException):
    pass

class ChannelTimeoutException(ChannelException):
    pass

class ChannelClosedException(ChannelException):
    pass

class InvalidMessageException(ChannelException):
    pass

class UnauthorizedAccessException(ChannelException):
    pass