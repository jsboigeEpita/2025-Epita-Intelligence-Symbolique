# -*- coding: utf-8 -*-
"""
Test direct du protocole de requête-réponse pour isoler les problèmes.
"""

import asyncio
import logging
import threading
import time
import unittest
import uuid
from datetime import datetime
import pytest

from argumentation_analysis.core.communication.message import (
    Message,
    MessageType,
    MessagePriority,
    AgentLevel,
)
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.hierarchical_channel import (
    HierarchicalChannel,
)
from argumentation_analysis.core.communication.collaboration_channel import (
    CollaborationChannel,
)
from argumentation_analysis.core.communication.data_channel import DataChannel

from argumentation_analysis.paths import DATA_DIR

# Configuration du logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("DirectTest")

import pytest_asyncio


@pytest.fixture
def middleware_instance():
    """Fixture pour initialiser et nettoyer le middleware."""
    logger.info("Setting up middleware fixture")

    # Créer le middleware
    middleware = MessageMiddleware()

    # Enregistrer les canaux
    hierarchical_channel = HierarchicalChannel("hierarchical")
    collaboration_channel = CollaborationChannel("collaboration")
    data_channel = DataChannel(DATA_DIR)

    middleware.register_channel(hierarchical_channel)
    middleware.register_channel(collaboration_channel)
    middleware.register_channel(data_channel)

    # Initialiser les protocoles
    middleware.initialize_protocols()

    logger.info("Middleware fixture setup complete")

    yield middleware

    # Code de teardown
    logger.info("Tearing down middleware fixture")
    middleware.shutdown()
    time.sleep(0.5)  # Laisser le temps pour le nettoyage
    logger.info("Middleware fixture teardown complete")


def test_direct_request_response(middleware_instance):
    """Test direct du protocole de requête-réponse en utilisant une fixture pytest."""

    async def run_test():
        logger.info("Starting test_direct_request_response")

        # Le middleware est maintenant passé via la fixture
        middleware = middleware_instance

        # Variable pour stocker la réponse entre les tâches
        response_received = None
        response_event = asyncio.Event()

        # Créer une tâche pour simuler l'agent qui répond
        async def responder_agent():
            logger.info("Responder agent started")

            # Recevoir la requête
            request = await asyncio.to_thread(
                middleware.receive_message,
                recipient_id="responder",
                channel_type=None,  # Tous les canaux
                timeout=10.0,
            )

            logger.info(
                f"Responder received request: {request.id if request else 'None'}"
            )

            if request:
                # Créer une réponse
                response = request.create_response(
                    content={
                        "status": "success",
                        "data": {"solution": "Use pattern X"},
                    },
                    sender_level=AgentLevel.TACTICAL,
                )

                logger.info(
                    f"Responder created response: {response.id} with reply_to={response.metadata.get('reply_to')}"
                )

                # Attendre un peu pour s'assurer que la requête est bien enregistrée
                await asyncio.sleep(1.0)

                # Envoyer la réponse
                success = middleware.send_message(response)

                logger.info(f"Response sent: {response.id}, success: {success}")

                # Stocker la réponse pour la vérification
                nonlocal response_received
                response_received = response
                response_event.set()
            else:
                logger.error("No request received by responder")

        # Démarrer l'agent qui répond
        responder_task = asyncio.create_task(responder_agent())

        # Attendre un peu pour que l'agent démarre
        await asyncio.sleep(1.0)

        logger.info("Sending request directly via middleware")

        # Créer et envoyer une requête
        request_msg = Message(
            message_type=MessageType.REQUEST,
            sender="requester",
            sender_level=AgentLevel.TACTICAL,
            content={"request_type": "test_request", "test": "data", "timeout": 15.0},
            recipient="responder",
            priority=MessagePriority.NORMAL,
            metadata={
                "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                "requires_ack": True,
            },
        )

        # Envoyer la requête
        middleware.send_message(request_msg)
        logger.info(f"Request sent: {request_msg.id}")

        # Attendre que la réponse soit reçue
        try:
            await asyncio.wait_for(response_event.wait(), timeout=10.0)
            logger.info("Response event set, response received")

            # Vérifier la réponse avec des assertions standard
            assert response_received is not None
            assert (
                response_received.content.get("data", {}).get("solution")
                == "Use pattern X"
            )
            assert response_received.metadata.get("reply_to") == request_msg.id

            logger.info(f"Received response: {response_received.id}")

        except asyncio.TimeoutError:
            logger.error("Timeout waiting for response")
            pytest.fail("Timeout waiting for response from responder agent.")
        except Exception as e:
            logger.error(f"Error in request-response test: {e}")
            pytest.fail(f"An unexpected error occurred: {e}")
        finally:
            # Attendre que la tâche de l'agent se termine
            try:
                await asyncio.wait_for(responder_task, timeout=5.0)
                logger.info("Responder task completed")
            except asyncio.TimeoutError:
                logger.warning(
                    "Responder task timed out. This might indicate an issue."
                )

        logger.info("test_direct_request_response completed")

    asyncio.run(run_test())
