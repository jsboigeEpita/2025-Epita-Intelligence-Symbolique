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

from argumentation_analysis.core.communication.message import (
    Message, MessageType, MessagePriority, AgentLevel
)
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel
from argumentation_analysis.core.communication.collaboration_channel import CollaborationChannel
from argumentation_analysis.core.communication.data_channel import DataChannel

from argumentation_analysis.paths import DATA_DIR

# Configuration du logger
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                   datefmt='%H:%M:%S')
logger = logging.getLogger("DirectTest")

class TestRequestResponseDirect(unittest.IsolatedAsyncioTestCase):
    """Test direct du protocole de requête-réponse."""
    
    async def asyncSetUp(self):
        """Initialisation asynchrone avant chaque test."""
        logger.info("Setting up test environment")
        
        # Créer le middleware
        self.middleware = MessageMiddleware()
        
        # Enregistrer les canaux
        self.hierarchical_channel = HierarchicalChannel("hierarchical")
        self.collaboration_channel = CollaborationChannel("collaboration")
        self.data_channel = DataChannel(DATA_DIR)
        
        self.middleware.register_channel(self.hierarchical_channel)
        self.middleware.register_channel(self.collaboration_channel)
        self.middleware.register_channel(self.data_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        logger.info("Test environment setup complete")
    
    async def asyncTearDown(self):
        """Nettoyage après chaque test."""
        logger.info("Tearing down test environment")
        
        # Arrêter proprement le middleware
        self.middleware.shutdown()
        
        # Attendre un peu pour que tout se termine
        await asyncio.sleep(0.5)
        
        logger.info("Test environment teardown complete")
    
    async def test_direct_request_response(self):
        """Test direct du protocole de requête-réponse."""
        logger.info("Starting test_direct_request_response")
        
        # Variable pour stocker la réponse entre les tâches
        response_received = None
        response_event = asyncio.Event()
        
        # Créer une tâche pour simuler l'agent qui répond
        async def responder_agent():
            logger.info("Responder agent started")
            
            # Recevoir la requête
            request = await asyncio.to_thread(
                self.middleware.receive_message,
                recipient_id="responder",
                channel_type=None,  # Tous les canaux
                timeout=10.0  # Timeout augmenté
            )
            
            logger.info(f"Responder received request: {request.id if request else 'None'}")
            
            if request:
                # Créer une réponse
                response = request.create_response(
                    content={"status": "success", "data": {"solution": "Use pattern X"}},
                    sender_level=AgentLevel.TACTICAL  # Spécifier explicitement le niveau
                )
                
                logger.info(f"Responder created response: {response.id} with reply_to={response.metadata.get('reply_to')}")
                
                # Attendre un peu pour s'assurer que la requête est bien enregistrée
                await asyncio.sleep(1.0)
                
                # Envoyer la réponse
                success = self.middleware.send_message(response)
                
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
        
        # Créer et envoyer une requête directement via le middleware
        request = Message(
            message_type=MessageType.REQUEST,
            sender="requester",
            sender_level=AgentLevel.TACTICAL,
            content={
                "request_type": "test_request",
                "test": "data",
                "timeout": 15.0
            },
            recipient="responder",
            priority=MessagePriority.NORMAL,
            metadata={
                "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                "requires_ack": True
            }
        )
        
        # Envoyer la requête
        self.middleware.send_message(request)
        logger.info(f"Request sent: {request.id}")
        
        # Attendre que la réponse soit reçue
        try:
            await asyncio.wait_for(response_event.wait(), timeout=10.0)
            logger.info("Response event set, response received")
            
            # Vérifier que la réponse a été reçue
            self.assertIsNotNone(response_received)
            self.assertEqual(response_received.content.get("data", {}).get("solution"), "Use pattern X")
            self.assertEqual(response_received.metadata.get("reply_to"), request.id)
            
            logger.info(f"Received response: {response_received.id}")
            
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for response")
            raise
        except Exception as e:
            logger.error(f"Error in request-response test: {e}")
            raise
        finally:
            # Attendre que la tâche se termine
            try:
                await asyncio.wait_for(responder_task, timeout=5.0)
                logger.info("Responder task completed")
            except asyncio.TimeoutError:
                logger.warning("Responder task timed out, but continuing test")
        
        logger.info("test_direct_request_response completed")

if __name__ == "__main__":
    unittest.main()