"""
Tests unitaires pour le middleware de messagerie du système de communication multi-canal.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

from argumentation_analysis.core.communication.message import Message, MessageType, MessagePriority, AgentLevel
from argumentation_analysis.core.communication.channel_interface import Channel, ChannelType
from argumentation_analysis.core.communication.middleware import MessageMiddleware

from argumentation_analysis.paths import DATA_DIR



class MockChannel(Channel):
    """Canal simulé pour les tests."""
    
    def __init__(self, channel_id: str, channel_type: ChannelType):
        super().__init__(channel_id, channel_type)
        self.sent_messages = []
        self.message_queue = {}
    
    def send_message(self, message: Message) -> bool:
        self.sent_messages.append(message)
        
        if message.recipient not in self.message_queue:
            self.message_queue[message.recipient] = []
        
        self.message_queue[message.recipient].append(message)
        return True
    
    def receive_message(self, recipient_id: str, timeout=None) -> Message:
        if recipient_id in self.message_queue and self.message_queue[recipient_id]:
            return self.message_queue[recipient_id].pop(0)
        return None
    
    def subscribe(self, subscriber_id, callback=None, filter_criteria=None):
        return f"sub-{subscriber_id}"
    
    def unsubscribe(self, subscription_id):
        return True
    
    def get_pending_messages(self, recipient_id, max_count=None):
        if recipient_id not in self.message_queue:
            return []
        
        messages = self.message_queue[recipient_id].copy()
        
        if max_count is not None:
            messages = messages[:max_count]
        
        return messages
    
    def get_channel_info(self):
        return {
            "id": self.id,
            "type": self.type.value,
            "message_count": sum(len(queue) for queue in self.message_queue.values()),
            "recipient_count": len(self.message_queue)
        }


class TestMessageMiddleware(unittest.TestCase):
    """Tests pour le middleware de messagerie."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer des canaux simulés
        self.hierarchical_channel = MockChannel("hierarchical", ChannelType.HIERARCHICAL)
        self.collaboration_channel = MockChannel("collaboration", ChannelType.COLLABORATION)
        self.data_channel = MockChannel(DATA_DIR, ChannelType.DATA)
        
        self.middleware.register_channel(self.hierarchical_channel)
        self.middleware.register_channel(self.collaboration_channel)
        self.middleware.register_channel(self.data_channel)
    
    def test_send_message(self):
        """Test de l'envoi d'un message."""
        # Créer un message
        message = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Envoyer le message
        result = self.middleware.send_message(message)
        
        # Vérifier que le message a été envoyé avec succès
        self.assertTrue(result)
        
        # Vérifier que le message a été routé vers le canal hiérarchique
        self.assertEqual(len(self.hierarchical_channel.sent_messages), 1)
        self.assertEqual(self.hierarchical_channel.sent_messages[0].id, message.id)
        
        # Vérifier que le canal a été défini dans le message
        self.assertEqual(message.channel, ChannelType.HIERARCHICAL.value)
    
    def test_receive_message(self):
        """Test de la réception d'un message."""
        # Créer et envoyer un message
        message = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        self.middleware.send_message(message)
        
        # Recevoir le message
        received_message = self.middleware.receive_message("tactical-agent-1", ChannelType.HIERARCHICAL)
        
        # Vérifier que le message reçu est correct
        self.assertIsNotNone(received_message)
        self.assertEqual(received_message.id, message.id)
        self.assertEqual(received_message.sender, "strategic-agent-1")
        self.assertEqual(received_message.recipient, "tactical-agent-1")
    
    def test_determine_channel(self):
        """Test de la détermination du canal approprié pour un message."""
        # Message de commande (devrait aller sur le canal hiérarchique)
        command_message = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1"
        )
        
        # Message de données (devrait aller sur le canal de données)
        data_message = Message(
            message_type=MessageType.INFORMATION,
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            content={"info_type": "analysis_result", DATA_DIR: {"result": "some data"}},
            recipient="tactical-agent-1"
        )
        
        # Message de collaboration (devrait aller sur le canal de collaboration)
        collab_message = Message(
            message_type=MessageType.REQUEST,
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            content={"request_type": "assistance", "description": "Need help"},
            recipient="tactical-agent-2"
        )
        
        # Vérifier la détermination des canaux
        self.assertEqual(self.middleware.determine_channel(command_message), ChannelType.HIERARCHICAL)
        self.assertEqual(self.middleware.determine_channel(data_message), ChannelType.DATA)  # Basé sur le type d'info
        self.assertEqual(self.middleware.determine_channel(collab_message), ChannelType.COLLABORATION)  # Basé sur le type de requête
        
        # Forcer le canal pour le message de données
        data_message.content["info_type"] = "analysis_result"
        data_message.channel = ChannelType.DATA.value
        self.assertEqual(self.middleware.determine_channel(data_message), ChannelType.DATA)
        
        # Forcer le canal pour le message de collaboration
        collab_message.content["request_type"] = "assistance"
        collab_message.channel = ChannelType.COLLABORATION.value
        self.assertEqual(self.middleware.determine_channel(collab_message), ChannelType.COLLABORATION)
    
    def test_get_pending_messages(self):
        """Test de la récupération des messages en attente."""
        # Créer et envoyer plusieurs messages
        recipient = "tactical-agent-1"
        
        messages = [
            Message(
                message_type=MessageType.COMMAND,
                sender="strategic-agent-1",
                sender_level=AgentLevel.STRATEGIC,
                content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
                recipient=recipient,
                priority=MessagePriority.HIGH
            ),
            Message(
                message_type=MessageType.COMMAND,
                sender="strategic-agent-2",
                sender_level=AgentLevel.STRATEGIC,
                content={"command_type": "allocate_resources", "parameters": {"resource_type": "cpu"}},
                recipient=recipient,
                priority=MessagePriority.NORMAL
            ),
            Message(
                message_type=MessageType.INFORMATION,
                sender="operational-agent-1",
                sender_level=AgentLevel.OPERATIONAL,
                content={"info_type": "task_result", DATA_DIR: {"result": "some data"}},
                recipient=recipient,
                priority=MessagePriority.NORMAL
            )
        ]
        
        for message in messages:
            self.middleware.send_message(message)
        
        # Récupérer les messages en attente
        pending_messages = self.middleware.get_pending_messages(recipient)
        
        # Vérifier que tous les messages sont récupérés
        self.assertEqual(len(pending_messages), 3)
        
        # Récupérer un nombre limité de messages
        limited_messages = self.middleware.get_pending_messages(recipient, max_count=2)
        self.assertEqual(len(limited_messages), 2)
    
    def test_message_handlers(self):
        """Test des gestionnaires de messages."""
        # Créer un gestionnaire simulé
        handler = MagicMock()
        
        # Enregistrer le gestionnaire pour les messages de commande
        self.middleware.register_message_handler(MessageType.COMMAND, handler)
        
        # Créer et envoyer un message de commande
        message = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Envoyer le message
        self.middleware.send_message(message)
        
        # Recevoir le message (ce qui devrait déclencher le gestionnaire)
        self.middleware.receive_message("tactical-agent-1", ChannelType.HIERARCHICAL)
        
        # Vérifier que le gestionnaire a été appelé
        handler.assert_called_once()
        self.assertEqual(handler.call_args[0][0].id, message.id)
    
    def test_get_channel(self):
        """Test de la récupération d'un canal par son type."""
        # Récupérer les canaux
        hierarchical = self.middleware.get_channel(ChannelType.HIERARCHICAL)
        collaboration = self.middleware.get_channel(ChannelType.COLLABORATION)
        data = self.middleware.get_channel(ChannelType.DATA)
        
        # Vérifier que les canaux sont correctement récupérés
        self.assertEqual(hierarchical, self.hierarchical_channel)
        self.assertEqual(collaboration, self.collaboration_channel)
        self.assertEqual(data, self.data_channel)
        
        # Vérifier qu'un canal inexistant retourne None
        self.assertIsNone(self.middleware.get_channel(ChannelType.NEGOTIATION))
    
    def test_get_statistics(self):
        """Test de la récupération des statistiques du middleware."""
        # Créer et envoyer plusieurs messages
        for i in range(5):
            message = Message(
                message_type=MessageType.COMMAND,
                sender=f"strategic-agent-{i}",
                sender_level=AgentLevel.STRATEGIC,
                content={"command_type": "analyze_text", "parameters": {"text_id": f"text-{i}"}},
                recipient=f"tactical-agent-{i}",
                priority=MessagePriority.HIGH
            )
            self.middleware.send_message(message)
        
        # Récupérer les statistiques
        stats = self.middleware.get_statistics()
        
        # Vérifier les statistiques
        self.assertEqual(stats["messages_sent"], 5)
        self.assertEqual(stats["by_channel"][ChannelType.HIERARCHICAL.value]["sent"], 5)


    def test_global_handler(self):
        """Test des gestionnaires globaux de messages."""
        # Créer un gestionnaire global simulé
        global_handler = MagicMock()
        
        # Enregistrer le gestionnaire global
        self.middleware.register_global_handler(global_handler)
        
        # Créer et envoyer un message
        message = Message(
            message_type=MessageType.INFORMATION,
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            content={"info_type": "status_update", DATA_DIR: {"status": "running"}},
            recipient="tactical-agent-1"
        )
        
        # Envoyer le message
        self.middleware.send_message(message)
        
        # Recevoir le message (ce qui devrait déclencher le gestionnaire global)
        self.middleware.receive_message("tactical-agent-1", ChannelType.HIERARCHICAL)
        
        # Vérifier que le gestionnaire global a été appelé
        global_handler.assert_called_once()
        self.assertEqual(global_handler.call_args[0][0].id, message.id)
    
    def test_initialize_protocols(self):
        """Test de l'initialisation des protocoles de communication."""
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Vérifier que les protocoles ont été initialisés
        self.assertIsNotNone(self.middleware.request_response)
        self.assertIsNotNone(self.middleware.publish_subscribe)
    
    @patch('argumentation_analysis.core.communication.request_response.RequestResponseProtocol')
    def test_send_request(self, mock_request_response):
        """Test de la méthode send_request."""
        # Configurer le mock
        mock_protocol = MagicMock()
        mock_request_response.return_value = mock_protocol
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Appeler send_request
        self.middleware.send_request(
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            request_type="get_analysis",
            description="Besoin d'une analyse",
            context={"text_id": "text-123"},
            recipient="tactical-agent-1",
            timeout=30
        )
        
        # Vérifier que la méthode du protocole a été appelée
        mock_protocol.send_request.assert_called_once()
    
    @patch('argumentation_analysis.core.communication.pub_sub.PublishSubscribeProtocol')
    def test_publish(self, mock_pub_sub):
        """Test de la méthode publish."""
        # Configurer le mock
        mock_protocol = MagicMock()
        mock_pub_sub.return_value = mock_protocol
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Appeler publish
        self.middleware.publish(
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            topic="analysis_results",
            data={"text_id": "text-123", "results": {"score": 0.85}}
        )
        
        # Vérifier que la méthode du protocole a été appelée
        mock_protocol.publish.assert_called_once()
    
    @patch('argumentation_analysis.core.communication.pub_sub.PublishSubscribeProtocol')
    def test_subscribe(self, mock_pub_sub):
        """Test de la méthode subscribe."""
        # Configurer le mock
        mock_protocol = MagicMock()
        mock_pub_sub.return_value = mock_protocol
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Créer un callback simulé
        callback = MagicMock()
        
        # Appeler subscribe
        self.middleware.subscribe(
            subscriber_id="tactical-agent-1",
            topic="analysis_results",
            callback=callback
        )
        
        # Vérifier que la méthode du protocole a été appelée
        mock_protocol.subscribe.assert_called_once()
    
    @patch('argumentation_analysis.core.communication.request_response.RequestResponseProtocol')
    @patch('argumentation_analysis.core.communication.pub_sub.PublishSubscribeProtocol')
    def test_shutdown(self, mock_pub_sub, mock_request_response):
        """Test de la méthode shutdown."""
        # Configurer les mocks
        mock_req_resp_protocol = MagicMock()
        mock_pub_sub_protocol = MagicMock()
        mock_request_response.return_value = mock_req_resp_protocol
        mock_pub_sub.return_value = mock_pub_sub_protocol
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Appeler shutdown
        self.middleware.shutdown()
        
        # Vérifier que les méthodes shutdown des protocoles ont été appelées
        mock_req_resp_protocol.shutdown.assert_called_once()
        mock_pub_sub_protocol.shutdown.assert_called_once()


class TestMessageMiddlewareAsync(unittest.IsolatedAsyncioTestCase):
    """Tests pour les méthodes asynchrones du middleware de messagerie."""
    
    async def asyncSetUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer des canaux simulés
        self.hierarchical_channel = MockChannel("hierarchical", ChannelType.HIERARCHICAL)
        self.middleware.register_channel(self.hierarchical_channel)
    
    async def test_receive_message_async(self):
        """Test de la méthode receive_message_async."""
        # Créer et envoyer un message
        message = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1"
        )
        
        self.middleware.send_message(message)
        
        # Recevoir le message de manière asynchrone
        received_message = await self.middleware.receive_message_async(
            "tactical-agent-1",
            ChannelType.HIERARCHICAL
        )
        
        # Vérifier que le message reçu est correct
        self.assertIsNotNone(received_message)
        self.assertEqual(received_message.id, message.id)
        self.assertEqual(received_message.sender, "strategic-agent-1")
        self.assertEqual(received_message.recipient, "tactical-agent-1")
    
    @patch('argumentation_analysis.core.communication.request_response.RequestResponseProtocol')
    async def test_send_request_async(self, mock_request_response):
        """Test de la méthode send_request_async."""
        # Configurer le mock
        mock_protocol = MagicMock()
        mock_protocol.send_request_async = AsyncMock()
        mock_protocol.send_request_async.return_value = {"status": "success"}
        mock_request_response.return_value = mock_protocol
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Appeler send_request_async
        result = await self.middleware.send_request_async(
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            request_type="get_analysis",
            description="Besoin d'une analyse",
            context={"text_id": "text-123"},
            recipient="tactical-agent-1",
            timeout=30
        )
        
        # Vérifier que la méthode du protocole a été appelée
        mock_protocol.send_request_async.assert_called_once()
        self.assertEqual(result, {"status": "success"})


if __name__ == "__main__":
    unittest.main()