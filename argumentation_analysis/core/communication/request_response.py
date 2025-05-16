"""
Implémentation du protocole de requête-réponse pour le système de communication multi-canal.

Ce protocole permet une communication synchrone où un agent envoie une requête
et attend une réponse. Il est particulièrement adapté aux interactions qui
nécessitent une réponse immédiate ou une confirmation.
"""

import uuid
import time
import threading
import asyncio
from typing import Dict, Any, Optional, Callable, Tuple, List
from datetime import datetime, timedelta

from .message import Message, MessageType, MessagePriority, AgentLevel


class RequestTimeoutError(Exception):
    """Exception levée lorsqu'une requête expire sans recevoir de réponse."""
    pass


class RequestResponseProtocol:
    """
    Implémentation du protocole de requête-réponse.
    
    Ce protocole gère l'envoi de requêtes et la réception des réponses correspondantes,
    avec gestion des timeouts et des réessais.
    """
    
    def __init__(self, middleware):
        """
        Initialise le protocole de requête-réponse.
        
        Args:
            middleware: Le middleware de messagerie à utiliser pour l'envoi et la réception
        """
        self.middleware = middleware
        self.pending_requests = {}  # Dictionnaire des requêtes en attente de réponse
        self.response_callbacks = {}  # Callbacks pour les réponses asynchrones
        self.lock = threading.RLock()  # Verrou pour les opérations concurrentes
        
        # Démarrer le thread de surveillance des timeouts
        self.running = True
        self.timeout_thread = threading.Thread(target=self._monitor_timeouts)
        self.timeout_thread.daemon = True
        self.timeout_thread.start()
    
    def send_request(
        self,
        sender: str,
        sender_level: AgentLevel,
        recipient: str,
        request_type: str,
        content: Dict[str, Any],
        timeout: float = 30.0,
        retry_count: int = 0,
        retry_delay: float = 1.0,
        priority: MessagePriority = MessagePriority.NORMAL,
        channel: Optional[str] = None
    ) -> Message:
        """
        Envoie une requête et attend la réponse.
        
        Args:
            sender: Identifiant de l'émetteur
            sender_level: Niveau de l'émetteur
            recipient: Identifiant du destinataire
            request_type: Type de requête
            content: Contenu de la requête
            timeout: Délai d'attente maximum en secondes
            retry_count: Nombre de tentatives en cas d'échec
            retry_delay: Délai entre les tentatives en secondes
            priority: Priorité de la requête
            channel: Canal à utiliser (optionnel)
            
        Returns:
            Le message de réponse
            
        Raises:
            RequestTimeoutError: Si aucune réponse n'est reçue avant l'expiration du délai
        """
        # Créer le message de requête
        request = Message(
            message_type=MessageType.REQUEST,
            sender=sender,
            sender_level=sender_level,
            content={
                "request_type": request_type,
                **content,
                "timeout": timeout
            },
            recipient=recipient,
            channel=channel,
            priority=priority,
            metadata={
                "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                "requires_ack": True
            }
        )
        
        # Tentatives d'envoi avec réessais
        for attempt in range(retry_count + 1):
            try:
                # Enregistrer la requête comme en attente
                with self.lock:
                    self.pending_requests[request.id] = {
                        "request": request,
                        "expires_at": datetime.now() + timedelta(seconds=timeout),
                        "response": None,
                        "completed": threading.Event()
                    }
                
                # Envoyer la requête
                self.middleware.send_message(request)
                
                # Attendre la réponse
                pending = self.pending_requests[request.id]
                if not pending["completed"].wait(timeout=timeout):
                    # Timeout atteint
                    if attempt < retry_count:
                        # Réessayer
                        time.sleep(retry_delay)
                        continue
                    else:
                        # Échec définitif
                        raise RequestTimeoutError(f"Request {request.id} timed out after {retry_count + 1} attempts")
                
                # Récupérer la réponse
                with self.lock:
                    response = pending["response"]
                    del self.pending_requests[request.id]
                
                return response
                
            except Exception as e:
                if attempt < retry_count:
                    # Réessayer
                    time.sleep(retry_delay)
                else:
                    # Échec définitif
                    raise e
    
    async def send_request_async(
        self,
        sender: str,
        sender_level: AgentLevel,
        recipient: str,
        request_type: str,
        content: Dict[str, Any],
        timeout: float = 30.0,
        retry_count: int = 0,
        retry_delay: float = 1.0,
        priority: MessagePriority = MessagePriority.NORMAL,
        channel: Optional[str] = None
    ) -> Message:
        """
        Version asynchrone de send_request.
        
        Args:
            sender: Identifiant de l'émetteur
            sender_level: Niveau de l'émetteur
            recipient: Identifiant du destinataire
            request_type: Type de requête
            content: Contenu de la requête
            timeout: Délai d'attente maximum en secondes
            retry_count: Nombre de tentatives en cas d'échec
            retry_delay: Délai entre les tentatives en secondes
            priority: Priorité de la requête
            channel: Canal à utiliser (optionnel)
            
        Returns:
            Le message de réponse
            
        Raises:
            RequestTimeoutError: Si aucune réponse n'est reçue avant l'expiration du délai
        """
        # Créer le message de requête
        request = Message(
            message_type=MessageType.REQUEST,
            sender=sender,
            sender_level=sender_level,
            content={
                "request_type": request_type,
                **content,
                "timeout": timeout
            },
            recipient=recipient,
            channel=channel,
            priority=priority,
            metadata={
                "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                "requires_ack": True
            }
        )
        
        # Tentatives d'envoi avec réessais
        for attempt in range(retry_count + 1):
            try:
                # Créer un futur pour la réponse
                response_future = asyncio.Future()
                
                # Enregistrer la requête comme en attente avec le futur
                with self.lock:
                    self.pending_requests[request.id] = {
                        "request": request,
                        "expires_at": datetime.now() + timedelta(seconds=timeout),
                        "response": None,
                        "completed": threading.Event(),
                        "future": response_future
                    }
                
                # Envoyer la requête
                self.middleware.send_message(request)
                
                # Attendre la réponse avec timeout
                try:
                    return await asyncio.wait_for(response_future, timeout=timeout)
                except asyncio.TimeoutError:
                    # Timeout atteint
                    if attempt < retry_count:
                        # Réessayer
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        # Échec définitif
                        raise RequestTimeoutError(f"Request {request.id} timed out after {retry_count + 1} attempts")
                
            except Exception as e:
                if attempt < retry_count:
                    # Réessayer
                    await asyncio.sleep(retry_delay)
                else:
                    # Échec définitif
                    raise e
    
    def send_request_async_callback(
        self,
        sender: str,
        sender_level: AgentLevel,
        recipient: str,
        request_type: str,
        content: Dict[str, Any],
        callback: Callable[[Optional[Message], Optional[Exception]], None],
        timeout: float = 30.0,
        retry_count: int = 0,
        retry_delay: float = 1.0,
        priority: MessagePriority = MessagePriority.NORMAL,
        channel: Optional[str] = None
    ) -> str:
        """
        Envoie une requête de manière asynchrone avec callback.
        
        Args:
            sender: Identifiant de l'émetteur
            sender_level: Niveau de l'émetteur
            recipient: Identifiant du destinataire
            request_type: Type de requête
            content: Contenu de la requête
            callback: Fonction de rappel à appeler lors de la réception de la réponse
            timeout: Délai d'attente maximum en secondes
            retry_count: Nombre de tentatives en cas d'échec
            retry_delay: Délai entre les tentatives en secondes
            priority: Priorité de la requête
            channel: Canal à utiliser (optionnel)
            
        Returns:
            L'identifiant de la requête
        """
        # Créer le message de requête
        request = Message(
            message_type=MessageType.REQUEST,
            sender=sender,
            sender_level=sender_level,
            content={
                "request_type": request_type,
                **content,
                "timeout": timeout
            },
            recipient=recipient,
            channel=channel,
            priority=priority,
            metadata={
                "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                "requires_ack": True
            }
        )
        
        # Enregistrer la requête et le callback
        with self.lock:
            self.pending_requests[request.id] = {
                "request": request,
                "expires_at": datetime.now() + timedelta(seconds=timeout),
                "response": None,
                "completed": threading.Event(),
                "callback": callback,
                "retry_count": retry_count,
                "retry_delay": retry_delay,
                "attempt": 0
            }
        
        # Envoyer la requête
        self.middleware.send_message(request)
        
        return request.id
    
    def handle_response(self, response: Message) -> bool:
        """
        Traite une réponse reçue.
        
        Args:
            response: Le message de réponse
            
        Returns:
            True si la réponse correspond à une requête en attente, False sinon
        """
        # Vérifier si la réponse correspond à une requête en attente
        request_id = response.metadata.get("reply_to")
        if request_id is None or request_id == "":
            return False
        
        with self.lock:
            if request_id not in self.pending_requests:
                return False
            
            pending = self.pending_requests[request_id]
            
            # Stocker la réponse
            pending["response"] = response
            
            # Signaler que la requête est complétée
            pending["completed"].set()
            
            # Si un futur est présent, le compléter
            if "future" in pending and not pending["future"].done():
                pending["future"].set_result(response)
            
            # Si un callback est présent, l'appeler
            if "callback" in pending:
                try:
                    pending["callback"](response, None)
                except Exception as e:
                    print(f"Error in response callback: {e}")
            
            # Si pas de callback ou de futur, la requête peut être supprimée
            if "callback" not in pending and "future" not in pending:
                del self.pending_requests[request_id]
        
        return True
    
    def _monitor_timeouts(self):
        """Thread qui surveille les timeouts des requêtes en attente."""
        while self.running:
            try:
                now = datetime.now()
                timed_out_requests = []
                
                # Identifier les requêtes expirées
                with self.lock:
                    for request_id, pending in list(self.pending_requests.items()):
                        if now > pending["expires_at"] and not pending["completed"].is_set():
                            # Vérifier s'il reste des tentatives
                            if "retry_count" in pending and "attempt" in pending:
                                if pending["attempt"] < pending["retry_count"]:
                                    # Incrémenter le compteur de tentatives
                                    pending["attempt"] += 1
                                    
                                    # Mettre à jour l'expiration
                                    pending["expires_at"] = now + timedelta(seconds=pending["request"].content.get("timeout", 30.0))
                                    
                                    # Renvoyer la requête
                                    self.middleware.send_message(pending["request"])
                                    
                                    # Attendre le délai de réessai
                                    time.sleep(pending["retry_delay"])
                                    continue
                            
                            # Plus de tentatives ou pas de réessai configuré
                            timed_out_requests.append(request_id)
                
                # Traiter les requêtes expirées
                for request_id in timed_out_requests:
                    with self.lock:
                        if request_id in self.pending_requests:
                            pending = self.pending_requests[request_id]
                            
                            # Créer l'erreur de timeout
                            error = RequestTimeoutError(f"Request {request_id} timed out")
                            
                            # Si un futur est présent, le compléter avec une erreur
                            if "future" in pending and not pending["future"].done():
                                pending["future"].set_exception(error)
                            
                            # Si un callback est présent, l'appeler avec l'erreur
                            if "callback" in pending:
                                try:
                                    pending["callback"](None, error)
                                except Exception as e:
                                    print(f"Error in timeout callback: {e}")
                            
                            # Signaler que la requête est complétée (avec erreur)
                            pending["completed"].set()
                            
                            # Supprimer la requête
                            del self.pending_requests[request_id]
                
                # Attendre un peu avant la prochaine vérification
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error in timeout monitor: {e}")
                time.sleep(1)
    
    def shutdown(self):
        """Arrête proprement le protocole."""
        self.running = False
        if self.timeout_thread.is_alive():
            self.timeout_thread.join(timeout=2)
        
        # Compléter toutes les requêtes en attente avec une erreur
        with self.lock:
            for request_id, pending in list(self.pending_requests.items()):
                error = Exception("Protocol shutdown")
                
                # Si un futur est présent, le compléter avec une erreur
                if "future" in pending and not pending["future"].done():
                    pending["future"].set_exception(error)
                
                # Si un callback est présent, l'appeler avec l'erreur
                if "callback" in pending:
                    try:
                        pending["callback"](None, error)
                    except Exception as e:
                        print(f"Error in shutdown callback: {e}")
                
                # Signaler que la requête est complétée (avec erreur)
                pending["completed"].set()
            
            # Vider le dictionnaire
            self.pending_requests.clear()