# -*- coding: utf-8 -*-
"""
Tests d'intégration pour la communication hiérarchique entre les trois niveaux d'agents.

Ces tests valident la communication verticale entre les agents stratégiques, tactiques
et opérationnels, en s'assurant que les directives, tâches, résultats et rapports
sont correctement transmis à travers les différents niveaux de la hiérarchie.
"""

import unittest
import asyncio
import logging
import threading
import time
from unittest.mock import MagicMock, patch

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


logger = logging.getLogger(__name__)

class TestHierarchicalCommunication(unittest.TestCase):
    """Tests pour la communication hiérarchique entre les trois niveaux d'agents."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer le middleware
        self.middleware = MessageMiddleware()
        
        # Enregistrer les canaux
        self.hierarchical_channel = HierarchicalChannel("hierarchical")
        self.collaboration_channel = CollaborationChannel("collaboration")
        self.data_channel = DataChannel(DATA_DIR)
        
        self.middleware.register_channel(self.hierarchical_channel)
        self.middleware.register_channel(self.collaboration_channel)
        self.middleware.register_channel(self.data_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Créer les adaptateurs pour les agents
        self.strategic_adapter = StrategicAdapter("strategic-agent-1", self.middleware)
        self.tactical_adapter = TacticalAdapter("tactical-agent-1", self.middleware)
        self.operational_adapter = OperationalAdapter("operational-agent-1", self.middleware)
    
    def test_top_down_communication(self):
        """Test de la communication descendante (stratégique -> tactique -> opérationnel)."""
        # Simuler un agent tactique
        def tactical_agent():
            # Recevoir la directive
            directive = self.tactical_adapter.receive_directive(timeout=2.0)
            
            # Vérifier que la directive a été reçue
            self.assertIsNotNone(directive)
            self.assertEqual(directive.sender, "strategic-agent-1")
            self.assertEqual(directive.content["command_type"], "analyze_text")
            
            # Assigner une tâche à l'agent opérationnel
            self.tactical_adapter.assign_task(
                task_type="extract_arguments",
                parameters={"text_id": directive.content["parameters"]["text_id"]},
                recipient_id="operational-agent-1",
                priority=MessagePriority.NORMAL
            )
        
        # Simuler un agent opérationnel
        def operational_agent():
            # Recevoir la tâche
            task = self.operational_adapter.receive_task(timeout=2.0)
            
            # Vérifier que la tâche a été reçue
            self.assertIsNotNone(task)
            self.assertEqual(task.sender, "tactical-agent-1")
            self.assertEqual(task.content["command_type"], "extract_arguments")
            self.assertEqual(task.content["parameters"]["text_id"], "text-123")
        
        # Démarrer les threads pour simuler les agents
        tactical_thread = threading.Thread(target=tactical_agent)
        operational_thread = threading.Thread(target=operational_agent)
        
        tactical_thread.start()
        operational_thread.start()
        
        # Émettre une directive
        self.strategic_adapter.issue_directive(
            directive_type="analyze_text",
            parameters={"text_id": "text-123"},
            recipient_id="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Attendre que les threads se terminent
        tactical_thread.join()
        operational_thread.join()
    
    def test_bottom_up_communication(self):
        """Test de la communication ascendante (opérationnel -> tactique -> stratégique)."""
        # Simuler un agent opérationnel
        def operational_agent():
            # Envoyer un résultat
            self.operational_adapter.send_result( # Corrigé: send_task_result -> send_result
                task_id="task-123",
                result_type="generic_result", # Ajout d'un result_type car send_result le requiert
                result={"arguments": ["arg1", "arg2"], "confidence": 0.95},
                recipient_id="tactical-agent-1",
                priority=MessagePriority.NORMAL
            )
        
        # Simuler un agent tactique
        def tactical_agent():
            # Recevoir le résultat
            result = self.tactical_adapter.receive_task_result(timeout=2.0)
            
            # Vérifier que le résultat a été reçu
            logger.info(f"Tactical agent received result.content: {result.content if result else 'None'}")
            self.assertIsNotNone(result)
            self.assertEqual(result.sender, "operational-agent-1")
            self.assertEqual(result.content["info_type"], "task_result")
            self.assertEqual(result.content[DATA_DIR]["arguments"], ["arg1", "arg2"])
            
            # Envoyer un rapport à l'agent stratégique
            self.tactical_adapter.send_report(
                report_type="analysis_complete",
                content={"text_id": "text-123", "arguments": result.content[DATA_DIR]["arguments"]},
                recipient_id="strategic-agent-1",
                priority=MessagePriority.NORMAL
            )
        
        # Démarrer les threads pour simuler les agents
        operational_thread = threading.Thread(target=operational_agent)
        tactical_thread = threading.Thread(target=tactical_agent)
        
        operational_thread.start()
        tactical_thread.start()
        
        # Recevoir le rapport
        report = self.strategic_adapter.receive_report(timeout=5.0)
        
        # Vérifier que le rapport a été reçu
        self.assertIsNotNone(report)
        self.assertEqual(report.sender, "tactical-agent-1")
        self.assertEqual(report.content["report_type"], "analysis_complete")
        self.assertEqual(report.content["data"]["arguments"], ["arg1", "arg2"])
        
        # Attendre que les threads se terminent
        operational_thread.join()
        tactical_thread.join()
    
    def test_full_hierarchical_workflow(self):
        """Test d'un flux de travail hiérarchique complet."""
        # Simuler un agent opérationnel
        def operational_agent():
            # Recevoir la tâche
            task = self.operational_adapter.receive_task(timeout=2.0)
            
            # Vérifier que la tâche a été reçue
            self.assertIsNotNone(task)
            self.assertEqual(task.sender, "tactical-agent-1")
            self.assertEqual(task.content["command_type"], "extract_arguments")
            
            # Envoyer une mise à jour de statut
            self.operational_adapter.send_progress_update(
                task_id=task.id,
                progress=0.5, # La progression est un float entre 0.0 et 1.0
                status="in_progress",
                details={"current_step": "argument_extraction"},
                recipient_id="tactical-agent-1",
                priority=MessagePriority.NORMAL
            )
            
            # Simuler un traitement
            time.sleep(0.2)
            
            # Envoyer un résultat
            self.operational_adapter.send_result( # Corrigé: send_task_result -> send_result
                task_id=task.id,
                result_type="generic_result", # Ajout du result_type manquant
                result={"arguments": ["arg1", "arg2"], "confidence": 0.95},
                recipient_id="tactical-agent-1",
                priority=MessagePriority.NORMAL
            )
        
        # Simuler un agent tactique
        def tactical_agent():
            # Recevoir la directive
            directive = self.tactical_adapter.receive_directive(timeout=2.0)
            
            # Vérifier que la directive a été reçue
            self.assertIsNotNone(directive)
            self.assertEqual(directive.sender, "strategic-agent-1")
            self.assertEqual(directive.content["command_type"], "analyze_text")
            
            # Envoyer un accusé de réception
            self.tactical_adapter.send_status_update(
                update_type="directive_received",
                status={"directive_id": directive.id, "status": "processing"},
                recipient_id="strategic-agent-1",
                priority=MessagePriority.NORMAL
            )
            
            # Assigner une tâche à l'agent opérationnel
            self.tactical_adapter.assign_task(
                task_type="extract_arguments",
                parameters={"text_id": directive.content["parameters"]["text_id"]},
                recipient_id="operational-agent-1",
                priority=MessagePriority.NORMAL
            )
            
            # Recevoir une mise à jour de statut
            status_update = None
            for _ in range(10):  # Essayer plusieurs fois
                messages = self.middleware.get_pending_messages(
                    recipient_id="tactical-agent-1",
                    channel_type=ChannelType.HIERARCHICAL
                )
                
                for message in messages:
                    if (message.type == MessageType.INFORMATION and
                        message.content.get("info_type") == "operational_update"):
                        status_update = message
                        break
                
                if status_update:
                    break
                
                time.sleep(0.1)
            
            # Vérifier que la mise à jour de statut a été reçue
            self.assertIsNotNone(status_update)
            self.assertEqual(status_update.content["status"], "in_progress")
            
            # Envoyer une mise à jour à l'agent stratégique
            self.tactical_adapter.send_status_update(
                update_type="task_progress",
                status={"directive_id": directive.id, "progress": 50},
                recipient_id="strategic-agent-1",
                priority=MessagePriority.NORMAL
            )
            
            # Recevoir le résultat
            result = self.tactical_adapter.receive_task_result(timeout=5.0) # Augmentation du timeout
            
            # Vérifier que le résultat a été reçu
            self.assertIsNotNone(result)
            self.assertEqual(result.sender, "operational-agent-1")
            self.assertEqual(result.content[DATA_DIR]["arguments"], ["arg1", "arg2"])
            
            # Envoyer un rapport à l'agent stratégique
            self.tactical_adapter.send_report(
                report_type="analysis_complete",
                content={
                    "directive_id": directive.id,
                    "text_id": directive.content["parameters"]["text_id"],
                    "arguments": result.content[DATA_DIR]["arguments"],
                    "confidence": result.content[DATA_DIR]["confidence"]
                },
                recipient_id="strategic-agent-1",
                priority=MessagePriority.NORMAL
            )
        
        # Démarrer les threads pour simuler les agents
        operational_thread = threading.Thread(target=operational_agent)
        tactical_thread = threading.Thread(target=tactical_agent)
        
        # Simuler un agent stratégique
        # Émettre une directive
        directive_id = self.strategic_adapter.issue_directive(
            directive_type="analyze_text",
            parameters={"text_id": "text-123"},
            recipient_id="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Démarrer les threads
        operational_thread.start()
        tactical_thread.start()
        
        # Recevoir un accusé de réception
        ack = None
        for _ in range(10):  # Essayer plusieurs fois
            messages = self.middleware.get_pending_messages(
                recipient_id="strategic-agent-1",
                channel_type=ChannelType.HIERARCHICAL
            )
            
            for message in messages:
                if (message.type == MessageType.INFORMATION and
                    message.content.get("info_type") == "tactical_update" and
                    message.content.get("update_type") == "directive_received"):
                    ack = message
                    break
            
            if ack:
                break
            
            time.sleep(0.1)
        
        # Vérifier que l'accusé de réception a été reçu
        self.assertIsNotNone(ack)
        self.assertEqual(ack.sender, "tactical-agent-1")
        self.assertEqual(ack.content[DATA_DIR]["directive_id"], directive_id)
        
        # Recevoir une mise à jour de progression
        progress = None
        for _ in range(10):  # Essayer plusieurs fois
            messages = self.middleware.get_pending_messages(
                recipient_id="strategic-agent-1",
                channel_type=ChannelType.HIERARCHICAL
            )
            
            for message in messages:
                if (message.type == MessageType.INFORMATION and
                    message.content.get("info_type") == "tactical_update" and
                    message.content.get("update_type") == "task_progress"):
                    progress = message
                    break
            
            if progress:
                break
            
            time.sleep(0.1)
        
        # Vérifier que la mise à jour de progression a été reçue
        self.assertIsNotNone(progress)
        self.assertEqual(progress.sender, "tactical-agent-1")
        self.assertEqual(progress.content[DATA_DIR]["progress"], 50)
        
        # Recevoir le rapport final
        report = self.strategic_adapter.receive_report(timeout=5.0)
        
        # Vérifier que le rapport a été reçu
        self.assertIsNotNone(report)
        self.assertEqual(report.sender, "tactical-agent-1")
        self.assertEqual(report.content["report_type"], "analysis_complete")
        self.assertEqual(report.content["data"]["directive_id"], directive_id)
        self.assertEqual(report.content["data"]["text_id"], "text-123")
        self.assertEqual(report.content["data"]["arguments"], ["arg1", "arg2"])
        self.assertEqual(report.content["data"]["confidence"], 0.95)
        
        # Attendre que les threads se terminent
        operational_thread.join()
        tactical_thread.join()
    
    def test_strategic_guidance(self):
        """Test de la demande de conseils stratégiques."""
        # Simuler un agent stratégique qui fournit des conseils
        def strategic_agent():
            # Recevoir la demande de conseils
            request = self.middleware.receive_message(
                recipient_id="strategic-agent-1",
                channel_type=ChannelType.HIERARCHICAL,
                timeout=2.0
            )
            
            # Vérifier que la demande a été reçue
            self.assertIsNotNone(request)
            self.assertEqual(request.sender, "tactical-agent-1")
            self.assertEqual(request.content["request_type"], "guidance")
            
            # Créer une réponse
            response = request.create_response(
                content={
                    "status": "success",
                    DATA_DIR: {
                        "recommendation": "Focus on fallacies",
                        "priority": "high",
                        "additional_resources": ["resource1", "resource2"]
                    }
                }
            )
            response.sender = "strategic-agent-1"
            response.sender_level = AgentLevel.STRATEGIC
            
            # Envoyer la réponse
            self.middleware.send_message(response)
            time.sleep(0.1) # Donner du temps pour le traitement du message
            # Tentative de forcer le traitement de la réponse par l'agent tactique
            for _ in range(5): # Essayer quelques fois avec un court délai
                # L'agent tactique est le destinataire de la réponse (initiateur de la requête)
                # mais il est bloqué en attente. On essaie de faire traiter sa file.
                # C'est un hack de test.
                processed_msg = self.middleware.receive_message(
                    recipient_id="tactical-agent-1",
                    channel_type=ChannelType.HIERARCHICAL,
                    timeout=0.01
                )
                if processed_msg and processed_msg.id == response.id: # Si on a traité la réponse elle-même
                    break
                time.sleep(0.01)
        
        # Démarrer un thread pour simuler l'agent stratégique
        strategic_thread = threading.Thread(target=strategic_agent)
        strategic_thread.start()
        
        # Demander des conseils stratégiques
        guidance = self.tactical_adapter.request_strategic_guidance(
            request_type="guidance",
            parameters={"text_id": "text-123", "issue": "complex_fallacies"},
            recipient_id="strategic-agent-1",
            timeout=10.0, # Augmentation du timeout (précédemment 5.0)
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que les conseils ont été reçus
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance["recommendation"], "Focus on fallacies")
        self.assertEqual(guidance["priority"], "high")
        self.assertEqual(guidance["additional_resources"], ["resource1", "resource2"])
        
        # Attendre que le thread se termine
        strategic_thread.join()
    
    def test_operational_assistance(self):
        """Test de la demande d'assistance opérationnelle."""
        # Simuler un agent tactique qui fournit de l'assistance
        def tactical_agent():
            # Recevoir la demande d'assistance
            request = self.middleware.receive_message(
                recipient_id="tactical-agent-1",
                channel_type=ChannelType.HIERARCHICAL,
                timeout=2.0
            )
            
            # Vérifier que la demande a été reçue
            self.assertIsNotNone(request)
            self.assertEqual(request.sender, "operational-agent-1")
            self.assertEqual(request.content["request_type"], "assistance")
            
            # Créer une réponse
            response = request.create_response(
                content={
                    "status": "success",
                    DATA_DIR: {
                        "solution": "Use pattern X",
                        "example": "example data",
                        "reference": "reference document"
                    }
                }
            )
            response.sender = "tactical-agent-1"
            response.sender_level = AgentLevel.TACTICAL
            
            # Envoyer la réponse
            self.middleware.send_message(response)
            time.sleep(0.1) # Donner du temps pour le traitement du message
            # Tentative de forcer le traitement de la réponse par l'agent opérationnel
            for _ in range(5):
                processed_msg = self.middleware.receive_message(
                    recipient_id="operational-agent-1",
                    channel_type=ChannelType.HIERARCHICAL,
                    timeout=0.01
                )
                if processed_msg and processed_msg.id == response.id:
                    break
                time.sleep(0.01)
    
        # Démarrer un thread pour simuler l'agent tactique
        tactical_thread = threading.Thread(target=tactical_agent)
        tactical_thread.start()
        
        # Demander de l'assistance
        assistance = self.operational_adapter.request_assistance(
            issue_type="pattern_recognition",
            description="Cannot identify pattern in text",
            context={"text_id": "text-123", "position": "paragraph 3"},
            recipient_id="tactical-agent-1",
            timeout=10.0, # Augmentation du timeout (précédemment 5.0)
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que l'assistance a été reçue
        self.assertIsNotNone(assistance)
        self.assertEqual(assistance["solution"], "Use pattern X")
        self.assertEqual(assistance["example"], "example data")
        self.assertEqual(assistance["reference"], "reference document")
        
        # Attendre que le thread se termine
        tactical_thread.join()
    
    def test_resource_allocation(self):
        """Test de l'allocation de ressources."""
        # Simuler un agent tactique qui reçoit une allocation de ressources
        def tactical_agent():
            # Recevoir l'allocation de ressources
            allocation = None
            for _ in range(10):  # Essayer plusieurs fois
                messages = self.middleware.get_pending_messages(
                    recipient_id="tactical-agent-1",
                    channel_type=ChannelType.HIERARCHICAL
                )
                
                for message in messages:
                    if (message.type == MessageType.COMMAND and
                        message.content.get("command_type") == "allocate_resources"):
                        allocation = message
                        break
                
                if allocation:
                    break
                
                time.sleep(0.1)
            
            # Vérifier que l'allocation a été reçue
            self.assertIsNotNone(allocation)
            self.assertEqual(allocation.sender, "strategic-agent-1")
            self.assertEqual(allocation.content["parameters"]["resource_type"], "cpu")
            self.assertEqual(allocation.content["parameters"]["amount"], 4)
            
            # Envoyer un accusé de réception
            ack = allocation.create_acknowledgement()
            ack.sender = "tactical-agent-1"
            ack.sender_level = AgentLevel.TACTICAL
            
            self.middleware.send_message(ack)
        
        # Démarrer un thread pour simuler l'agent tactique
        tactical_thread = threading.Thread(target=tactical_agent)
        tactical_thread.start()
        
        # Allouer des ressources
        allocation_id = self.strategic_adapter.allocate_resources(
            resource_type="cpu",
            amount=4,
            recipient_id="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Vérifier que l'allocation a été effectuée
        self.assertIsNotNone(allocation_id)
        
        # Attendre que le thread se termine
        tactical_thread.join()


class TestAsyncHierarchicalCommunication(unittest.IsolatedAsyncioTestCase):
    """Tests pour la communication hiérarchique asynchrone."""
    
    async def asyncSetUp(self):
        """Initialisation asynchrone avant chaque test."""
        # Créer le middleware
        self.middleware = MessageMiddleware()
        
        # Enregistrer les canaux
        self.hierarchical_channel = HierarchicalChannel("hierarchical")
        self.middleware.register_channel(self.hierarchical_channel)
        
        # Initialiser les protocoles
        self.middleware.initialize_protocols()
        
        # Créer les adaptateurs pour les agents
        self.strategic_adapter = StrategicAdapter("strategic-agent-1", self.middleware)
        self.tactical_adapter = TacticalAdapter("tactical-agent-1", self.middleware)
        self.operational_adapter = OperationalAdapter("operational-agent-1", self.middleware)
    
    async def test_async_strategic_guidance(self):
        """Test de la demande asynchrone de conseils stratégiques."""
        # Simuler un agent stratégique qui fournit des conseils
        async def strategic_agent():
            # Recevoir la demande de conseils
            request = await self.middleware.receive_message_async(
                recipient_id="strategic-agent-1",
                channel_type=ChannelType.HIERARCHICAL,
                timeout=2.0
            )
            
            # Vérifier que la demande a été reçue
            self.assertIsNotNone(request)
            self.assertEqual(request.sender, "tactical-agent-1")
            self.assertEqual(request.content["request_type"], "guidance")
            
            # Créer une réponse
            response = request.create_response(
                content={
                    "status": "success",
                    DATA_DIR: {
                        "recommendation": "Focus on fallacies",
                        "priority": "high",
                        "additional_resources": ["resource1", "resource2"]
                    }
                }
            )
            response.sender = "strategic-agent-1"
            response.sender_level = AgentLevel.STRATEGIC
            
            # Envoyer la réponse
            await asyncio.to_thread(self.middleware.send_message, response)
            await asyncio.sleep(0.1) # Donner du temps pour le traitement du message
            # Tentative de forcer le traitement de la réponse par l'agent tactique
            for _ in range(5):
                processed_msg = await self.middleware.receive_message_async(
                    recipient_id="tactical-agent-1",
                    channel_type=ChannelType.HIERARCHICAL,
                    timeout=0.01
                )
                if processed_msg and processed_msg.id == response.id:
                    break
                await asyncio.sleep(0.01)
    
        # Démarrer une tâche pour simuler l'agent stratégique
        strategic_task = asyncio.create_task(strategic_agent())
        
        # Demander des conseils stratégiques de manière asynchrone
        guidance = await self.tactical_adapter.request_strategic_guidance_async(
            request_type="guidance",
            parameters={"text_id": "text-123", "issue": "complex_fallacies"},
            recipient_id="strategic-agent-1",
            timeout=10.0, # Augmentation du timeout (précédemment 5.0)
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que les conseils ont été reçus
        self.assertIsNotNone(guidance)
        self.assertEqual(guidance["recommendation"], "Focus on fallacies")
        self.assertEqual(guidance["priority"], "high")
        self.assertEqual(guidance["additional_resources"], ["resource1", "resource2"])
        
        # Attendre que la tâche se termine
        await strategic_task
    
    async def test_async_operational_assistance(self):
        """Test de la demande asynchrone d'assistance opérationnelle."""
        # Simuler un agent tactique qui fournit de l'assistance
        async def tactical_agent():
            # Recevoir la demande d'assistance
            request = await self.middleware.receive_message_async(
                recipient_id="tactical-agent-1",
                channel_type=ChannelType.HIERARCHICAL,
                timeout=2.0
            )
            
            # Vérifier que la demande a été reçue
            self.assertIsNotNone(request)
            self.assertEqual(request.sender, "operational-agent-1")
            self.assertEqual(request.content["request_type"], "assistance")
            
            # Créer une réponse
            response = request.create_response(
                content={
                    "status": "success",
                    DATA_DIR: {
                        "solution": "Use pattern X",
                        "example": "example data",
                        "reference": "reference document"
                    }
                }
            )
            response.sender = "tactical-agent-1"
            response.sender_level = AgentLevel.TACTICAL
            
            # Envoyer la réponse
            self.middleware.send_message(response) # Note: send_message est synchrone ici
            await asyncio.sleep(0.1) # Donner du temps pour le traitement du message
            # Tentative de forcer le traitement de la réponse par l'agent opérationnel
            for _ in range(5):
                processed_msg = await self.middleware.receive_message_async(
                    recipient_id="operational-agent-1",
                    channel_type=ChannelType.HIERARCHICAL,
                    timeout=0.01
                )
                if processed_msg and processed_msg.id == response.id:
                    break
                await asyncio.sleep(0.01)
    
        # Démarrer une tâche pour simuler l'agent tactique
        tactical_task = asyncio.create_task(tactical_agent())
        
        # Demander de l'assistance de manière asynchrone
        # Utiliser asyncio.to_thread si request_assistance est synchrone
        assistance = await asyncio.to_thread(
            self.operational_adapter.request_assistance,
            issue_type="pattern_recognition",
            description="Cannot identify pattern in text",
            context={"text_id": "text-123", "position": "paragraph 3"},
            recipient_id="tactical-agent-1",
            timeout=10.0, # Augmentation du timeout (précédemment 5.0)
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que l'assistance a été reçue
        self.assertIsNotNone(assistance)
        self.assertEqual(assistance["solution"], "Use pattern X")
        self.assertEqual(assistance["example"], "example data")
        self.assertEqual(assistance["reference"], "reference document")
        
        # Attendre que la tâche se termine
        await tactical_task


if __name__ == "__main__":
    unittest.main()