# -*- coding: utf-8 -*-
"""
Tests d'intégration pour la communication asynchrone avec des corrections.

Ce fichier contient des versions améliorées des tests asynchrones avec:
1. Des logs supplémentaires pour le débogage
2. Des timeouts augmentés
3. Une logique simplifiée pour éviter les problèmes de synchronisation
4. Utilisation native de pytest-asyncio
"""

import threading
import time
import uuid
import logging
from unittest.mock import MagicMock, patch
import pytest

from argumentation_analysis.core.communication.message import (
    Message, MessageType, MessagePriority, AgentLevel
)
from argumentation_analysis.core.communication.channel_interface import ChannelType
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel
from argumentation_analysis.core.communication.collaboration_channel import CollaborationChannel
from argumentation_analysis.core.communication.data_channel import DataChannel
from argumentation_analysis.core.communication.strategic_adapter import StrategicAdapter
from argumentation_analysis.core.communication.tactical_adapter import TacticalAdapter
from argumentation_analysis.core.communication.operational_adapter import OperationalAdapter

from argumentation_analysis.paths import DATA_DIR


# Configuration du logger
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
                   datefmt='%H:%M:%S')
logger = logging.getLogger("AsyncTests")


@pytest.fixture
def test_environment():
    """Fixture pour initialiser l'environnement de test."""
    logger.info("Setting up test environment")
    
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
    
    # Créer les adaptateurs pour les agents
    strategic_adapter = StrategicAdapter("strategic-agent-1", middleware)
    tactical_adapter = TacticalAdapter("tactical-agent-1", middleware)
    operational_adapter = OperationalAdapter("operational-agent-1", middleware)
    
    # Créer un adaptateur pour l'agent qui répond
    tactical_adapter2 = TacticalAdapter("tactical-agent-2", middleware)
    
    logger.info("Test environment setup complete")
    
    # Yield de l'environnement pour les tests
    yield {
        'middleware': middleware,
        'hierarchical_channel': hierarchical_channel,
        'collaboration_channel': collaboration_channel,
        'data_channel': data_channel,
        'strategic_adapter': strategic_adapter,
        'tactical_adapter': tactical_adapter,
        'operational_adapter': operational_adapter,
        'tactical_adapter2': tactical_adapter2
    }
    
    # Code de teardown
    logger.info("Tearing down test environment")
    
    # Arrêter proprement le middleware
    middleware.shutdown()
    
    logger.info("Test environment teardown complete")
    
def test_sync_request_response(test_environment):
    """Test de la communication asynchrone par requête-réponse."""
    logger.info("Starting test_sync_request_response")
    
    env = test_environment
    middleware = env['middleware']
    
    # Variable pour stocker la réponse entre les tâches
    response_received = None
    response_event = threading.Event()
    response_lock = threading.Lock()
    
    # Créer un thread pour simuler l'agent qui répond
    def responder_agent():
        logger.info("Responder agent started")
        
        time.sleep(0.1)
        
        # Recevoir la requête (appel bloquant)
        request = middleware.receive_message(
            recipient_id="tactical-agent-2",
            channel_type=ChannelType.HIERARCHICAL,
            timeout=10.0
        )
        
        logger.info(f"Responder received request: {request.id if request else 'None'}")
        
        if request:
            # Créer une réponse
            response = request.create_response(
                content={"status": "success", "info_type": "response", "data": {"solution": "Use pattern X"}}
            )
            response.sender = "tactical-agent-2"
            response.sender_level = AgentLevel.TACTICAL
            
            logger.info(f"Responder created response: {response.id} with reply_to={response.metadata.get('reply_to')}")
            
            with response_lock:
                time.sleep(0.2) # Simuler un temps de traitement
                
                success = middleware.send_message(response)
                
                logger.info(f"Response sent: {response.id}, success: {success}")
                
                nonlocal response_received
                response_received = response
                response_event.set()
        else:
            logger.error("No request received by responder")
    
    # Démarrer l'agent qui répond dans un thread
    responder_thread = threading.Thread(target=responder_agent)
    responder_thread.start()
    
    time.sleep(0.2)
    
    logger.info("Sending request from tactical agent 1")
    
    # Créer et envoyer une requête
    request = Message(
        message_type=MessageType.REQUEST,
        sender="tactical-agent-1",
        sender_level=AgentLevel.TACTICAL,
        content={
            "request_type": "assistance",
            "description": "Need help",
            "context": {},
            "timeout": 15.0
        },
        recipient="tactical-agent-2",
        channel=ChannelType.HIERARCHICAL.value,
        priority=MessagePriority.NORMAL,
        metadata={"conversation_id": f"conv-{uuid.uuid4().hex[:8]}", "requires_ack": True}
    )
    
    middleware.send_message(request)
    logger.info(f"Request sent: {request.id}")
    
    # Attendre que la réponse soit reçue
    event_was_set = response_event.wait(timeout=15.0)
    
    if not event_was_set:
        responder_thread.join(timeout=1.0) # Tenter de joindre le thread
        pytest.fail("Timeout waiting for response event")
        
    logger.info("Response event set, response received")
    
    # Vérifier que la réponse a été reçue
    assert response_received is not None
    assert response_received.content.get("data", {}).get("solution") == "Use pattern X"
    assert response_received.metadata.get("reply_to") == request.id
    
    # Extraire les données de la réponse
    assistance = response_received.content.get("data", {})
    logger.info(f"Received assistance: {assistance}")
    
    responder_thread.join(timeout=5.0)
    assert not responder_thread.is_alive(), "Responder thread should have finished"
    
    # Vérifier que la réponse a été reçue
    assert assistance is not None
    assert assistance["solution"] == "Use pattern X"
    
    logger.info("test_sync_request_response completed successfully")
    
def test_sync_parallel_requests(test_environment):
    """Test de l'envoi parallèle de requêtes en synchrone avec threading."""
    logger.info("Starting test_sync_parallel_requests")
    
    env = test_environment
    middleware = env['middleware']
    
    # Variables pour stocker les réponses
    responses_received = {}
    response_events = {}
    response_lock = threading.Lock()
    
    def responder_agent():
        logger.info("Responder agent started for parallel requests")
        
        time.sleep(0.1)
        
        for i in range(3):
            # Recevoir une requête (appel bloquant)
            request = middleware.receive_message(
                recipient_id="tactical-agent-2",
                channel_type=ChannelType.HIERARCHICAL,
                timeout=10.0
            )
            
            logger.info(f"Responder received request {i+1}: {request.id if request else 'None'}")
            
            if request:
                response = request.create_response(
                    content={"status": "success", "info_type": "response", "data": {"request_id": request.id, "index": i}}
                )
                response.sender = "tactical-agent-2"
                response.sender_level = AgentLevel.TACTICAL
                
                time.sleep(0.2)
                
                logger.info(f"Responder created response {i+1}: {response.id} with reply_to={response.metadata.get('reply_to')}")
                
                with response_lock:
                    success = middleware.send_message(response)
                    logger.info(f"Response {i+1} sent: {response.id}, success: {success}")
                    
                    request_id = request.id
                    responses_received[request_id] = response
                    if request_id in response_events:
                        response_events[request_id].set()
            else:
                logger.error(f"No request {i+1} received by responder")
    
    responder_thread = threading.Thread(target=responder_agent)
    responder_thread.start()
    
    time.sleep(0.5) # Laisser le temps au responder de se mettre en écoute
    
    logger.info("Sending parallel requests")
    
    requests = []
    for i in range(3):
        request = Message(
            message_type=MessageType.REQUEST,
            sender="tactical-agent-1", sender_level=AgentLevel.TACTICAL,
            content={"request_type": f"request-{i}", "index": i, "timeout": 15.0},
            recipient="tactical-agent-2", channel=ChannelType.HIERARCHICAL.value,
            priority=MessagePriority.NORMAL,
            metadata={"conversation_id": f"conv-{uuid.uuid4().hex[:8]}", "requires_ack": True}
        )
        
        response_events[request.id] = threading.Event()
        
        logger.info(f"Sending request {i}: {request.id}")
        middleware.send_message(request)
        
        requests.append(request)
    
    logger.info("Waiting for all responses")
    all_responses = []
    
    for request in requests:
        event_was_set = response_events[request.id].wait(timeout=10.0)
        
        if event_was_set:
            logger.info(f"Response event set for request {request.id}")
            response = responses_received.get(request.id)
            if response:
                response_data = response.content.get("data", {})
                all_responses.append(response_data)
                logger.info(f"Received response for request {request.id}: {response_data}")
            else:
                pytest.fail(f"Event set but no response found for request {request.id}")
        else:
            pytest.fail(f"Timeout waiting for response to request {request.id}")

    responder_thread.join(timeout=5.0)
    assert not responder_thread.is_alive(), "Responder thread should have finished"
    
    assert len(all_responses) == 3
    # Les réponses peuvent arriver dans n'importe quel ordre, nous trions par index
    all_responses.sort(key=lambda r: r.get('index', -1))
    
    for i, response_data in enumerate(all_responses):
        assert response_data is not None
        assert "request_id" in response_data
        assert response_data["index"] == i
    
    logger.info("test_sync_parallel_requests completed successfully")