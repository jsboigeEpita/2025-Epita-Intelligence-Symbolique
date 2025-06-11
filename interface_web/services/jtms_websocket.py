#!/usr/bin/env python3
"""
Gestionnaire WebSocket pour JTMS
================================

Service WebSocket pour la communication temps réel avec l'interface JTMS.
Gère les mises à jour automatiques des réseaux de croyances et justifications.

Version: 1.0.0
Auteur: Intelligence Symbolique EPITA
Date: 11/06/2025
"""

import json
import logging
import asyncio
from typing import Dict, List, Set, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import queue
import time

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Types de messages WebSocket pour JTMS."""
    BELIEF_ADDED = "belief_added"
    BELIEF_UPDATED = "belief_updated"
    BELIEF_REMOVED = "belief_removed"
    JUSTIFICATION_ADDED = "justification_added"
    JUSTIFICATION_UPDATED = "justification_updated"
    NETWORK_UPDATED = "network_updated"
    SESSION_CREATED = "session_created"
    SESSION_UPDATED = "session_updated"
    CONSISTENCY_CHECK = "consistency_check"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class WebSocketMessage:
    """Message WebSocket structuré pour JTMS."""
    type: MessageType
    session_id: str
    data: Dict[str, Any]
    timestamp: str
    client_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Convertit le message en JSON."""
        return json.dumps({
            'type': self.type.value,
            'session_id': self.session_id,
            'data': self.data,
            'timestamp': self.timestamp,
            'client_id': self.client_id
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WebSocketMessage':
        """Crée un message depuis JSON."""
        data = json.loads(json_str)
        return cls(
            type=MessageType(data['type']),
            session_id=data['session_id'],
            data=data['data'],
            timestamp=data['timestamp'],
            client_id=data.get('client_id')
        )


class WebSocketClient:
    """Représente un client WebSocket connecté."""
    
    def __init__(self, client_id: str, websocket, session_ids: Set[str] = None):
        self.client_id = client_id
        self.websocket = websocket
        self.session_ids = session_ids or set()
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        
    async def send_message(self, message: WebSocketMessage) -> bool:
        """Envoie un message au client."""
        try:
            await self.websocket.send(message.to_json())
            return True
        except Exception as e:
            logger.error(f"Erreur envoi message au client {self.client_id}: {e}")
            return False
    
    def is_subscribed_to_session(self, session_id: str) -> bool:
        """Vérifie si le client est abonné à une session."""
        return session_id in self.session_ids
    
    def subscribe_to_session(self, session_id: str):
        """Abonne le client à une session."""
        self.session_ids.add(session_id)
    
    def unsubscribe_from_session(self, session_id: str):
        """Désabonne le client d'une session."""
        self.session_ids.discard(session_id)


class JTMSWebSocketManager:
    """Gestionnaire WebSocket principal pour JTMS."""
    
    def __init__(self):
        self.clients: Dict[str, WebSocketClient] = {}
        self.message_queue = queue.Queue()
        self.running = False
        self.broadcast_thread = None
        self._callbacks: Dict[MessageType, List[Callable]] = {}
        
    def start(self):
        """Démarre le gestionnaire WebSocket."""
        if not self.running:
            self.running = True
            self.broadcast_thread = threading.Thread(target=self._broadcast_worker, daemon=True)
            self.broadcast_thread.start()
            logger.info("Gestionnaire WebSocket JTMS démarré")
    
    def stop(self):
        """Arrête le gestionnaire WebSocket."""
        self.running = False
        if self.broadcast_thread:
            self.broadcast_thread.join(timeout=5)
        logger.info("Gestionnaire WebSocket JTMS arrêté")
    
    async def register_client(self, client_id: str, websocket) -> WebSocketClient:
        """Enregistre un nouveau client WebSocket."""
        client = WebSocketClient(client_id, websocket)
        self.clients[client_id] = client
        
        # Message de bienvenue
        welcome_message = WebSocketMessage(
            type=MessageType.HEARTBEAT,
            session_id="system",
            data={"message": "Connexion WebSocket JTMS établie", "client_id": client_id},
            timestamp=datetime.now().isoformat(),
            client_id=client_id
        )
        
        await client.send_message(welcome_message)
        logger.info(f"Client WebSocket {client_id} enregistré")
        return client
    
    def unregister_client(self, client_id: str):
        """Désenregistre un client WebSocket."""
        if client_id in self.clients:
            del self.clients[client_id]
            logger.info(f"Client WebSocket {client_id} désenregistré")
    
    def add_callback(self, message_type: MessageType, callback: Callable):
        """Ajoute un callback pour un type de message."""
        if message_type not in self._callbacks:
            self._callbacks[message_type] = []
        self._callbacks[message_type].append(callback)
    
    def queue_message(self, message: WebSocketMessage):
        """Ajoute un message à la queue de diffusion."""
        self.message_queue.put(message)
    
    def broadcast_to_session(self, session_id: str, message_type: MessageType, data: Dict[str, Any]):
        """Diffuse un message à tous les clients d'une session."""
        message = WebSocketMessage(
            type=message_type,
            session_id=session_id,
            data=data,
            timestamp=datetime.now().isoformat()
        )
        self.queue_message(message)
    
    def broadcast_belief_added(self, session_id: str, belief_name: str, belief_data: Dict[str, Any]):
        """Diffuse l'ajout d'une croyance."""
        self.broadcast_to_session(
            session_id,
            MessageType.BELIEF_ADDED,
            {
                "belief_name": belief_name,
                "belief_data": belief_data,
                "action": "add"
            }
        )
    
    def broadcast_belief_updated(self, session_id: str, belief_name: str, old_status: str, new_status: str):
        """Diffuse la mise à jour d'une croyance."""
        self.broadcast_to_session(
            session_id,
            MessageType.BELIEF_UPDATED,
            {
                "belief_name": belief_name,
                "old_status": old_status,
                "new_status": new_status,
                "action": "update"
            }
        )
    
    def broadcast_justification_added(self, session_id: str, justification_data: Dict[str, Any]):
        """Diffuse l'ajout d'une justification."""
        self.broadcast_to_session(
            session_id,
            MessageType.JUSTIFICATION_ADDED,
            {
                "justification_data": justification_data,
                "action": "add"
            }
        )
    
    def broadcast_network_updated(self, session_id: str, network_data: Dict[str, Any]):
        """Diffuse une mise à jour complète du réseau."""
        self.broadcast_to_session(
            session_id,
            MessageType.NETWORK_UPDATED,
            {
                "network_data": network_data,
                "action": "full_update"
            }
        )
    
    def broadcast_consistency_result(self, session_id: str, is_consistent: bool, conflicts: List[Dict]):
        """Diffuse les résultats d'une vérification de cohérence."""
        self.broadcast_to_session(
            session_id,
            MessageType.CONSISTENCY_CHECK,
            {
                "is_consistent": is_consistent,
                "conflicts": conflicts,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def _broadcast_worker(self):
        """Thread worker pour la diffusion des messages."""
        logger.info("Worker de diffusion WebSocket démarré")
        
        while self.running:
            try:
                # Récupérer un message de la queue avec timeout
                try:
                    message = self.message_queue.get(timeout=1.0)
                except queue.Empty:
                    continue
                
                # Diffuser le message aux clients concernés
                asyncio.run(self._send_to_clients(message))
                
                # Traiter les callbacks
                self._process_callbacks(message)
                
            except Exception as e:
                logger.error(f"Erreur dans worker de diffusion: {e}")
                time.sleep(0.1)
    
    async def _send_to_clients(self, message: WebSocketMessage):
        """Envoie un message aux clients concernés."""
        clients_to_remove = []
        
        for client_id, client in self.clients.items():
            try:
                # Vérifier si le client doit recevoir ce message
                if (message.session_id == "system" or 
                    client.is_subscribed_to_session(message.session_id)):
                    
                    success = await client.send_message(message)
                    if not success:
                        clients_to_remove.append(client_id)
                        
            except Exception as e:
                logger.error(f"Erreur envoi message au client {client_id}: {e}")
                clients_to_remove.append(client_id)
        
        # Nettoyer les clients déconnectés
        for client_id in clients_to_remove:
            self.unregister_client(client_id)
    
    def _process_callbacks(self, message: WebSocketMessage):
        """Traite les callbacks pour un message."""
        if message.type in self._callbacks:
            for callback in self._callbacks[message.type]:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Erreur dans callback {callback.__name__}: {e}")
    
    def get_client_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques des clients connectés."""
        return {
            "total_clients": len(self.clients),
            "clients": [
                {
                    "client_id": client.client_id,
                    "connected_at": client.connected_at.isoformat(),
                    "subscribed_sessions": list(client.session_ids),
                    "last_heartbeat": client.last_heartbeat.isoformat()
                }
                for client in self.clients.values()
            ],
            "queue_size": self.message_queue.qsize()
        }


class JTMSWebSocketDecorator:
    """Décorateur pour intégrer WebSocket aux services JTMS existants."""
    
    def __init__(self, websocket_manager: JTMSWebSocketManager):
        self.ws_manager = websocket_manager
    
    def belief_operation(self, operation_type: str):
        """Décorateur pour les opérations sur les croyances."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                
                # Extraire les informations de la session
                session_id = kwargs.get('session_id') or getattr(args[0], 'current_session_id', 'default')
                
                if operation_type == "add" and len(args) > 1:
                    belief_name = args[1] if len(args) > 1 else kwargs.get('belief_name')
                    if belief_name:
                        self.ws_manager.broadcast_belief_added(
                            session_id, belief_name, {"status": "unknown"}
                        )
                
                elif operation_type == "update" and len(args) > 1:
                    belief_name = args[1] if len(args) > 1 else kwargs.get('belief_name')
                    if belief_name:
                        self.ws_manager.broadcast_belief_updated(
                            session_id, belief_name, "unknown", "valid"
                        )
                
                return result
            return wrapper
        return decorator
    
    def justification_operation(self):
        """Décorateur pour les opérations sur les justifications."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                
                session_id = kwargs.get('session_id') or getattr(args[0], 'current_session_id', 'default')
                
                # Diffuser l'ajout de justification
                if len(args) > 1:
                    self.ws_manager.broadcast_justification_added(
                        session_id, {"conclusion": args[1] if len(args) > 1 else "unknown"}
                    )
                
                return result
            return wrapper
        return decorator


# Instance globale du gestionnaire WebSocket
websocket_manager = JTMSWebSocketManager()


def get_websocket_manager() -> JTMSWebSocketManager:
    """Retourne l'instance globale du gestionnaire WebSocket."""
    return websocket_manager


def initialize_websocket_service():
    """Initialise le service WebSocket JTMS."""
    websocket_manager.start()
    logger.info("Service WebSocket JTMS initialisé")


def shutdown_websocket_service():
    """Arrête le service WebSocket JTMS."""
    websocket_manager.stop()
    logger.info("Service WebSocket JTMS arrêté")


# Fonctions utilitaires pour l'intégration Flask
def setup_websocket_callbacks(jtms_service=None):
    """Configure les callbacks WebSocket pour l'intégration avec les services JTMS."""
    if not jtms_service:
        return
    
    # Exemples de callbacks (à adapter selon l'API réelle du JTMS)
    def on_belief_change(belief_name: str, old_status: str, new_status: str, session_id: str):
        """Callback appelé lors du changement d'une croyance."""
        websocket_manager.broadcast_belief_updated(session_id, belief_name, old_status, new_status)
    
    def on_network_change(session_id: str, network_data: Dict[str, Any]):
        """Callback appelé lors du changement du réseau."""
        websocket_manager.broadcast_network_updated(session_id, network_data)
    
    # Enregistrer les callbacks si l'API le permet
    if hasattr(jtms_service, 'register_callback'):
        jtms_service.register_callback('belief_changed', on_belief_change)
        jtms_service.register_callback('network_changed', on_network_change)
        logger.info("Callbacks WebSocket enregistrés avec le service JTMS")


if __name__ == "__main__":
    # Test standalone du service WebSocket
    logging.basicConfig(level=logging.INFO)
    
    # Créer et démarrer le gestionnaire
    manager = JTMSWebSocketManager()
    manager.start()
    
    # Test de diffusion
    manager.broadcast_to_session(
        "test_session",
        MessageType.BELIEF_ADDED,
        {"belief_name": "test_belief", "status": "unknown"}
    )
    
    # Attendre un peu puis arrêter
    import time
    time.sleep(2)
    manager.stop()
    print("Test WebSocket terminé")