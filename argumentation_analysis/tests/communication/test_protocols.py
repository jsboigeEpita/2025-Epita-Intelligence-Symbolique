"""
Tests unitaires pour les protocoles de communication du système multi-canal.
"""

import unittest
import asyncio
import threading
import time
from unittest.mock import MagicMock, patch

from argumentation_analysis.core.communication.message import (
    Message, MessageType, MessagePriority, AgentLevel
)
from argumentation_analysis.core.communication.channel_interface import ChannelType
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel
from argumentation_analysis.core.communication.request_response import RequestResponseProtocol
from argumentation_analysis.core.communication.pub_sub import PublishSubscribeProtocol

from argumentation_analysis.paths import DATA_DIR



class TestRequestResponseProtocol(unittest.TestCase):
    """Tests pour le protocole de requête-réponse."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer un canal
        self.channel = HierarchicalChannel("test-hierarchical")
        self.middleware.register_channel(self.channel)
        
        # Créer le protocole
        self.protocol = RequestResponseProtocol(self.middleware)
    
    def test_send_request(self):
        """Test de l'envoi d'une requête."""
        # Simuler la réponse à une requête
        def simulate_response():
            time.sleep(0.1)  # Attendre un peu pour simuler un traitement
            
            # Récupérer la requête
            request = self.middleware.receive_message(
                recipient_id="tactical-agent-2",
                channel_type=ChannelType.HIERARCHICAL
            )
            
            if request:
                # Créer une réponse
                response = Message(
                    message_type=MessageType.RESPONSE,
                    sender="tactical-agent-2",
                    sender_level=AgentLevel.TACTICAL,
                    content={"status": "success", DATA_DIR: {"result": "assistance provided"}},
                    recipient=request.sender,
                    priority=request.priority,
                    metadata={"reply_to": request.id, "conversation_id": request.metadata.get("conversation_id")}
                )
                
                # Envoyer la réponse
                self.middleware.send_message(response)
        
        # Démarrer un thread pour simuler la réponse
        response_thread = threading.Thread(target=simulate_response)
        response_thread.start()
        
        # Envoyer une requête
        response = self.protocol.send_request(
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            recipient="tactical-agent-2",
            request_type="assistance",
            content={"description": "Need help", "context": {}},
            timeout=2.0,
            priority=MessagePriority.NORMAL,
            channel=ChannelType.HIERARCHICAL.value
        )
        
        # Attendre que le thread se termine
        response_thread.join()
        
        # Vérifier que la réponse a été reçue
        self.assertIsNotNone(response)
        self.assertEqual(response.type, MessageType.RESPONSE)
        self.assertEqual(response.sender, "tactical-agent-2")
        self.assertEqual(response.content["status"], "success")
    
    def test_request_timeout(self):
        """Test du timeout d'une requête."""
        # Envoyer une requête sans réponse
        response = self.protocol.send_request(
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            recipient="tactical-agent-2",
            request_type="assistance",
            content={"description": "Need help", "context": {}},
            timeout=0.1,  # Timeout court
            priority=MessagePriority.NORMAL,
            channel=ChannelType.HIERARCHICAL.value
        )
        
        # Vérifier que la réponse est None (timeout)
        self.assertIsNone(response)
    
    def test_handle_response(self):
        """Test de la gestion des réponses."""
        # Créer une requête
        request_id = "request-123"
        conversation_id = "conv-456"
        
        # Enregistrer une attente de réponse
        self.protocol.pending_requests[request_id] = {
            "event": threading.Event(),
            "response": None,
            "conversation_id": conversation_id
        }
        
        # Créer une réponse
        response = Message(
            message_type=MessageType.RESPONSE,
            sender="tactical-agent-2",
            sender_level=AgentLevel.TACTICAL,
            content={"status": "success", DATA_DIR: {"result": "assistance provided"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.NORMAL,
            metadata={"reply_to": request_id, "conversation_id": conversation_id}
        )
        
        # Appeler le gestionnaire de réponses
        self.protocol.handle_response(response)
        
        # Vérifier que la réponse a été enregistrée
        self.assertEqual(self.protocol.pending_requests[request_id]["response"], response)
        
        # Vérifier que l'événement a été déclenché
        self.assertTrue(self.protocol.pending_requests[request_id]["event"].is_set())
    
    def test_multiple_requests(self):
        """Test de l'envoi de plusieurs requêtes simultanées."""
        # Simuler les réponses à des requêtes
        def simulate_responses():
            time.sleep(0.1)  # Attendre un peu pour simuler un traitement
            
            # Traiter plusieurs requêtes
            for _ in range(3):
                # Récupérer une requête
                request = self.middleware.receive_message(
                    recipient_id="tactical-agent-2",
                    channel_type=ChannelType.HIERARCHICAL
                )
                
                if request:
                    # Créer une réponse
                    response = Message(
                        message_type=MessageType.RESPONSE,
                        sender="tactical-agent-2",
                        sender_level=AgentLevel.TACTICAL,
                        content={"status": "success", DATA_DIR: {"request_id": request.id}},
                        recipient=request.sender,
                        priority=request.priority,
                        metadata={"reply_to": request.id, "conversation_id": request.metadata.get("conversation_id")}
                    )
                    
                    # Envoyer la réponse
                    self.middleware.send_message(response)
        
        # Démarrer un thread pour simuler les réponses
        response_thread = threading.Thread(target=simulate_responses)
        response_thread.start()
        
        # Envoyer plusieurs requêtes
        responses = []
        for i in range(3):
            response = self.protocol.send_request(
                sender="tactical-agent-1",
                sender_level=AgentLevel.TACTICAL,
                recipient="tactical-agent-2",
                request_type=f"request-{i}",
                content={"index": i},
                timeout=2.0,
                priority=MessagePriority.NORMAL,
                channel=ChannelType.HIERARCHICAL.value
            )
            responses.append(response)
        
        # Attendre que le thread se termine
        response_thread.join()
        
        # Vérifier que toutes les réponses ont été reçues
        self.assertEqual(len(responses), 3)
        for response in responses:
            self.assertIsNotNone(response)
            self.assertEqual(response.type, MessageType.RESPONSE)
            self.assertEqual(response.sender, "tactical-agent-2")
            self.assertEqual(response.content["status"], "success")


class TestPublishSubscribeProtocol(unittest.TestCase):
    """Tests pour le protocole de publication-abonnement."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer un canal
        self.channel = HierarchicalChannel("test-hierarchical")
        self.middleware.register_channel(self.channel)
        
        # Créer le protocole
        self.protocol = PublishSubscribeProtocol(self.middleware)
    
    def test_subscribe_and_publish(self):
        """Test de l'abonnement et de la publication."""
        # Créer un callback simulé
        callback = MagicMock()
        
        # S'abonner à un topic
        subscription_id = self.protocol.subscribe(
            subscriber_id="tactical-agent-1",
            topic_id="test-topic",
            callback=callback
        )
        
        # Vérifier que l'abonnement a été créé
        self.assertIsNotNone(subscription_id)
        self.assertIn("test-topic", self.protocol.topics)
        self.assertIn("tactical-agent-1", self.protocol.topics["test-topic"]["subscribers"])
        
        # Publier un message sur le topic
        self.protocol.publish(
            topic_id="test-topic",
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={DATA_DIR: "test data"},
            priority=MessagePriority.NORMAL
        )
        
        # Attendre un peu pour que le message soit traité
        time.sleep(0.1)
        
        # Vérifier que le callback a été appelé
        callback.assert_called_once()
        self.assertEqual(callback.call_args[0][0].content[DATA_DIR], "test data")
    
    def test_unsubscribe(self):
        """Test du désabonnement."""
        # S'abonner à un topic
        subscription_id = self.protocol.subscribe(
            subscriber_id="tactical-agent-1",
            topic_id="test-topic",
            callback=MagicMock()
        )
        
        # Vérifier que l'abonnement a été créé
        self.assertIn("test-topic", self.protocol.topics)
        self.assertIn("tactical-agent-1", self.protocol.topics["test-topic"]["subscribers"])
        
        # Se désabonner
        result = self.protocol.unsubscribe(subscription_id)
        
        # Vérifier que le désabonnement a réussi
        self.assertTrue(result)
        self.assertNotIn("tactical-agent-1", self.protocol.topics["test-topic"]["subscribers"])
    
    def test_topic_pattern_matching(self):
        """Test de la correspondance des patterns de topics."""
        # Créer des callbacks simulés
        callback1 = MagicMock()
        callback2 = MagicMock()
        callback3 = MagicMock()
        
        # S'abonner à des topics avec des patterns
        self.protocol.subscribe(
            subscriber_id="agent1",
            topic_id="events.system.*",
            callback=callback1
        )
        
        self.protocol.subscribe(
            subscriber_id="agent2",
            topic_id="events.*.critical",
            callback=callback2
        )
        
        self.protocol.subscribe(
            subscriber_id="agent3",
            topic_id="events.system.critical",
            callback=callback3
        )
        
        # Publier un message qui correspond à tous les patterns
        self.protocol.publish(
            topic_id="events.system.critical",
            sender="system",
            sender_level=AgentLevel.SYSTEM,
            content={"alert": "critical error"},
            priority=MessagePriority.CRITICAL
        )
        
        # Attendre un peu pour que le message soit traité
        time.sleep(0.1)
        
        # Vérifier que tous les callbacks ont été appelés
        callback1.assert_called_once()
        callback2.assert_called_once()
        callback3.assert_called_once()
        
        # Réinitialiser les mocks
        callback1.reset_mock()
        callback2.reset_mock()
        callback3.reset_mock()
        
        # Publier un message qui correspond à un seul pattern
        self.protocol.publish(
            topic_id="events.system.warning",
            sender="system",
            sender_level=AgentLevel.SYSTEM,
            content={"alert": "warning"},
            priority=MessagePriority.HIGH
        )
        
        # Attendre un peu pour que le message soit traité
        time.sleep(0.1)
        
        # Vérifier que seul le callback correspondant a été appelé
        callback1.assert_called_once()
        callback2.assert_not_called()
        callback3.assert_not_called()
    
    def test_filter_criteria(self):
        """Test des critères de filtrage."""
        # Créer un callback simulé
        callback = MagicMock()
        
        # S'abonner à un topic avec des critères de filtrage
        self.protocol.subscribe(
            subscriber_id="tactical-agent-1",
            topic_id="events",
            callback=callback,
            filter_criteria={
                "priority": "high",
                "content": {"event_type": "alert"}
            }
        )
        
        # Publier un message qui correspond aux critères
        self.protocol.publish(
            topic_id="events",
            sender="system",
            sender_level=AgentLevel.SYSTEM,
            content={"event_type": "alert", "description": "High CPU usage"},
            priority=MessagePriority.HIGH
        )
        
        # Attendre un peu pour que le message soit traité
        time.sleep(0.1)
        
        # Vérifier que le callback a été appelé
        callback.assert_called_once()
        
        # Réinitialiser le mock
        callback.reset_mock()
        
        # Publier un message qui ne correspond pas aux critères
        self.protocol.publish(
            topic_id="events",
            sender="system",
            sender_level=AgentLevel.SYSTEM,
            content={"event_type": "info", "description": "System status"},
            priority=MessagePriority.NORMAL
        )
        
        # Attendre un peu pour que le message soit traité
        time.sleep(0.1)
        
        # Vérifier que le callback n'a pas été appelé
        callback.assert_not_called()


class TestAsyncProtocols(unittest.IsolatedAsyncioTestCase):
    """Tests pour les fonctionnalités asynchrones des protocoles."""
    
    async def asyncSetUp(self):
        """Initialisation asynchrone avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer un canal
        self.channel = HierarchicalChannel("test-hierarchical")
        self.middleware.register_channel(self.channel)
        
        # Créer les protocoles
        self.request_response = RequestResponseProtocol(self.middleware)
        self.publish_subscribe = PublishSubscribeProtocol(self.middleware)
    
    async def test_send_request_async(self):
        """Test de l'envoi asynchrone d'une requête."""
        # Simuler la réponse à une requête
        async def simulate_response():
            await asyncio.sleep(0.1)  # Attendre un peu pour simuler un traitement
            
            # Récupérer la requête
            request = self.middleware.receive_message(
                recipient_id="tactical-agent-2",
                channel_type=ChannelType.HIERARCHICAL
            )
            
            if request:
                # Créer une réponse
                response = Message(
                    message_type=MessageType.RESPONSE,
                    sender="tactical-agent-2",
                    sender_level=AgentLevel.TACTICAL,
                    content={"status": "success", DATA_DIR: {"result": "assistance provided"}},
                    recipient=request.sender,
                    priority=request.priority,
                    metadata={"reply_to": request.id, "conversation_id": request.metadata.get("conversation_id")}
                )
                
                # Envoyer la réponse
                self.middleware.send_message(response)
        
        # Démarrer une tâche pour simuler la réponse
        asyncio.create_task(simulate_response())
        
        # Envoyer une requête de manière asynchrone
        response = await self.request_response.send_request_async(
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            recipient="tactical-agent-2",
            request_type="assistance",
            content={"description": "Need help", "context": {}},
            timeout=2.0,
            priority=MessagePriority.NORMAL,
            channel=ChannelType.HIERARCHICAL.value
        )
        
        # Vérifier que la réponse a été reçue
        self.assertIsNotNone(response)
        self.assertEqual(response.type, MessageType.RESPONSE)
        self.assertEqual(response.sender, "tactical-agent-2")
        self.assertEqual(response.content["status"], "success")
    
    async def test_request_timeout_async(self):
        """Test du timeout d'une requête asynchrone."""
        # Envoyer une requête sans réponse
        response = await self.request_response.send_request_async(
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            recipient="tactical-agent-2",
            request_type="assistance",
            content={"description": "Need help", "context": {}},
            timeout=0.1,  # Timeout court
            priority=MessagePriority.NORMAL,
            channel=ChannelType.HIERARCHICAL.value
        )
        
        # Vérifier que la réponse est None (timeout)
        self.assertIsNone(response)


if __name__ == "__main__":
    unittest.main()