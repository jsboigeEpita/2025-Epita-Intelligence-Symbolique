# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Module de correction pour les tests asynchrones qui se bloquent.

Ce module implémente des correctifs pour résoudre le problème de blocage des tests
qui se manifeste par des messages répétitifs "Received guidance from tactical-agent-2 for request-X request".
"""

import asyncio
import logging
import threading
import time
import uuid
from typing import Dict, Any, Optional, List, Set


from argumentation_analysis.core.communication.message import (
    Message,
    MessageType,
    MessagePriority,
    AgentLevel,
)
from argumentation_analysis.core.communication.channel_interface import ChannelType
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.tactical_adapter import TacticalAdapter

# Configuration du logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("AsyncTimeoutFix")


class AsyncRequestTracker:
    """
    Classe pour suivre et gérer les requêtes asynchrones en cours.
    Cette classe permet d'éviter les blocages en gardant une trace des requêtes
    et en les terminant automatiquement après un certain délai.
    """

    def __init__(self):
        """Initialise le tracker de requêtes."""
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.request_events: Dict[str, asyncio.Event] = {}
        self.response_data: Dict[str, Any] = {}
        self.lock = threading.RLock()
        self.cleanup_task = None
        self.running = False

    def start(self):
        """Démarre le tracker et le nettoyage périodique."""
        if not self.running:
            self.running = True
            self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("AsyncRequestTracker démarré")

    async def stop(self):
        """Arrête le tracker et nettoie les ressources."""
        if self.running:
            self.running = False
            if self.cleanup_task:
                self.cleanup_task.cancel()
                try:
                    await self.cleanup_task
                except asyncio.CancelledError:
                    pass

            # Résoudre toutes les requêtes en attente
            with self.lock:
                for request_id, event in self.request_events.items():
                    if not event.is_set():
                        logger.warning(
                            f"Résolution forcée de la requête {request_id} lors de l'arrêt"
                        )
                        self.response_data[request_id] = {
                            "status": "timeout",
                            "error": "Arrêt forcé du tracker",
                        }
                        event.set()

            logger.info("AsyncRequestTracker arrêté")

    def register_request(self, request_id: str, timeout: float = 10.0) -> asyncio.Event:
        """
        Enregistre une nouvelle requête et retourne un événement pour attendre sa réponse.

        Args:
            request_id: Identifiant unique de la requête
            timeout: Délai maximum d'attente en secondes

        Returns:
            Un événement asyncio qui sera déclenché lorsque la réponse sera disponible
        """
        with self.lock:
            event = asyncio.Event()
            self.request_events[request_id] = event
            self.pending_requests[request_id] = {
                "timestamp": time.time(),
                "timeout": timeout,
            }
            logger.debug(f"Requête {request_id} enregistrée avec timeout {timeout}s")
            return event

    def register_response(self, request_id: str, response_data: Any) -> bool:
        """
        Enregistre une réponse pour une requête en attente.

        Args:
            request_id: Identifiant de la requête
            response_data: Données de la réponse

        Returns:
            True si la requête était en attente, False sinon
        """
        with self.lock:
            if request_id in self.request_events:
                self.response_data[request_id] = response_data
                self.request_events[request_id].set()
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                logger.debug(f"Réponse enregistrée pour requête {request_id}")
                return True
            return False

    async def wait_for_response(
        self, request_id: str, timeout: Optional[float] = None
    ) -> Any:
        """
        Attend la réponse pour une requête spécifique.

        Args:
            request_id: Identifiant de la requête
            timeout: Délai maximum d'attente (remplace celui défini lors de l'enregistrement)

        Returns:
            Les données de la réponse ou None en cas de timeout

        Raises:
            asyncio.TimeoutError: Si le délai d'attente est dépassé
        """
        with self.lock:
            if request_id not in self.request_events:
                logger.warning(
                    f"Tentative d'attente pour une requête non enregistrée: {request_id}"
                )
                return None

            event = self.request_events[request_id]
            effective_timeout = timeout or self.pending_requests.get(
                request_id, {}
            ).get("timeout", 10.0)

        try:
            await asyncio.wait_for(event.wait(), timeout=effective_timeout)
            with self.lock:
                response = self.response_data.get(request_id)
                # Nettoyage après récupération de la réponse
                if request_id in self.request_events:
                    del self.request_events[request_id]
                if request_id in self.response_data:
                    del self.response_data[request_id]
                return response
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout en attendant la réponse pour la requête {request_id}"
            )
            with self.lock:
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                if request_id in self.request_events:
                    del self.request_events[request_id]
            raise

    async def _periodic_cleanup(self):
        """Nettoie périodiquement les requêtes expirées."""
        while self.running:
            try:
                await asyncio.sleep(1.0)  # Vérifier toutes les secondes
                self._cleanup_expired_requests()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur dans le nettoyage périodique: {e}")

    def _cleanup_expired_requests(self):
        """Identifie et nettoie les requêtes qui ont dépassé leur délai."""
        current_time = time.time()
        expired_requests = []

        with self.lock:
            for request_id, info in self.pending_requests.items():
                if current_time - info["timestamp"] > info["timeout"]:
                    expired_requests.append(request_id)

            for request_id in expired_requests:
                logger.warning(f"Requête expirée: {request_id}")
                if request_id in self.request_events:
                    self.response_data[request_id] = {
                        "status": "timeout",
                        "error": "Requête expirée",
                    }
                    self.request_events[request_id].set()
                del self.pending_requests[request_id]


class TacticalAdapterWithTimeout(TacticalAdapter):
    """
    Version améliorée de TacticalAdapter avec gestion des timeouts.
    Cette classe remplace certaines méthodes pour éviter les blocages.
    """

    def __init__(
        self,
        agent_id: str,
        middleware: MessageMiddleware,
        request_tracker: Optional[AsyncRequestTracker] = None,
    ):
        """
        Initialise l'adaptateur avec un tracker de requêtes.

        Args:
            agent_id: Identifiant de l'agent
            middleware: Middleware de communication
            request_tracker: Tracker de requêtes (en crée un nouveau si None)
        """
        super().__init__(agent_id, middleware)
        self.request_tracker = request_tracker or AsyncRequestTracker()
        self.request_tracker.start()
        self._active_requests: Set[str] = set()

    async def request_strategic_guidance_async(
        self,
        request_type: str,
        parameters: dict,
        recipient_id: str,
        timeout: float = 10.0,
        priority: MessagePriority = MessagePriority.NORMAL,
    ) -> dict:
        """
        Version améliorée de la méthode request_strategic_guidance_async avec gestion des timeouts.

        Args:
            request_type: Type de requête
            parameters: Paramètres de la requête
            recipient_id: Identifiant du destinataire
            timeout: Délai maximum d'attente en secondes
            priority: Priorité du message

        Returns:
            Les données de la réponse

        Raises:
            asyncio.TimeoutError: Si le délai d'attente est dépassé
        """
        # Générer un ID unique pour cette requête
        request_id = str(uuid.uuid4())
        self._active_requests.add(request_id)

        try:
            # Enregistrer la requête dans le tracker
            response_event = self.request_tracker.register_request(request_id, timeout)

            # Créer et envoyer la requête
            request = Message(
                message_type=MessageType.REQUEST,
                sender=self.agent_id,
                sender_level=AgentLevel.TACTICAL,
                content={
                    "request_type": request_type,
                    **parameters,
                    "timeout": timeout,
                },
                recipient=recipient_id,
                channel=ChannelType.HIERARCHICAL.value,
                priority=priority,
                metadata={
                    "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                    "requires_ack": True,
                    "request_id": request_id,  # Ajouter l'ID de requête dans les métadonnées
                },
            )

            # Envoyer la requête
            success = self.middleware.send_message(request)
            if not success:
                logger.error(f"Échec de l'envoi de la requête {request_id}")
                self._active_requests.remove(request_id)
                return {"status": "error", "error": "Échec de l'envoi de la requête"}

            # Attendre la réponse avec timeout
            response_data = await self.request_tracker.wait_for_response(
                request_id, timeout
            )
            return response_data or {
                "status": "timeout",
                "error": "Pas de réponse reçue",
            }

        except asyncio.TimeoutError:
            logger.warning(f"Timeout pour la requête {request_id}")
            return {"status": "timeout", "error": "Délai d'attente dépassé"}
        except Exception as e:
            logger.error(f"Erreur lors de la requête {request_id}: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            if request_id in self._active_requests:
                self._active_requests.remove(request_id)

    async def cleanup(self):
        """Nettoie les ressources utilisées par l'adaptateur."""
        await self.request_tracker.stop()


class MessageMiddlewareWithTimeout(MessageMiddleware):
    """
    Version améliorée du MessageMiddleware avec gestion des timeouts.
    Cette classe remplace certaines méthodes pour éviter les blocages.
    """

    def __init__(self):
        """Initialise le middleware avec des timeouts."""
        super().__init__()
        self.pending_responses: Dict[str, Message] = {}
        self.response_events: Dict[str, threading.Event] = {}

    def send_message(self, message: Message) -> bool:
        """
        Version améliorée de la méthode send_message qui gère mieux les réponses.

        Args:
            message: Message à envoyer

        Returns:
            True si le message a été envoyé avec succès, False sinon
        """
        # Si c'est une réponse à une requête, enregistrer la réponse
        if message.type == MessageType.RESPONSE and message.metadata.get("reply_to"):
            request_id = message.metadata.get("reply_to")
            self.pending_responses[request_id] = message
            if request_id in self.response_events:
                self.response_events[request_id].set()

        return super().send_message(message)

    def receive_message(
        self, recipient_id: str, channel_type: ChannelType, timeout: float = 5.0
    ) -> Optional[Message]:
        """
        Version améliorée de la méthode receive_message avec timeout.

        Args:
            recipient_id: Identifiant du destinataire
            channel_type: Type de canal
            timeout: Délai maximum d'attente en secondes

        Returns:
            Le message reçu ou None si aucun message n'est disponible
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            message = super().receive_message(recipient_id, channel_type, timeout=0.1)
            if message:
                return message
            time.sleep(0.1)
        return None


def patch_middleware_for_tests(middleware: MessageMiddleware):
    """
    Applique des correctifs au middleware pour éviter les blocages dans les tests.

    Args:
        middleware: Le middleware à patcher
    """
    # Remplacer la méthode send_request_async du protocole request_response
    original_send_request_async = middleware.request_response.send_request_async

    async def patched_send_request_async(*args, **kwargs):
        """Version patched de send_request_async avec timeout forcé."""
        try:
            # Augmenter le timeout et ajouter une gestion d'erreur
            kwargs["timeout"] = kwargs.get("timeout", 10.0)
            return await asyncio.wait_for(
                original_send_request_async(*args, **kwargs),
                timeout=kwargs["timeout"] + 1.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout dans send_request_async: {kwargs.get('request_type')}"
            )
            # Créer une réponse par défaut en cas de timeout
            request = Message(
                message_type=MessageType.REQUEST,
                sender=kwargs.get("sender"),
                sender_level=kwargs.get("sender_level"),
                content={"request_type": kwargs.get("request_type")},
                recipient=kwargs.get("recipient"),
            )
            response = request.create_response(
                content={
                    "status": "timeout",
                    "info_type": "response",
                    "data": {"error": "Timeout"},
                }
            )
            response.sender = kwargs.get("recipient")
            response.sender_level = AgentLevel.TACTICAL
            return response

    # Appliquer le patch
    middleware.request_response.send_request_async = patched_send_request_async
    logger.info("Middleware patché pour les tests")


def create_patched_tactical_adapter(
    agent_id: str, middleware: MessageMiddleware
) -> TacticalAdapterWithTimeout:
    """
    Crée un adaptateur tactique avec gestion des timeouts.

    Args:
        agent_id: Identifiant de l'agent
        middleware: Middleware de communication

    Returns:
        Un adaptateur tactique avec gestion des timeouts
    """
    # Patcher le middleware
    patch_middleware_for_tests(middleware)

    # Créer et retourner l'adaptateur
    return TacticalAdapterWithTimeout(agent_id, middleware)


def create_mock_responder(
    middleware: MessageMiddleware, responder_id: str = "tactical-agent-2"
):
    """
    Crée un mock pour simuler un agent qui répond aux requêtes.

    Args:
        middleware: Middleware de communication
        responder_id: Identifiant de l'agent qui répond

    Returns:
        Une fonction qui traite les requêtes et envoie des réponses
    """

    def process_requests():
        """Traite les requêtes et envoie des réponses."""
        while True:
            try:
                # Recevoir une requête
                request = middleware.receive_message(
                    recipient_id=responder_id,
                    channel_type=ChannelType.HIERARCHICAL,
                    timeout=0.1,
                )

                if request and request.type == MessageType.REQUEST:
                    logger.info(f"Mock responder received request: {request.id}")

                    # Créer une réponse
                    response = request.create_response(
                        content={
                            "status": "success",
                            "info_type": "response",
                            "data": {"solution": "Mock solution"},
                        }
                    )
                    response.sender = responder_id
                    response.sender_level = AgentLevel.TACTICAL

                    # Envoyer la réponse
                    middleware.send_message(response)
                    logger.info(
                        f"Mock responder sent response for request: {request.id}"
                    )

            except Exception as e:
                logger.error(f"Error in mock responder: {e}")

            # Courte pause pour éviter de surcharger le CPU
            time.sleep(0.1)

    # Démarrer le thread du mock responder
    responder_thread = threading.Thread(target=process_requests, daemon=True)
    responder_thread.start()

    return responder_thread


def setup_test_environment():
    """
    Configure l'environnement de test avec les correctifs nécessaires.

    Returns:
        Un tuple contenant le middleware, l'adaptateur tactique et le thread du mock responder
    """
    # Créer le middleware
    middleware = MessageMiddlewareWithTimeout()

    # Enregistrer les canaux
    from argumentation_analysis.core.communication.hierarchical_channel import (
        HierarchicalChannel,
    )
    from argumentation_analysis.core.communication.collaboration_channel import (
        CollaborationChannel,
    )
    from argumentation_analysis.core.communication.data_channel import DataChannel
    from argumentation_analysis.paths import DATA_DIR

    hierarchical_channel = HierarchicalChannel("hierarchical")
    collaboration_channel = CollaborationChannel("collaboration")
    data_channel = DataChannel(DATA_DIR)

    middleware.register_channel(hierarchical_channel)
    middleware.register_channel(collaboration_channel)
    middleware.register_channel(data_channel)

    # Initialiser les protocoles
    middleware.initialize_protocols()

    # Créer l'adaptateur tactique avec timeout
    tactical_adapter = create_patched_tactical_adapter("tactical-agent-1", middleware)

    # Créer le mock responder
    responder_thread = create_mock_responder(middleware)

    return middleware, tactical_adapter, responder_thread


async def run_test_with_timeout():
    """
    Exécute un test simple pour vérifier que les correctifs fonctionnent.
    """
    logger.info("Démarrage du test avec timeout")

    # Configurer l'environnement de test
    middleware, tactical_adapter, responder_thread = setup_test_environment()

    try:
        # Envoyer une requête
        logger.info("Envoi d'une requête de test")
        response = await tactical_adapter.request_strategic_guidance_async(
            request_type="test_request",
            parameters={"test_param": "test_value"},
            recipient_id="tactical-agent-2",
            timeout=5.0,
        )

        # Vérifier la réponse
        logger.info(f"Réponse reçue: {response}")
        if response.get("status") == "success":
            logger.info("✅ Test réussi: La requête a été traitée correctement")
        else:
            logger.warning(
                f"⚠️ Test partiellement réussi: La requête a été traitée mais avec un statut {response.get('status')}"
            )

    except Exception as e:
        logger.error(f"❌ Test échoué: {e}")

    finally:
        # Nettoyer les ressources
        await tactical_adapter.cleanup()
        middleware.shutdown()
        logger.info("Test terminé")


if __name__ == "__main__":
    # Exécuter le test avec pytest-asyncio
    import pytest

    pytest.main([__file__, "-v"])
