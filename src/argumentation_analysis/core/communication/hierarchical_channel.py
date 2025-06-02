"""
Implémentation du canal hiérarchique pour le système de communication multi-canal.

Ce canal est dédié aux communications formelles entre les différents niveaux
de la hiérarchie (stratégique, tactique, opérationnel). Il est optimisé pour
les communications verticales et suit un modèle de communication structuré.
"""

import uuid
import threading
import queue
import logging
from typing import Dict, Any, Optional, List, Callable, Set
from datetime import datetime

from .channel_interface import Channel, ChannelType, ChannelException, ChannelTimeoutException
from .message import Message, MessageType, MessagePriority, AgentLevel


class HierarchicalChannel(Channel):
    """
    Canal de communication hiérarchique pour les échanges formels entre niveaux.
    
    Ce canal supporte les communications bidirectionnelles entre les niveaux
    stratégique, tactique et opérationnel, avec garantie de livraison et
    ordonnancement des messages.
    """
    
    def __init__(self, channel_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialise un nouveau canal hiérarchique.
        
        Args:
            channel_id: Identifiant unique du canal
            config: Configuration spécifique au canal (optionnel)
        """
        super().__init__(channel_id, ChannelType.HIERARCHICAL, config)
        
        # Files d'attente de messages par destinataire
        self.message_queues = {}
        
        # Verrou pour les opérations concurrentes
        self.lock = threading.RLock()
        
        # Configuration du logger
        self.logger = logging.getLogger(f"HierarchicalChannel.{channel_id}")
        self.logger.setLevel(logging.INFO)
        
        # Statistiques
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "by_direction": {
                "strategic_to_tactical": 0,
                "tactical_to_strategic": 0,
                "tactical_to_operational": 0,
                "operational_to_tactical": 0,
                "same_level": 0
            },
            "by_priority": {
                "low": 0,
                "normal": 0,
                "high": 0,
                "critical": 0
            }
        }
    
    def send_message(self, message: Message) -> bool:
        """
        Envoie un message via ce canal.
        
        Args:
            message: Le message à envoyer
            
        Returns:
            True si le message a été envoyé avec succès, False sinon
        """
        try:
            # Vérifier que le message a un destinataire
            if not message.recipient:
                self.logger.error(f"Message {message.id} has no recipient")
                return False
            
            # Vérifier que le message a un type valide pour ce canal
            valid_types = [
                MessageType.COMMAND, MessageType.INFORMATION,
                MessageType.REQUEST, MessageType.RESPONSE
            ]
            if message.type not in valid_types:
                self.logger.warning(f"Message type {message.type} not ideal for hierarchical channel")
            
            # Créer la file d'attente du destinataire si elle n'existe pas
            with self.lock:
                if message.recipient not in self.message_queues:
                    self.message_queues[message.recipient] = queue.PriorityQueue()
            
            # Déterminer la priorité numérique (plus petit = plus prioritaire)
            priority_values = {
                MessagePriority.CRITICAL: 0,
                MessagePriority.HIGH: 1,
                MessagePriority.NORMAL: 2,
                MessagePriority.LOW: 3
            }
            priority_value = priority_values.get(message.priority, 2)
            
            # Ajouter le message à la file d'attente du destinataire
            self.message_queues[message.recipient].put((priority_value, datetime.now(), message))
            
            # Mettre à jour les statistiques
            with self.lock:
                self.stats["messages_sent"] += 1
                self.stats["by_priority"][message.priority.value] += 1
                
                # Déterminer la direction de la communication
                if message.sender_level == AgentLevel.STRATEGIC and message.recipient.startswith("tactical"):
                    self.stats["by_direction"]["strategic_to_tactical"] += 1
                elif message.sender_level == AgentLevel.TACTICAL and message.recipient.startswith("strategic"):
                    self.stats["by_direction"]["tactical_to_strategic"] += 1
                elif message.sender_level == AgentLevel.TACTICAL and message.recipient.startswith("operational"):
                    self.stats["by_direction"]["tactical_to_operational"] += 1
                elif message.sender_level == AgentLevel.OPERATIONAL and message.recipient.startswith("tactical"):
                    self.stats["by_direction"]["operational_to_tactical"] += 1
                else:
                    self.stats["by_direction"]["same_level"] += 1
            
            # Notifier les abonnés si nécessaire
            self._notify_subscribers(message)
            
            self.logger.info(f"Message {message.id} sent to {message.recipient}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            return False
    
    def receive_message(self, recipient_id: str, timeout: Optional[float] = None) -> Optional[Message]:
        """
        Reçoit un message de ce canal pour un destinataire spécifique.
        
        Args:
            recipient_id: Identifiant du destinataire
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)
            
        Returns:
            Le message reçu ou None si timeout
        """
        try:
            # Vérifier si le destinataire a une file d'attente
            with self.lock:
                if recipient_id not in self.message_queues:
                    self.message_queues[recipient_id] = queue.PriorityQueue()
            
            q_size = self.message_queues[recipient_id].qsize()
            self.logger.info(f"Attempting to get message for {recipient_id}. Queue size: {q_size}. Timeout: {timeout}")
            
            # Récupérer un message de la file d'attente
            try:
                priority, timestamp, message_obj = self.message_queues[recipient_id].get(block=True, timeout=timeout)
                self.logger.info(f"Successfully got message {message_obj.id} for {recipient_id} from queue.")
                
                # Mettre à jour les statistiques
                with self.lock:
                    self.stats["messages_received"] += 1
                
                self.logger.info(f"Message {message_obj.id} received by {recipient_id}")
                return message_obj
                
            except queue.Empty:
                self.logger.warning(f"Queue empty for {recipient_id} after timeout {timeout}s.")
                return None
            
        except Exception as e:
            self.logger.error(f"Error receiving message: {str(e)}")
            return None
    
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
        subscription_id = f"sub-{uuid.uuid4().hex[:8]}"
        
        with self.lock:
            self.subscribers[subscription_id] = {
                "subscriber_id": subscriber_id,
                "callback": callback,
                "filter_criteria": filter_criteria,
                "created_at": datetime.now()
            }
        
        self.logger.info(f"Subscriber {subscriber_id} registered with ID {subscription_id}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Désabonne un agent de ce canal.
        
        Args:
            subscription_id: Identifiant d'abonnement
            
        Returns:
            True si désabonnement réussi, False sinon
        """
        with self.lock:
            if subscription_id in self.subscribers:
                subscriber_id = self.subscribers[subscription_id]["subscriber_id"]
                del self.subscribers[subscription_id]
                self.logger.info(f"Subscriber {subscriber_id} unregistered (ID {subscription_id})")
                return True
            
            self.logger.warning(f"Subscription ID {subscription_id} not found")
            return False
    
    def get_pending_messages(self, recipient_id: str, max_count: Optional[int] = None) -> List[Message]:
        """
        Récupère les messages en attente pour un destinataire spécifique.
        
        Args:
            recipient_id: Identifiant du destinataire
            max_count: Nombre maximum de messages à récupérer (None pour tous)
            
        Returns:
            Liste des messages en attente
        """
        messages = []
        
        with self.lock:
            # Vérifier si le destinataire a une file d'attente
            if recipient_id not in self.message_queues:
                return []
            
            # Créer une nouvelle file d'attente pour stocker les messages
            new_queue = queue.PriorityQueue()
            original_queue = self.message_queues[recipient_id]
            
            # Récupérer tous les messages tout en les préservant
            count = 0
            items = []
            
            # Extraire tous les éléments de la file d'origine
            while not original_queue.empty():
                item = original_queue.get()
                items.append(item)
            
            # Traiter les éléments extraits
            for item in items:
                # Ajouter le message à la liste de résultats si la limite n'est pas atteinte
                if max_count is None or count < max_count:
                    messages.append(item[2])  # Le message est le 3ème élément du tuple
                    count += 1
                
                # Remettre l'élément dans la nouvelle file d'attente
                new_queue.put(item)
            
            # Remplacer la file d'origine par la nouvelle
            self.message_queues[recipient_id] = new_queue
            
            self.logger.info(f"Retrieved {len(messages)} pending messages for {recipient_id}")
        
        return messages
    
    def get_channel_info(self) -> Dict[str, Any]:
        """
        Récupère des informations sur ce canal.
        
        Returns:
            Un dictionnaire d'informations sur le canal
        """
        with self.lock:
            queue_sizes = {
                recipient: queue_obj.qsize()
                for recipient, queue_obj in self.message_queues.items()
            }
            
            return {
                "id": self.id,
                "type": self.type.value,
                "stats": self.stats,
                "queue_sizes": queue_sizes,
                "subscriber_count": len(self.subscribers)
            }
    
    def _notify_subscribers(self, message: Message) -> None:
        """
        Notifie les abonnés intéressés par un message.
        
        Args:
            message: Le message à notifier
        """
        with self.lock:
            for subscription_id, subscriber in self.subscribers.items():
                # Vérifier si le message correspond aux critères de filtrage
                if self.matches_filter(message, subscriber.get("filter_criteria")):
                    # Appeler le callback si présent
                    if subscriber.get("callback"):
                        try:
                            subscriber["callback"](message)
                        except Exception as e:
                            self.logger.error(f"Error in subscriber callback: {str(e)}")
    
    def clear_queue(self, recipient_id: str) -> int:
        """
        Vide la file d'attente d'un destinataire.
        
        Args:
            recipient_id: Identifiant du destinataire
            
        Returns:
            Le nombre de messages supprimés
        """
        with self.lock:
            if recipient_id not in self.message_queues:
                return 0
            
            # Compter le nombre de messages
            count = self.message_queues[recipient_id].qsize()
            
            # Créer une nouvelle file vide
            self.message_queues[recipient_id] = queue.PriorityQueue()
            
            self.logger.info(f"Cleared {count} messages from queue of {recipient_id}")
            return count