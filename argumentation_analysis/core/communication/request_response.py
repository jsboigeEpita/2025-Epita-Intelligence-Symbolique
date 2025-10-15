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
import logging
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
        self.lock = (
            threading.RLock()
        )  # Verrou threading pour compatibilité avec les méthodes synchrones
        self.async_lock = (
            asyncio.Lock()
        )  # Verrou AsyncIO pour les opérations asynchrones
        self.early_responses = {}  # File d'attente pour les réponses anticipées
        self.early_responses_by_conversation = (
            {}
        )  # Réponses anticipées indexées par conversation_id

        # Configuration du logger
        self.logger = logging.getLogger("RequestResponseProtocol")
        self.logger.setLevel(logging.INFO)

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
        channel: Optional[str] = None,
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
            content={"request_type": request_type, **content, "timeout": timeout},
            recipient=recipient,
            channel=channel,
            priority=priority,
            metadata={
                "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                "requires_ack": True,
            },
        )

        # Vérifier s'il y a une réponse anticipée pour cette requête
        conversation_id = request.metadata.get("conversation_id")
        with self.lock:
            # Vérifier par ID de requête (cas peu probable mais possible)
            if request.id in self.early_responses:
                early_response = self.early_responses[request.id]["response"]
                del self.early_responses[request.id]
                self.logger.info(f"Using early response for request {request.id}")
                return early_response

            # Vérifier par ID de conversation
            if (
                conversation_id
                and conversation_id in self.early_responses_by_conversation
            ):
                early_response = self.early_responses_by_conversation[conversation_id][
                    "response"
                ]
                request_id = early_response.metadata.get("reply_to")
                if request_id in self.early_responses:
                    del self.early_responses[request_id]
                del self.early_responses_by_conversation[conversation_id]
                self.logger.info(
                    f"Using early response for conversation {conversation_id}"
                )
                return early_response

        # Tentatives d'envoi avec réessais
        for attempt in range(retry_count + 1):
            try:
                # Enregistrer la requête comme en attente
                with self.lock:
                    self.pending_requests[request.id] = {
                        "request": request,
                        "expires_at": datetime.now() + timedelta(seconds=timeout),
                        "response": None,
                        "completed": threading.Event(),
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
                        raise RequestTimeoutError(
                            f"Request {request.id} timed out after {retry_count + 1} attempts"
                        )

                # Récupérer la réponse
                response = None
                with self.lock:
                    if request.id in self.pending_requests:
                        pending_entry = self.pending_requests[request.id]
                        response = pending_entry[
                            "response"
                        ]  # Récupérer la réponse stockée par handle_response
                        # Pour les requêtes synchrones simples (pas de futur, pas de callback),
                        # nous pouvons supprimer la requête ici car send_request est sur le point de retourner.
                        if (
                            "future" not in pending_entry
                            and "callback" not in pending_entry
                        ):
                            del self.pending_requests[request.id]
                            self.logger.info(
                                f"Synchronous request {request.id} processed and removed by send_request."
                            )
                    elif (
                        request.id in self.early_responses
                    ):  # Si elle a été traitée très rapidement
                        self.logger.info(
                            f"Request {request.id} was processed as early response, retrieving from early_responses."
                        )
                        response = self.early_responses[request.id]["response"]
                        del self.early_responses[request.id]
                        conversation_id = response.metadata.get("conversation_id")
                        if (
                            conversation_id
                            and conversation_id in self.early_responses_by_conversation
                        ):
                            del self.early_responses_by_conversation[conversation_id]
                    else:
                        self.logger.warning(
                            f"Request {request.id} not found in pending_requests or early_responses after wait."
                        )

                if response is None:
                    self.logger.error(
                        f"send_request for {request.id} completed wait but response is None. This indicates a timeout or logic error."
                    )
                    # Ne pas lever RequestTimeoutError ici si le wait a réussi, cela masquerait la cause.
                    # Le timeout est géré par le `if not pending["completed"].wait(timeout=timeout):` plus haut.
                    # Si on arrive ici, c'est que wait() a réussi mais response est None.
                    # Cela peut arriver si _handle_timeout a été appelé et a supprimé la requête
                    # avant que cette section ne soit atteinte, mais après que .wait() ait été débloqué.
                    # Ou si handle_response n'a pas correctement stocké la réponse.
                    # On retourne None, et l'appelant (test) échouera sur l'assertion.
                    pass  # Laisser l'assertion du test échouer si guidance est None

                return response

            except Exception as e:
                if attempt < retry_count:
                    # Réessayer
                    time.sleep(retry_delay)
                else:
                    # Échec définitif
                    self.logger.error(f"Error in send_request: {e}")
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
        channel: Optional[str] = None,
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
            content={"request_type": request_type, **content, "timeout": timeout},
            recipient=recipient,
            channel=channel,
            priority=priority,
            metadata={
                "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                "requires_ack": True,
            },
        )

        self.logger.info(f"Created request {request.id} from {sender} to {recipient}")

        # Vérifier s'il y a une réponse anticipée pour cette requête
        conversation_id = request.metadata.get("conversation_id")
        with self.lock:
            # D'abord, vérifier si une réponse anticipée existe pour cette requête spécifique
            if request.id in self.early_responses:
                early_response = self.early_responses[request.id]["response"]
                del self.early_responses[request.id]
                self.logger.info(f"Using early response for request {request.id}")
                return early_response

            # Vérifier par ID de conversation
            if (
                conversation_id
                and conversation_id in self.early_responses_by_conversation
            ):
                early_response = self.early_responses_by_conversation[conversation_id][
                    "response"
                ]
                request_id = early_response.metadata.get("reply_to")
                if request_id in self.early_responses:
                    del self.early_responses[request_id]
                del self.early_responses_by_conversation[conversation_id]
                self.logger.info(
                    f"Using early response for conversation {conversation_id}"
                )
                return early_response

        # Tentatives d'envoi avec réessais
        for attempt in range(retry_count + 1):
            try:
                # Créer un futur pour la réponse
                response_future = asyncio.Future()

                # Race condition fix: attendre avant enregistrement des requêtes
                await asyncio.sleep(0.1)

                # Utiliser le verrou AsyncIO pour les opérations asynchrones
                async with self.async_lock:
                    # Enregistrer la requête comme en attente avec le futur
                    with self.lock:
                        self.pending_requests[request.id] = {
                            "request": request,
                            "expires_at": datetime.now() + timedelta(seconds=timeout),
                            "response": None,
                            "completed": threading.Event(),
                            "future": response_future,
                            "loop": asyncio.get_running_loop(),  # Stocker la boucle actuelle
                        }
                        self.logger.info(
                            f"Registered request {request.id} in pending_requests"
                        )

                        # Vérifier à nouveau s'il y a une réponse anticipée après avoir enregistré la requête
                        # Cela permet de capturer les réponses qui sont arrivées entre-temps
                        if request.id in self.early_responses:
                            early_response = self.early_responses[request.id][
                                "response"
                            ]
                            del self.early_responses[request.id]
                            self.logger.info(
                                f"Using early response for request {request.id} after registration"
                            )

                            # Compléter le futur avec la réponse anticipée
                            response_future.set_result(early_response)

                            # Supprimer la requête des requêtes en attente
                            del self.pending_requests[request.id]

                            return early_response

                        # Vérifier par ID de conversation
                        if (
                            conversation_id
                            and conversation_id in self.early_responses_by_conversation
                        ):
                            early_response = self.early_responses_by_conversation[
                                conversation_id
                            ]["response"]
                            request_id = early_response.metadata.get("reply_to")
                            if request_id in self.early_responses:
                                del self.early_responses[request_id]
                            del self.early_responses_by_conversation[conversation_id]
                            self.logger.info(
                                f"Using early response for conversation {conversation_id} after registration"
                            )

                            # Compléter le futur avec la réponse anticipée
                            response_future.set_result(early_response)

                            # Supprimer la requête des requêtes en attente
                            del self.pending_requests[request.id]

                            return early_response

                # Envoyer la requête
                self.middleware.send_message(request)
                self.logger.info(f"Sent request {request.id} to {recipient}")

                # Attendre la réponse avec timeout
                try:
                    self.logger.info(
                        f"Waiting for response to request {request.id} with timeout {timeout}s"
                    )
                    return await asyncio.wait_for(response_future, timeout=timeout)
                except asyncio.TimeoutError:
                    # Timeout atteint
                    if attempt < retry_count:
                        # Réessayer
                        self.logger.warning(
                            f"Timeout for request {request.id}, retrying ({attempt+1}/{retry_count+1})"
                        )
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        # Échec définitif
                        self.logger.error(
                            f"Request {request.id} timed out after {retry_count + 1} attempts"
                        )
                        raise RequestTimeoutError(
                            f"Request {request.id} timed out after {retry_count + 1} attempts"
                        )

            except asyncio.CancelledError:
                # Gérer l'annulation de la tâche
                with self.lock:
                    if request.id in self.pending_requests:
                        del self.pending_requests[request.id]
                self.logger.warning(f"Request {request.id} was cancelled")
                raise
            except Exception as e:
                if attempt < retry_count:
                    # Réessayer
                    self.logger.warning(
                        f"Error for request {request.id}, retrying: {e}"
                    )
                    await asyncio.sleep(retry_delay)
                else:
                    # Échec définitif
                    self.logger.error(f"Error in send_request_async: {e}")
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
        channel: Optional[str] = None,
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
            content={"request_type": request_type, **content, "timeout": timeout},
            recipient=recipient,
            channel=channel,
            priority=priority,
            metadata={
                "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                "requires_ack": True,
            },
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
                "attempt": 0,
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
            self.logger.warning(f"Response {response.id} has no reply_to metadata")
            return False

        self.logger.info(f"Handling response {response.id} for request {request_id}")

        with self.lock:
            # Vérifier si la requête est en attente
            if request_id in self.pending_requests:
                pending = self.pending_requests[request_id]

                # Stocker la réponse
                pending["response"] = response

                # Signaler que la requête est complétée
                pending["completed"].set()

                # Si un futur est présent, le compléter
                if "future" in pending:
                    if not pending["future"].done():
                        try:
                            self.logger.info(
                                f"Attempting to set future result for request {request_id}"
                            )
                            loop = pending.get("loop")
                            if (
                                loop and loop.is_running()
                            ):  # Vérifier aussi si la boucle tourne
                                loop.call_soon_threadsafe(
                                    pending["future"].set_result, response
                                )
                            elif loop and not loop.is_running():
                                self.logger.warning(
                                    f"Asyncio loop for future of request {request_id} is not running. Setting result directly if future not done."
                                )
                                if not pending["future"].done():  # Double vérification
                                    pending["future"].set_result(response)
                            else:  # Fallback si la boucle n'a pas été stockée ou est None
                                self.logger.warning(
                                    f"Asyncio loop not found or invalid for future of request {request_id}. Setting result directly if future not done."
                                )
                                if not pending["future"].done():  # Double vérification
                                    pending["future"].set_result(response)
                        except (
                            Exception
                        ) as e:  # Inclut InvalidStateError si la future est déjà résolue/annulée ailleurs
                            self.logger.error(
                                f"Error setting future result for request {request_id}: {e}"
                            )
                    else:
                        self.logger.info(
                            f"Future for request {request_id} was already done when handling response (no action taken)."
                        )

                # Si un callback est présent, l'appeler
                if "callback" in pending:
                    try:
                        self.logger.info(f"Calling callback for request {request_id}")
                        pending["callback"](response, None)
                    except Exception as e:
                        self.logger.error(f"Error in response callback: {e}")

                # Pour les requêtes synchrones simples (pas de futur, pas de callback),
                # la suppression est maintenant gérée par send_request après récupération de la réponse.
                # Pour les requêtes avec futur ou callback, elles restent jusqu'à ce que le futur/callback
                # soit traité ou qu'elles expirent.
                if "future" in pending or "callback" in pending:
                    # Ne pas supprimer ici, send_request_async ou _handle_timeout s'en chargeront
                    pass
                elif (
                    request_id in self.pending_requests
                ):  # S'assurer qu'elle n'a pas déjà été supprimée par send_request
                    # Ce cas ne devrait plus être nécessaire si send_request gère la suppression
                    # des requêtes synchrones simples.
                    # self.logger.info(f"Removing request {request_id} from pending requests by handle_response (should be rare).")
                    # del self.pending_requests[request_id]
                    pass

                return True
            else:
                # Vérifier si la réponse est pour une requête qui n'a pas encore été enregistrée
                # Cela peut arriver en raison de problèmes de synchronisation
                self.logger.warning(
                    f"Request {request_id} not found in pending requests. Storing as early response."
                )

                # Stocker la réponse anticipée pour une future requête
                self.early_responses[request_id] = {
                    "response": response,
                    "timestamp": datetime.now(),
                }

                # Stocker également par ID de conversation si disponible
                conversation_id = response.metadata.get("conversation_id")
                if conversation_id:
                    self.early_responses_by_conversation[conversation_id] = {
                        "response": response,
                        "timestamp": datetime.now(),
                    }
                    self.logger.info(
                        f"Stored early response for conversation {conversation_id}"
                    )

                self.logger.info(f"Stored early response for request {request_id}")

                # Afficher les requêtes en attente pour le débogage
                self.logger.info(
                    f"Current pending requests: {list(self.pending_requests.keys())}"
                )
                self.logger.info(
                    f"Current early responses: {list(self.early_responses.keys())}"
                )
                self.logger.info(
                    f"Current early responses by conversation: {list(self.early_responses_by_conversation.keys())}"
                )

                return True

    def _monitor_timeouts(self):
        """Thread qui surveille les timeouts des requêtes en attente et nettoie les réponses anticipées."""
        while self.running:
            try:
                now = datetime.now()
                timed_out_requests = []
                expired_early_responses = []

                # Identifier les requêtes expirées
                with self.lock:
                    # Vérifier les requêtes en attente
                    for request_id, pending in list(self.pending_requests.items()):
                        if (
                            now > pending["expires_at"]
                            and not pending["completed"].is_set()
                        ):
                            # Vérifier s'il reste des tentatives
                            if "retry_count" in pending and "attempt" in pending:
                                if pending["attempt"] < pending["retry_count"]:
                                    # Incrémenter le compteur de tentatives
                                    pending["attempt"] += 1

                                    # Mettre à jour l'expiration
                                    pending["expires_at"] = now + timedelta(
                                        seconds=pending["request"].content.get(
                                            "timeout", 30.0
                                        )
                                    )

                                    # Renvoyer la requête
                                    self.middleware.send_message(pending["request"])

                                    # Attendre le délai de réessai sans bloquer le verrou
                                    continue

                            # Plus de tentatives ou pas de réessai configuré
                            timed_out_requests.append(request_id)

                    # Nettoyer les réponses anticipées expirées (plus de 5 minutes)
                    for request_id, early_response in list(
                        self.early_responses.items()
                    ):
                        if (
                            now - early_response["timestamp"]
                        ).total_seconds() > 300:  # 5 minutes
                            expired_early_responses.append(("request", request_id))

                    # Nettoyer les réponses anticipées par conversation expirées
                    for conv_id, early_response in list(
                        self.early_responses_by_conversation.items()
                    ):
                        if (
                            now - early_response["timestamp"]
                        ).total_seconds() > 300:  # 5 minutes
                            expired_early_responses.append(("conversation", conv_id))

                # Traiter les requêtes expirées (en dehors du bloc verrouillé)
                for request_id in timed_out_requests:
                    self._handle_timeout(request_id)

                # Supprimer les réponses anticipées expirées
                with self.lock:
                    for type_id, id_value in expired_early_responses:
                        if type_id == "request" and id_value in self.early_responses:
                            del self.early_responses[id_value]
                            self.logger.info(
                                f"Removed expired early response for request {id_value}"
                            )
                        elif (
                            type_id == "conversation"
                            and id_value in self.early_responses_by_conversation
                        ):
                            del self.early_responses_by_conversation[id_value]
                            self.logger.info(
                                f"Removed expired early response for conversation {id_value}"
                            )

                # Attendre un peu avant la prochaine vérification
                time.sleep(0.1)

            except Exception as e:
                self.logger.error(f"Error in timeout monitor: {e}")
                time.sleep(1)

    def _handle_timeout(self, request_id):
        """
        Gère le timeout d'une requête.

        Args:
            request_id: L'identifiant de la requête expirée
        """
        with self.lock:
            if request_id in self.pending_requests:
                pending = self.pending_requests[request_id]

                # Vérifier si la requête n'a pas été complétée juste avant le timeout
                if pending["completed"].is_set():
                    self.logger.info(
                        f"Request {request_id} was completed just before timeout handling. Ignoring timeout."
                    )
                    # La requête est complétée, handle_response s'en est occupé ou va s'en occuper.
                    # Si c'est une requête synchrone sans callback/future, elle a dû être retirée par handle_response.
                    # Si c'est une future, send_request_async la retirera.
                    # Si c'est un callback, elle reste jusqu'à ce que le moniteur la nettoie après un vrai timeout.
                    # Pour être sûr, si elle est encore là et complétée, on peut la retirer.
                    if (
                        request_id in self.pending_requests
                        and "callback" not in pending
                        and "future" not in pending
                    ):
                        # Cas d'une requête synchrone qui aurait dû être retirée par handle_response
                        # mais qui est encore là pour une raison quelconque.
                        # Normalement, handle_response la retire.
                        pass  # Ne pas la supprimer ici pour éviter de masquer un autre problème.
                    return

                # Créer l'erreur de timeout
                error = RequestTimeoutError(f"Request {request_id} timed out")

                # Si un futur est présent, le compléter avec une erreur
                if "future" in pending:
                    future = pending["future"]
                    if not future.done():
                        try:
                            loop = pending.get("loop")
                            if loop and loop.is_running():
                                loop.call_soon_threadsafe(future.set_exception, error)
                            elif not loop:
                                self.logger.warning(
                                    f"Asyncio loop not found for future of request {request_id} in _handle_timeout, setting exception directly."
                                )
                                future.set_exception(
                                    error
                                )  # Fallback, mais risque InvalidStateError si la boucle est arrêtée
                            else:  # loop exists but not running
                                self.logger.warning(
                                    f"Asyncio loop for future of request {request_id} is not running in _handle_timeout. Setting exception directly."
                                )
                                future.set_exception(error)  # Fallback
                        except (
                            Exception
                        ) as e:  # Inclut InvalidStateError si la future est déjà résolue/annulée ailleurs
                            self.logger.error(
                                f"Error setting future exception for request {request_id} in _handle_timeout: {e}"
                            )
                    else:
                        self.logger.info(
                            f"Future for request {request_id} was already done when handling timeout."
                        )

                # Si un callback est présent, l'appeler avec l'erreur
                if "callback" in pending:
                    try:
                        pending["callback"](None, error)
                    except Exception as e:
                        self.logger.error(f"Error in timeout callback: {e}")

                # Signaler que la requête est complétée (avec erreur)
                pending["completed"].set()

                # Supprimer la requête
                del self.pending_requests[request_id]
                self.logger.info(f"Request {request_id} timed out and was removed")

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
                    loop = pending.get("loop")
                    if loop:
                        loop.call_soon_threadsafe(
                            pending["future"].set_exception, error
                        )
                    else:  # Fallback
                        self.logger.warning(
                            f"Asyncio loop not found for future of request {request_id} during shutdown, setting exception directly."
                        )
                        pending["future"].set_exception(error)

                # Si un callback est présent, l'appeler avec l'erreur
                if "callback" in pending:
                    try:
                        pending["callback"](None, error)
                    except Exception as e:
                        self.logger.error(f"Error in shutdown callback: {e}")

                # Signaler que la requête est complétée (avec erreur)
                pending["completed"].set()

            # Vider les dictionnaires
            self.pending_requests.clear()
            self.early_responses.clear()
            self.early_responses_by_conversation.clear()
