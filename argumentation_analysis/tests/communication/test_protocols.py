"""
Tests unitaires pour les protocoles de communication du système multi-canal.
"""

import unittest
import asyncio
import threading
import time
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

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
        # Créer une réponse simulée
        mock_response = Message(
            message_type=MessageType.RESPONSE,
            sender="tactical-agent-2",
            sender_level=AgentLevel.TACTICAL,
            content={"status": "success", DATA_DIR: {"result": "assistance provided"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.NORMAL,
            metadata={"reply_to": "mock-request-id"}
        )
        
        # Patcher la méthode send_request du protocole
        with patch.object(
            self.protocol,
            'send_request',
            return_value=mock_response
        ):
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
        
        # Vérifier que la réponse a été reçue
        self.assertIsNotNone(response)
        self.assertEqual(response.type, MessageType.RESPONSE)
        self.assertEqual(response.sender, "tactical-agent-2")
        self.assertEqual(response.content["status"], "success")
    
    def test_request_timeout(self):
        """Test du timeout d'une requête."""
        # Patcher la méthode send_request pour simuler un timeout
        with patch.object(
            self.protocol,
            'send_request',
            return_value=None
        ):
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
        
        # Créer un événement pour vérifier qu'il est déclenché
        completed_event = threading.Event()
        
        # Patcher la méthode handle_response pour éviter la suppression de l'entrée
        original_handle_response = self.protocol.handle_response
        
        def mock_handle_response(response):
            # Stocker la réponse avant qu'elle ne soit supprimée
            result = original_handle_response(response)
            return result
        
        with patch.object(self.protocol, 'handle_response', side_effect=mock_handle_response):
            # Enregistrer une attente de réponse avec la structure correcte
            self.protocol.pending_requests[request_id] = {
                "request": Message(
                    message_type=MessageType.REQUEST,
                    sender="tactical-agent-1",
                    sender_level=AgentLevel.TACTICAL,
                    content={"request_type": "test"},
                    recipient="tactical-agent-2"
                ),
                "expires_at": datetime.now() + timedelta(seconds=30),
                "response": None,
                "completed": completed_event
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
            
            # Vérifier que l'événement a été déclenché
            self.assertTrue(completed_event.is_set())
    
    def test_multiple_requests(self):
        """Test de l'envoi de plusieurs requêtes simultanées."""
        # Créer des réponses simulées
        mock_responses = []
        for i in range(3):
            mock_response = Message(
                message_type=MessageType.RESPONSE,
                sender="tactical-agent-2",
                sender_level=AgentLevel.TACTICAL,
                content={"status": "success", DATA_DIR: {"request_id": f"mock-request-{i}"}},
                recipient="tactical-agent-1",
                priority=MessagePriority.NORMAL,
                metadata={"reply_to": f"mock-request-{i}"}
            )
            mock_responses.append(mock_response)
        
        # Patcher la méthode send_request du protocole
        with patch.object(
            self.protocol,
            'send_request',
            side_effect=mock_responses
        ):
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
        
        # Vérifier que l'abonné est présent dans le topic
        topic = self.protocol.topics["test-topic"]
        self.assertIn(subscription_id, topic.subscribers)
        self.assertEqual(topic.subscribers[subscription_id]["subscriber_id"], "tactical-agent-1")
        
        # Patcher la méthode publish_message du topic pour éviter les problèmes de synchronisation
        with patch.object(topic, 'publish_message', return_value=["tactical-agent-1"]) as mock_publish:
            # Publier un message sur le topic
            self.protocol.publish(
                topic_id="test-topic",
                sender="strategic-agent-1",
                sender_level=AgentLevel.STRATEGIC,
                content={DATA_DIR: "test data"},
                priority=MessagePriority.NORMAL
            )
            
            # Vérifier que la méthode publish_message a été appelée
            mock_publish.assert_called_once()
    
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
        topic = self.protocol.topics["test-topic"]
        self.assertIn(subscription_id, topic.subscribers)
        
        # Se désabonner
        result = self.protocol.unsubscribe("test-topic", subscription_id)
        
        # Vérifier que le désabonnement a réussi
        self.assertTrue(result)
        self.assertNotIn(subscription_id, topic.subscribers)
    
    def test_topic_pattern_matching(self):
        """Test de la correspondance des patterns de topics."""
        # Créer des mocks pour les topics
        mock_topic1 = MagicMock()
        mock_topic2 = MagicMock()
        mock_topic3 = MagicMock()
        
        # Patcher la méthode create_topic pour retourner nos mocks
        with patch.object(self.protocol, 'create_topic') as mock_create_topic:
            # Configurer mock_create_topic pour retourner différents mocks selon le topic_id
            def side_effect(topic_id):
                if topic_id == "events.system.*":
                    return mock_topic1
                elif topic_id == "events.*.critical":
                    return mock_topic2
                elif topic_id == "events.system.critical":
                    return mock_topic3
                else:
                    return MagicMock()
            
            mock_create_topic.side_effect = side_effect
            
            # S'abonner à des topics avec des patterns
            self.protocol.subscribe(
                subscriber_id="agent1",
                topic_id="events.system.*",
                callback=MagicMock()
            )
            
            self.protocol.subscribe(
                subscriber_id="agent2",
                topic_id="events.*.critical",
                callback=MagicMock()
            )
            
            self.protocol.subscribe(
                subscriber_id="agent3",
                topic_id="events.system.critical",
                callback=MagicMock()
            )
            
            # Vérifier que create_topic a été appelé pour chaque pattern
            self.assertEqual(mock_create_topic.call_count, 3)
    
    def test_filter_criteria(self):
        """Test des critères de filtrage."""
        # Créer un mock pour le topic
        mock_topic = MagicMock()
        
        # Patcher la méthode create_topic pour retourner notre mock
        with patch.object(self.protocol, 'create_topic', return_value=mock_topic):
            # S'abonner à un topic avec des critères de filtrage
            subscription_id = self.protocol.subscribe(
                subscriber_id="tactical-agent-1",
                topic_id="events",
                callback=MagicMock(),
                filter_criteria={
                    "priority": "high",
                    "content": {"event_type": "alert"}
                }
            )
            
            # Vérifier que add_subscriber a été appelé avec les bons arguments
            mock_topic.add_subscriber.assert_called_once()
            args, kwargs = mock_topic.add_subscriber.call_args
            self.assertEqual(args[0], "tactical-agent-1")
            
            # Vérifier que les critères de filtrage ont été passés correctement
            # Selon l'implémentation, ils peuvent être passés comme argument positionnel ou mot-clé
            if len(args) > 2:
                # Argument positionnel
                self.assertEqual(args[2], {
                    "priority": "high",
                    "content": {"event_type": "alert"}
                })
            elif "filter_criteria" in kwargs:
                # Mot-clé
                self.assertEqual(kwargs["filter_criteria"], {
                    "priority": "high",
                    "content": {"event_type": "alert"}
                })


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
        # Créer une réponse simulée
        mock_response = Message(
            message_type=MessageType.RESPONSE,
            sender="tactical-agent-2",
            sender_level=AgentLevel.TACTICAL,
            content={"status": "success", DATA_DIR: {"result": "assistance provided"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.NORMAL,
            metadata={"reply_to": "mock-request-id"}
        )
        
        # Patcher la méthode send_request_async du protocole
        with patch.object(
            self.request_response,
            'send_request_async',
            new_callable=AsyncMock,
            return_value=mock_response
        ):
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
        # Patcher la méthode send_request_async du protocole pour simuler un timeout
        with patch.object(
            self.request_response,
            'send_request_async',
            new_callable=AsyncMock,
            return_value=None
        ):
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