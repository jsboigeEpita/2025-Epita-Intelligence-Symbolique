"""
Implémentation du protocole de publication-abonnement pour le système de communication multi-canal.

Ce protocole permet à des agents de publier des messages sur des sujets (topics)
auxquels d'autres agents peuvent s'abonner. Ce modèle découple les émetteurs des
récepteurs et permet une communication one-to-many efficace.
"""

import uuid
import threading
import asyncio
from typing import Dict, Any, Optional, Callable, List, Set
from datetime import datetime, timedelta

from .message import Message, MessageType, MessagePriority, AgentLevel


class Topic:
    """
    Représentation d'un sujet (topic) dans le système de publication-abonnement.
    
    Un topic est un canal logique sur lequel des messages peuvent être publiés
    et auquel des agents peuvent s'abonner.
    """
    
    def __init__(self, topic_id: str, description: Optional[str] = None, ttl: Optional[int] = None):
        """
        Initialise un nouveau topic.
        
        Args:
            topic_id: Identifiant unique du topic
            description: Description du topic (optionnel)
            ttl: Durée de vie par défaut des messages en secondes (optionnel)
        """
        self.id = topic_id
        self.description = description
        self.ttl = ttl
        self.subscribers = {}  # Dictionnaire des abonnés avec leurs filtres
        self.messages = []  # Historique des messages (pour les abonnés tardifs)
        self.max_history = 100  # Nombre maximum de messages à conserver
        self.lock = threading.RLock()  # Verrou pour les opérations concurrentes
    
    def add_subscriber(self, subscriber_id: str, callback: Optional[Callable[[Message], None]] = None,
                      filter_criteria: Optional[Dict[str, Any]] = None) -> str:
        """
        Ajoute un abonné à ce topic.
        
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
        
        return subscription_id
    
    def remove_subscriber(self, subscription_id: str) -> bool:
        """
        Supprime un abonné de ce topic.
        
        Args:
            subscription_id: Identifiant d'abonnement
            
        Returns:
            True si désabonnement réussi, False sinon
        """
        with self.lock:
            if subscription_id in self.subscribers:
                del self.subscribers[subscription_id]
                return True
            return False
    
    def publish_message(self, message: Message) -> List[str]:
        """
        Publie un message sur ce topic et le distribue aux abonnés.
        
        Args:
            message: Le message à publier
            
        Returns:
            Liste des identifiants des abonnés qui ont reçu le message
        """
        recipients = []
        
        with self.lock:
            # Ajouter le message à l'historique
            self.messages.append({
                "message": message,
                "published_at": datetime.now()
            })
            
            # Limiter la taille de l'historique
            if len(self.messages) > self.max_history:
                self.messages = self.messages[-self.max_history:]
            
            # Distribuer le message aux abonnés
            for subscription_id, subscriber in self.subscribers.items():
                # Vérifier si le message correspond aux critères de filtrage
                if self._matches_filter(message, subscriber.get("filter_criteria")):
                    # Appeler le callback si présent
                    if subscriber.get("callback"):
                        try:
                            subscriber["callback"](message)
                        except Exception as e:
                            print(f"Error in subscriber callback: {e}")
                    
                    recipients.append(subscriber["subscriber_id"])
        
        return recipients
    
    def get_recent_messages(self, count: Optional[int] = None, 
                           filter_criteria: Optional[Dict[str, Any]] = None) -> List[Message]:
        """
        Récupère les messages récents de ce topic.
        
        Args:
            count: Nombre maximum de messages à récupérer (None pour tous)
            filter_criteria: Critères de filtrage des messages (optionnel)
            
        Returns:
            Liste des messages récents
        """
        with self.lock:
            # Filtrer les messages selon les critères
            filtered_messages = [
                entry["message"] for entry in self.messages
                if not filter_criteria or self._matches_filter(entry["message"], filter_criteria)
            ]
            
            # Limiter le nombre de messages
            if count is not None:
                filtered_messages = filtered_messages[-count:]
            
            return filtered_messages
    
    def _matches_filter(self, message: Message, filter_criteria: Optional[Dict[str, Any]]) -> bool:
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
            if key == "sender":
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
    
    def get_subscriber_count(self) -> int:
        """
        Récupère le nombre d'abonnés à ce topic.
        
        Returns:
            Le nombre d'abonnés
        """
        with self.lock:
            return len(self.subscribers)
    
    def get_message_count(self) -> int:
        """
        Récupère le nombre de messages dans l'historique de ce topic.
        
        Returns:
            Le nombre de messages
        """
        with self.lock:
            return len(self.messages)
    
    def get_topic_info(self) -> Dict[str, Any]:
        """
        Récupère des informations sur ce topic.
        
        Returns:
            Un dictionnaire d'informations sur le topic
        """
        with self.lock:
            return {
                "id": self.id,
                "description": self.description,
                "ttl": self.ttl,
                "subscriber_count": len(self.subscribers),
                "message_count": len(self.messages),
                "created_at": self.messages[0]["published_at"].isoformat() if self.messages else None,
                "last_message_at": self.messages[-1]["published_at"].isoformat() if self.messages else None
            }


class PublishSubscribeProtocol:
    """
    Implémentation du protocole de publication-abonnement.
    
    Ce protocole gère la création de topics, l'abonnement des agents et la
    publication de messages.
    """
    
    def __init__(self, middleware):
        """
        Initialise le protocole de publication-abonnement.
        
        Args:
            middleware: Le middleware de messagerie à utiliser pour l'envoi et la réception
        """
        self.middleware = middleware
        self.topics = {}  # Dictionnaire des topics
        self.lock = threading.RLock()  # Verrou pour les opérations concurrentes
        
        # Démarrer le thread de nettoyage des messages expirés
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired_messages)
        self.cleanup_thread.daemon = True
        self.cleanup_thread.start()
    
    def create_topic(self, topic_id: str, description: Optional[str] = None, 
                    ttl: Optional[int] = None) -> Topic:
        """
        Crée un nouveau topic.
        
        Args:
            topic_id: Identifiant unique du topic
            description: Description du topic (optionnel)
            ttl: Durée de vie par défaut des messages en secondes (optionnel)
            
        Returns:
            Le topic créé
        """
        with self.lock:
            if topic_id in self.topics:
                return self.topics[topic_id]
            
            topic = Topic(topic_id, description, ttl)
            self.topics[topic_id] = topic
            return topic
    
    def get_topic(self, topic_id: str) -> Optional[Topic]:
        """
        Récupère un topic existant.
        
        Args:
            topic_id: Identifiant du topic
            
        Returns:
            Le topic ou None s'il n'existe pas
        """
        with self.lock:
            return self.topics.get(topic_id)
    
    def delete_topic(self, topic_id: str) -> bool:
        """
        Supprime un topic.
        
        Args:
            topic_id: Identifiant du topic
            
        Returns:
            True si suppression réussie, False sinon
        """
        with self.lock:
            if topic_id in self.topics:
                del self.topics[topic_id]
                return True
            return False
    
    def publish(
        self,
        topic_id: str,
        sender: str,
        sender_level: AgentLevel,
        content: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Publie un message sur un topic.
        
        Args:
            topic_id: Identifiant du topic
            sender: Identifiant de l'émetteur
            sender_level: Niveau de l'émetteur
            content: Contenu du message
            priority: Priorité du message
            ttl: Durée de vie du message en secondes (optionnel)
            metadata: Métadonnées additionnelles (optionnel)
            
        Returns:
            Liste des identifiants des abonnés qui ont reçu le message
        """
        # Créer ou récupérer le topic
        topic = self.create_topic(topic_id)
        
        # Créer le message
        message = Message(
            message_type=MessageType.PUBLICATION,
            sender=sender,
            sender_level=sender_level,
            content=content,
            recipient=None,  # Pas de destinataire spécifique
            channel=None,  # Le canal sera déterminé par le middleware
            priority=priority,
            metadata={
                "topic": topic_id,
                "ttl": ttl or topic.ttl,
                **(metadata or {})
            }
        )
        
        # Publier le message sur le topic
        recipients = topic.publish_message(message)
        
        # Envoyer le message via le middleware
        self.middleware.send_message(message)
        
        return recipients
    
    def subscribe(
        self,
        topic_id: str,
        subscriber_id: str,
        callback: Optional[Callable[[Message], None]] = None,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Abonne un agent à un topic.
        
        Args:
            topic_id: Identifiant du topic
            subscriber_id: Identifiant de l'abonné
            callback: Fonction de rappel à appeler lors de la réception d'un message (optionnel)
            filter_criteria: Critères de filtrage des messages (optionnel)
            
        Returns:
            Un identifiant d'abonnement
        """
        # Créer ou récupérer le topic
        topic = self.create_topic(topic_id)
        
        # Ajouter l'abonné au topic
        subscription_id = topic.add_subscriber(subscriber_id, callback, filter_criteria)
        
        # Créer un message d'abonnement
        message = Message(
            message_type=MessageType.SUBSCRIPTION,
            sender=subscriber_id,
            sender_level=AgentLevel.SYSTEM,  # À remplacer par le niveau réel de l'agent
            content={
                "topic": topic_id,
                "filter": filter_criteria
            },
            recipient=None,  # Pas de destinataire spécifique
            channel=None,  # Le canal sera déterminé par le middleware
            priority=MessagePriority.NORMAL,
            metadata={
                "subscription_id": subscription_id
            }
        )
        
        # Envoyer le message d'abonnement via le middleware
        self.middleware.send_message(message)
        
        return subscription_id
    
    def unsubscribe(self, topic_id: str, subscription_id: str) -> bool:
        """
        Désabonne un agent d'un topic.
        
        Args:
            topic_id: Identifiant du topic
            subscription_id: Identifiant d'abonnement
            
        Returns:
            True si désabonnement réussi, False sinon
        """
        topic = self.get_topic(topic_id)
        if not topic:
            return False
        
        return topic.remove_subscriber(subscription_id)
    
    def get_topics(self) -> List[str]:
        """
        Récupère la liste des identifiants de tous les topics.
        
        Returns:
            Liste des identifiants de topics
        """
        with self.lock:
            return list(self.topics.keys())
    
    def get_topic_info(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère des informations sur un topic.
        
        Args:
            topic_id: Identifiant du topic
            
        Returns:
            Un dictionnaire d'informations sur le topic ou None s'il n'existe pas
        """
        topic = self.get_topic(topic_id)
        if not topic:
            return None
        
        return topic.get_topic_info()
    
    def _cleanup_expired_messages(self):
        """Thread qui nettoie périodiquement les messages expirés."""
        while self.running:
            try:
                now = datetime.now()
                
                with self.lock:
                    for topic_id, topic in self.topics.items():
                        with topic.lock:
                            # Filtrer les messages non expirés
                            topic.messages = [
                                entry for entry in topic.messages
                                if not entry["message"].metadata.get("ttl") or
                                entry["published_at"] + timedelta(seconds=entry["message"].metadata["ttl"]) > now
                            ]
                
                # Attendre avant le prochain nettoyage
                threading.Event().wait(60)  # Nettoyer toutes les minutes
                
            except Exception as e:
                print(f"Error in message cleanup: {e}")
                threading.Event().wait(5)  # Attendre un peu en cas d'erreur
    
    def shutdown(self):
        """Arrête proprement le protocole."""
        self.running = False
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=2)