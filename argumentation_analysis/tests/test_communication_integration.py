"""
Tests d'intégration pour le système de communication multi-canal.

Ces tests valident l'intégration des différents composants du système de communication
et vérifient que les agents peuvent communiquer efficacement à travers les différents canaux.
"""

import unittest
import asyncio
import threading
import time
import uuid
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



class TestCommunicationIntegration(unittest.TestCase):
    """Tests d'intégration pour le système de communication multi-canal."""
    
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
    
    def test_strategic_tactical_communication(self):
        """Test de la communication entre les niveaux stratégique et tactique."""
        # Simuler un agent tactique qui reçoit une directive et envoie un rapport
        def tactical_agent():
            # Recevoir la directive
            directive = self.tactical_adapter.receive_directive(timeout=2.0)
            
            # Vérifier que la directive a été reçue
            self.assertIsNotNone(directive)
            self.assertEqual(directive.sender, "strategic-agent-1")
            self.assertEqual(directive.content["command_type"], "analyze_text")
            
            # Envoyer un rapport
            self.tactical_adapter.send_report(
                report_type="status_update",
                content={"status": "in_progress", "completion": 50},
                recipient_id="strategic-agent-1",
                priority=MessagePriority.NORMAL
            )
        
        # Démarrer un thread pour simuler l'agent tactique
        tactical_thread = threading.Thread(target=tactical_agent)
        tactical_thread.start()
        
        # Simuler un agent stratégique qui émet une directive et reçoit un rapport
        # Émettre une directive
        self.strategic_adapter.issue_directive(
            directive_type="analyze_text",
            parameters={"text_id": "text-123"},
            recipient_id="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Recevoir un rapport
        report = self.strategic_adapter.receive_report(timeout=2.0)
        
        # Vérifier que le rapport a été reçu
        self.assertIsNotNone(report)
        self.assertEqual(report.sender, "tactical-agent-1")
        self.assertEqual(report.content["report_type"], "status_update")
        self.assertEqual(report.content["data"]["completion"], 50)
        
        # Attendre que le thread se termine
        tactical_thread.join()
    
    def test_tactical_operational_communication(self):
        """Test de la communication entre les niveaux tactique et opérationnel."""
        # Simuler un agent opérationnel qui reçoit une tâche et envoie un résultat
        def operational_agent():
            # Recevoir la tâche
            task = self.operational_adapter.receive_task(timeout=2.0)
            
            # Vérifier que la tâche a été reçue
            self.assertIsNotNone(task)
            self.assertEqual(task.sender, "tactical-agent-1")
            self.assertEqual(task.content["command_type"], "extract_arguments")
            
            # Envoyer un résultat
            self.operational_adapter.send_task_result(
                task_id=task.id,
                result={"arguments": ["arg1", "arg2"], "confidence": 0.95},
                recipient_id="tactical-agent-1",
                priority=MessagePriority.NORMAL
            )
        
        # Démarrer un thread pour simuler l'agent opérationnel
        operational_thread = threading.Thread(target=operational_agent)
        operational_thread.start()
        
        # Simuler un agent tactique qui assigne une tâche et reçoit un résultat
        # Assigner une tâche
        self.tactical_adapter.assign_task(
            task_type="extract_arguments",
            parameters={"text_id": "text-123"},
            recipient_id="operational-agent-1",
            priority=MessagePriority.NORMAL
        )
        
        # Recevoir un résultat
        result = self.tactical_adapter.receive_task_result(timeout=2.0)
        
        # Vérifier que le résultat a été reçu
        self.assertIsNotNone(result)
        self.assertEqual(result.sender, "operational-agent-1")
        self.assertEqual(result.content["info_type"], "task_result")
        self.assertEqual(result.content["data"]["arguments"], ["arg1", "arg2"])
        
        # Attendre que le thread se termine
        operational_thread.join()
    
    def test_request_response_communication(self):
        """Test de la communication par requête-réponse."""
        # Simuler un agent qui répond aux requêtes
        def responder_agent():
            # Recevoir la requête
            request = self.middleware.receive_message(
                recipient_id="tactical-agent-2",
                channel_type=ChannelType.HIERARCHICAL,
                timeout=2.0
            )
            
            # Vérifier que la requête a été reçue
            self.assertIsNotNone(request)
            self.assertEqual(request.sender, "tactical-agent-1")
            self.assertEqual(request.content["request_type"], "assistance")
            
            # Créer une réponse
            response = request.create_response(
                content={"status": "success", "info_type": "response", "data": {"solution": "Use pattern X"}}
            )
            response.sender = "tactical-agent-2"
            response.sender_level = AgentLevel.TACTICAL
            
            # Envoyer la réponse
            self.middleware.send_message(response)
        
        # Créer un adaptateur pour l'agent qui répond
        tactical_adapter2 = TacticalAdapter("tactical-agent-2", self.middleware)
        
        # Démarrer un thread pour simuler l'agent qui répond
        responder_thread = threading.Thread(target=responder_agent)
        responder_thread.start()
        
        # Envoyer une requête
        assistance = self.tactical_adapter.request_strategic_guidance(
            request_type="assistance",
            parameters={"description": "Need help", "context": {}},
            recipient_id="tactical-agent-2",
            timeout=2.0,
            priority=MessagePriority.NORMAL
        )
        
        # Vérifier que la réponse a été reçue
        self.assertIsNotNone(assistance)
        self.assertEqual(assistance["solution"], "Use pattern X")
        
        # Attendre que le thread se termine
        responder_thread.join()
    
    def test_publish_subscribe_communication(self):
        """Test de la communication par publication-abonnement."""
        # Créer un callback simulé
        callback = MagicMock()
        
        # S'abonner à un topic
        subscription_id = self.middleware.subscribe(
            subscriber_id="tactical-agent-1",
            topic_id="events.system",
            callback=callback
        )
        
        # Vérifier que l'abonnement a été créé
        self.assertIsNotNone(subscription_id)
        
        # Publier un message sur le topic
        self.middleware.publish(
            topic_id="events.system",
            sender="system",
            sender_level=AgentLevel.SYSTEM,
            content={"event_type": "resource_update", "data": {"cpu_available": 8}},
            priority=MessagePriority.NORMAL
        )
        
        # Attendre un peu pour que le message soit traité
        time.sleep(0.1)
        
        # Vérifier que le callback a été appelé
        callback.assert_called_once()
        self.assertEqual(callback.call_args[0][0].content["event_type"], "resource_update")
        self.assertEqual(callback.call_args[0][0].content[DATA_DIR]["cpu_available"], 8)
    
    def test_data_sharing(self):
        """Test du partage de données."""
        # Stocker des données
        data_id = "test-data-123"
        data = {"dataset": "fallacies", "entries": [{"id": 1, "text": "example"}]}
        
        version_id = self.data_channel.store_data(
            data_id=data_id,
            data=data,
            metadata={"data_type": "dataset", "owner": "tactical-agent-1"}
        )
        
        # Vérifier que les données ont été stockées
        self.assertIsNotNone(version_id)
        
        # Récupérer les données
        retrieved_data, metadata = self.data_channel.get_data(
            data_id=data_id,
            version_id=version_id
        )
        
        # Vérifier que les données ont été récupérées
        self.assertIsNotNone(retrieved_data)
        self.assertEqual(retrieved_data["dataset"], "fallacies")
        self.assertEqual(retrieved_data["entries"][0]["text"], "example")
    
    def test_end_to_end_workflow(self):
        """Test d'un flux de travail complet de bout en bout."""
        # Simuler un agent opérationnel
        def operational_agent():
            # Recevoir la tâche
            task = self.operational_adapter.receive_task(timeout=2.0)
            
            # Vérifier que la tâche a été reçue
            self.assertIsNotNone(task)
            
            # Envoyer une mise à jour de statut
            self.operational_adapter.send_progress_update(
                task_id=task.id,
                progress=50,
                status="in_progress",
                details={"current_step": "argument_extraction"},
                recipient_id="tactical-agent-1",
                priority=MessagePriority.NORMAL
            )
            
            # Envoyer un résultat
            self.operational_adapter.send_result(
                task_id=task.id,
                result_type="analysis_result",
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
            
            # Assigner une tâche à l'agent opérationnel
            self.tactical_adapter.assign_task(
                task_type="extract_arguments",
                parameters={"text_id": "text-123"},
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
                        message.content.get("info_type") == "status_update"):
                        status_update = message
                        break
                
                if status_update:
                    break
                
                time.sleep(0.1)
            
            # Vérifier que la mise à jour de statut a été reçue
            self.assertIsNotNone(status_update)
            self.assertEqual(status_update.content["data"]["status"], "in_progress")
            
            # Recevoir le résultat
            result = self.tactical_adapter.receive_task_result(timeout=2.0)
            
            # Vérifier que le résultat a été reçu
            self.assertIsNotNone(result)
            
            # Envoyer un rapport à l'agent stratégique
            self.tactical_adapter.send_report(
                report_type="analysis_complete",
                content={"text_id": "text-123", "arguments": ["arg1", "arg2"]},
                recipient_id="strategic-agent-1",
                priority=MessagePriority.NORMAL
            )
        
        # Démarrer les threads pour simuler les agents
        operational_thread = threading.Thread(target=operational_agent)
        tactical_thread = threading.Thread(target=tactical_agent)
        
        operational_thread.start()
        tactical_thread.start()
        
        # Simuler un agent stratégique
        # Émettre une directive
        self.strategic_adapter.issue_directive(
            directive_type="analyze_text",
            parameters={"text_id": "text-123"},
            recipient_id="tactical-agent-1",
            priority=MessagePriority.HIGH
        )
        
        # Recevoir un rapport
        report = self.strategic_adapter.receive_report(timeout=5.0)
        
        # Vérifier que le rapport a été reçu
        self.assertIsNotNone(report)
        self.assertEqual(report.content["report_type"], "analysis_complete")
        self.assertEqual(report.content["data"]["text_id"], "text-123")
        self.assertEqual(report.content["data"]["arguments"], ["arg1", "arg2"])
        
        # Attendre que les threads se terminent
        operational_thread.join()
        tactical_thread.join()


class TestAsyncCommunicationIntegration(unittest.IsolatedAsyncioTestCase):
    """Tests d'intégration pour la communication asynchrone."""
    
    async def asyncSetUp(self):
        """Initialisation asynchrone avant chaque test."""
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
    
    async def test_async_request_response(self):
        """Test de la communication asynchrone par requête-réponse."""
        # Simuler un agent qui répond aux requêtes
        # Créer un adaptateur pour l'agent qui répond
        tactical_adapter2 = TacticalAdapter("tactical-agent-2", self.middleware)
        
        # Créer une file d'attente pour les requêtes et les réponses
        request_queue = asyncio.Queue()
        response_queue = asyncio.Queue()
        
        # Simuler un agent qui répond aux requêtes
        async def responder_agent():
            # Attendre une requête de la file d'attente
            request = await request_queue.get()
            
            # Créer une réponse
            response = request.create_response(
                content={"status": "success", "info_type": "response", "data": {"solution": "Use pattern X"}}
            )
            response.sender = "tactical-agent-2"
            response.sender_level = AgentLevel.TACTICAL
            
            # Mettre la réponse dans la file d'attente des réponses
            await response_queue.put(response)
        
        # Remplacer la méthode send_message du middleware pour intercepter les requêtes
        original_send_message = self.middleware.send_message
        def intercepted_send_message(message):
            if (message.type == MessageType.REQUEST and
                message.recipient == "tactical-agent-2" and
                message.content.get("request_type") == "assistance"):
                # Mettre la requête dans la file d'attente
                asyncio.create_task(request_queue.put(message))
            return original_send_message(message)
        
        # Remplacer la méthode send_request_async pour retourner la réponse de la file d'attente
        original_send_request_async = self.middleware.request_response.send_request_async
        async def intercepted_send_request_async(*args, **kwargs):
            # Appeler la méthode originale pour envoyer la requête
            asyncio.create_task(original_send_request_async(*args, **kwargs))
            # Attendre et retourner la réponse de la file d'attente
            response = await response_queue.get()
            return response
        
        # Appliquer les remplacements
        self.middleware.send_message = intercepted_send_message
        self.middleware.request_response.send_request_async = intercepted_send_request_async
        
        try:
            # Démarrer l'agent qui répond
            responder_task = asyncio.create_task(responder_agent())
            
            # Envoyer une requête de manière asynchrone
            assistance = await self.tactical_adapter.request_strategic_guidance_async(
                request_type="assistance",
                parameters={"description": "Need help", "context": {}},
                recipient_id="tactical-agent-2",
                timeout=10.0,  # Augmenter le timeout
                priority=MessagePriority.NORMAL
            )
            
            # Attendre que la tâche se termine
            await responder_task
            
            # Vérifier que la réponse a été reçue
            self.assertIsNotNone(assistance)
            self.assertEqual(assistance["solution"], "Use pattern X")
        finally:
            # Restaurer les méthodes originales
            self.middleware.send_message = original_send_message
            self.middleware.request_response.send_request_async = original_send_request_async
    
    async def test_async_parallel_requests(self):
        """Test de l'envoi parallèle de requêtes asynchrones."""
        # Créer des files d'attente pour les requêtes et les réponses
        request_queue = asyncio.Queue()
        response_queues = {}
        
        # Simuler un agent qui répond aux requêtes
        async def responder_agent():
            # Traiter 3 requêtes
            for _ in range(3):
                # Attendre une requête de la file d'attente
                request = await request_queue.get()
                
                # Créer une réponse
                response = request.create_response(
                    content={"status": "success", "info_type": "response", "data": {"request_id": request.id}}
                )
                response.sender = "tactical-agent-2"
                response.sender_level = AgentLevel.TACTICAL
                
                # Attendre un peu pour simuler un traitement
                await asyncio.sleep(0.1)
                
                # Mettre la réponse dans la file d'attente correspondante
                await response_queues[request.id].put(response)
        
        # Créer un adaptateur pour l'agent qui répond
        tactical_adapter2 = TacticalAdapter("tactical-agent-2", self.middleware)
        
        # Démarrer une tâche pour simuler l'agent qui répond
        responder_task = asyncio.create_task(responder_agent())
        
        # Envoyer plusieurs requêtes en parallèle
        request_tasks = []
        for i in range(3):
            task = self.tactical_adapter.request_strategic_guidance_async(
                request_type=f"request-{i}",
                parameters={"index": i},
                recipient_id="tactical-agent-2",
                timeout=2.0,
                priority=MessagePriority.NORMAL
            )
            request_tasks.append(task)
        
        # Remplacer la méthode send_message du middleware pour intercepter les requêtes
        original_send_message = self.middleware.send_message
        def intercepted_send_message(message):
            if (message.type == MessageType.REQUEST and
                message.recipient == "tactical-agent-2" and
                message.content.get("request_type", "").startswith("request-")):
                # Créer une file d'attente pour cette requête
                response_queues[message.id] = asyncio.Queue()
                # Mettre la requête dans la file d'attente
                asyncio.create_task(request_queue.put(message))
            return original_send_message(message)
        
        # Remplacer la méthode send_request_async pour retourner la réponse de la file d'attente
        original_send_request_async = self.middleware.request_response.send_request_async
        async def intercepted_send_request_async(*args, **kwargs):
            # Appeler la méthode originale pour envoyer la requête
            request = Message(
                message_type=MessageType.REQUEST,
                sender=kwargs.get("sender"),
                sender_level=kwargs.get("sender_level"),
                content={
                    "request_type": kwargs.get("request_type"),
                    **kwargs.get("content", {}),
                    "timeout": kwargs.get("timeout", 30.0)
                },
                recipient=kwargs.get("recipient"),
                channel=kwargs.get("channel"),
                priority=kwargs.get("priority", MessagePriority.NORMAL),
                metadata={
                    "conversation_id": f"conv-{uuid.uuid4().hex[:8]}",
                    "requires_ack": True
                }
            )
            
            # Envoyer la requête
            intercepted_send_message(request)
            
            # Attendre et retourner la réponse de la file d'attente
            if request.id in response_queues:
                response = await response_queues[request.id].get()
                return response
            return None
        
        # Appliquer les remplacements
        self.middleware.send_message = intercepted_send_message
        self.middleware.request_response.send_request_async = intercepted_send_request_async
        
        try:
            # Démarrer l'agent qui répond
            responder_task = asyncio.create_task(responder_agent())
            
            # Envoyer plusieurs requêtes en parallèle
            request_tasks = []
            for i in range(3):
                task = self.tactical_adapter.request_strategic_guidance_async(
                    request_type=f"request-{i}",
                    parameters={"index": i},
                    recipient_id="tactical-agent-2",
                    timeout=10.0,  # Augmenter le timeout
                    priority=MessagePriority.NORMAL
                )
                request_tasks.append(task)
            
            # Attendre que toutes les requêtes soient traitées
            responses = await asyncio.gather(*request_tasks)
            
            # Attendre que la tâche se termine
            await responder_task
            
            # Vérifier que toutes les réponses ont été reçues
            self.assertEqual(len(responses), 3)
            for response in responses:
                self.assertIsNotNone(response)
                self.assertIn("request_id", response)
        finally:
            # Restaurer les méthodes originales
            self.middleware.send_message = original_send_message
            self.middleware.request_response.send_request_async = original_send_request_async


if __name__ == "__main__":
    unittest.main()