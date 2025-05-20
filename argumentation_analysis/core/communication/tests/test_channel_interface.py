"""
Tests unitaires pour l'interface de canal du système de communication multi-canal.
"""

import unittest
from unittest.mock import MagicMock, patch

from argumentation_analysis.core.communication.channel_interface import (
    Channel, ChannelType, ChannelException, ChannelFullException,
    ChannelTimeoutException, ChannelClosedException, InvalidMessageException,
    UnauthorizedAccessException
)
from argumentation_analysis.core.communication.message import Message, MessageType, MessagePriority, AgentLevel


class TestChannelType(unittest.TestCase):
    """Tests pour l'énumération ChannelType."""
    
    def test_channel_types(self):
        """Vérifie que tous les types de canaux sont correctement définis."""
        self.assertEqual(ChannelType.HIERARCHICAL.value, "hierarchical")
        self.assertEqual(ChannelType.COLLABORATION.value, "collaboration")
        self.assertEqual(ChannelType.NEGOTIATION.value, "negotiation")
        self.assertEqual(ChannelType.FEEDBACK.value, "feedback")
        self.assertEqual(ChannelType.SYSTEM.value, "system")


class MockChannel(Channel):
    """Implémentation concrète de Channel pour les tests."""
    
    def __init__(self, channel_id, channel_type, config=None):
        super().__init__(channel_id, channel_type, config)
        self.messages = {}  # messages par destinataire
    
    def send_message(self, message):
        if message.recipient not in self.messages:
            self.messages[message.recipient] = []
        self.messages[message.recipient].append(message)
        return True
    
    def receive_message(self, recipient_id, timeout=None):
        if recipient_id in self.messages and self.messages[recipient_id]:
            return self.messages[recipient_id].pop(0)
        return None
    
    def subscribe(self, subscriber_id, callback=None, filter_criteria=None):
        self.subscribers[subscriber_id] = {
            "callback": callback,
            "filter_criteria": filter_criteria
        }
        return f"subscription-{subscriber_id}"
    
    def unsubscribe(self, subscription_id):
        subscriber_id = subscription_id.replace("subscription-", "")
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
            return True
        return False
    
    def get_pending_messages(self, recipient_id, max_count=None):
        if recipient_id not in self.messages:
            return []
        
        messages = self.messages[recipient_id].copy()
        if max_count is not None:
            messages = messages[:max_count]
        
        return messages
    
    def get_channel_info(self):
        return {
            "id": self.id,
            "type": self.type.value,
            "subscribers": len(self.subscribers),
            "messages": sum(len(msgs) for msgs in self.messages.values())
        }


class TestChannel(unittest.TestCase):
    """Tests pour la classe abstraite Channel."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.channel = MockChannel("test-channel", ChannelType.HIERARCHICAL, {"buffer_size": 100})
    
    def test_init(self):
        """Test de l'initialisation d'un canal."""
        self.assertEqual(self.channel.id, "test-channel")
        self.assertEqual(self.channel.type, ChannelType.HIERARCHICAL)
        self.assertEqual(self.channel.config, {"buffer_size": 100})
        self.assertEqual(self.channel.subscribers, {})
    
    def test_matches_filter_no_criteria(self):
        """Test de la méthode matches_filter sans critères."""
        message = Message(
            message_type=MessageType.COMMAND,
            sender="agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command": "test"},
            recipient="agent-2"
        )
        
        # Sans critères, tous les messages correspondent
        self.assertTrue(self.channel.matches_filter(message, {}))
        self.assertTrue(self.channel.matches_filter(message, None))
    
    def test_matches_filter_message_type(self):
        """Test de la méthode matches_filter avec critère de type de message."""
        message = Message(
            message_type=MessageType.COMMAND,
            sender="agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command": "test"},
            recipient="agent-2"
        )
        
        # Correspondance avec le type de message
        self.assertTrue(self.channel.matches_filter(message, {"message_type": "command"}))
        self.assertTrue(self.channel.matches_filter(message, {"message_type": ["command", "request"]}))
        
        # Non-correspondance avec le type de message
        self.assertFalse(self.channel.matches_filter(message, {"message_type": "information"}))
        self.assertFalse(self.channel.matches_filter(message, {"message_type": ["information", "response"]}))
    
    def test_matches_filter_sender(self):
        """Test de la méthode matches_filter avec critère d'expéditeur."""
        message = Message(
            message_type=MessageType.COMMAND,
            sender="agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command": "test"},
            recipient="agent-2"
        )
        
        # Correspondance avec l'expéditeur
        self.assertTrue(self.channel.matches_filter(message, {"sender": "agent-1"}))
        self.assertTrue(self.channel.matches_filter(message, {"sender": ["agent-1", "agent-3"]}))
        
        # Non-correspondance avec l'expéditeur
        self.assertFalse(self.channel.matches_filter(message, {"sender": "agent-2"}))
        self.assertFalse(self.channel.matches_filter(message, {"sender": ["agent-2", "agent-3"]}))
    
    def test_matches_filter_priority(self):
        """Test de la méthode matches_filter avec critère de priorité."""
        message = Message(
            message_type=MessageType.COMMAND,
            sender="agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command": "test"},
            recipient="agent-2",
            priority=MessagePriority.HIGH
        )
        
        # Correspondance avec la priorité
        self.assertTrue(self.channel.matches_filter(message, {"priority": "high"}))
        self.assertTrue(self.channel.matches_filter(message, {"priority": ["high", "critical"]}))
        
        # Non-correspondance avec la priorité
        self.assertFalse(self.channel.matches_filter(message, {"priority": "normal"}))
        self.assertFalse(self.channel.matches_filter(message, {"priority": ["normal", "low"]}))
    
    def test_matches_filter_sender_level(self):
        """Test de la méthode matches_filter avec critère de niveau d'expéditeur."""
        message = Message(
            message_type=MessageType.COMMAND,
            sender="agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command": "test"},
            recipient="agent-2"
        )
        
        # Correspondance avec le niveau d'expéditeur
        self.assertTrue(self.channel.matches_filter(message, {"sender_level": "strategic"}))
        self.assertTrue(self.channel.matches_filter(message, {"sender_level": ["strategic", "tactical"]}))
        
        # Non-correspondance avec le niveau d'expéditeur
        self.assertFalse(self.channel.matches_filter(message, {"sender_level": "operational"}))
        self.assertFalse(self.channel.matches_filter(message, {"sender_level": ["operational", "system"]}))
    
    def test_matches_filter_content(self):
        """Test de la méthode matches_filter avec critère de contenu."""
        message = Message(
            message_type=MessageType.COMMAND,
            sender="agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command": "test", "priority": "high", "tags": ["important", "urgent"]},
            recipient="agent-2"
        )
        
        # Correspondance avec le contenu
        self.assertTrue(self.channel.matches_filter(message, {"content": {"command": "test"}}))
        self.assertTrue(self.channel.matches_filter(message, {"content": {"priority": "high"}}))
        
        # Non-correspondance avec le contenu
        self.assertFalse(self.channel.matches_filter(message, {"content": {"command": "other"}}))
        self.assertFalse(self.channel.matches_filter(message, {"content": {"priority": "low"}}))
        self.assertFalse(self.channel.matches_filter(message, {"content": {"unknown": "value"}}))
    
    def test_matches_filter_multiple_criteria(self):
        """Test de la méthode matches_filter avec plusieurs critères."""
        message = Message(
            message_type=MessageType.COMMAND,
            sender="agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command": "test", "priority": "high"},
            recipient="agent-2",
            priority=MessagePriority.HIGH
        )
        
        # Correspondance avec tous les critères
        self.assertTrue(self.channel.matches_filter(message, {
            "message_type": "command",
            "sender": "agent-1",
            "priority": "high",
            "content": {"command": "test"}
        }))
        
        # Non-correspondance avec un critère
        self.assertFalse(self.channel.matches_filter(message, {
            "message_type": "command",
            "sender": "agent-1",
            "priority": "normal",  # Ne correspond pas
            "content": {"command": "test"}
        }))
        
        self.assertFalse(self.channel.matches_filter(message, {
            "message_type": "command",
            "sender": "agent-1",
            "priority": "high",
            "content": {"command": "other"}  # Ne correspond pas
        }))


class TestChannelExceptions(unittest.TestCase):
    """Tests pour les exceptions liées aux canaux."""
    
    def test_channel_exceptions(self):
        """Vérifie que les exceptions sont correctement définies."""
        # Vérifier que les exceptions héritent correctement
        self.assertTrue(issubclass(ChannelFullException, ChannelException))
        self.assertTrue(issubclass(ChannelTimeoutException, ChannelException))
        self.assertTrue(issubclass(ChannelClosedException, ChannelException))
        self.assertTrue(issubclass(InvalidMessageException, ChannelException))
        self.assertTrue(issubclass(UnauthorizedAccessException, ChannelException))
        
        # Vérifier que les exceptions peuvent être levées et attrapées
        try:
            raise ChannelFullException("Le canal est plein")
            self.fail("L'exception n'a pas été levée")
        except ChannelException as e:
            self.assertEqual(str(e), "Le canal est plein")
        
        try:
            raise ChannelTimeoutException("Timeout sur le canal")
            self.fail("L'exception n'a pas été levée")
        except ChannelException as e:
            self.assertEqual(str(e), "Timeout sur le canal")


if __name__ == "__main__":
    unittest.main()