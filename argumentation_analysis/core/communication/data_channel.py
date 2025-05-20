"""
Implémentation du canal de données pour le système de communication multi-canal.

Ce canal est spécialisé dans le transfert efficace de volumes importants de données
structurées entre agents, comme des résultats d'analyse, des extraits de texte
ou des représentations formelles.
"""

import uuid
import threading
import logging
import json
import gzip
import base64
from typing import Dict, Any, Optional, List, Callable, Set, Tuple
from datetime import datetime
from collections import defaultdict

from .channel_interface import Channel, ChannelType, ChannelException
from .message import Message, MessageType, MessagePriority, AgentLevel

from argumentation_analysis.paths import DATA_DIR



class DataStore:
    """
    Stockage de données pour le canal de données.
    
    Cette classe gère le stockage et la récupération des données volumineuses,
    avec support pour la compression, le versionnement et le streaming.
    """
    
    def __init__(self, store_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialise un nouveau stockage de données.
        
        Args:
            store_id: Identifiant unique du stockage
            config: Configuration du stockage (optionnel)
        """
        self.id = store_id
        self.config = config or {}
        self.data_items = {}  # Dictionnaire des éléments de données par ID
        self.versions = defaultdict(list)  # Historique des versions par ID de données
        self.lock = threading.RLock()
        self.logger = logging.getLogger(f"DataStore.{store_id}")
    
    def store_data(self, data_id: str, data: Any, metadata: Optional[Dict[str, Any]] = None,
                 compress: bool = True) -> str:
        """
        Stocke un élément de données.
        
        Args:
            data_id: Identifiant de l'élément de données
            data: Les données à stocker
            metadata: Métadonnées associées aux données (optionnel)
            compress: Indique si les données doivent être compressées (par défaut: True)
            
        Returns:
            L'identifiant de version de l'élément de données
        """
        version_id = f"v-{uuid.uuid4().hex[:8]}"
        
        with self.lock:
            # Sérialiser les données
            serialized_data = self._serialize_data(data)
            
            # Compresser les données si nécessaire
            if compress and len(serialized_data) > 1024:  # Seuil de compression
                compressed_data = gzip.compress(serialized_data.encode('utf-8'))
                data_content = base64.b64encode(compressed_data).decode('utf-8')
                is_compressed = True
            else:
                data_content = serialized_data
                is_compressed = False
            
            # Créer l'élément de données
            data_item = {
                "id": data_id,
                "version_id": version_id,
                "content": data_content,
                "metadata": metadata or {},
                "is_compressed": is_compressed,
                "size": len(serialized_data),
                "compressed_size": len(data_content) if is_compressed else None,
                "created_at": datetime.now().isoformat()
            }
            
            # Stocker l'élément de données
            self.data_items[f"{data_id}:{version_id}"] = data_item
            
            # Ajouter la version à l'historique
            self.versions[data_id].append(version_id)
            
            self.logger.info(f"Data item {data_id} stored with version {version_id}")
            return version_id
    
    def get_data(self, data_id: str, version_id: Optional[str] = None) -> Tuple[Any, Dict[str, Any]]:
        """
        Récupère un élément de données.
        
        Args:
            data_id: Identifiant de l'élément de données
            version_id: Identifiant de version (None pour la dernière version)
            
        Returns:
            Un tuple (données, métadonnées)
            
        Raises:
            KeyError: Si l'élément de données n'existe pas
        """
        with self.lock:
            # Déterminer la version à récupérer
            if version_id is None:
                if data_id not in self.versions or not self.versions[data_id]:
                    raise KeyError(f"Data item {data_id} not found")
                
                version_id = self.versions[data_id][-1]  # Dernière version
            
            # Récupérer l'élément de données
            item_key = f"{data_id}:{version_id}"
            if item_key not in self.data_items:
                raise KeyError(f"Data item {data_id} with version {version_id} not found")
            
            data_item = self.data_items[item_key]
            
            # Décompresser les données si nécessaire
            if data_item["is_compressed"]:
                compressed_data = base64.b64decode(data_item["content"])
                decompressed_data = gzip.decompress(compressed_data).decode('utf-8')
                data_content = decompressed_data
            else:
                data_content = data_item["content"]
            
            # Désérialiser les données
            data = self._deserialize_data(data_content)
            
            self.logger.info(f"Data item {data_id} with version {version_id} retrieved")
            return data, data_item["metadata"]
    
    def delete_data(self, data_id: str, version_id: Optional[str] = None) -> bool:
        """
        Supprime un élément de données.
        
        Args:
            data_id: Identifiant de l'élément de données
            version_id: Identifiant de version (None pour toutes les versions)
            
        Returns:
            True si suppression réussie, False sinon
        """
        with self.lock:
            if data_id not in self.versions:
                self.logger.warning(f"Data item {data_id} not found")
                return False
            
            if version_id is None:
                # Supprimer toutes les versions
                for v_id in self.versions[data_id]:
                    item_key = f"{data_id}:{v_id}"
                    if item_key in self.data_items:
                        del self.data_items[item_key]
                
                del self.versions[data_id]
                self.logger.info(f"All versions of data item {data_id} deleted")
                return True
            else:
                # Supprimer une version spécifique
                item_key = f"{data_id}:{version_id}"
                if item_key not in self.data_items:
                    self.logger.warning(f"Data item {data_id} with version {version_id} not found")
                    return False
                
                del self.data_items[item_key]
                self.versions[data_id].remove(version_id)
                
                if not self.versions[data_id]:
                    del self.versions[data_id]
                
                self.logger.info(f"Data item {data_id} with version {version_id} deleted")
                return True
    
    def get_versions(self, data_id: str) -> List[str]:
        """
        Récupère la liste des versions d'un élément de données.
        
        Args:
            data_id: Identifiant de l'élément de données
            
        Returns:
            Liste des identifiants de version
        """
        with self.lock:
            return self.versions.get(data_id, []).copy()
    
    def get_data_info(self, data_id: str, version_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Récupère des informations sur un élément de données.
        
        Args:
            data_id: Identifiant de l'élément de données
            version_id: Identifiant de version (None pour la dernière version)
            
        Returns:
            Un dictionnaire d'informations sur l'élément de données ou None s'il n'existe pas
        """
        with self.lock:
            # Déterminer la version à récupérer
            if version_id is None:
                if data_id not in self.versions or not self.versions[data_id]:
                    return None
                
                version_id = self.versions[data_id][-1]  # Dernière version
            
            # Récupérer l'élément de données
            item_key = f"{data_id}:{version_id}"
            if item_key not in self.data_items:
                return None
            
            data_item = self.data_items[item_key].copy()
            
            # Supprimer le contenu pour alléger l'information
            data_item.pop("content", None)
            
            return data_item
    
    def _serialize_data(self, data: Any) -> str:
        """
        Sérialise des données en chaîne JSON.
        
        Args:
            data: Les données à sérialiser
            
        Returns:
            Les données sérialisées
        """
        return json.dumps(data)
    
    def _deserialize_data(self, serialized_data: str) -> Any:
        """
        Désérialise des données JSON.
        
        Args:
            serialized_data: Les données sérialisées
            
        Returns:
            Les données désérialisées
        """
        return json.loads(serialized_data)


class DataChannel(Channel):
    """
    Canal de communication spécialisé dans le transfert de données volumineuses.
    
    Ce canal optimise le transfert de grandes quantités de données structurées
    entre agents, avec support pour la compression, le streaming et le versionnement.
    """
    
    def __init__(self, channel_id: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialise un nouveau canal de données.
        
        Args:
            channel_id: Identifiant unique du canal
            config: Configuration spécifique au canal (optionnel)
        """
        super().__init__(channel_id, ChannelType.DATA, config)
        
        # Stockage de données
        self.data_store = DataStore(f"{channel_id}-store", config)
        
        # Files d'attente de messages par destinataire
        self.message_queues = defaultdict(list)
        
        # Verrou pour les opérations concurrentes
        self.lock = threading.RLock()
        
        # Configuration du logger
        self.logger = logging.getLogger(f"DataChannel.{channel_id}")
        self.logger.setLevel(logging.INFO)
        
        # Statistiques
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "data_items_stored": 0,
            "data_items_retrieved": 0,
            "total_data_size": 0,
            "compressed_data_size": 0
        }
        
        # Configuration
        self.config = config or {}  # S'assurer que config n'est jamais None
        self.compression_threshold = self.config.get("compression_threshold", 1024)
        self.max_inline_data_size = self.config.get("max_inline_data_size", 10240)
    
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
            
            # Vérifier si le message contient des données volumineuses
            data = message.content.get("data")
            if data and isinstance(data, dict) and len(str(data)) > self.max_inline_data_size:
                # Stocker les données séparément
                data_id = f"data-{uuid.uuid4().hex[:8]}"
                version_id = self.data_store.store_data(
                    data_id, 
                    data, 
                    metadata={
                        "message_id": message.id,
                        "sender": message.sender,
                        "recipient": message.recipient,
                        "timestamp": message.timestamp.isoformat()
                    },
                    compress=True
                )
                
                # Remplacer les données par une référence
                message.content["data"] = None
                message.content["data_reference"] = {
                    "data_id": data_id,
                    "version_id": version_id,
                    "size": len(str(data))
                }
                
                # Mettre à jour les statistiques
                with self.lock:
                    self.stats["data_items_stored"] += 1
                    self.stats["total_data_size"] += len(str(data))
                
                self.logger.info(f"Large data from message {message.id} stored separately with ID {data_id}")
            
            # Ajouter le message à la file d'attente du destinataire
            with self.lock:
                self.message_queues[message.recipient].append({
                    "message": message,
                    "timestamp": datetime.now(),
                    "read": False
                })
                
                # Mettre à jour les statistiques
                self.stats["messages_sent"] += 1
            
            # Notifier les abonnés
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
            with self.lock:
                # Vérifier s'il y a des messages non lus
                if recipient_id in self.message_queues:
                    for i, entry in enumerate(self.message_queues[recipient_id]):
                        if not entry["read"]:
                            # Récupérer le message
                            message = entry["message"]
                            
                            # Vérifier si le message contient une référence à des données
                            data_reference = message.content.get("data_reference")
                            if data_reference:
                                try:
                                    # Récupérer les données
                                    data, _ = self.data_store.get_data(
                                        data_reference["data_id"],
                                        data_reference.get("version_id")
                                    )
                                    
                                    # Remplacer la référence par les données
                                    message.content["data"] = data
                                    message.content.pop("data_reference", None)
                                    
                                    # Mettre à jour les statistiques
                                    self.stats["data_items_retrieved"] += 1
                                    
                                    self.logger.info(f"Data for message {message.id} retrieved from storage")
                                    
                                except Exception as e:
                                    self.logger.error(f"Error retrieving data for message {message.id}: {str(e)}")
                            
                            # Marquer le message comme lu
                            self.message_queues[recipient_id][i]["read"] = True
                            
                            # Mettre à jour les statistiques
                            self.stats["messages_received"] += 1
                            
                            self.logger.info(f"Message {message.id} received by {recipient_id}")
                            return message
            
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
            # Vérifier s'il y a des messages non lus
            if recipient_id in self.message_queues:
                for entry in self.message_queues[recipient_id]:
                    if not entry["read"]:
                        message = entry["message"]
                        
                        # Vérifier si le message contient une référence à des données
                        data_reference = message.content.get("data_reference")
                        if data_reference:
                            try:
                                # Récupérer les données
                                data, _ = self.data_store.get_data(
                                    data_reference["data_id"],
                                    data_reference.get("version_id")
                                )
                                
                                # Créer une copie du message avec les données
                                message_copy = Message(
                                    message_type=message.type,
                                    sender=message.sender,
                                    sender_level=message.sender_level,
                                    content={**message.content, "data": data, "data_reference": None},
                                    recipient=message.recipient,
                                    channel=message.channel,
                                    priority=message.priority,
                                    metadata=message.metadata,
                                    message_id=message.id,
                                    timestamp=message.timestamp
                                )
                                
                                messages.append(message_copy)
                                
                            except Exception as e:
                                self.logger.error(f"Error retrieving data for message {message.id}: {str(e)}")
                                messages.append(message)
                        else:
                            messages.append(message)
                        
                        # Limiter le nombre de messages
                        if max_count is not None and len(messages) >= max_count:
                            break
        
        return messages
    
    def get_channel_info(self) -> Dict[str, Any]:
        """
        Récupère des informations sur ce canal.
        
        Returns:
            Un dictionnaire d'informations sur le canal
        """
        with self.lock:
            return {
                "id": self.id,
                "type": self.type.value,
                "stats": self.stats,
                "subscriber_count": len(self.subscribers),
                "compression_threshold": self.compression_threshold,
                "max_inline_data_size": self.max_inline_data_size
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
    
    def store_data(self, data_id: str, data: Any, metadata: Optional[Dict[str, Any]] = None,
                 compress: bool = True) -> str:
        """
        Stocke des données dans le canal.
        
        Args:
            data_id: Identifiant des données
            data: Les données à stocker
            metadata: Métadonnées associées aux données (optionnel)
            compress: Indique si les données doivent être compressées (par défaut: True)
            
        Returns:
            L'identifiant de version des données
        """
        version_id = self.data_store.store_data(data_id, data, metadata, compress)
        
        # Mettre à jour les statistiques
        with self.lock:
            self.stats["data_items_stored"] += 1
            self.stats["total_data_size"] += len(str(data))
        
        return version_id
    
    def get_data(self, data_id: str, version_id: Optional[str] = None) -> Tuple[Any, Dict[str, Any]]:
        """
        Récupère des données du canal.
        
        Args:
            data_id: Identifiant des données
            version_id: Identifiant de version (None pour la dernière version)
            
        Returns:
            Un tuple (données, métadonnées)
        """
        data, metadata = self.data_store.get_data(data_id, version_id)
        
        # Mettre à jour les statistiques
        with self.lock:
            self.stats["data_items_retrieved"] += 1
        
        return data, metadata
    
    def delete_data(self, data_id: str, version_id: Optional[str] = None) -> bool:
        """
        Supprime des données du canal.
        
        Args:
            data_id: Identifiant des données
            version_id: Identifiant de version (None pour toutes les versions)
            
        Returns:
            True si suppression réussie, False sinon
        """
        return self.data_store.delete_data(data_id, version_id)
    
    def get_data_info(self, data_id: str, version_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Récupère des informations sur des données.
        
        Args:
            data_id: Identifiant des données
            version_id: Identifiant de version (None pour la dernière version)
            
        Returns:
            Un dictionnaire d'informations sur les données ou None si elles n'existent pas
        """
        return self.data_store.get_data_info(data_id, version_id)