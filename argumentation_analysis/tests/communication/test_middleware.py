"""
Tests unitaires pour le middleware de messagerie du système de communication multi-canal.
"""

import unittest
import asyncio
import threading
import time
from unittest.mock import MagicMock, patch

from argumentation_analysis.core.communication.message import (
    Message, MessageType, MessagePriority, AgentLevel
)
from argumentation_analysis.core.communication.channel_interface import (
    Channel, ChannelType, ChannelException
)
from argumentation_analysis.core.communication.middleware import MessageMiddleware
from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel
from argumentation_analysis.core.communication.collaboration_channel import CollaborationChannel
from argumentation_analysis.core.communication.data_channel import DataChannel

from argumentation_analysis.paths import DATA_DIR



class TestMessageMiddleware(unittest.TestCase):
    """Tests pour le middleware de messagerie."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer des canaux réels
        self.hierarchical_channel = HierarchicalChannel("test-hierarchical")
        self.collaboration_channel = CollaborationChannel("test-collaboration")
        self.data_channel = DataChannel("test-data")
        
        self.middleware.register_channel(self.hierarchical_channel)
        self.middleware.register_channel(self.collaboration_channel)
        self.middleware.register_channel(self.data_channel)
        
        # Messages de test
        self.command_message = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        self.info_message = Message(
            message_type=MessageType.INFORMATION,
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            content={"info_type": "task_result", DATA_DIR: {"result": "extraction complete"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        self.request_message = Message(
            message_type=MessageType.REQUEST,
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            content={"request_type": "assistance", "description": "Need help", "context": {}},
            recipient="tactical-agent-2",
            priority=MessagePriority.NORMAL
        )
    
    def test_register_channel(self):
        """Test de l'enregistrement d'un canal."""
        # Créer un nouveau canal
        new_channel = HierarchicalChannel("test-new")
        
        # Enregistrer le canal
        self.middleware.register_channel(new_channel)
        
        # Vérifier que le canal a été enregistré
        self.assertEqual(self.middleware.get_channel(ChannelType.HIERARCHICAL), new_channel)
        
        # Vérifier que les statistiques ont été initialisées
        self.assertIn(ChannelType.HIERARCHICAL.value, self.middleware.stats["by_channel"])
    
    def test_determine_channel(self):
        """Test de la détermination du canal approprié pour un message."""
        # Message de commande (devrait aller sur le canal hiérarchique)
        self.assertEqual(
            self.middleware.determine_channel(self.command_message),
            ChannelType.HIERARCHICAL
        )
        
        # Message d'information (dépend du contenu)
        self.assertEqual(
            self.middleware.determine_channel(self.info_message),
            ChannelType.HIERARCHICAL
        )
        
        # Message de requête d'assistance (devrait aller sur le canal de collaboration)
        self.request_message.content["request_type"] = "assistance"
        self.assertEqual(
            self.middleware.determine_channel(self.request_message),
            ChannelType.COLLABORATION
        )
        
        # Message avec canal spécifié
        self.info_message.channel = ChannelType.DATA.value
        self.assertEqual(
            self.middleware.determine_channel(self.info_message),
            ChannelType.DATA
        )
    
    def test_send_message(self):
        """Test de l'envoi d'un message."""
        # Envoyer un message
        result = self.middleware.send_message(self.command_message)
        
        # Vérifier que le message a été envoyé avec succès
        self.assertTrue(result)
        
        # Vérifier que le canal a été défini dans le message
        self.assertEqual(self.command_message.channel, ChannelType.HIERARCHICAL.value)
        
        # Vérifier que les statistiques ont été mises à jour
        self.assertEqual(self.middleware.stats["messages_sent"], 1)
        self.assertEqual(self.middleware.stats["by_channel"][ChannelType.HIERARCHICAL.value]["sent"], 1)
        
        # Vérifier que le message est dans la file d'attente du destinataire
        pending = self.hierarchical_channel.get_pending_messages("tactical-agent-1")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].id, self.command_message.id)
    
    def test_receive_message(self):
        """Test de la réception d'un message."""
        # Envoyer un message
        self.middleware.send_message(self.command_message)
        
        # Recevoir le message
        received = self.middleware.receive_message(
            recipient_id="tactical-agent-1",
            channel_type=ChannelType.HIERARCHICAL,
            timeout=1.0
        )
        
        # Vérifier que le message reçu est correct
        self.assertIsNotNone(received)
        self.assertEqual(received.id, self.command_message.id)
        
        # Vérifier que les statistiques ont été mises à jour
        self.assertEqual(self.middleware.stats["messages_received"], 1)
        self.assertEqual(self.middleware.stats["by_channel"][ChannelType.HIERARCHICAL.value]["received"], 1)
    
    def test_receive_message_from_any_channel(self):
        """Test de la réception d'un message de n'importe quel canal."""
        # Envoyer des messages sur différents canaux
        self.middleware.send_message(self.command_message)  # Hiérarchique
        
        self.info_message.channel = ChannelType.DATA.value
        self.middleware.send_message(self.info_message)  # Données
        
        # Recevoir un message sans spécifier le canal
        received = self.middleware.receive_message(
            recipient_id="tactical-agent-1",
            timeout=1.0
        )
        
        # Vérifier qu'un message a été reçu
        self.assertIsNotNone(received)
        
        # Recevoir un autre message
        received2 = self.middleware.receive_message(
            recipient_id="tactical-agent-1",
            timeout=1.0
        )
        
        # Vérifier qu'un autre message a été reçu
        self.assertIsNotNone(received2)
        
        # Vérifier que les deux messages sont différents
        self.assertNotEqual(received.id, received2.id)
    
    def test_get_pending_messages(self):
        """Test de la récupération des messages en attente."""
        # Envoyer des messages sur différents canaux
        self.middleware.send_message(self.command_message)  # Hiérarchique
        
        self.info_message.channel = ChannelType.DATA.value
        self.middleware.send_message(self.info_message)  # Données
        
        # Récupérer les messages en attente d'un canal spécifique
        hierarchical_pending = self.middleware.get_pending_messages(
            recipient_id="tactical-agent-1",
            channel_type=ChannelType.HIERARCHICAL
        )
        
        # Vérifier que seuls les messages du canal spécifié sont récupérés
        self.assertEqual(len(hierarchical_pending), 1)
        self.assertEqual(hierarchical_pending[0].id, self.command_message.id)
        
        # Récupérer les messages en attente de tous les canaux
        all_pending = self.middleware.get_pending_messages(
            recipient_id="tactical-agent-1"
        )
        
        # Vérifier que tous les messages sont récupérés
        self.assertEqual(len(all_pending), 2)
    
    def test_message_handlers(self):
        """Test des gestionnaires de messages."""
        # Créer un gestionnaire simulé
        handler = MagicMock()
        
        # Enregistrer le gestionnaire pour les messages de commande
        self.middleware.register_message_handler(MessageType.COMMAND, handler)
        
        # Envoyer un message de commande
        self.middleware.send_message(self.command_message)
        
        # Recevoir le message (ce qui devrait déclencher le gestionnaire)
        self.middleware.receive_message(
            recipient_id="tactical-agent-1",
            channel_type=ChannelType.HIERARCHICAL
        )
        
        # Vérifier que le gestionnaire a été appelé
        handler.assert_called_once()
        self.assertEqual(handler.call_args[0][0].id, self.command_message.id)
    
    def test_global_handler(self):
        """Test du gestionnaire global."""
        # Créer un gestionnaire global simulé
        global_handler = MagicMock()
        
        # Enregistrer le gestionnaire global
        self.middleware.register_global_handler(global_handler)
        
        # Envoyer des messages de différents types
        self.middleware.send_message(self.command_message)
        self.middleware.send_message(self.info_message)
        
        # Recevoir les messages (ce qui devrait déclencher le gestionnaire global)
        self.middleware.receive_message(
            recipient_id="tactical-agent-1",
            channel_type=ChannelType.HIERARCHICAL
        )
        self.middleware.receive_message(
            recipient_id="tactical-agent-1",
            channel_type=ChannelType.HIERARCHICAL
        )
        
        # Vérifier que le gestionnaire global a été appelé pour chaque message
        self.assertEqual(global_handler.call_count, 2)
    
    def test_get_statistics(self):
        """Test de la récupération des statistiques."""
        # Envoyer des messages
        self.middleware.send_message(self.command_message)
        self.middleware.send_message(self.info_message)
        
        # Recevoir un message
        self.middleware.receive_message(
            recipient_id="tactical-agent-1",
            channel_type=ChannelType.HIERARCHICAL
        )
        
        # Récupérer les statistiques
        stats = self.middleware.get_statistics()
        
        # Vérifier les statistiques
        self.assertEqual(stats["messages_sent"], 2)
        self.assertEqual(stats["messages_received"], 1)
        self.assertEqual(stats["by_channel"][ChannelType.HIERARCHICAL.value]["sent"], 2)
        self.assertEqual(stats["by_channel"][ChannelType.HIERARCHICAL.value]["received"], 1)
    
    def test_get_channel_info(self):
        """Test de la récupération des informations sur un canal."""
        # Envoyer un message
        self.middleware.send_message(self.command_message)
        
        # Récupérer les informations sur le canal
        info = self.middleware.get_channel_info(ChannelType.HIERARCHICAL)
        
        # Vérifier les informations
        self.assertEqual(info["id"], "test-hierarchical")
        self.assertEqual(info["type"], "hierarchical")
        self.assertEqual(info["stats"]["messages_sent"], 1)
        self.assertEqual(info["queue_sizes"]["tactical-agent-1"], 1)
    
    def test_initialize_protocols(self):
        """Test de l'initialisation des protocoles."""
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Vérifier que les protocoles ont été initialisés
        self.assertIsNotNone(self.middleware.request_response)
        self.assertIsNotNone(self.middleware.publish_subscribe)
    
    def test_send_request(self):
        """Test de l'envoi d'une requête."""
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Utiliser un mock pour simuler la méthode send_request du protocole
        with patch.object(
            self.middleware.request_response,
            'send_request',
            return_value=Message(
                message_type=MessageType.RESPONSE,
                sender="tactical-agent-2",
                sender_level=AgentLevel.TACTICAL,
                content={"status": "success", DATA_DIR: {"result": "assistance provided"}},
                recipient="tactical-agent-1",
                priority=MessagePriority.NORMAL,
                metadata={"reply_to": "mock-request-id"}
            )
        ) as mock_send_request:
        
            # Envoyer une requête
            response = self.middleware.send_request(
                sender="tactical-agent-1",
                sender_level=AgentLevel.TACTICAL,
                recipient="tactical-agent-2",
                request_type="assistance",
                content={"description": "Need help", "context": {}},
                timeout=2.0,
                priority=MessagePriority.NORMAL,
                channel=ChannelType.COLLABORATION.value
            )
            
            # Vérifier que la méthode du protocole a été appelée
            mock_send_request.assert_called_once()
        
            # Vérifier que la réponse a été reçue
            self.assertIsNotNone(response)
            self.assertEqual(response.type, MessageType.RESPONSE)
            self.assertEqual(response.sender, "tactical-agent-2")
            self.assertEqual(response.content["status"], "success")
    
    def test_publish_subscribe(self):
        """Test du protocole de publication-abonnement."""
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Créer un callback simulé
        callback = MagicMock()
        
        # S'abonner à un topic
        subscription_id = self.middleware.subscribe(
            subscriber_id="tactical-agent-1",
            topic_id="test-topic",
            callback=callback
        )
        
        # Vérifier que l'abonnement a été créé
        self.assertIsNotNone(subscription_id)
        
        # Publier un message sur le topic
        self.middleware.publish(
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


class TestAsyncMiddleware(unittest.IsolatedAsyncioTestCase):
    """Tests pour les fonctionnalités asynchrones du middleware."""
    
    async def asyncSetUp(self):
        """Initialisation asynchrone avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer des canaux
        self.hierarchical_channel = HierarchicalChannel("test-hierarchical")
        self.middleware.register_channel(self.hierarchical_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
    
    async def test_receive_message_async(self):
        """Test de la réception asynchrone d'un message."""
        # Envoyer un message
        message = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        self.middleware.send_message(message)
        
        # Recevoir le message de manière asynchrone
        received = await self.middleware.receive_message_async(
            recipient_id="tactical-agent-1",
            channel_type=ChannelType.HIERARCHICAL,
            timeout=1.0
        )
        
        # Vérifier que le message reçu est correct
        self.assertIsNotNone(received)
        self.assertEqual(received.id, message.id)
    
    async def test_send_request_async(self):
        """Test de l'envoi asynchrone d'une requête."""
        # Utiliser un mock pour simuler la méthode send_request_async du protocole
        from unittest.mock import patch, AsyncMock
        
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
            self.middleware.request_response,
            'send_request_async',
            new_callable=AsyncMock,
            return_value=mock_response
        ) as mock_send_request:
            
            # Appeler la méthode du middleware qui utilise le protocole
            response = await self.middleware.send_request_async(
                sender="tactical-agent-1",
                sender_level=AgentLevel.TACTICAL,
                recipient="tactical-agent-2",
                request_type="assistance",
                content={"description": "Need help", "context": {}},
                timeout=1.0,
                priority=MessagePriority.NORMAL,
                channel=ChannelType.HIERARCHICAL.value
            )
            
            # Vérifier que la méthode du protocole a été appelée
            mock_send_request.assert_called_once()
            
            # Vérifier que la réponse est celle attendue
            self.assertIsNotNone(response)
            self.assertEqual(response.type, MessageType.RESPONSE)
            self.assertEqual(response.sender, "tactical-agent-2")
            self.assertEqual(response.content["status"], "success")


if __name__ == "__main__":
    unittest.main()