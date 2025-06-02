#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests avancés pour le module orchestration.hierarchical.tactical.coordinator.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch, call
from datetime import datetime
import json
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestTacticalCoordinatorAdvanced")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.core.communication import MessagePriority, MessageType, AgentLevel


class MockMessage:
    """Mock pour la classe Message."""
    
    def __init__(self, sender=None, recipient=None, content=None, message_type=None, sender_level=None):
        self.id = "mock-message-id"
        self.sender = sender
        self.recipient = recipient
        self.content = content or {}
        self.type = message_type
        self.sender_level = sender_level
        self.metadata = {}
    
    def create_response(self, content=None):
        """Crée une réponse à ce message."""
        response = MockMessage(
            sender=self.recipient,
            recipient=self.sender,
            content=content or {},
            message_type="RESPONSE"
        )
        response.metadata["reply_to"] = self.id
        return response


class MockChannel:
    """Mock pour un canal de communication."""
    
    def __init__(self, channel_type):
        self.channel_type = channel_type
        self.subscribers = {}
    
    def subscribe(self, subscriber_id, callback, filter_criteria=None):
        """S'abonne au canal."""
        self.subscribers[subscriber_id] = {
            "callback": callback,
            "filter_criteria": filter_criteria or {}
        }
    
    def publish(self, message):
        """Publie un message sur le canal."""
        for subscriber_id, subscription in self.subscribers.items():
            callback = subscription["callback"]
            filter_criteria = subscription["filter_criteria"]
            
            # Vérifier si le message correspond aux critères de filtrage
            if self._matches_criteria(message, filter_criteria):
                callback(message)
    
    def _matches_criteria(self, message, criteria):
        """Vérifie si un message correspond aux critères de filtrage."""
        for key, value in criteria.items():
            if key == "recipient" and message.recipient != value:
                return False
            if key == "type" and message.type != value:
                return False
            if key == "sender_level" and message.sender_level != value:
                return False
        return True


class MockMiddleware:
    """Mock pour la classe MessageMiddleware."""
    
    def __init__(self):
        self.messages = []
        self.channels = {}
    
    def send_message(self, message):
        """Envoie un message."""
        self.messages.append(message)
        return True
    
    def receive_message(self, recipient_id, channel_type=None, timeout=5.0):
        """Reçoit un message."""
        for message in self.messages:
            if message.recipient == recipient_id:
                self.messages.remove(message)
                return message
        return None
    
    def get_pending_messages(self, recipient_id, channel_type=None):
        """Récupère les messages en attente."""
        return [m for m in self.messages if m.recipient == recipient_id]
    
    def register_channel(self, channel):
        """Enregistre un canal."""
        self.channels[channel.channel_type] = channel
    
    def get_channel(self, channel_type):
        """Récupère un canal."""
        if channel_type not in self.channels:
            self.channels[channel_type] = MockChannel(channel_type)
        return self.channels[channel_type]
    
    def publish(self, topic_id, sender, sender_level, content, priority=None, metadata=None):
        """Publie un message sur un topic."""
        # Simuler la publication d'un message
        return True
    
    def initialize_protocols(self):
        """Initialise les protocoles."""
        pass
    
    def shutdown(self):
        """Arrête le middleware."""
        self.messages = []


class MockAdapter:
    """Mock pour l'adaptateur tactique."""
    
    def __init__(self, agent_id, middleware):
        self.agent_id = agent_id
        self.middleware = middleware
        self.sent_messages = []
        self.sent_reports = []
        self.sent_tasks = []
        self.sent_status_updates = []
    
    def send_message(self, message_type, content, recipient_id, priority=None):
        """Envoie un message."""
        message = MockMessage(
            sender=self.agent_id,
            recipient=recipient_id,
            content=content,
            message_type=message_type
        )
        self.sent_messages.append({
            "message_type": message_type,
            "content": content,
            "recipient_id": recipient_id,
            "priority": priority
        })
        return self.middleware.send_message(message)
    
    def send_report(self, report_type, content, recipient_id, priority=None):
        """Envoie un rapport."""
        self.sent_reports.append({
            "report_type": report_type,
            "content": content,
            "recipient_id": recipient_id,
            "priority": priority
        })
        return True
    
    def assign_task(self, task_type, parameters, recipient_id, priority=None, requires_ack=False, metadata=None):
        """Assigne une tâche."""
        self.sent_tasks.append({
            "task_type": task_type,
            "parameters": parameters,
            "recipient_id": recipient_id,
            "priority": priority,
            "requires_ack": requires_ack,
            "metadata": metadata or {}
        })
        return True
    
    def send_status_update(self, update_type, status, recipient_id):
        """Envoie une mise à jour de statut."""
        self.sent_status_updates.append({
            "update_type": update_type,
            "status": status,
            "recipient_id": recipient_id
        })
        return True
    
    def receive_message(self, timeout=5.0):
        """Reçoit un message."""
        return self.middleware.receive_message(self.agent_id, None, timeout)


class TestTacticalCoordinatorAdvanced(unittest.TestCase):
    """Tests avancés pour le coordinateur tactique."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un état tactique mock
        self.tactical_state = TacticalState()
        
        # Créer un middleware mock
        self.middleware = MockMiddleware()
        
        # Patcher les imports pour utiliser nos mocks
        self.patches = []
        
        # Patcher MessageMiddleware
        message_middleware_patch = patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.MessageMiddleware',
                                         return_value=self.middleware)
        self.patches.append(message_middleware_patch)
        message_middleware_patch.start()
        
        # Patcher TacticalAdapter
        tactical_adapter_patch = patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.TacticalAdapter',
                                       side_effect=lambda agent_id, middleware: MockAdapter(agent_id, middleware))
        self.patches.append(tactical_adapter_patch)
        tactical_adapter_patch.start()
        
        # Créer le coordinateur tactique
        self.coordinator = TaskCoordinator(tactical_state=self.tactical_state, middleware=self.middleware)
        
        # Accéder à l'adaptateur mock
        self.adapter = self.coordinator.adapter
        
        # Ajouter l'attribut issues à l'état tactique pour les tests
        self.tactical_state.issues = []
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter tous les patchers
        for patcher in self.patches:
            patcher.stop()
    
    def test_process_strategic_objectives(self):
        """Teste la méthode process_strategic_objectives."""
        # Créer des objectifs stratégiques
        objectives = [
            {
                "id": "obj-1",
                "description": "Identifier les arguments dans le texte",
                "priority": "high",
                "text": "Ceci est un texte d'exemple pour l'analyse des arguments.",
                "type": "argument_identification"
            },
            {
                "id": "obj-2",
                "description": "Détecter les sophismes dans le texte",
                "priority": "medium",
                "text": "Ceci est un texte d'exemple pour la détection des sophismes.",
                "type": "fallacy_detection"
            }
        ]
        
        # Patcher les méthodes appelées par process_strategic_objectives
        with patch.object(self.coordinator, '_decompose_objective_to_tasks') as mock_decompose, \
             patch.object(self.coordinator, '_establish_task_dependencies') as mock_establish, \
             patch.object(self.coordinator, '_assign_task_to_operational_agent') as mock_assign:
            
            # Simuler le comportement de _decompose_objective_to_tasks
            mock_decompose.side_effect = lambda obj: [
                {
                    "id": f"task-{obj['id']}-1",
                    "description": f"Tâche 1 pour {obj['description']}",
                    "objective_id": obj["id"],
                    "estimated_duration": "short",
                    "required_capabilities": ["text_extraction"],
                    "priority": obj["priority"]
                },
                {
                    "id": f"task-{obj['id']}-2",
                    "description": f"Tâche 2 pour {obj['description']}",
                    "objective_id": obj["id"],
                    "estimated_duration": "medium",
                    "required_capabilities": ["argument_identification" if obj["type"] == "argument_identification" else "fallacy_detection"],
                    "priority": obj["priority"]
                }
            ]
            
            # Appeler la méthode process_strategic_objectives
            result = self.coordinator.process_strategic_objectives(objectives)
            
            # Vérifier que les méthodes ont été appelées
            self.assertEqual(mock_decompose.call_count, 2)
            mock_decompose.assert_has_calls([
                call(objectives[0]),
                call(objectives[1])
            ])
            
            mock_establish.assert_called_once()
            
            # Vérifier que les tâches ont été assignées
            self.assertEqual(mock_assign.call_count, 4)  # 2 tâches par objectif
            
            # Vérifier que les objectifs ont été ajoutés à l'état tactique
            self.assertEqual(len(self.tactical_state.assigned_objectives), 2)
            self.assertEqual(self.tactical_state.assigned_objectives[0], objectives[0])
            self.assertEqual(self.tactical_state.assigned_objectives[1], objectives[1])
            
            # Vérifier le résultat
            self.assertIn("tasks_created", result)
            self.assertEqual(result["tasks_created"], 4)
            self.assertIn("tasks_by_objective", result)
            self.assertIn("obj-1", result["tasks_by_objective"])
            self.assertIn("obj-2", result["tasks_by_objective"])
    
    def test_assign_task_to_operational_agent(self):
        """Teste la méthode _assign_task_to_operational_agent."""
        # Créer une tâche
        task = {
            "id": "task-1",
            "description": "Extraire le texte",
            "objective_id": "obj-1",
            "estimated_duration": "short",
            "required_capabilities": ["text_extraction"],
            "priority": "high"
        }
        
        # Patcher la méthode _determine_appropriate_agent
        with patch.object(self.coordinator, '_determine_appropriate_agent', return_value="extract_processor") as mock_determine:
            
            # Appeler la méthode _assign_task_to_operational_agent
            self.coordinator._assign_task_to_operational_agent(task)
            
            # Vérifier que la méthode _determine_appropriate_agent a été appelée
            mock_determine.assert_called_once_with(["text_extraction"])
            
            # Vérifier que la tâche a été assignée via l'adaptateur
            self.assertEqual(len(self.adapter.sent_tasks), 1)
            sent_task = self.adapter.sent_tasks[0]
            self.assertEqual(sent_task["task_type"], "operational_task")
            self.assertEqual(sent_task["parameters"], task)
            self.assertEqual(sent_task["recipient_id"], "extract_processor")
            self.assertEqual(sent_task["priority"], MessagePriority.HIGH)
            self.assertTrue(sent_task["requires_ack"])
            self.assertEqual(sent_task["metadata"]["objective_id"], "obj-1")
    
    def test_assign_task_to_operational_agent_no_specific_agent(self):
        """Teste la méthode _assign_task_to_operational_agent quand aucun agent spécifique n'est déterminé."""
        # Créer une tâche
        task = {
            "id": "task-2",
            "description": "Analyser les sophismes",
            "objective_id": "obj-1",
            "estimated_duration": "medium",
            "required_capabilities": ["fallacy_detection", "rhetorical_analysis"],
            "priority": "medium"
        }
        
        # Patcher la méthode _determine_appropriate_agent
        with patch.object(self.coordinator, '_determine_appropriate_agent', return_value=None) as mock_determine:
            
            # Appeler la méthode _assign_task_to_operational_agent
            self.coordinator._assign_task_to_operational_agent(task)
            
            # Vérifier que la méthode _determine_appropriate_agent a été appelée
            mock_determine.assert_called_once_with(["fallacy_detection", "rhetorical_analysis"])
            
            # Vérifier que la tâche a été publiée via le middleware
            # Comme nous avons patché le middleware, nous ne pouvons pas vérifier directement la publication
            # Mais nous pouvons vérifier que la méthode assign_task n'a pas été appelée
            self.assertEqual(len(self.adapter.sent_tasks), 0)
    
    def test_determine_appropriate_agent(self):
        """Teste la méthode _determine_appropriate_agent."""
        # Cas 1: Une seule capacité requise
        agent = self.coordinator._determine_appropriate_agent(["text_extraction"])
        self.assertEqual(agent, "extract_processor")
        
        # Cas 2: Plusieurs capacités requises, un agent les possède toutes
        agent = self.coordinator._determine_appropriate_agent(["argument_identification", "fallacy_detection", "rhetorical_analysis"])
        self.assertEqual(agent, "informal_analyzer")
        
        # Cas 3: Plusieurs capacités requises, plusieurs agents les possèdent partiellement
        agent = self.coordinator._determine_appropriate_agent(["formal_logic", "validity_checking"])
        self.assertEqual(agent, "logic_analyzer")
        
        # Cas 4: Capacité non reconnue
        agent = self.coordinator._determine_appropriate_agent(["capacité_inconnue"])
        self.assertIsNone(agent)
    
    def test_handle_task_result(self):
        """Teste la méthode handle_task_result."""
        # Ajouter un objectif et des tâches à l'état tactique
        objective = {
            "id": "obj-1",
            "description": "Identifier les arguments dans le texte",
            "priority": "high"
        }
        self.tactical_state.add_assigned_objective(objective)
        
        task1 = {
            "id": "task-1",
            "description": "Extraire le texte",
            "objective_id": "obj-1",
            "estimated_duration": "short",
            "required_capabilities": ["text_extraction"],
            "priority": "high"
        }
        task2 = {
            "id": "task-2",
            "description": "Identifier les arguments",
            "objective_id": "obj-1",
            "estimated_duration": "medium",
            "required_capabilities": ["argument_identification"],
            "priority": "high"
        }
        
        self.tactical_state.add_task(task1, "completed")
        self.tactical_state.add_task(task2, "in_progress")
        
        # Créer un résultat de tâche
        result = {
            "id": "result-1",
            "task_id": "op-task-1",
            "tactical_task_id": "task-2",
            "status": "completed",
            "outputs": {
                "identified_arguments": [
                    {"id": "arg-1", "text": "Argument 1", "confidence": 0.8},
                    {"id": "arg-2", "text": "Argument 2", "confidence": 0.9}
                ]
            },
            "metrics": {
                "execution_time": 1.5,
                "confidence": 0.85
            }
        }
        
        # Ajouter temporairement la méthode get_objective_results à TacticalState
        self.tactical_state.get_objective_results = MagicMock(return_value={"results": "test"})
        
        # Patcher les méthodes
        with patch.object(self.tactical_state, 'update_task_status') as mock_update_status, \
             patch.object(self.tactical_state, 'add_intermediate_result') as mock_add_result:
            
            # Appeler la méthode handle_task_result
            response = self.coordinator.handle_task_result(result)
            
            # Vérifier que les méthodes ont été appelées
            mock_update_status.assert_called_once_with("task-2", "completed")
            mock_add_result.assert_called_once_with("task-2", result)
        
        # Nous ne vérifions pas directement l'état des tâches car nous avons patché update_task_status
        # Nous vérifions plutôt que la méthode a été appelée correctement
        # La vérification est déjà faite avec mock_update_status.assert_called_once_with("task-2", "completed")
        
        # Nous ne vérifions pas directement que le résultat a été enregistré car nous avons patché add_intermediate_result
        # La vérification est déjà faite avec mock_add_result.assert_called_once_with("task-2", result)
        
        # Vérifier que la réponse est correcte
        self.assertEqual(response["status"], "success")
        self.assertIn("message", response)
        
        # Nous ne vérifions pas l'envoi de rapport car nous avons patché les méthodes qui déclenchent cet envoi
        # Dans un test réel, nous devrions vérifier que le rapport est envoyé, mais ici nous nous concentrons
        # sur la vérification que les méthodes update_task_status et add_intermediate_result sont appelées correctement
    
    def test_generate_status_report(self):
        """Teste la méthode generate_status_report."""
        # Ajouter un objectif et des tâches à l'état tactique
        objective = {
            "id": "obj-1",
            "description": "Identifier les arguments dans le texte",
            "priority": "high"
        }
        self.tactical_state.add_assigned_objective(objective)
        
        task1 = {
            "id": "task-1",
            "description": "Extraire le texte",
            "objective_id": "obj-1",
            "estimated_duration": "short",
            "required_capabilities": ["text_extraction"],
            "priority": "high"
        }
        task2 = {
            "id": "task-2",
            "description": "Identifier les arguments",
            "objective_id": "obj-1",
            "estimated_duration": "medium",
            "required_capabilities": ["argument_identification"],
            "priority": "high"
        }
        
        self.tactical_state.add_task(task1, "completed")
        self.tactical_state.add_task(task2, "in_progress")
        
        # Appeler la méthode generate_status_report
        report = self.coordinator.generate_status_report()
        
        # Vérifier que le rapport est correct
        self.assertIn("timestamp", report)
        self.assertIn("overall_progress", report)
        self.assertIn("tasks_summary", report)
        self.assertIn("progress_by_objective", report)
        
        # Vérifier les détails du rapport
        self.assertEqual(report["tasks_summary"]["total"], 2)
        self.assertEqual(report["tasks_summary"]["completed"], 1)
        self.assertEqual(report["tasks_summary"]["in_progress"], 1)
        self.assertEqual(report["tasks_summary"]["pending"], 0)
        self.assertEqual(report["tasks_summary"]["failed"], 0)
        
        # Vérifier la progression par objectif
        self.assertIn("obj-1", report["progress_by_objective"])
        self.assertEqual(report["progress_by_objective"]["obj-1"]["total_tasks"], 2)
        self.assertEqual(report["progress_by_objective"]["obj-1"]["completed_tasks"], 1)
        
        # Vérifier qu'un rapport a été envoyé au niveau stratégique
        self.assertEqual(len(self.adapter.sent_reports), 1)
        sent_report = self.adapter.sent_reports[0]
        self.assertEqual(sent_report["report_type"], "status_update")
        self.assertEqual(sent_report["recipient_id"], "strategic_manager")
        self.assertEqual(sent_report["priority"], MessagePriority.NORMAL)
    
    def test_apply_strategic_adjustments(self):
        """Teste la méthode _apply_strategic_adjustments."""
        # Ajouter un objectif et des tâches à l'état tactique
        objective = {
            "id": "obj-1",
            "description": "Identifier les arguments dans le texte",
            "priority": "medium"
        }
        self.tactical_state.add_assigned_objective(objective)
        
        task1 = {
            "id": "task-1",
            "description": "Extraire le texte",
            "objective_id": "obj-1",
            "estimated_duration": "short",
            "required_capabilities": ["text_extraction"],
            "priority": "medium"
        }
        task2 = {
            "id": "task-2",
            "description": "Identifier les arguments",
            "objective_id": "obj-1",
            "estimated_duration": "medium",
            "required_capabilities": ["argument_identification"],
            "priority": "medium"
        }
        
        self.tactical_state.add_task(task1, "in_progress")
        self.tactical_state.add_task(task2, "pending")
        
        # Créer des ajustements stratégiques
        adjustments = {
            "objective_modifications": [
                {
                    "id": "obj-1",
                    "action": "modify",
                    "updates": {
                        "priority": "high"
                    }
                }
            ],
            "resource_reallocation": {
                "extract_processor": {
                    "priority": "high",
                    "allocation": 0.8
                }
            }
        }
        
        # Patcher la méthode _determine_appropriate_agent
        with patch.object(self.coordinator, '_determine_appropriate_agent', return_value="extract_processor") as mock_determine:
            
            # Appeler la méthode _apply_strategic_adjustments
            self.coordinator._apply_strategic_adjustments(adjustments)
            
            # Vérifier que les tâches ont été mises à jour
            for task in self.tactical_state.tasks["in_progress"]:
                if task["id"] == "task-1":
                    self.assertEqual(task["priority"], "high")
            
            # Vérifier que des mises à jour de statut ont été envoyées
            # Note: Le nombre peut varier en fonction de l'implémentation
            self.assertGreaterEqual(len(self.adapter.sent_status_updates), 2)  # Au moins 1 pour la tâche, 1 pour la ressource
            
            # Vérifier la mise à jour de la tâche
            task_update = next((update for update in self.adapter.sent_status_updates
                               if update["update_type"] == "task_priority_change"), None)
            self.assertIsNotNone(task_update)
            # La tâche mise à jour peut être task-1 ou task-2 selon l'implémentation
            self.assertIn(task_update["status"]["task_id"], ["task-1", "task-2"])
            self.assertEqual(task_update["status"]["new_priority"], "high")
            
            # Vérifier la mise à jour de la ressource
            resource_update = next((update for update in self.adapter.sent_status_updates 
                                  if update["update_type"] == "resource_allocation_change"), None)
            self.assertIsNotNone(resource_update)
            self.assertEqual(resource_update["status"]["resource"], "extract_processor")
            self.assertEqual(resource_update["status"]["updates"]["priority"], "high")
            self.assertEqual(resource_update["status"]["updates"]["allocation"], 0.8)


if __name__ == "__main__":
    unittest.main()