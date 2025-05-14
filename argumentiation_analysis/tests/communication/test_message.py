"""
Tests unitaires pour les structures de messages du système de communication multi-canal.
"""

import unittest
from datetime import datetime
import json

from argumentiation_analysis.core.communication.message import (

from argumentiation_analysis.paths import DATA_DIR

    Message, MessageType, MessagePriority, AgentLevel,
    CommandMessage, InformationMessage, RequestMessage, EventMessage
)


class TestMessage(unittest.TestCase):
    """Tests pour la classe de base Message."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.message = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.HIGH,
            metadata={"conversation_id": "conv-123"}
        )
    
    def test_message_creation(self):
        """Test de la création d'un message."""
        self.assertEqual(self.message.type, MessageType.COMMAND)
        self.assertEqual(self.message.sender, "strategic-agent-1")
        self.assertEqual(self.message.sender_level, AgentLevel.STRATEGIC)
        self.assertEqual(self.message.recipient, "tactical-agent-1")
        self.assertEqual(self.message.priority, MessagePriority.HIGH)
        self.assertEqual(self.message.content["command_type"], "analyze_text")
        self.assertEqual(self.message.metadata["conversation_id"], "conv-123")
        self.assertIsNotNone(self.message.id)
        self.assertIsInstance(self.message.timestamp, datetime)
    
    def test_to_dict(self):
        """Test de la conversion d'un message en dictionnaire."""
        message_dict = self.message.to_dict()
        
        self.assertEqual(message_dict["type"], "command")
        self.assertEqual(message_dict["sender"], "strategic-agent-1")
        self.assertEqual(message_dict["sender_level"], "strategic")
        self.assertEqual(message_dict["recipient"], "tactical-agent-1")
        self.assertEqual(message_dict["priority"], "high")
        self.assertEqual(message_dict["content"]["command_type"], "analyze_text")
        self.assertEqual(message_dict["metadata"]["conversation_id"], "conv-123")
    
    def test_from_dict(self):
        """Test de la création d'un message à partir d'un dictionnaire."""
        message_dict = self.message.to_dict()
        new_message = Message.from_dict(message_dict)
        
        self.assertEqual(new_message.id, self.message.id)
        self.assertEqual(new_message.type, self.message.type)
        self.assertEqual(new_message.sender, self.message.sender)
        self.assertEqual(new_message.sender_level, self.message.sender_level)
        self.assertEqual(new_message.recipient, self.message.recipient)
        self.assertEqual(new_message.priority, self.message.priority)
        self.assertEqual(new_message.content, self.message.content)
        self.assertEqual(new_message.metadata, self.message.metadata)
        self.assertEqual(new_message.timestamp, self.message.timestamp)
    
    def test_is_response_to(self):
        """Test de la vérification si un message est une réponse à une requête."""
        # Créer une requête
        request = Message(
            message_type=MessageType.REQUEST,
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            content={"request_type": "get_data", "parameters": {}},
            recipient="operational-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        # Créer une réponse à cette requête
        response = Message(
            message_type=MessageType.RESPONSE,
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            content={"status": "success", DATA_DIR: {"result": "some data"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.NORMAL,
            metadata={"reply_to": request.id}
        )
        
        # Vérifier que la réponse est bien identifiée comme telle
        self.assertTrue(response.is_response_to(request.id))
        
        # Vérifier qu'un autre message n'est pas identifié comme une réponse
        self.assertFalse(self.message.is_response_to(request.id))
    
    def test_requires_acknowledgement(self):
        """Test de la vérification si un message nécessite un accusé de réception."""
        # Message sans accusé de réception
        self.assertFalse(self.message.requires_acknowledgement())
        
        # Message avec accusé de réception
        message_with_ack = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.HIGH,
            metadata={"requires_ack": True}
        )
        
        self.assertTrue(message_with_ack.requires_acknowledgement())
    
    def test_create_response(self):
        """Test de la création d'une réponse à un message."""
        response = self.message.create_response(
            content={"status": "success", DATA_DIR: {"result": "analysis complete"}}
        )
        
        self.assertEqual(response.type, MessageType.RESPONSE)
        self.assertEqual(response.sender, "tactical-agent-1")
        self.assertEqual(response.recipient, "strategic-agent-1")
        self.assertEqual(response.priority, self.message.priority)
        self.assertEqual(response.content["status"], "success")
        self.assertEqual(response.metadata["reply_to"], self.message.id)
    
    def test_create_acknowledgement(self):
        """Test de la création d'un accusé de réception."""
        ack = self.message.create_acknowledgement()
        
        self.assertEqual(ack.type, MessageType.RESPONSE)
        self.assertEqual(ack.sender, "tactical-agent-1")
        self.assertEqual(ack.recipient, "strategic-agent-1")
        self.assertEqual(ack.content["status"], "acknowledged")
        self.assertEqual(ack.content["message_id"], self.message.id)
        self.assertEqual(ack.metadata["reply_to"], self.message.id)
        self.assertTrue(ack.metadata["acknowledgement"])


class TestSpecializedMessages(unittest.TestCase):
    """Tests pour les classes de messages spécialisées."""
    
    def test_command_message(self):
        """Test de la création d'un message de commande."""
        command = CommandMessage(
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            command_type="analyze_text",
            parameters={"text_id": "text-123"},
            recipient="tactical-agent-1",
            constraints={"deadline": "2025-06-06T12:00:00"},
            priority=MessagePriority.HIGH,
            requires_ack=True
        )
        
        self.assertEqual(command.type, MessageType.COMMAND)
        self.assertEqual(command.content["command_type"], "analyze_text")
        self.assertEqual(command.content["parameters"]["text_id"], "text-123")
        self.assertEqual(command.content["constraints"]["deadline"], "2025-06-06T12:00:00")
        self.assertTrue(command.requires_acknowledgement())
    
    def test_information_message(self):
        """Test de la création d'un message d'information."""
        info = InformationMessage(
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            info_type="analysis_result",
            data={"result": "some data", "confidence": 0.95},
            recipient="tactical-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        self.assertEqual(info.type, MessageType.INFORMATION)
        self.assertEqual(info.content["info_type"], "analysis_result")
        self.assertEqual(info.content[DATA_DIR]["result"], "some data")
        self.assertEqual(info.content[DATA_DIR]["confidence"], 0.95)
    
    def test_request_message(self):
        """Test de la création d'un message de requête."""
        request = RequestMessage(
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            request_type="get_analysis",
            description="Need analysis for text-123",
            context={"text_id": "text-123", "priority": "high"},
            recipient="operational-agent-1",
            response_format="json",
            timeout=30,
            priority=MessagePriority.NORMAL
        )
        
        self.assertEqual(request.type, MessageType.REQUEST)
        self.assertEqual(request.content["request_type"], "get_analysis")
        self.assertEqual(request.content["description"], "Need analysis for text-123")
        self.assertEqual(request.content["context"]["text_id"], "text-123")
        self.assertEqual(request.content["response_format"], "json")
        self.assertEqual(request.content["timeout"], 30)
    
    def test_event_message(self):
        """Test de la création d'un message d'événement."""
        event = EventMessage(
            sender="system",
            sender_level=AgentLevel.SYSTEM,
            event_type="resource_warning",
            description="CPU usage high",
            details={"cpu_usage": 85, "memory_usage": 70},
            recommended_action="Reduce parallel processing",
            priority=MessagePriority.HIGH
        )
        
        self.assertEqual(event.type, MessageType.EVENT)
        self.assertEqual(event.content["event_type"], "resource_warning")
        self.assertEqual(event.content["description"], "CPU usage high")
        self.assertEqual(event.content["details"]["cpu_usage"], 85)
        self.assertEqual(event.content["recommended_action"], "Reduce parallel processing")
        self.assertIsNone(event.recipient)  # Les événements sont généralement diffusés


if __name__ == "__main__":
    unittest.main()