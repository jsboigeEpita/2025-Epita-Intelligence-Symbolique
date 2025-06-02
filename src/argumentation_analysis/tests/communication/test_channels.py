# -*- coding: utf-8 -*-
"""
Tests unitaires pour les canaux de communication du système multi-canal.
"""

import unittest
import threading
import time
from unittest.mock import MagicMock, patch

from argumentation_analysis.core.communication.message import (
    Message, MessageType, MessagePriority, AgentLevel
)
from argumentation_analysis.core.communication.channel_interface import (
    Channel, ChannelType, ChannelException, ChannelTimeoutException
)
from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel

from argumentation_analysis.paths import DATA_DIR



class TestHierarchicalChannel(unittest.TestCase):
    """Tests pour le canal hiérarchique."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.channel = HierarchicalChannel("test-hierarchical")
        
        # Messages de test
        self.strategic_to_tactical = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        self.tactical_to_operational = Message(
            message_type=MessageType.COMMAND,
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            content={"command_type": "extract_arguments", "parameters": {"text_id": "text-123"}},
            recipient="operational-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        self.operational_to_tactical = Message(
            message_type=MessageType.INFORMATION,
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            content={"info_type": "task_result", DATA_DIR: {"result": "extraction complete"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.NORMAL
        )
    
    def test_channel_creation(self):
        """Test de la création d'un canal."""
        self.assertEqual(self.channel.id, "test-hierarchical")
        self.assertEqual(self.channel.type, ChannelType.HIERARCHICAL)
        self.assertEqual(len(self.channel.message_queues), 0)
        self.assertEqual(self.channel.stats["messages_sent"], 0)
        self.assertEqual(self.channel.stats["messages_received"], 0)
    
    def test_send_message(self):
        """Test de l'envoi d'un message."""
        # Envoyer un message
        result = self.channel.send_message(self.strategic_to_tactical)
        
        # Vérifier que le message a été envoyé avec succès
        self.assertTrue(result)
        
        # Vérifier que la file d'attente du destinataire a été créée
        self.assertIn("tactical-agent-1", self.channel.message_queues)
        
        # Vérifier que les statistiques ont été mises à jour
        self.assertEqual(self.channel.stats["messages_sent"], 1)
        self.assertEqual(self.channel.stats["by_direction"]["strategic_to_tactical"], 1)
        self.assertEqual(self.channel.stats["by_priority"]["high"], 1)
    
    def test_receive_message(self):
        """Test de la réception d'un message."""
        # Envoyer un message
        self.channel.send_message(self.strategic_to_tactical)
        
        # Recevoir le message
        received = self.channel.receive_message("tactical-agent-1", timeout=1.0)
        
        # Vérifier que le message reçu est correct
        self.assertIsNotNone(received)
        self.assertEqual(received.id, self.strategic_to_tactical.id)
        self.assertEqual(received.sender, "strategic-agent-1")
        self.assertEqual(received.recipient, "tactical-agent-1")
        
        # Vérifier que les statistiques ont été mises à jour
        self.assertEqual(self.channel.stats["messages_received"], 1)
    
    def test_receive_message_timeout(self):
        """Test de la réception d'un message avec timeout."""
        # Essayer de recevoir un message d'une file vide
        received = self.channel.receive_message("tactical-agent-1", timeout=0.1)
        
        # Vérifier qu'aucun message n'a été reçu
        self.assertIsNone(received)
    
    def test_message_priority(self):
        """Test de la priorité des messages."""
        # Créer des messages avec différentes priorités
        low_priority = Message(
            message_type=MessageType.INFORMATION,
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            content={"info_type": "status", DATA_DIR: {"status": "idle"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.LOW
        )
        
        normal_priority = Message(
            message_type=MessageType.INFORMATION,
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            content={"info_type": "status", DATA_DIR: {"status": "working"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        high_priority = Message(
            message_type=MessageType.INFORMATION,
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            content={"info_type": "status", DATA_DIR: {"status": "critical"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        critical_priority = Message(
            message_type=MessageType.INFORMATION,
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            content={"info_type": "status", DATA_DIR: {"status": "emergency"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.CRITICAL
        )
        
        # Envoyer les messages dans un ordre différent de leur priorité
        self.channel.send_message(low_priority)
        self.channel.send_message(high_priority)
        self.channel.send_message(normal_priority)
        self.channel.send_message(critical_priority)
        
        # Recevoir les messages et vérifier l'ordre
        received1 = self.channel.receive_message("tactical-agent-1")
        received2 = self.channel.receive_message("tactical-agent-1")
        received3 = self.channel.receive_message("tactical-agent-1")
        received4 = self.channel.receive_message("tactical-agent-1")
        
        # Vérifier que les messages sont reçus dans l'ordre de priorité
        self.assertEqual(received1.priority, MessagePriority.CRITICAL)
        self.assertEqual(received2.priority, MessagePriority.HIGH)
        self.assertEqual(received3.priority, MessagePriority.NORMAL)
        self.assertEqual(received4.priority, MessagePriority.LOW)
    
    def test_get_pending_messages(self):
        """Test de la récupération des messages en attente."""
        # Envoyer plusieurs messages
        self.channel.send_message(self.strategic_to_tactical)
        self.channel.send_message(self.operational_to_tactical)
        
        # Récupérer les messages en attente
        pending = self.channel.get_pending_messages("tactical-agent-1")
        
        # Vérifier que tous les messages sont récupérés
        self.assertEqual(len(pending), 2)
        
        # Vérifier que les messages sont toujours dans la file d'attente
        self.assertEqual(self.channel.message_queues["tactical-agent-1"].qsize(), 2)
        
        # Récupérer un nombre limité de messages
        limited = self.channel.get_pending_messages("tactical-agent-1", max_count=1)
        
        # Vérifier que seul le nombre demandé de messages est récupéré
        self.assertEqual(len(limited), 1)
    
    def test_subscribe_and_notify(self):
        """Test de l'abonnement et de la notification."""
        # Créer un callback simulé
        callback = MagicMock()
        
        # S'abonner au canal
        subscription_id = self.channel.subscribe(
            subscriber_id="observer-1",
            callback=callback,
            filter_criteria={"sender_level": "operational"}
        )
        
        # Vérifier que l'abonnement a été créé
        self.assertIn(subscription_id, self.channel.subscribers)
        
        # Envoyer un message qui correspond aux critères
        self.channel.send_message(self.operational_to_tactical)
        
        # Vérifier que le callback a été appelé
        callback.assert_called_once()
        self.assertEqual(callback.call_args[0][0].id, self.operational_to_tactical.id)
        
        # Réinitialiser le mock
        callback.reset_mock()
        
        # Envoyer un message qui ne correspond pas aux critères
        self.channel.send_message(self.strategic_to_tactical)
        
        # Vérifier que le callback n'a pas été appelé
        callback.assert_not_called()
    
    def test_unsubscribe(self):
        """Test du désabonnement."""
        # S'abonner au canal
        subscription_id = self.channel.subscribe(
            subscriber_id="observer-1",
            callback=MagicMock()
        )
        
        # Vérifier que l'abonnement a été créé
        self.assertIn(subscription_id, self.channel.subscribers)
        
        # Se désabonner
        result = self.channel.unsubscribe(subscription_id)
        
        # Vérifier que le désabonnement a réussi
        self.assertTrue(result)
        
        # Vérifier que l'abonnement a été supprimé
        self.assertNotIn(subscription_id, self.channel.subscribers)
    
    def test_clear_queue(self):
        """Test de la suppression des messages d'une file d'attente."""
        # Envoyer plusieurs messages
        self.channel.send_message(self.strategic_to_tactical)
        self.channel.send_message(self.operational_to_tactical)
        
        # Vérifier que les messages sont dans la file d'attente
        self.assertEqual(self.channel.message_queues["tactical-agent-1"].qsize(), 2)
        
        # Vider la file d'attente
        count = self.channel.clear_queue("tactical-agent-1")
        
        # Vérifier que le nombre correct de messages a été supprimé
        self.assertEqual(count, 2)
        
        # Vérifier que la file d'attente est vide
        self.assertEqual(self.channel.message_queues["tactical-agent-1"].qsize(), 0)
    
    def test_get_channel_info(self):
        """Test de la récupération des informations sur le canal."""
        # Envoyer quelques messages
        self.channel.send_message(self.strategic_to_tactical)
        self.channel.send_message(self.tactical_to_operational)
        
        # Récupérer les informations sur le canal
        info = self.channel.get_channel_info()
        
        # Vérifier les informations
        self.assertEqual(info["id"], "test-hierarchical")
        self.assertEqual(info["type"], "hierarchical")
        self.assertEqual(info["stats"]["messages_sent"], 2)
        self.assertEqual(len(info["queue_sizes"]), 2)
        self.assertEqual(info["queue_sizes"]["tactical-agent-1"], 1)
        self.assertEqual(info["queue_sizes"]["operational-agent-1"], 1)


class TestConcurrentAccess(unittest.TestCase):
    """Tests pour l'accès concurrent au canal."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.channel = HierarchicalChannel("test-concurrent")
    
    def test_concurrent_send_receive(self):
        """Test de l'envoi et de la réception concurrents."""
        # Nombre de messages à envoyer par thread
        message_count = 100
        
        # Fonction pour envoyer des messages
        def send_messages():
            for i in range(message_count):
                message = Message(
                    message_type=MessageType.INFORMATION,
                    sender=f"sender-{threading.get_ident()}",
                    sender_level=AgentLevel.OPERATIONAL,
                    content={"info_type": "status", DATA_DIR: {"index": i}},
                    recipient="receiver",
                    priority=MessagePriority.NORMAL
                )
                self.channel.send_message(message)
        
        # Fonction pour recevoir des messages
        received_messages = []
        
        def receive_messages():
            for _ in range(message_count * 2):  # 2 threads d'envoi
                message = self.channel.receive_message("receiver", timeout=5.0)
                if message:
                    received_messages.append(message)
        
        # Créer et démarrer les threads
        sender1 = threading.Thread(target=send_messages)
        sender2 = threading.Thread(target=send_messages)
        receiver = threading.Thread(target=receive_messages)
        
        sender1.start()
        sender2.start()
        receiver.start()
        
        # Attendre que les threads se terminent
        sender1.join()
        sender2.join()
        receiver.join()
        
        # Vérifier que tous les messages ont été reçus
        self.assertEqual(len(received_messages), message_count * 2)
        
        # Vérifier que les statistiques sont correctes
        self.assertEqual(self.channel.stats["messages_sent"], message_count * 2)
        self.assertEqual(self.channel.stats["messages_received"], message_count * 2)


if __name__ == "__main__":
    unittest.main()