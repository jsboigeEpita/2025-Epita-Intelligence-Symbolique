#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le Coordinateur de Tâches de l'architecture hiérarchique.
"""

import unittest
import sys
import os
import json
import logging
from datetime import datetime
from unittest.mock import MagicMock, patch

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestTaskCoordinator")

# Ajouter le répertoire racine au chemin Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import du module à tester
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.core.communication import (
    MessageMiddleware, TacticalAdapter,
    ChannelType, MessagePriority, Message, MessageType, AgentLevel
)


class TestTaskCoordinator(unittest.TestCase):
    """Tests unitaires pour le Coordinateur de Tâches."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.tactical_state = MagicMock(spec=TacticalState)
        self.tactical_state.add_assigned_objective = MagicMock()
        self.tactical_state.add_task = MagicMock()
        self.tactical_state.add_task_dependency = MagicMock()
        self.tactical_state.log_tactical_action = MagicMock()
        self.tactical_state.update_task_status = MagicMock()
        self.tactical_state.add_task_result = MagicMock()
        self.tactical_state.get_objective_results = MagicMock(return_value={})
        self.tactical_state.tasks = {
            "pending": [], "in_progress": [], "completed": [], "failed": []
        }
        self.tactical_state.assigned_objectives = []
        
        self.middleware = MagicMock(spec=MessageMiddleware)
        self.middleware.get_channel = MagicMock(return_value=MagicMock())
        self.middleware.publish = MagicMock()
        
        self.adapter = MagicMock(spec=TacticalAdapter)
        
        with patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.TacticalAdapter') as mock_adapter_class:
            mock_adapter_class.return_value = self.adapter
            self.coordinator = TaskCoordinator(
                tactical_state=self.tactical_state,
                middleware=self.middleware
            )
    
    def test_initialization(self):
        """Teste l'initialisation du coordinateur de tâches."""
        self.assertEqual(self.coordinator.state, self.tactical_state)
        self.assertEqual(self.coordinator.middleware, self.middleware)
        self.assertEqual(self.coordinator.adapter, self.adapter)
        self.assertIn("informal_analyzer", self.coordinator.agent_capabilities)
        self.middleware.get_channel.assert_called_once_with(ChannelType.HIERARCHICAL)
        self.middleware.get_channel().subscribe.assert_called_once()
    
    def test_process_strategic_objectives(self):
        """Teste la méthode process_strategic_objectives."""
        objectives = [
            {"id": "obj-1", "description": "Identifier les arguments", "priority": "high"},
            {"id": "obj-2", "description": "Détecter les sophismes", "priority": "medium"}
        ]
        
        with patch.object(self.coordinator, '_decompose_objective_to_tasks') as mock_decompose:
            mock_decompose.side_effect = [
                [
                    {"id": "task-obj-1-1", "description": "Extraire", "objective_id": "obj-1", "required_capabilities": ["text_extraction"]},
                    {"id": "task-obj-1-2", "description": "Identifier", "objective_id": "obj-1", "required_capabilities": ["argument_identification"]}
                ],
                [
                    {"id": "task-obj-2-1", "description": "Analyser sophismes", "objective_id": "obj-2", "required_capabilities": ["fallacy_detection"]}
                ]
            ]
            
            with patch.object(self.coordinator, '_establish_task_dependencies') as mock_establish:
                with patch.object(self.coordinator, '_assign_task_to_operational_agent') as mock_assign:
                    result = self.coordinator.process_strategic_objectives(objectives)
                    
                    self.tactical_state.add_assigned_objective.assert_any_call(objectives[0])
                    self.tactical_state.add_assigned_objective.assert_any_call(objectives[1])
                    self.assertEqual(self.tactical_state.add_assigned_objective.call_count, 2)
                    
                    mock_decompose.assert_any_call(objectives[0])
                    mock_decompose.assert_any_call(objectives[1])
                    
                    mock_establish.assert_called_once()
                    
                    self.assertEqual(self.tactical_state.add_task.call_count, 3)
                    self.assertEqual(mock_assign.call_count, 3)
                    
                    self.assertEqual(result["tasks_created"], 3)
                    self.assertEqual(len(result["tasks_by_objective"]), 2)
                    self.assertEqual(len(result["tasks_by_objective"]["obj-1"]), 2)
                    self.assertEqual(len(result["tasks_by_objective"]["obj-2"]), 1)

if __name__ == "__main__":
    unittest.main()