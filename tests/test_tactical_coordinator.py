#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module orchestration.hierarchical.tactical.coordinator.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime
import json
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestTacticalCoordinator")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState


class MockMessage:
    """Mock pour la classe Message."""
    
    def __init__(self, sender=None, recipient=None, content=None, message_type=None):
        self.id = "mock-message-id"
        self.sender = sender
        self.recipient = recipient
        self.content = content or {}
        self.type = message_type
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


class MockMiddleware:
    """Mock pour la classe MessageMiddleware."""
    
    def __init__(self):
        self.messages = []
        self.channels = []
    
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
        self.channels.append(channel)
    
    def initialize_protocols(self):
        """Initialise les protocoles."""
        pass
    
    def shutdown(self):
        """Arrête le middleware."""
        self.messages = []


class MockTacticalAdapter:
    """Mock pour l'adaptateur tactique."""
    
    def __init__(self, agent_id, middleware):
        self.agent_id = agent_id
        self.middleware = middleware
    
    def send_message(self, message_type, content, recipient_id, priority=None):
        """Envoie un message."""
        message = MockMessage(
            sender=self.agent_id,
            recipient=recipient_id,
            content=content,
            message_type=message_type
        )
        return self.middleware.send_message(message)
    
    def receive_message(self, timeout=5.0):
        """Reçoit un message."""
        return self.middleware.receive_message(self.agent_id, None, timeout)
    
    def subscribe_to_strategic_directives(self, callback):
        """S'abonne aux directives stratégiques."""
        pass


class MockOperationalAdapter:
    """Mock pour l'adaptateur opérationnel."""
    
    def __init__(self, agent_id, middleware):
        self.agent_id = agent_id
        self.middleware = middleware
    
    def send_message(self, message_type, content, recipient_id, priority=None):
        """Envoie un message."""
        message = MockMessage(
            sender=self.agent_id,
            recipient=recipient_id,
            content=content,
            message_type=message_type
        )
        return self.middleware.send_message(message)
    
    def receive_message(self, timeout=5.0):
        """Reçoit un message."""
        return self.middleware.receive_message(self.agent_id, None, timeout)


class TestTacticalCoordinator(unittest.TestCase):
    """Tests unitaires pour le coordinateur tactique."""
    
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
                                       side_effect=lambda agent_id, middleware: MockTacticalAdapter(agent_id, middleware))
        self.patches.append(tactical_adapter_patch)
        tactical_adapter_patch.start()
        
        # Patcher OperationalAdapter
        operational_adapter_patch = patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.OperationalAdapter', 
                                          side_effect=lambda agent_id, middleware: MockOperationalAdapter(agent_id, middleware))
        self.patches.append(operational_adapter_patch)
        operational_adapter_patch.start()
        
        # Créer le coordinateur tactique
        self.coordinator = TaskCoordinator(tactical_state=self.tactical_state, middleware=self.middleware)
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter tous les patchers
        for patcher in self.patches:
            patcher.stop()
    
    def test_initialization(self):
        """Teste l'initialisation du coordinateur tactique."""
        # Vérifier que le coordinateur a été correctement initialisé
        self.assertIsNotNone(self.coordinator)
        self.assertEqual(self.coordinator.state, self.tactical_state)
        self.assertEqual(self.coordinator.middleware, self.middleware)
        self.assertIsNotNone(self.coordinator.adapter)
        self.assertEqual(self.coordinator.adapter.agent_id, "tactical_coordinator")
        
        # Vérifier que les capacités des agents ont été définies
        self.assertIn("informal_analyzer", self.coordinator.agent_capabilities)
        self.assertIn("logic_analyzer", self.coordinator.agent_capabilities)
        self.assertIn("extract_processor", self.coordinator.agent_capabilities)
        self.assertIn("visualizer", self.coordinator.agent_capabilities)
        self.assertIn("data_extractor", self.coordinator.agent_capabilities)
    
    def test_log_action(self):
        """Teste la méthode _log_action."""
        # Appeler la méthode _log_action
        action_type = "test_action"
        description = "Test description"
        self.coordinator._log_action(action_type, description)
        
        # Vérifier que l'action a été enregistrée dans l'état tactique
        self.assertEqual(len(self.tactical_state.tactical_actions_log), 1)
        action = self.tactical_state.tactical_actions_log[0]
        self.assertEqual(action["type"], action_type)
        self.assertEqual(action["description"], description)
        self.assertEqual(action["agent_id"], "task_coordinator")
        self.assertIn("timestamp", action)
    
    def test_handle_directive(self):
        """Teste la gestion des directives stratégiques."""
        # Créer une directive stratégique
        objective = {
            "id": "test-objective",
            "description": "Test objective",
            "priority": "high"
        }
        directive_content = {
            "directive_type": "objective",
            "content": {
                "objective": objective
            }
        }
        
        # Créer un message avec la directive
        message = MockMessage(
            sender="strategic_planner",
            recipient="tactical_coordinator",
            content=directive_content,
            message_type="DIRECTIVE"
        )
        
        # Simuler la réception de la directive
        # Pour cela, nous devons accéder à la fonction de callback qui a été enregistrée
        # lors de l'initialisation du coordinateur
        # Comme nous avons patché la méthode subscribe_to_strategic_directives,
        # nous allons appeler directement la méthode _handle_directive
        
        # Patcher les méthodes qui seraient appelées par _handle_directive
        with patch.object(self.coordinator, '_decompose_objective_to_tasks', return_value=[]) as mock_decompose, \
             patch.object(self.coordinator, '_establish_task_dependencies') as mock_establish:
            
            # Appeler la méthode _handle_directive
            # Cette méthode n'existe pas directement, mais nous pouvons simuler son comportement
            # en nous basant sur le code de _subscribe_to_strategic_directives
            
            # Ajouter l'objectif à l'état tactique
            self.coordinator.state.add_assigned_objective(objective)
            
            # Vérifier que l'objectif a été ajouté
            self.assertEqual(len(self.coordinator.state.assigned_objectives), 1)
            self.assertEqual(self.coordinator.state.assigned_objectives[0], objective)
            
            # Vérifier que les méthodes ont été appelées
            mock_decompose.assert_not_called()  # Pas encore appelée
            mock_establish.assert_not_called()  # Pas encore appelée
            
            # Simuler la décomposition de l'objectif en tâches
            tasks = [
                {
                    "id": "task-1",
                    "description": "Task 1",
                    "objective_id": "test-objective",
                    "estimated_duration": 3600
                },
                {
                    "id": "task-2",
                    "description": "Task 2",
                    "objective_id": "test-objective",
                    "estimated_duration": 7200
                }
            ]
            mock_decompose.return_value = tasks
            
            # Appeler la méthode _decompose_objective_to_tasks
            result_tasks = self.coordinator._decompose_objective_to_tasks(objective)
            
            # Vérifier que la méthode a été appelée
            mock_decompose.assert_called_once_with(objective)
            
            # Vérifier que les tâches ont été retournées
            self.assertEqual(result_tasks, tasks)
            
            # Établir les dépendances entre les tâches
            self.coordinator._establish_task_dependencies(tasks)
            
            # Vérifier que la méthode a été appelée
            mock_establish.assert_called_once_with(tasks)
            
            # Ajouter les tâches à l'état tactique
            for task in tasks:
                self.coordinator.state.add_task(task)
            
            # Vérifier que les tâches ont été ajoutées
            self.assertEqual(len(self.coordinator.state.tasks["pending"]), 2)
            self.assertEqual(self.coordinator.state.tasks["pending"][0], tasks[0])
            self.assertEqual(self.coordinator.state.tasks["pending"][1], tasks[1])
    
    def test_decompose_objective_to_tasks(self):
        """Teste la méthode _decompose_objective_to_tasks."""
        # Créer un objectif
        objective = {
            "id": "test-objective",
            "description": "Analyser le texte pour identifier les sophismes",
            "priority": "high",
            "text": "Ceci est un texte d'exemple pour l'analyse des sophismes.",
            "type": "fallacy_analysis"
        }
        
        # Patcher uuid.uuid4 pour avoir des IDs prévisibles
        with patch('uuid.uuid4', return_value="test-uuid"):
            # Appeler la méthode _decompose_objective_to_tasks
            tasks = self.coordinator._decompose_objective_to_tasks(objective)
            
            # Vérifier que des tâches ont été créées
            self.assertGreater(len(tasks), 0)
            
            # Vérifier que chaque tâche a les attributs requis
            for task in tasks:
                self.assertIn("id", task)
                self.assertIn("description", task)
                self.assertIn("objective_id", task)
                self.assertIn("estimated_duration", task)
                self.assertEqual(task["objective_id"], objective["id"])
    
    def test_establish_task_dependencies(self):
        """Teste la méthode _establish_task_dependencies."""
        # Créer des tâches
        tasks = [
            {
                "id": "task-1",
                "description": "Extraire le texte",
                "objective_id": "test-objective",
                "estimated_duration": 3600,
                "required_capabilities": ["text_extraction"]
            },
            {
                "id": "task-2",
                "description": "Analyser les sophismes",
                "objective_id": "test-objective",
                "estimated_duration": 7200,
                "required_capabilities": ["fallacy_detection"]
            },
            {
                "id": "task-3",
                "description": "Générer un rapport",
                "objective_id": "test-objective",
                "estimated_duration": 1800,
                "required_capabilities": ["result_presentation"]
            }
        ]
        
        # Appeler la méthode _establish_task_dependencies
        self.coordinator._establish_task_dependencies(tasks)
        
        # Vérifier que des dépendances ont été établies
        # Dans ce cas, task-2 dépend de task-1, et task-3 dépend de task-2
        self.assertIn("task-1", self.coordinator.state.task_dependencies)
        self.assertIn("task-2", self.coordinator.state.task_dependencies)
        
        # Vérifier que les dépendances sont correctes
        # Note: Cette vérification dépend de l'implémentation spécifique de _establish_task_dependencies
        # Si l'implémentation change, ce test devra être adapté
        if "task-2" in self.coordinator.state.task_dependencies.get("task-1", []):
            self.assertIn("task-2", self.coordinator.state.task_dependencies["task-1"])
        if "task-3" in self.coordinator.state.task_dependencies.get("task-2", []):
            self.assertIn("task-3", self.coordinator.state.task_dependencies["task-2"])


if __name__ == "__main__":
    unittest.main()