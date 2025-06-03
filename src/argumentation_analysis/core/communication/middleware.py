"""
Middleware de messagerie central pour le système de communication multi-canal.

Ce module implémente le composant central qui gère tous les aspects de la communication
entre les agents à travers différents canaux spécialisés.
"""

import uuid
import threading
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union, Set
from datetime import datetime

from .message import Message, MessageType, MessagePriority, AgentLevel
from .channel_interface import Channel, ChannelType, ChannelException


class MessageMiddleware:
    """
    Middleware de messagerie central pour le système de communication multi-canal.
    
    Ce composant coordonne les échanges entre les agents à travers différents canaux
    spécialisés, gère le routage des messages et fournit une interface unifiée pour
    l'envoi et la réception de messages.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le middleware de messagerie.
        
        Args:
            config: Configuration du middleware (optionnel)
        """
        self.config = config or {}
        self.channels = {}  # Dictionnaire des canaux par type
        self.message_handlers = {}  # Gestionnaires de messages par type
        self.global_handlers = []  # Gestionnaires globaux pour tous les messages
        self.lock = threading.RLock()  # Verrou pour les opérations concurrentes
        
        # Configuration du logger
        self.logger = logging.getLogger("MessageMiddleware")
        self.logger.setLevel(logging.INFO)
        
        # Statistiques
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0,
            "by_channel": {},
            "by_type": {},
            "by_priority": {}
        }
        
        # Initialiser les protocoles
        self.request_response = None  # Sera initialisé plus tard
        self.publish_subscribe = None  # Sera initialisé plus tard
    
    def register_channel(self, channel: Channel) -> None:
        """
        Enregistre un canal auprès du middleware.
        
        Args:
            channel: Le canal à enregistrer
        """
        with self.lock:
            self.channels[channel.type] = channel
            self.stats["by_channel"][channel.type.value] = {
                "sent": 0,
                "received": 0,
                "errors": 0
            }
            self.logger.info(f"Channel registered: {channel.type.value}")
    
    def get_channel(self, channel_type: ChannelType) -> Optional[Channel]:
        """
        Récupère un canal par son type.
        
        Args:
            channel_type: Le type de canal
            
        Returns:
            Le canal ou None s'il n'existe pas
        """
        with self.lock:
            return self.channels.get(channel_type)
    
    def register_message_handler(self, message_type: MessageType, 
                               handler: Callable[[Message], None]) -> None:
        """
        Enregistre un gestionnaire pour un type de message spécifique.
        
        Args:
            message_type: Le type de message
            handler: La fonction de gestion
        """
        with self.lock:
            if message_type not in self.message_handlers:
                self.message_handlers[message_type] = []
            self.message_handlers[message_type].append(handler)
    
    def register_global_handler(self, handler: Callable[[Message], None]) -> None:
        """
        Enregistre un gestionnaire global pour tous les messages.
        
        Args:
            handler: La fonction de gestion
        """
        with self.lock:
            self.global_handlers.append(handler)
    
    def determine_channel(self, message: Message) -> ChannelType:
        """
        Détermine le canal approprié pour un message.
        
        Args:
            message: Le message à router
            
        Returns:
            Le type de canal approprié
        """
        # Si le canal est spécifié dans le message, l'utiliser
        if message.channel:
            try:
                return ChannelType(message.channel)
            except ValueError:
                self.logger.warning(f"Invalid channel specified in message: {message.channel}")
        
        # Règles de routage par défaut basées sur le type de message
        if message.type == MessageType.COMMAND:
            return ChannelType.HIERARCHICAL
        elif message.type == MessageType.INFORMATION:
            # Les informations peuvent aller sur différents canaux selon le contenu
            if "analysis_result" in message.content.get("info_type", ""):
                return ChannelType.DATA
            return ChannelType.HIERARCHICAL
        elif message.type == MessageType.REQUEST:
            request_type = message.content.get("request_type", "")
            if "assistance" in request_type:
                return ChannelType.COLLABORATION
            return ChannelType.HIERARCHICAL
        elif message.type == MessageType.RESPONSE:
            # Les réponses suivent généralement le même canal que la requête
            return ChannelType.HIERARCHICAL
        elif message.type == MessageType.EVENT:
            return ChannelType.FEEDBACK
        elif message.type == MessageType.CONTROL:
            return ChannelType.SYSTEM
        elif message.type == MessageType.PUBLICATION:
            return ChannelType.DATA
        elif message.type == MessageType.SUBSCRIPTION:
            return ChannelType.SYSTEM
        
        # Canal par défaut
        return ChannelType.HIERARCHICAL
    
    def send_message(self, message: Message) -> bool:
        """
        Envoie un message via le middleware.
        
        Args:
            message: Le message à envoyer
            
        Returns:
            True si le message a été envoyé avec succès, False sinon
        """
        try:
            # Déterminer le canal approprié
            channel_type = self.determine_channel(message)
            
            # Récupérer le canal
            channel = self.get_channel(channel_type)
            if not channel:
                self.logger.error(f"Channel not found: {channel_type.value}")
                return False
            
            # Mettre à jour le canal dans le message
            message.channel = channel_type.value
            
            # Envoyer le message via le canal
            success = channel.send_message(message)
            
            # Mettre à jour les statistiques
            with self.lock:
                self.stats["messages_sent"] += 1
                self.stats["by_channel"][channel_type.value]["sent"] += 1
                
                if message.type.value not in self.stats["by_type"]:
                    self.stats["by_type"][message.type.value] = 0
                self.stats["by_type"][message.type.value] += 1
                
                if message.priority.value not in self.stats["by_priority"]:
                    self.stats["by_priority"][message.priority.value] = 0
                self.stats["by_priority"][message.priority.value] += 1
            
            # Journaliser l'envoi
            self.logger.info(f"Message sent: {message.id} via {channel_type.value}")
            
            return success
            
        except Exception as e:
            # Mettre à jour les statistiques d'erreur
            with self.lock:
                self.stats["errors"] += 1
                if channel_type:
                    self.stats["by_channel"][channel_type.value]["errors"] += 1
            
            # Journaliser l'erreur
            self.logger.error(f"Error sending message: {str(e)}")
            return False
    
    def receive_message(self, recipient_id: str, channel_type: Optional[ChannelType] = None,
                      timeout: Optional[float] = None) -> Optional[Message]:
        """
        Reçoit un message pour un destinataire spécifique.
        
        Args:
            recipient_id: Identifiant du destinataire
            channel_type: Type de canal à écouter (optionnel)
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)
            
        Returns:
            Le message reçu ou None si timeout
        """
        try:
            # Si le canal est spécifié, écouter uniquement ce canal
            if channel_type:
                channel = self.get_channel(channel_type)
                if not channel:
                    self.logger.error(f"Channel not found: {channel_type.value}")
                    return None
                
                message = channel.receive_message(recipient_id, timeout)
                
                if message:
                    # Mettre à jour les statistiques
                    with self.lock:
                        self.stats["messages_received"] += 1
                        self.stats["by_channel"][channel_type.value]["received"] += 1
                    
                    # Vérifier si c'est une réponse à une requête en attente
                    if message.type == MessageType.RESPONSE and self.request_response:
                        request_id = message.metadata.get("reply_to")
                        if request_id:
                            self.logger.info(f"Received response {message.id} for request {request_id}")
                            result = self.request_response.handle_response(message)
                            self.logger.info(f"Response handler result: {result}")
                    
                    # Appeler les gestionnaires de messages
                    self._handle_message(message)
                
                return message
            
            # Sinon, écouter tous les canaux
            # Créer une liste de tous les canaux
            channels = list(self.channels.values())
            
            # Attendre un message sur n'importe quel canal
            # Implémentation simple: vérifier chaque canal séquentiellement
            # Une implémentation plus avancée utiliserait des files d'attente et des threads
            
            if timeout is not None:
                end_time = datetime.now().timestamp() + timeout
            
            while True:
                for channel in channels:
                    message = channel.receive_message(recipient_id, 0)  # Pas d'attente
                    
                    if message:
                        # Mettre à jour les statistiques
                        with self.lock:
                            self.stats["messages_received"] += 1
                            self.stats["by_channel"][channel.type.value]["received"] += 1
                        
                        # Vérifier si c'est une réponse à une requête en attente
                        if message.type == MessageType.RESPONSE and self.request_response:
                            request_id = message.metadata.get("reply_to")
                            if request_id:
                                self.logger.info(f"Received response {message.id} for request {request_id}")
                                result = self.request_response.handle_response(message)
                                self.logger.info(f"Response handler result: {result}")
                        
                        # Appeler les gestionnaires de messages
                        self._handle_message(message)
                        
                        return message
                
                # Vérifier si le timeout est atteint
                if timeout is not None and datetime.now().timestamp() > end_time:
                    return None
                
                # Petite pause pour éviter de surcharger le CPU
                threading.Event().wait(0.01)
            
        except Exception as e:
            # Mettre à jour les statistiques d'erreur
            with self.lock:
                self.stats["errors"] += 1
            
            # Journaliser l'erreur
            self.logger.error(f"Error receiving message: {str(e)}")
            return None
    
    async def receive_message_async(self, recipient_id: str, channel_type: Optional[ChannelType] = None,
                                 timeout: Optional[float] = None) -> Optional[Message]:
        """
        Version asynchrone de receive_message.
        
        Args:
            recipient_id: Identifiant du destinataire
            channel_type: Type de canal à écouter (optionnel)
            timeout: Délai d'attente maximum en secondes (None pour attente indéfinie)
            
        Returns:
            Le message reçu ou None si timeout
        """
        # Cette implémentation est simplifiée et utilise la version synchrone
        # Une implémentation complète utiliserait des primitives asyncio
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.receive_message(recipient_id, channel_type, timeout)
        )
    
    def _handle_message(self, message: Message) -> None:
        """
        Appelle les gestionnaires appropriés pour un message.
        
        Args:
            message: Le message à traiter
        """
        # Traitement spécial pour les réponses
        if message.type == MessageType.RESPONSE and self.request_response:
            request_id = message.metadata.get("reply_to")
            if request_id:
                self.logger.info(f"Handling response {message.id} for request {request_id}")
                try:
                    result = self.request_response.handle_response(message)
                    self.logger.info(f"Response handler result: {result}")
                    
                    # Si la réponse a été traitée avec succès, ne pas continuer avec les autres gestionnaires
                    if result:
                        return
                except Exception as e:
                    self.logger.error(f"Error in response handler: {str(e)}")
        
        # Appeler les gestionnaires spécifiques au type de message
        # Éviter d'appeler à nouveau le gestionnaire de réponses si c'est une réponse
        if message.type != MessageType.RESPONSE or not self.request_response:
            handlers = self.message_handlers.get(message.type, [])
            for handler in handlers:
                try:
                    handler(message)
                except Exception as e:
                    self.logger.error(f"Error in message handler: {str(e)}")
        
        # Appeler les gestionnaires globaux
        for handler in self.global_handlers:
            try:
                handler(message)
            except Exception as e:
                self.logger.error(f"Error in global handler: {str(e)}")
    
    def get_pending_messages(self, recipient_id: str, channel_type: Optional[ChannelType] = None,
                          max_count: Optional[int] = None) -> List[Message]:
        """
        Récupère les messages en attente pour un destinataire spécifique.
        
        Args:
            recipient_id: Identifiant du destinataire
            channel_type: Type de canal à vérifier (optionnel)
            max_count: Nombre maximum de messages à récupérer (None pour tous)
            
        Returns:
            Liste des messages en attente
        """
        messages = []
        
        try:
            # Si le canal est spécifié, vérifier uniquement ce canal
            if channel_type:
                channel = self.get_channel(channel_type)
                if not channel:
                    self.logger.error(f"Channel not found: {channel_type.value}")
                    return []
                
                return channel.get_pending_messages(recipient_id, max_count)
            
            # Sinon, vérifier tous les canaux
            remaining = max_count
            
            for channel in self.channels.values():
                channel_messages = channel.get_pending_messages(
                    recipient_id, 
                    remaining if remaining is not None else None
                )
                
                messages.extend(channel_messages)
                
                if remaining is not None:
                    remaining -= len(channel_messages)
                    if remaining <= 0:
                        break
            
            return messages
            
        except Exception as e:
            # Journaliser l'erreur
            self.logger.error(f"Error getting pending messages: {str(e)}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du middleware.
        
        Returns:
            Un dictionnaire de statistiques
        """
        with self.lock:
            return self.stats.copy()
    
    def get_channel_info(self, channel_type: ChannelType) -> Optional[Dict[str, Any]]:
        """
        Récupère des informations sur un canal.
        
        Args:
            channel_type: Le type de canal
            
        Returns:
            Un dictionnaire d'informations sur le canal ou None s'il n'existe pas
        """
        channel = self.get_channel(channel_type)
        if not channel:
            return None
        
        return channel.get_channel_info()
    
    def initialize_protocols(self):
        """Initialise les protocoles de communication."""
        from .request_response import RequestResponseProtocol
        from .pub_sub import PublishSubscribeProtocol
        
        self.request_response = RequestResponseProtocol(self)
        self.publish_subscribe = PublishSubscribeProtocol(self)
        
        # Ne pas enregistrer le gestionnaire de réponses ici car il est déjà appelé dans _handle_message
        # Cela évite le double traitement des réponses
        
        # Ajouter un gestionnaire global pour déboguer tous les messages
        self.register_global_handler(self._debug_message_handler)
    
    def _debug_message_handler(self, message: Message) -> None:
        """Gestionnaire de débogage pour tous les messages."""
        if message.type == MessageType.RESPONSE:
            request_id = message.metadata.get("reply_to")
            self.logger.info(f"DEBUG: Received response {message.id} for request {request_id}")
            
            # Ne pas appeler directement le gestionnaire de réponses ici
            # car il est déjà appelé dans _handle_message
    
    def send_request(self, *args, **kwargs):
        """
        Envoie une requête via le protocole de requête-réponse.
        
        Voir RequestResponseProtocol.send_request pour les paramètres.
        """
        if not self.request_response:
            self.initialize_protocols()
        
        return self.request_response.send_request(*args, **kwargs)
    
    async def send_request_async(self, *args, **kwargs):
        """
        Version asynchrone de send_request.
        
        Voir RequestResponseProtocol.send_request_async pour les paramètres.
        """
        if not self.request_response:
            self.initialize_protocols()
        
        return await self.request_response.send_request_async(*args, **kwargs)
    
    def publish(self, *args, **kwargs):
        """
        Publie un message via le protocole de publication-abonnement.
        
        Voir PublishSubscribeProtocol.publish pour les paramètres.
        """
        if not self.publish_subscribe:
            self.initialize_protocols()
        
        return self.publish_subscribe.publish(*args, **kwargs)
    
    def subscribe(self, *args, **kwargs):
        """
        Abonne un agent à un topic via le protocole de publication-abonnement.
        
        Voir PublishSubscribeProtocol.subscribe pour les paramètres.
        """
        if not self.publish_subscribe:
            self.initialize_protocols()
        
        return self.publish_subscribe.subscribe(*args, **kwargs)
    
    def shutdown(self):
        """Arrête proprement le middleware et tous ses composants."""
        # Arrêter les protocoles
        if self.request_response:
            self.request_response.shutdown()
        
        if self.publish_subscribe:
            self.publish_subscribe.shutdown()
        
        # Journaliser l'arrêt
        self.logger.info("MessageMiddleware shutdown")