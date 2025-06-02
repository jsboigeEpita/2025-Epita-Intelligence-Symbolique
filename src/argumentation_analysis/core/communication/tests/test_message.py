# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module de message du système de communication multi-canal.
"""

import unittest
import json
from datetime import datetime
from unittest.mock import patch

from argumentation_analysis.core.communication.message import (
    Message, MessageType, MessagePriority, AgentLevel,
    CommandMessage, InformationMessage, RequestMessage, EventMessage
)

from argumentation_analysis.paths import DATA_DIR


class TestMessageEnums(unittest.TestCase):
    """Tests pour les énumérations du module message."""
    
    def test_message_type_enum(self):
        """Vérifie que les types de messages sont correctement définis."""
        self.assertEqual(MessageType.COMMAND.value, "command")
        self.assertEqual(MessageType.INFORMATION.value, "information")
        self.assertEqual(MessageType.REQUEST.value, "request")
        self.assertEqual(MessageType.RESPONSE.value, "response")
        self.assertEqual(MessageType.EVENT.value, "event")
        self.assertEqual(MessageType.CONTROL.value, "control")
        self.assertEqual(MessageType.PUBLICATION.value, "publication")
        self.assertEqual(MessageType.SUBSCRIPTION.value, "subscription")
    
    def test_message_priority_enum(self):
        """Vérifie que les priorités de messages sont correctement définies."""
        self.assertEqual(MessagePriority.LOW.value, "low")
        self.assertEqual(MessagePriority.NORMAL.value, "normal")
        self.assertEqual(MessagePriority.HIGH.value, "high")
        self.assertEqual(MessagePriority.CRITICAL.value, "critical")
    
    def test_agent_level_enum(self):
        """Vérifie que les niveaux d'agents sont correctement définis."""
        self.assertEqual(AgentLevel.STRATEGIC.value, "strategic")
        self.assertEqual(AgentLevel.TACTICAL.value, "tactical")
        self.assertEqual(AgentLevel.OPERATIONAL.value, "operational")
        self.assertEqual(AgentLevel.SYSTEM.value, "system")


class TestMessage(unittest.TestCase):
    """Tests pour la classe Message."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.message = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            recipient="tactical-agent-1",
            channel="hierarchical",
            priority=MessagePriority.HIGH,
            metadata={"conversation_id": "conv-456"}
        )
    
    def test_init(self):
        """Test de l'initialisation d'un message."""
        self.assertEqual(self.message.type, MessageType.COMMAND)
        self.assertEqual(self.message.sender, "strategic-agent-1")
        self.assertEqual(self.message.sender_level, AgentLevel.STRATEGIC)
        self.assertEqual(self.message.content, {
            "command_type": "analyze_text", 
            "parameters": {"text_id": "text-123"}
        })
        self.assertEqual(self.message.recipient, "tactical-agent-1")
        self.assertEqual(self.message.channel, "hierarchical")
        self.assertEqual(self.message.priority, MessagePriority.HIGH)
        self.assertEqual(self.message.metadata, {"conversation_id": "conv-456"})
        
        # Vérifier que l'ID et le timestamp sont générés automatiquement
        self.assertTrue(self.message.id.startswith("command-"))
        self.assertIsInstance(self.message.timestamp, datetime)
    
    def test_init_with_custom_id_and_timestamp(self):
        """Test de l'initialisation d'un message avec ID et timestamp personnalisés."""
        custom_id = "custom-id-123"
        custom_timestamp = datetime(2025, 5, 19, 12, 0, 0)
        
        message = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text"},
            message_id=custom_id,
            timestamp=custom_timestamp
        )
        
        self.assertEqual(message.id, custom_id)
        self.assertEqual(message.timestamp, custom_timestamp)
    
    def test_to_dict(self):
        """Test de la conversion d'un message en dictionnaire."""
        message_dict = self.message.to_dict()
        
        self.assertEqual(message_dict["type"], "command")
        self.assertEqual(message_dict["sender"], "strategic-agent-1")
        self.assertEqual(message_dict["sender_level"], "strategic")
        self.assertEqual(message_dict["content"], {
            "command_type": "analyze_text", 
            "parameters": {"text_id": "text-123"}
        })
        self.assertEqual(message_dict["recipient"], "tactical-agent-1")
        self.assertEqual(message_dict["channel"], "hierarchical")
        self.assertEqual(message_dict["priority"], "high")
        self.assertEqual(message_dict["metadata"], {"conversation_id": "conv-456"})
        
        # Vérifier que l'ID et le timestamp sont inclus
        self.assertEqual(message_dict["id"], self.message.id)
        self.assertEqual(message_dict["timestamp"], self.message.timestamp.isoformat())
    
    def test_from_dict(self):
        """Test de la création d'un message à partir d'un dictionnaire."""
        message_dict = {
            "id": "command-abc123",
            "type": "command",
            "sender": "strategic-agent-1",
            "sender_level": "strategic",
            "content": {"command_type": "analyze_text", "parameters": {"text_id": "text-123"}},
            "recipient": "tactical-agent-1",
            "channel": "hierarchical",
            "priority": "high",
            "metadata": {"conversation_id": "conv-456"},
            "timestamp": "2025-05-19T12:00:00"
        }
        
        message = Message.from_dict(message_dict)
        
        self.assertEqual(message.id, "command-abc123")
        self.assertEqual(message.type, MessageType.COMMAND)
        self.assertEqual(message.sender, "strategic-agent-1")
        self.assertEqual(message.sender_level, AgentLevel.STRATEGIC)
        self.assertEqual(message.content, {
            "command_type": "analyze_text", 
            "parameters": {"text_id": "text-123"}
        })
        self.assertEqual(message.recipient, "tactical-agent-1")
        self.assertEqual(message.channel, "hierarchical")
        self.assertEqual(message.priority, MessagePriority.HIGH)
        self.assertEqual(message.metadata, {"conversation_id": "conv-456"})
        self.assertEqual(message.timestamp, datetime.fromisoformat("2025-05-19T12:00:00"))
    
    def test_is_response_to(self):
        """Test de la méthode is_response_to."""
        # Créer une réponse
        response = Message(
            message_type=MessageType.RESPONSE,
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            content={"status": "success", "result": "analysis complete"},
            recipient="strategic-agent-1",
            metadata={"reply_to": self.message.id}
        )
        
        # Vérifier que la réponse est bien identifiée
        self.assertTrue(response.is_response_to(self.message.id))
        
        # Vérifier qu'un autre message n'est pas identifié comme réponse
        other_message = Message(
            message_type=MessageType.RESPONSE,
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            content={"status": "success"},
            recipient="strategic-agent-1",
            metadata={"reply_to": "other-id"}
        )
        
        self.assertFalse(other_message.is_response_to(self.message.id))
        
        # Vérifier qu'un message qui n'est pas une réponse n'est pas identifié comme réponse
        not_response = Message(
            message_type=MessageType.COMMAND,
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            content={"command_type": "report"},
            recipient="strategic-agent-1"
        )
        
        self.assertFalse(not_response.is_response_to(self.message.id))
    
    def test_requires_acknowledgement(self):
        """Test de la méthode requires_acknowledgement."""
        # Message sans accusé de réception requis
        self.assertFalse(self.message.requires_acknowledgement())
        
        # Message avec accusé de réception requis
        message_with_ack = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={"command_type": "analyze_text"},
            recipient="tactical-agent-1",
            metadata={"requires_ack": True}
        )
        
        self.assertTrue(message_with_ack.requires_acknowledgement())
    
    def test_create_response(self):
        """Test de la méthode create_response."""
        response = self.message.create_response(
            content={"status": "success", "result": "analysis complete"},
            priority=MessagePriority.NORMAL,
            sender_level=AgentLevel.TACTICAL
        )
        
        self.assertEqual(response.type, MessageType.RESPONSE)
        self.assertEqual(response.sender, "tactical-agent-1")  # Le destinataire du message original
        self.assertEqual(response.sender_level, AgentLevel.TACTICAL)
        self.assertEqual(response.content, {"status": "success", "result": "analysis complete"})
        self.assertEqual(response.recipient, "strategic-agent-1")  # L'expéditeur du message original
        self.assertEqual(response.channel, "hierarchical")
        self.assertEqual(response.priority, MessagePriority.NORMAL)
        
        # Vérifier les métadonnées de la réponse
        self.assertEqual(response.metadata["reply_to"], self.message.id)
        self.assertEqual(response.metadata["conversation_id"], "conv-456")
        self.assertTrue(response.metadata["is_response"])
    
    def test_create_acknowledgement(self):
        """Test de la méthode create_acknowledgement."""
        ack = self.message.create_acknowledgement()
        
        self.assertEqual(ack.type, MessageType.RESPONSE)
        self.assertEqual(ack.sender, "tactical-agent-1")  # Le destinataire du message original
        self.assertEqual(ack.sender_level, AgentLevel.SYSTEM)
        self.assertEqual(ack.content, {"status": "acknowledged", "message_id": self.message.id})
        self.assertEqual(ack.recipient, "strategic-agent-1")  # L'expéditeur du message original
        self.assertEqual(ack.channel, "hierarchical")
        self.assertEqual(ack.priority, MessagePriority.HIGH)
        
        # Vérifier les métadonnées de l'accusé de réception
        self.assertEqual(ack.metadata["reply_to"], self.message.id)
        self.assertEqual(ack.metadata["conversation_id"], "conv-456")
        self.assertTrue(ack.metadata["acknowledgement"])


class TestCommandMessage(unittest.TestCase):
    """Tests pour la classe CommandMessage."""
    
    def test_init(self):
        """Test de l'initialisation d'un message de commande."""
        command = CommandMessage(
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            command_type="analyze_text",
            parameters={"text_id": "text-123", "depth": "full"},
            recipient="tactical-agent-1",
            constraints={"max_time": 60, "max_resources": "medium"},
            priority=MessagePriority.HIGH,
            requires_ack=True
        )
        
        # Vérifier les attributs de base
        self.assertEqual(command.type, MessageType.COMMAND)
        self.assertEqual(command.sender, "strategic-agent-1")
        self.assertEqual(command.sender_level, AgentLevel.STRATEGIC)
        self.assertEqual(command.recipient, "tactical-agent-1")
        self.assertEqual(command.priority, MessagePriority.HIGH)
        
        # Vérifier le contenu spécifique aux commandes
        self.assertEqual(command.content["command_type"], "analyze_text")
        self.assertEqual(command.content["parameters"], {"text_id": "text-123", "depth": "full"})
        self.assertEqual(command.content["constraints"], {"max_time": 60, "max_resources": "medium"})
        
        # Vérifier les métadonnées
        self.assertTrue(command.metadata["requires_ack"])


class TestInformationMessage(unittest.TestCase):
    """Tests pour la classe InformationMessage."""
    
    def test_init(self):
        """Test de l'initialisation d'un message d'information."""
        info = InformationMessage(
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            info_type="analysis_result",
            data={"text_id": "text-123", "results": {"score": 0.85, "confidence": "high"}},
            recipient="tactical-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier les attributs de base
        self.assertEqual(info.type, MessageType.INFORMATION)
        self.assertEqual(info.sender, "operational-agent-1")
        self.assertEqual(info.sender_level, AgentLevel.OPERATIONAL)
        self.assertEqual(info.recipient, "tactical-agent-1")
        self.assertEqual(info.priority, MessagePriority.NORMAL)
        
        # Vérifier le contenu spécifique aux informations
        self.assertEqual(info.content["info_type"], "analysis_result")
        self.assertEqual(info.content[DATA_DIR], {
            "text_id": "text-123", 
            "results": {"score": 0.85, "confidence": "high"}
        })


class TestRequestMessage(unittest.TestCase):
    """Tests pour la classe RequestMessage."""
    
    def test_init(self):
        """Test de l'initialisation d'un message de requête."""
        request = RequestMessage(
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            request_type="get_analysis",
            description="Besoin d'une analyse détaillée du texte",
            context={"text_id": "text-123", "previous_analysis": "basic"},
            recipient="operational-agent-1",
            response_format="json",
            timeout=30,
            priority=MessagePriority.HIGH
        )
        
        # Vérifier les attributs de base
        self.assertEqual(request.type, MessageType.REQUEST)
        self.assertEqual(request.sender, "tactical-agent-1")
        self.assertEqual(request.sender_level, AgentLevel.TACTICAL)
        self.assertEqual(request.recipient, "operational-agent-1")
        self.assertEqual(request.priority, MessagePriority.HIGH)
        
        # Vérifier le contenu spécifique aux requêtes
        self.assertEqual(request.content["request_type"], "get_analysis")
        self.assertEqual(request.content["description"], "Besoin d'une analyse détaillée du texte")
        self.assertEqual(request.content["context"], {
            "text_id": "text-123", 
            "previous_analysis": "basic"
        })
        self.assertEqual(request.content["response_format"], "json")
        self.assertEqual(request.content["timeout"], 30)


class TestEventMessage(unittest.TestCase):
    """Tests pour la classe EventMessage."""
    
    def test_init(self):
        """Test de l'initialisation d'un message d'événement."""
        event = EventMessage(
            sender="system-monitor",
            sender_level=AgentLevel.SYSTEM,
            event_type="resource_warning",
            description="Utilisation élevée de la mémoire",
            details={"memory_usage": 85, "threshold": 80, "process_id": 1234},
            recommended_action="Libérer des ressources non utilisées",
            priority=MessagePriority.HIGH
        )
        
        # Vérifier les attributs de base
        self.assertEqual(event.type, MessageType.EVENT)
        self.assertEqual(event.sender, "system-monitor")
        self.assertEqual(event.sender_level, AgentLevel.SYSTEM)
        self.assertEqual(event.recipient, None)  # Les événements sont généralement diffusés
        self.assertEqual(event.priority, MessagePriority.HIGH)
        
        # Vérifier le contenu spécifique aux événements
        self.assertEqual(event.content["event_type"], "resource_warning")
        self.assertEqual(event.content["description"], "Utilisation élevée de la mémoire")
        self.assertEqual(event.content["details"], {
            "memory_usage": 85, 
            "threshold": 80, 
            "process_id": 1234
        })
        self.assertEqual(event.content["recommended_action"], "Libérer des ressources non utilisées")


if __name__ == "__main__":
    unittest.main()