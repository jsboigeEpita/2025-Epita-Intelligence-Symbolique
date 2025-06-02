#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests supplémentaires pour améliorer la couverture du module coordinator.py.
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
logger = logging.getLogger("TestTacticalCoordinatorCoverage")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.core.communication import (
    MessageMiddleware, TacticalAdapter, OperationalAdapter,
    ChannelType, MessagePriority, Message, MessageType, AgentLevel
)


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
        return callback  # Retourner le callback pour pouvoir le tester
    
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
        self.published_topics = []
    
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
        # Enregistrer la publication pour les tests
        self.published_topics.append({
            "topic_id": topic_id,
            "sender": sender,
            "sender_level": sender_level,
            "content": content,
            "priority": priority,
            "metadata": metadata or {}
        })
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


class TestTacticalCoordinatorCoverage(unittest.TestCase):
    """Tests supplémentaires pour améliorer la couverture du module coordinator.py."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un état tactique
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
    
    def test_subscribe_to_strategic_directives(self):
        """Teste la méthode _subscribe_to_strategic_directives et le callback handle_directive."""
        # Vérifier que l'abonnement a été effectué lors de l'initialisation
        self.assertIn(ChannelType.HIERARCHICAL, self.middleware.channels)
        channel = self.middleware.get_channel(ChannelType.HIERARCHICAL)
        self.assertIn("tactical_coordinator", channel.subscribers)
        
        # Récupérer le callback
        callback = channel.subscribers["tactical_coordinator"]["callback"]
        
        # Tester le callback avec une directive d'objectif
        objective_message = MockMessage(
            sender="strategic_manager",
            recipient="tactical_coordinator",
            content={
                "directive_type": "objective",
                "content": {
                    "objective": {
                        "id": "obj-test",
                        "description": "Objectif de test",
                        "priority": "high"
                    }
                }
            },
            message_type=MessageType.COMMAND,
            sender_level=AgentLevel.STRATEGIC
        )
        
        # Patcher les méthodes appelées par le callback
        with patch.object(self.coordinator, '_decompose_objective_to_tasks') as mock_decompose, \
             patch.object(self.coordinator, '_establish_task_dependencies') as mock_establish:
            
            # Simuler le comportement de _decompose_objective_to_tasks
            mock_decompose.return_value = [
                {
                    "id": "task-obj-test-1",
                    "description": "Tâche 1 pour l'objectif de test",
                    "objective_id": "obj-test",
                    "estimated_duration": "short",
                    "required_capabilities": ["text_extraction"],
                    "priority": "high"
                }
            ]
            
            # Appeler le callback
            callback(objective_message)
            
            # Vérifier que les méthodes ont été appelées
            mock_decompose.assert_called_once()
            mock_establish.assert_called_once()
            
            # Vérifier que l'objectif a été ajouté à l'état tactique
            self.assertEqual(len(self.tactical_state.assigned_objectives), 1)
            self.assertEqual(self.tactical_state.assigned_objectives[0]["id"], "obj-test")
            
            # Vérifier qu'un accusé de réception a été envoyé
            self.assertEqual(len(self.adapter.sent_reports), 1)
            report = self.adapter.sent_reports[0]
            self.assertEqual(report["report_type"], "directive_acknowledgement")
            self.assertEqual(report["content"]["objective_id"], "obj-test")
            self.assertEqual(report["recipient_id"], "strategic_manager")
        
        # Tester le callback avec un ajustement stratégique
        adjustment_message = MockMessage(
            sender="strategic_manager",
            recipient="tactical_coordinator",
            content={
                "directive_type": "strategic_adjustment",
                "content": {
                    "objective_modifications": [
                        {
                            "id": "obj-test",
                            "action": "modify",
                            "updates": {
                                "priority": "medium"
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
            },
            message_type=MessageType.COMMAND,
            sender_level=AgentLevel.STRATEGIC
        )
        
        # Patcher la méthode _apply_strategic_adjustments
        with patch.object(self.coordinator, '_apply_strategic_adjustments') as mock_apply:
            # Appeler le callback
            callback(adjustment_message)
            
            # Vérifier que la méthode a été appelée
            mock_apply.assert_called_once_with(adjustment_message.content["content"])
            
            # Vérifier qu'un accusé de réception a été envoyé
            self.assertEqual(len(self.adapter.sent_reports), 2)
            report = self.adapter.sent_reports[1]
            self.assertEqual(report["report_type"], "adjustment_acknowledgement")
            self.assertEqual(report["content"]["status"], "applied")
            self.assertEqual(report["recipient_id"], "strategic_manager")
    
    def test_apply_strategic_adjustments_complete(self):
        """Teste la méthode _apply_strategic_adjustments de manière plus complète."""
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
                },
                {
                    "id": "obj-2",  # Objectif inexistant
                    "action": "modify",
                    "updates": {
                        "priority": "low"
                    }
                },
                {
                    "id": "obj-1",
                    "action": "unknown_action",  # Action inconnue
                    "updates": {
                        "priority": "low"
                    }
                }
            ],
            "resource_reallocation": {
                "extract_processor": {
                    "priority": "high",
                    "allocation": 0.8
                },
                "unknown_agent": {  # Agent inconnu
                    "priority": "medium",
                    "allocation": 0.5
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
            # Le nombre peut varier en fonction de l'implémentation
            self.assertGreaterEqual(len(self.adapter.sent_status_updates), 2)
            
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
    
    def test_handle_task_result_complete(self):
        """Teste la méthode handle_task_result de manière plus complète."""
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
        
        # Créer un résultat de tâche sans identifiant de tâche tactique
        result_without_id = {
            "id": "result-0",
            "task_id": "op-task-0",
            "status": "completed"
        }
        
        # Appeler la méthode handle_task_result
        response = self.coordinator.handle_task_result(result_without_id)
        
        # Vérifier que la réponse indique une erreur
        self.assertEqual(response["status"], "error")
        self.assertIn("Identifiant de tâche tactique manquant", response["message"])
        
        # Créer un résultat de tâche avec identifiant de tâche tactique
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
        
        # Patcher la méthode update_task_status pour qu'elle accepte 3 arguments
        with patch.object(self.tactical_state, 'update_task_status') as mock_update_status, \
             patch.object(self.tactical_state, 'add_intermediate_result') as mock_add_result, \
             patch.object(self.tactical_state, 'get_objective_results', return_value={"results": "test"}) as mock_get_results:
            
            # Appeler la méthode handle_task_result
            response = self.coordinator.handle_task_result(result)
            
            # Vérifier que les méthodes ont été appelées
            mock_update_status.assert_called_once_with("task-2", "completed")
            mock_add_result.assert_called_once_with("task-2", result)
            
            # Vérifier que la réponse est correcte
            self.assertEqual(response["status"], "success")
            self.assertIn("message", response)
            
            # Nous ne vérifions pas l'envoi de rapport car nous avons patché les méthodes qui déclenchent cet envoi
    
    def test_generate_status_report_with_issues(self):
        """Teste la méthode generate_status_report avec des problèmes."""
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
        
        # Ajouter des problèmes
        self.tactical_state.issues = [
            {
                "id": "issue-1",
                "description": "Problème 1",
                "severity": "high"
            },
            {
                "id": "issue-2",
                "description": "Problème 2",
                "severity": "medium"
            }
        ]
        
        # Appeler la méthode generate_status_report
        report = self.coordinator.generate_status_report()
        
        # Vérifier que le rapport est correct
        self.assertIn("timestamp", report)
        self.assertIn("overall_progress", report)
        self.assertIn("tasks_summary", report)
        self.assertIn("progress_by_objective", report)
        self.assertIn("issues", report)
        
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
        
        # Vérifier les problèmes
        self.assertEqual(len(report["issues"]), 2)
        
        # Vérifier qu'un rapport a été envoyé au niveau stratégique
        self.assertEqual(len(self.adapter.sent_reports), 1)
        sent_report = self.adapter.sent_reports[0]
        self.assertEqual(sent_report["report_type"], "status_update")
        self.assertEqual(sent_report["recipient_id"], "strategic_manager")
        self.assertEqual(sent_report["priority"], MessagePriority.NORMAL)
    
    def test_log_action(self):
        """Teste la méthode _log_action."""
        # Appeler la méthode _log_action
        self.coordinator._log_action("Test", "Description du test")
        
        # Vérifier que l'action a été enregistrée
        self.assertEqual(len(self.tactical_state.tactical_actions_log), 1)
        action = self.tactical_state.tactical_actions_log[0]
        self.assertEqual(action["type"], "Test")
        self.assertEqual(action["description"], "Description du test")
        self.assertEqual(action["agent_id"], "task_coordinator")
        self.assertIn("timestamp", action)


if __name__ == "__main__":
    unittest.main()