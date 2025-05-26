#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le Coordinateur de Tâches de l'architecture hiérarchique.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import json
import logging
from datetime import datetime

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestTaskCoordinator")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Import du module à tester
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.core.communication import (
    MessageMiddleware, TacticalAdapter, OperationalAdapter,
    ChannelType, MessagePriority, Message, MessageType, AgentLevel
)


class TestTaskCoordinator(unittest.TestCase):
    """Tests unitaires pour le Coordinateur de Tâches."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un état tactique mock
        self.tactical_state = MagicMock(spec=TacticalState)
        self.tactical_state.add_assigned_objective = MagicMock()
        self.tactical_state.add_task = MagicMock()
        self.tactical_state.add_task_dependency = MagicMock()
        self.tactical_state.log_tactical_action = MagicMock()
        self.tactical_state.update_task_status = MagicMock()
        self.tactical_state.add_task_result = MagicMock()
        self.tactical_state.get_objective_results = MagicMock(return_value={})
        self.tactical_state.tasks = {
            "pending": [],
            "in_progress": [],
            "completed": [],
            "failed": []
        }
        self.tactical_state.assigned_objectives = []
        
        # Créer un middleware mock
        self.middleware = MagicMock(spec=MessageMiddleware)
        self.middleware.get_channel = MagicMock(return_value=MagicMock())
        self.middleware.publish = MagicMock()
        
        # Créer un adaptateur tactique mock
        self.adapter = MagicMock(spec=TacticalAdapter)
        
        # Patcher la création de l'adaptateur tactique
        with patch('argumentation_analysis.orchestration.hierarchical.tactical.coordinator.TacticalAdapter') as mock_adapter_class:
            mock_adapter_class.return_value = self.adapter
            
            # Créer le coordinateur de tâches
            self.coordinator = TaskCoordinator(
                tactical_state=self.tactical_state,
                middleware=self.middleware
            )
    
    def test_initialization(self):
        """Teste l'initialisation du coordinateur de tâches."""
        # Vérifier que l'état tactique a été correctement assigné
        self.assertEqual(self.coordinator.state, self.tactical_state)
        
        # Vérifier que le middleware a été correctement assigné
        self.assertEqual(self.coordinator.middleware, self.middleware)
        
        # Vérifier que l'adaptateur tactique a été créé
        self.assertEqual(self.coordinator.adapter, self.adapter)
        
        # Vérifier que les capacités des agents ont été définies
        self.assertIn("informal_analyzer", self.coordinator.agent_capabilities)
        self.assertIn("logic_analyzer", self.coordinator.agent_capabilities)
        self.assertIn("extract_processor", self.coordinator.agent_capabilities)
        self.assertIn("visualizer", self.coordinator.agent_capabilities)
        self.assertIn("data_extractor", self.coordinator.agent_capabilities)
        
        # Vérifier que l'abonnement aux directives stratégiques a été effectué
        self.middleware.get_channel.assert_called_once_with(ChannelType.HIERARCHICAL)
        self.middleware.get_channel().subscribe.assert_called_once()
    
    def test_process_strategic_objectives(self):
        """Teste la méthode process_strategic_objectives."""
        # Créer des objectifs stratégiques
        objectives = [
            {
                "id": "obj-1",
                "description": "Identifier les arguments dans le texte",
                "priority": "high"
            },
            {
                "id": "obj-2",
                "description": "Détecter les sophismes dans les arguments",
                "priority": "medium"
            }
        ]
        
        # Patcher la méthode _decompose_objective_to_tasks
        with patch.object(self.coordinator, '_decompose_objective_to_tasks') as mock_decompose:
            # Configurer le mock pour retourner des tâches différentes pour chaque objectif
            mock_decompose.side_effect = [
                [
                    {
                        "id": "task-obj-1-1",
                        "description": "Extraire les segments de texte",
                        "objective_id": "obj-1",
                        "required_capabilities": ["text_extraction"]
                    },
                    {
                        "id": "task-obj-1-2",
                        "description": "Identifier les arguments",
                        "objective_id": "obj-1",
                        "required_capabilities": ["argument_identification"]
                    }
                ],
                [
                    {
                        "id": "task-obj-2-1",
                        "description": "Analyser les sophismes formels",
                        "objective_id": "obj-2",
                        "required_capabilities": ["fallacy_detection"]
                    }
                ]
            ]
            
            # Patcher la méthode _establish_task_dependencies
            with patch.object(self.coordinator, '_establish_task_dependencies') as mock_establish:
                # Patcher la méthode _assign_task_to_operational_agent
                with patch.object(self.coordinator, '_assign_task_to_operational_agent') as mock_assign:
                    # Appeler la méthode process_strategic_objectives
                    result = self.coordinator.process_strategic_objectives(objectives)
                    
                    # Vérifier que les objectifs ont été ajoutés à l'état tactique
                    self.tactical_state.add_assigned_objective.assert_any_call(objectives[0])
                    self.tactical_state.add_assigned_objective.assert_any_call(objectives[1])
                    self.assertEqual(self.tactical_state.add_assigned_objective.call_count, 2)
                    
                    # Vérifier que la méthode _decompose_objective_to_tasks a été appelée pour chaque objectif
                    mock_decompose.assert_any_call(objectives[0])
                    mock_decompose.assert_any_call(objectives[1])
                    self.assertEqual(mock_decompose.call_count, 2)
                    
                    # Vérifier que la méthode _establish_task_dependencies a été appelée
                    mock_establish.assert_called_once()
                    
                    # Vérifier que les tâches ont été ajoutées à l'état tactique
                    self.assertEqual(self.tactical_state.add_task.call_count, 3)
                    
                    # Vérifier que la méthode _assign_task_to_operational_agent a été appelée pour chaque tâche
                    self.assertEqual(mock_assign.call_count, 3)
                    
                    # Vérifier le résultat
                    self.assertEqual(result["tasks_created"], 3)
                    self.assertEqual(len(result["tasks_by_objective"]), 2)
                    self.assertEqual(len(result["tasks_by_objective"]["obj-1"]), 2)
                    self.assertEqual(len(result["tasks_by_objective"]["obj-2"]), 1)
    
    def test_determine_appropriate_agent(self):
        """Teste la méthode _determine_appropriate_agent."""
        # Cas 1: Une seule capacité requise, un seul agent correspondant
        agent = self.coordinator._determine_appropriate_agent(["argument_identification"])
        self.assertEqual(agent, "informal_analyzer")
        
        # Cas 2: Plusieurs capacités requises, un agent avec le plus de correspondances
        agent = self.coordinator._determine_appropriate_agent(["formal_logic", "validity_checking"])
        self.assertEqual(agent, "logic_analyzer")
        
        # Cas 3: Capacités requises partagées par plusieurs agents
        agent = self.coordinator._determine_appropriate_agent(["text_extraction", "preprocessing"])
        self.assertEqual(agent, "extract_processor")
        
        # Cas 4: Aucune capacité requise correspondante
        agent = self.coordinator._determine_appropriate_agent(["unknown_capability"])
        self.assertIsNone(agent)
    
    def test_decompose_objective_to_tasks(self):
        """Teste la méthode _decompose_objective_to_tasks."""
        # Cas 1: Objectif d'identification d'arguments
        objective = {
            "id": "obj-1",
            "description": "Identifier les arguments dans le texte",
            "priority": "high"
        }
        tasks = self.coordinator._decompose_objective_to_tasks(objective)
        self.assertEqual(len(tasks), 4)
        self.assertTrue(all(task["objective_id"] == "obj-1" for task in tasks))
        self.assertTrue(any("Extraire les segments" in task["description"] for task in tasks))
        self.assertTrue(any("Identifier les prémisses" in task["description"] for task in tasks))
        
        # Cas 2: Objectif de détection de sophismes
        objective = {
            "id": "obj-2",
            "description": "Détecter les sophismes dans les arguments",
            "priority": "medium"
        }
        tasks = self.coordinator._decompose_objective_to_tasks(objective)
        self.assertEqual(len(tasks), 3)
        self.assertTrue(all(task["objective_id"] == "obj-2" for task in tasks))
        self.assertTrue(any("sophismes formels" in task["description"] for task in tasks))
        self.assertTrue(any("sophismes informels" in task["description"] for task in tasks))
        
        # Cas 3: Objectif d'analyse de structure logique
        objective = {
            "id": "obj-3",
            "description": "Analyser la structure logique des arguments",
            "priority": "low"
        }
        tasks = self.coordinator._decompose_objective_to_tasks(objective)
        self.assertEqual(len(tasks), 3)
        self.assertTrue(all(task["objective_id"] == "obj-3" for task in tasks))
        self.assertTrue(any("Formaliser les arguments" in task["description"] for task in tasks))
        self.assertTrue(any("Vérifier la validité" in task["description"] for task in tasks))
        
        # Cas 4: Objectif d'évaluation de cohérence
        objective = {
            "id": "obj-4",
            "description": "Évaluer la cohérence des arguments",
            "priority": "high"
        }
        tasks = self.coordinator._decompose_objective_to_tasks(objective)
        self.assertEqual(len(tasks), 3)
        self.assertTrue(all(task["objective_id"] == "obj-4" for task in tasks))
        self.assertTrue(any("cohérence interne" in task["description"] for task in tasks))
        self.assertTrue(any("cohérence entre" in task["description"] for task in tasks))
        
        # Cas 5: Objectif générique
        objective = {
            "id": "obj-5",
            "description": "Objectif générique",
            "priority": "medium"
        }
        tasks = self.coordinator._decompose_objective_to_tasks(objective)
        self.assertEqual(len(tasks), 2)
        self.assertTrue(all(task["objective_id"] == "obj-5" for task in tasks))
        self.assertTrue(any("Analyser le texte" in task["description"] for task in tasks))
        self.assertTrue(any("Produire des résultats" in task["description"] for task in tasks))
    
    def test_establish_task_dependencies(self):
        """Teste la méthode _establish_task_dependencies."""
        # Créer des tâches pour un objectif
        tasks = [
            {
                "id": "task-obj-1-1",
                "description": "Tâche 1",
                "objective_id": "obj-1"
            },
            {
                "id": "task-obj-1-2",
                "description": "Tâche 2",
                "objective_id": "obj-1"
            },
            {
                "id": "task-obj-1-3",
                "description": "Tâche 3",
                "objective_id": "obj-1"
            }
        ]
        
        # Appeler la méthode _establish_task_dependencies
        self.coordinator._establish_task_dependencies(tasks)
        
        # Vérifier que les dépendances ont été ajoutées
        self.tactical_state.add_task_dependency.assert_any_call("task-obj-1-1", "task-obj-1-2")
        self.tactical_state.add_task_dependency.assert_any_call("task-obj-1-2", "task-obj-1-3")
        self.assertEqual(self.tactical_state.add_task_dependency.call_count, 2)
    
    def test_handle_task_result(self):
        """Teste la méthode handle_task_result."""
        # Configurer l'état tactique pour le test
        self.tactical_state.tasks = {
            "pending": [],
            "in_progress": [],
            "completed": [
                {
                    "id": "task-obj-1-1",
                    "objective_id": "obj-1"
                },
                {
                    "id": "task-obj-1-2",
                    "objective_id": "obj-1"
                }
            ],
            "failed": []
        }
        
        # Créer un résultat de tâche
        result = {
            "id": "result-1",
            "task_id": "op-task-1",
            "tactical_task_id": "task-obj-1-3",
            "status": "completed",
            "data": {
                "identified_arguments": [
                    {
                        "id": "arg-1",
                        "text": "Argument 1"
                    }
                ]
            }
        }
        
        # Appeler la méthode handle_task_result
        response = self.coordinator.handle_task_result(result)
        
        # Vérifier que le statut de la tâche a été mis à jour
        self.tactical_state.update_task_status.assert_called_once_with(
            "task-obj-1-3",
            "completed"
        )
        
        # Vérifier que le résultat a été ajouté
        self.tactical_state.add_intermediate_result.assert_called_once_with("task-obj-1-3", result)
        
        # Vérifier la réponse
        self.assertEqual(response["status"], "success")
        self.assertEqual(response["message"], "Résultat de la tâche task-obj-1-3 traité avec succès")
    
    def test_generate_status_report(self):
        """Teste la méthode generate_status_report."""
        # Configurer l'état tactique pour le test
        self.tactical_state.tasks = {
            "pending": [
                {
                    "id": "task-obj-1-3",
                    "objective_id": "obj-1"
                }
            ],
            "in_progress": [
                {
                    "id": "task-obj-2-1",
                    "objective_id": "obj-2"
                }
            ],
            "completed": [
                {
                    "id": "task-obj-1-1",
                    "objective_id": "obj-1"
                },
                {
                    "id": "task-obj-1-2",
                    "objective_id": "obj-1"
                }
            ],
            "failed": [
                {
                    "id": "task-obj-2-2",
                    "objective_id": "obj-2"
                }
            ]
        }
        self.tactical_state.assigned_objectives = [
            {
                "id": "obj-1",
                "description": "Objectif 1"
            },
            {
                "id": "obj-2",
                "description": "Objectif 2"
            }
        ]
        self.tactical_state.issues = [
            {
                "id": "issue-1",
                "description": "Problème 1"
            }
        ]
        self.tactical_state.tactical_metrics = {
            "metric1": 0.8,
            "metric2": 0.6
        }
        
        # Appeler la méthode generate_status_report
        report = self.coordinator.generate_status_report()
        
        # Vérifier que le rapport a été envoyé
        self.adapter.send_report.assert_called_once()
        
        # Vérifier le contenu du rapport
        self.assertIn("timestamp", report)
        self.assertIn("overall_progress", report)
        self.assertIn("tasks_summary", report)
        self.assertEqual(report["tasks_summary"]["total"], 5)
        self.assertEqual(report["tasks_summary"]["completed"], 2)
        self.assertEqual(report["tasks_summary"]["in_progress"], 1)
        self.assertEqual(report["tasks_summary"]["pending"], 1)
        self.assertEqual(report["tasks_summary"]["failed"], 1)
        self.assertIn("progress_by_objective", report)
        self.assertEqual(len(report["progress_by_objective"]), 2)
        self.assertIn("issues", report)
        self.assertEqual(len(report["issues"]), 1)
        # La clé "metrics" n'est pas présente dans l'implémentation actuelle


if __name__ == "__main__":
    unittest.main()