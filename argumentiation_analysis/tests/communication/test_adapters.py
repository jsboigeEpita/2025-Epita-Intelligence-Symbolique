"""
Tests unitaires pour les adaptateurs du système de communication multi-canal.
"""

import unittest
import asyncio
import threading
import time
from unittest.mock import MagicMock, patch

from argumentiation_analysis.core.communication.message import (
    Message, MessageType, MessagePriority, AgentLevel
)
from argumentiation_analysis.core.communication.channel_interface import ChannelType
from argumentiation_analysis.core.communication.middleware import MessageMiddleware
from argumentiation_analysis.core.communication.hierarchical_channel import HierarchicalChannel
from argumentiation_analysis.core.communication.collaboration_channel import CollaborationChannel
from argumentiation_analysis.core.communication.data_channel import DataChannel
from argumentiation_analysis.core.communication.strategic_adapter import StrategicAdapter
from argumentiation_analysis.core.communication.tactical_adapter import TacticalAdapter
from argumentiation_analysis.core.communication.operational_adapter import OperationalAdapter


class TestStrategicAdapter(unittest.TestCase):
    """Tests pour l'adaptateur des agents stratégiques."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer des canaux
        self.hierarchical_channel = HierarchicalChannel("test-hierarchical")
        self.collaboration_channel = CollaborationChannel("test-collaboration")
        self.data_channel = DataChannel("test-data")
        
        self.middleware.register_channel(self.hierarchical_channel)
        self.middleware.register_channel(self.collaboration_channel)
        self.middleware.register_channel(self.data_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Créer l'adaptateur
        self.adapter = StrategicAdapter("strategic-agent-1", self.middleware)
    
    def test_issue_directive(self):
        """Test de l'émission d'une directive."""
        # Émettre une directive
        directive_id = self.adapter.issue_directive(
            directive_type="analyze_text",
            parameters={"text_id": "text-123"},
            recipient_id="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Vérifier que la directive a été émise
        self.assertIsNotNone(directive_id)
        
        # Vérifier que la directive est dans la file d'attente du destinataire
        pending = self.hierarchical_channel.get_pending_messages("tactical-agent-1")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].type, MessageType.COMMAND)
        self.assertEqual(pending[0].sender, "strategic-agent-1")
        self.assertEqual(pending[0].content["command_type"], "analyze_text")
    
    def test_receive_report(self):
        """Test de la réception d'un rapport."""
        # Créer un rapport
        report = Message(
            message_type=MessageType.INFORMATION,
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            content={
                "info_type": "report",
                "report_type": "status_update",
                "data": {"status": "in_progress", "completion": 50}
            },
            recipient="strategic-agent-1",
            channel=ChannelType.HIERARCHICAL.value,
            priority=MessagePriority.NORMAL
        )
        
        # Envoyer le rapport via le middleware
        self.middleware.send_message(report)
        
        # Recevoir le rapport
        received_report = self.adapter.receive_report(timeout=1.0)
        
        # Vérifier que le rapport a été reçu
        self.assertIsNotNone(received_report)
        self.assertEqual(received_report.sender, "tactical-agent-1")
        self.assertEqual(received_report.content["report_type"], "status_update")
        self.assertEqual(received_report.content["data"]["completion"], 50)
    
    def test_allocate_resources(self):
        """Test de l'allocation de ressources."""
        # Allouer des ressources
        allocation_id = self.adapter.allocate_resources(
            resource_type="cpu",
            amount=4,
            recipient_id="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Vérifier que l'allocation a été effectuée
        self.assertIsNotNone(allocation_id)
        
        # Vérifier que l'allocation est dans la file d'attente du destinataire
        pending = self.hierarchical_channel.get_pending_messages("tactical-agent-1")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].type, MessageType.COMMAND)
        self.assertEqual(pending[0].content["command_type"], "allocate_resources")
        self.assertEqual(pending[0].content["parameters"]["resource_type"], "cpu")
        self.assertEqual(pending[0].content["parameters"]["amount"], 4)
    
    def test_provide_guidance(self):
        """Test de la fourniture de conseils."""
        # Simuler une demande de conseils
        def simulate_request():
            time.sleep(0.1)  # Attendre un peu pour simuler un traitement
            
            # Créer une requête
            request = Message(
                message_type=MessageType.REQUEST,
                sender="tactical-agent-1",
                sender_level=AgentLevel.TACTICAL,
                content={
                    "request_type": "guidance",
                    "description": "Need guidance on text analysis",
                    "context": {"text_id": "text-123"}
                },
                recipient="strategic-agent-1",
                channel=ChannelType.HIERARCHICAL.value,
                priority=MessagePriority.NORMAL,
                metadata={"conversation_id": "conv-123"}
            )
            
            # Envoyer la requête via le middleware
            self.middleware.send_message(request)
        
        # Démarrer un thread pour simuler la demande
        request_thread = threading.Thread(target=simulate_request)
        request_thread.start()
        
        # Attendre un peu pour que la requête soit envoyée
        time.sleep(0.2)
        
        # Recevoir la demande de conseils
        request = self.adapter.receive_guidance_request(timeout=1.0)
        
        # Vérifier que la demande a été reçue
        self.assertIsNotNone(request)
        self.assertEqual(request.sender, "tactical-agent-1")
        self.assertEqual(request.content["request_type"], "guidance")
        
        # Fournir des conseils
        response_id = self.adapter.provide_guidance(
            request_id=request.id,
            guidance={"recommendation": "Focus on fallacies", "priority": "high"},
            priority=MessagePriority.HIGH
        )
        
        # Vérifier que la réponse a été envoyée
        self.assertIsNotNone(response_id)
        
        # Attendre que le thread se termine
        request_thread.join()
    
    def test_broadcast_announcement(self):
        """Test de la diffusion d'une annonce."""
        # Diffuser une annonce
        announcement_id = self.adapter.broadcast_announcement(
            announcement_type="system_update",
            content={"description": "New analysis algorithm available", "version": "2.0"},
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que l'annonce a été diffusée
        self.assertIsNotNone(announcement_id)
        
        # Vérifier que l'annonce a été publiée
        # (Nous ne pouvons pas vérifier directement les messages publiés,
        # mais nous pouvons vérifier que la méthode publish a été appelée)
        # Pour cela, il faudrait mocker la méthode publish du middleware


class TestTacticalAdapter(unittest.TestCase):
    """Tests pour l'adaptateur des agents tactiques."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer des canaux
        self.hierarchical_channel = HierarchicalChannel("test-hierarchical")
        self.collaboration_channel = CollaborationChannel("test-collaboration")
        self.data_channel = DataChannel("test-data")
        
        self.middleware.register_channel(self.hierarchical_channel)
        self.middleware.register_channel(self.collaboration_channel)
        self.middleware.register_channel(self.data_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Créer l'adaptateur
        self.adapter = TacticalAdapter("tactical-agent-1", self.middleware)
    
    def test_receive_directive(self):
        """Test de la réception d'une directive."""
        # Créer une directive
        directive = Message(
            message_type=MessageType.COMMAND,
            sender="strategic-agent-1",
            sender_level=AgentLevel.STRATEGIC,
            content={
                "command_type": "analyze_text",
                "parameters": {"text_id": "text-123"}
            },
            recipient="tactical-agent-1",
            channel=ChannelType.HIERARCHICAL.value,
            priority=MessagePriority.HIGH
        )
        
        # Envoyer la directive via le middleware
        self.middleware.send_message(directive)
        
        # Recevoir la directive
        received_directive = self.adapter.receive_directive(timeout=1.0)
        
        # Vérifier que la directive a été reçue
        self.assertIsNotNone(received_directive)
        self.assertEqual(received_directive.sender, "strategic-agent-1")
        self.assertEqual(received_directive.content["command_type"], "analyze_text")
        self.assertEqual(received_directive.content["parameters"]["text_id"], "text-123")
    
    def test_assign_task(self):
        """Test de l'assignation d'une tâche."""
        # Assigner une tâche
        task_id = self.adapter.assign_task(
            task_type="extract_arguments",
            parameters={"text_id": "text-123"},
            recipient_id="operational-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que la tâche a été assignée
        self.assertIsNotNone(task_id)
        
        # Vérifier que la tâche est dans la file d'attente du destinataire
        pending = self.hierarchical_channel.get_pending_messages("operational-agent-1")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].type, MessageType.COMMAND)
        self.assertEqual(pending[0].sender, "tactical-agent-1")
        self.assertEqual(pending[0].content["command_type"], "extract_arguments")
    
    def test_send_report(self):
        """Test de l'envoi d'un rapport."""
        # Envoyer un rapport
        report_id = self.adapter.send_report(
            report_type="status_update",
            content={"status": "in_progress", "completion": 50},
            recipient_id="strategic-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que le rapport a été envoyé
        self.assertIsNotNone(report_id)
        
        # Vérifier que le rapport est dans la file d'attente du destinataire
        pending = self.hierarchical_channel.get_pending_messages("strategic-agent-1")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].type, MessageType.INFORMATION)
        self.assertEqual(pending[0].sender, "tactical-agent-1")
        self.assertEqual(pending[0].content["info_type"], "report")
        self.assertEqual(pending[0].content["report_type"], "status_update")
        self.assertEqual(pending[0].content["data"]["completion"], 50)
    
    def test_receive_task_result(self):
        """Test de la réception d'un résultat de tâche."""
        # Créer un résultat de tâche
        result = Message(
            message_type=MessageType.INFORMATION,
            sender="operational-agent-1",
            sender_level=AgentLevel.OPERATIONAL,
            content={
                "info_type": "task_result",
                "task_type": "extract_arguments",
                "data": {"arguments": ["arg1", "arg2"], "confidence": 0.95}
            },
            recipient="tactical-agent-1",
            channel=ChannelType.HIERARCHICAL.value,
            priority=MessagePriority.NORMAL
        )
        
        # Envoyer le résultat via le middleware
        self.middleware.send_message(result)
        
        # Recevoir le résultat
        received_result = self.adapter.receive_task_result(timeout=1.0)
        
        # Vérifier que le résultat a été reçu
        self.assertIsNotNone(received_result)
        self.assertEqual(received_result.sender, "operational-agent-1")
        self.assertEqual(received_result.content["info_type"], "task_result")
        self.assertEqual(received_result.content["task_type"], "extract_arguments")
        self.assertEqual(received_result.content["data"]["arguments"], ["arg1", "arg2"])
    
    def test_request_strategic_guidance(self):
        """Test de la demande de conseils stratégiques."""
        # Simuler une réponse à une demande de conseils
        def simulate_response():
            time.sleep(0.1)  # Attendre un peu pour simuler un traitement
            
            # Récupérer la requête
            request = self.middleware.receive_message(
                recipient_id="strategic-agent-1",
                channel_type=ChannelType.HIERARCHICAL
            )
            
            if request:
                # Créer une réponse
                response = Message(
                    message_type=MessageType.RESPONSE,
                    sender="strategic-agent-1",
                    sender_level=AgentLevel.STRATEGIC,
                    content={
                        "status": "success",
                        "data": {"recommendation": "Focus on fallacies", "priority": "high"}
                    },
                    recipient=request.sender,
                    channel=ChannelType.HIERARCHICAL.value,
                    priority=request.priority,
                    metadata={"reply_to": request.id, "conversation_id": request.metadata.get("conversation_id")}
                )
                
                # Envoyer la réponse via le middleware
                self.middleware.send_message(response)
        
        # Démarrer un thread pour simuler la réponse
        response_thread = threading.Thread(target=simulate_response)
        response_thread.start()
        
        # Demander des conseils stratégiques
        guidance = self.adapter.request_strategic_guidance(
            request_type="guidance",
            parameters={"text_id": "text-123", "issue": "complex_fallacies"},
            recipient_id="strategic-agent-1",
            timeout=2.0,
            priority=MessagePriority.NORMAL
        )
        
        # Attendre que le thread se termine
        response_thread.join()
        
        # Vérifier que les conseils ont été reçus
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance["recommendation"], "Focus on fallacies")
        self.assertEqual(guidance["priority"], "high")
    
    def test_collaborate_with_tactical(self):
        """Test de la collaboration avec d'autres agents tactiques."""
        # Collaborer avec d'autres agents tactiques
        collaboration_id = self.adapter.collaborate_with_tactical(
            collaboration_type="task_coordination",
            content={"task_id": "task-123", "status": "need_assistance"},
            recipient_ids=["tactical-agent-2", "tactical-agent-3"],
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que la collaboration a été initiée
        self.assertIsNotNone(collaboration_id)
        
        # Vérifier que le message de collaboration a été envoyé
        # (Nous ne pouvons pas vérifier directement les messages dans le canal de collaboration,
        # car ils sont destinés à un groupe et non à des destinataires individuels)


class TestOperationalAdapter(unittest.TestCase):
    """Tests pour l'adaptateur des agents opérationnels."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer des canaux
        self.hierarchical_channel = HierarchicalChannel("test-hierarchical")
        self.collaboration_channel = CollaborationChannel("test-collaboration")
        self.data_channel = DataChannel("test-data")
        
        self.middleware.register_channel(self.hierarchical_channel)
        self.middleware.register_channel(self.collaboration_channel)
        self.middleware.register_channel(self.data_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Créer l'adaptateur
        self.adapter = OperationalAdapter("operational-agent-1", self.middleware)
    
    def test_receive_task(self):
        """Test de la réception d'une tâche."""
        # Créer une tâche
        task = Message(
            message_type=MessageType.COMMAND,
            sender="tactical-agent-1",
            sender_level=AgentLevel.TACTICAL,
            content={
                "command_type": "extract_arguments",
                "parameters": {"text_id": "text-123"}
            },
            recipient="operational-agent-1",
            channel=ChannelType.HIERARCHICAL.value,
            priority=MessagePriority.NORMAL
        )
        
        # Envoyer la tâche via le middleware
        self.middleware.send_message(task)
        
        # Recevoir la tâche
        received_task = self.adapter.receive_task(timeout=1.0)
        
        # Vérifier que la tâche a été reçue
        self.assertIsNotNone(received_task)
        self.assertEqual(received_task.sender, "tactical-agent-1")
        self.assertEqual(received_task.content["command_type"], "extract_arguments")
        self.assertEqual(received_task.content["parameters"]["text_id"], "text-123")
    
    def test_send_task_result(self):
        """Test de l'envoi d'un résultat de tâche."""
        # Envoyer un résultat de tâche
        result_id = self.adapter.send_task_result(
            task_id="task-123",
            result={"arguments": ["arg1", "arg2"], "confidence": 0.95},
            recipient_id="tactical-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que le résultat a été envoyé
        self.assertIsNotNone(result_id)
        
        # Vérifier que le résultat est dans la file d'attente du destinataire
        pending = self.hierarchical_channel.get_pending_messages("tactical-agent-1")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].type, MessageType.INFORMATION)
        self.assertEqual(pending[0].sender, "operational-agent-1")
        self.assertEqual(pending[0].content["info_type"], "task_result")
        self.assertEqual(pending[0].content["task_id"], "task-123")
        self.assertEqual(pending[0].content["data"]["arguments"], ["arg1", "arg2"])
    
    def test_request_assistance(self):
        """Test de la demande d'assistance."""
        # Simuler une réponse à une demande d'assistance
        def simulate_response():
            time.sleep(0.1)  # Attendre un peu pour simuler un traitement
            
            # Récupérer la requête
            request = self.middleware.receive_message(
                recipient_id="tactical-agent-1",
                channel_type=ChannelType.HIERARCHICAL
            )
            
            if request:
                # Créer une réponse
                response = Message(
                    message_type=MessageType.RESPONSE,
                    sender="tactical-agent-1",
                    sender_level=AgentLevel.TACTICAL,
                    content={
                        "status": "success",
                        "data": {"solution": "Use pattern X", "example": "example data"}
                    },
                    recipient=request.sender,
                    channel=ChannelType.HIERARCHICAL.value,
                    priority=request.priority,
                    metadata={"reply_to": request.id, "conversation_id": request.metadata.get("conversation_id")}
                )
                
                # Envoyer la réponse via le middleware
                self.middleware.send_message(response)
        
        # Démarrer un thread pour simuler la réponse
        response_thread = threading.Thread(target=simulate_response)
        response_thread.start()
        
        # Demander de l'assistance
        assistance = self.adapter.request_assistance(
            issue_type="pattern_recognition",
            description="Cannot identify pattern in text",
            context={"text_id": "text-123", "position": "paragraph 3"},
            recipient_id="tactical-agent-1",
            timeout=2.0,
            priority=MessagePriority.NORMAL
        )
        
        # Attendre que le thread se termine
        response_thread.join()
        
        # Vérifier que l'assistance a été reçue
        self.assertIsNotNone(assistance)
        self.assertEqual(assistance["solution"], "Use pattern X")
        self.assertEqual(assistance["example"], "example data")
    
    def test_send_status_update(self):
        """Test de l'envoi d'une mise à jour de statut."""
        # Envoyer une mise à jour de statut
        update_id = self.adapter.send_status_update(
            status="in_progress",
            progress=75,
            details={"current_step": "argument_extraction", "remaining_time": "2min"},
            recipient_id="tactical-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que la mise à jour a été envoyée
        self.assertIsNotNone(update_id)
        
        # Vérifier que la mise à jour est dans la file d'attente du destinataire
        pending = self.hierarchical_channel.get_pending_messages("tactical-agent-1")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].type, MessageType.INFORMATION)
        self.assertEqual(pending[0].sender, "operational-agent-1")
        self.assertEqual(pending[0].content["info_type"], "status_update")
        self.assertEqual(pending[0].content["data"]["status"], "in_progress")
        self.assertEqual(pending[0].content["data"]["progress"], 75)
    
    def test_access_shared_data(self):
        """Test de l'accès aux données partagées."""
        # Simuler des données partagées
        data_id = "shared-data-123"
        version_id = "v1"
        shared_data = {"dataset": "fallacies", "entries": [{"id": 1, "text": "example"}]}
        
        # Stocker les données dans le canal de données
        self.data_channel.store_data(
            data_id=data_id,
            data=shared_data,
            metadata={"data_type": "dataset", "owner": "tactical-agent-1"}
        )
        
        # Accéder aux données partagées
        retrieved_data = self.adapter.access_shared_data(
            data_id=data_id,
            version_id=version_id
        )
        
        # Vérifier que les données ont été récupérées
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_data["dataset"], "fallacies")
        self.assertEqual(retrieved_data["entries"][0]["text"], "example")


class TestAsyncAdapters(unittest.IsolatedAsyncioTestCase):
    """Tests pour les fonctionnalités asynchrones des adaptateurs."""
    
    async def asyncSetUp(self):
        """Initialisation asynchrone avant chaque test."""
        self.middleware = MessageMiddleware()
        
        # Enregistrer des canaux
        self.hierarchical_channel = HierarchicalChannel("test-hierarchical")
        self.middleware.register_channel(self.hierarchical_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Créer les adaptateurs
        self.tactical_adapter = TacticalAdapter("tactical-agent-1", self.middleware)
        self.operational_adapter = OperationalAdapter("operational-agent-1", self.middleware)
    
    async def test_request_strategic_guidance_async(self):
        """Test de la demande asynchrone de conseils stratégiques."""
        # Simuler une réponse à une demande de conseils
        async def simulate_response():
            await asyncio.sleep(0.1)  # Attendre un peu pour simuler un traitement
            
            # Récupérer la requête
            request = self.middleware.receive_message(
                recipient_id="strategic-agent-1",
                channel_type=ChannelType.HIERARCHICAL
            )
            
            if request:
                # Créer une réponse
                response = Message(
                    message_type=MessageType.RESPONSE,
                    sender="strategic-agent-1",
                    sender_level=AgentLevel.STRATEGIC,
                    content={
                        "status": "success",
                        "data": {"recommendation": "Focus on fallacies", "priority": "high"}
                    },
                    recipient=request.sender,
                    channel=ChannelType.HIERARCHICAL.value,
                    priority=request.priority,
                    metadata={"reply_to": request.id, "conversation_id": request.metadata.get("conversation_id")}
                )
                
                # Envoyer la réponse via le middleware
                self.middleware.send_message(response)
        
        # Démarrer une tâche pour simuler la réponse
        asyncio.create_task(simulate_response())
        
        # Demander des conseils stratégiques de manière asynchrone
        guidance = await self.tactical_adapter.request_strategic_guidance_async(
            request_type="guidance",
            parameters={"text_id": "text-123", "issue": "complex_fallacies"},
            recipient_id="strategic-agent-1",
            timeout=2.0,
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que les conseils ont été reçus
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance["recommendation"], "Focus on fallacies")
        self.assertEqual(guidance["priority"], "high")
    
    async def test_request_assistance_async(self):
        """Test de la demande asynchrone d'assistance."""
        # Simuler une réponse à une demande d'assistance
        async def simulate_response():
            await asyncio.sleep(0.1)  # Attendre un peu pour simuler un traitement
            
            # Récupérer la requête
            request = self.middleware.receive_message(
                recipient_id="tactical-agent-1",
                channel_type=ChannelType.HIERARCHICAL
            )
            
            if request:
                # Créer une réponse
                response = Message(
                    message_type=MessageType.RESPONSE,
                    sender="tactical-agent-1",
                    sender_level=AgentLevel.TACTICAL,
                    content={
                        "status": "success",
                        "data": {"solution": "Use pattern X", "example": "example data"}
                    },
                    recipient=request.sender,
                    channel=ChannelType.HIERARCHICAL.value,
                    priority=request.priority,
                    metadata={"reply_to": request.id, "conversation_id": request.metadata.get("conversation_id")}
                )
                
                # Envoyer la réponse via le middleware
                self.middleware.send_message(response)
        
        # Démarrer une tâche pour simuler la réponse
        asyncio.create_task(simulate_response())
        
        # Demander de l'assistance de manière asynchrone
        assistance = await self.operational_adapter.request_assistance_async(
            issue_type="pattern_recognition",
            description="Cannot identify pattern in text",
            context={"text_id": "text-123", "position": "paragraph 3"},
            recipient_id="tactical-agent-1",
            timeout=2.0,
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que l'assistance a été reçue
        self.assertIsNotNone(assistance)
        self.assertEqual(assistance["solution"], "Use pattern X")
        self.assertEqual(assistance["example"], "example data")


if __name__ == "__main__":
    unittest.main()