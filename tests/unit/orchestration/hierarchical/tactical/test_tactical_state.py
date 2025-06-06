# -*- coding: utf-8 -*-
"""
Tests pour le module state.py du niveau tactique.
"""

import unittest
import json
from unittest.mock import patch, MagicMock

from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState


class TestTacticalState(unittest.TestCase):
    """Tests pour la classe TacticalState."""

    def setUp(self):
        """Initialise un état tactique pour les tests."""
        self.state = TacticalState()
        
        # Objectif de test
        self.test_objective = {
            "id": "obj-001",
            "description": "Analyser les sophismes dans le texte",
            "priority": "high"
        }
        
        # Tâches de test
        self.test_task1 = {
            "id": "task-001",
            "description": "Identifier les sophismes ad hominem",
            "objective_id": "obj-001",
            "estimated_duration": 60
        }
        
        self.test_task2 = {
            "id": "task-002",
            "description": "Identifier les sophismes d'appel à l'autorité",
            "objective_id": "obj-001",
            "estimated_duration": 45
        }
        
        # Conflit de test
        self.test_conflict = {
            "id": "conflict-001",
            "description": "Contradiction entre analyses de sophismes",
            "involved_tasks": ["task-001", "task-002"],
            "severity": "medium"
        }
        
        # Résolution de conflit
        self.test_resolution = {
            "method": "consensus",
            "description": "Résolution par consensus entre agents",
            "timestamp": "2025-05-22T10:00:00Z"
        }
        
        # Action tactique
        self.test_action = {
            "timestamp": "2025-05-22T10:15:00Z",
            "type": "task_assignment",
            "description": "Assignation de tâche à l'agent informel",
            "agent_id": "agent-informal-001"
        }
        
        # Résultat d'analyse rhétorique
        self.test_rhetorical_result = {
            "fallacies": ["ad_hominem", "appeal_to_authority"],
            "confidence": 0.85,
            "context": "Débat politique"
        }

    def test_initialization(self):
        """Teste l'initialisation de l'état tactique."""
        self.assertEqual(len(self.state.assigned_objectives), 0)
        self.assertEqual(len(self.state.tasks["pending"]), 0)
        self.assertEqual(len(self.state.tasks["in_progress"]), 0)
        self.assertEqual(len(self.state.tasks["completed"]), 0)
        self.assertEqual(len(self.state.tasks["failed"]), 0)
        self.assertEqual(len(self.state.task_assignments), 0)
        self.assertEqual(len(self.state.task_dependencies), 0)
        self.assertEqual(len(self.state.task_progress), 0)
        self.assertEqual(len(self.state.intermediate_results), 0)
        self.assertEqual(len(self.state.identified_conflicts), 0)
        self.assertEqual(self.state.tactical_metrics["task_completion_rate"], 0.0)
        self.assertEqual(len(self.state.tactical_metrics["agent_utilization"]), 0)
        self.assertEqual(self.state.tactical_metrics["conflict_resolution_rate"], 0.0)
        self.assertEqual(len(self.state.tactical_actions_log), 0)

    def test_add_assigned_objective(self):
        """Teste l'ajout d'un objectif assigné."""
        self.state.add_assigned_objective(self.test_objective)
        self.assertEqual(len(self.state.assigned_objectives), 1)
        self.assertEqual(self.state.assigned_objectives[0], self.test_objective)

    def test_add_task(self):
        """Teste l'ajout d'une tâche."""
        self.state.add_task(self.test_task1)
        self.assertEqual(len(self.state.tasks["pending"]), 1)
        self.assertEqual(self.state.tasks["pending"][0], self.test_task1)
        
        # Test avec un statut spécifique
        self.state.add_task(self.test_task2, "in_progress")
        self.assertEqual(len(self.state.tasks["in_progress"]), 1)
        self.assertEqual(self.state.tasks["in_progress"][0], self.test_task2)
        
        # Test avec un statut invalide
        self.state.add_task({"id": "task-003", "description": "Test"}, "invalid_status")
        self.assertEqual(len(self.state.tasks.get("invalid_status", [])), 0)

    def test_update_task_status(self):
        """Teste la mise à jour du statut d'une tâche."""
        # Ajouter une tâche
        self.state.add_task(self.test_task1)
        
        # Mettre à jour le statut
        result = self.state.update_task_status(self.test_task1["id"], "in_progress")
        self.assertTrue(result)
        self.assertEqual(len(self.state.tasks["pending"]), 0)
        self.assertEqual(len(self.state.tasks["in_progress"]), 1)
        
        # Tester avec un statut invalide
        result = self.state.update_task_status(self.test_task1["id"], "invalid_status")
        self.assertFalse(result)
        
        # Tester avec un ID de tâche invalide
        result = self.state.update_task_status("invalid-id", "completed")
        self.assertFalse(result)

    def test_assign_task(self):
        """Teste l'assignation d'une tâche à un agent."""
        # Ajouter une tâche
        self.state.add_task(self.test_task1)
        
        # Assigner la tâche
        result = self.state.assign_task(self.test_task1["id"], "agent-001")
        self.assertTrue(result)
        self.assertEqual(self.state.task_assignments[self.test_task1["id"]], "agent-001")
        
        # Tester avec un ID de tâche invalide
        result = self.state.assign_task("invalid-id", "agent-001")
        self.assertFalse(result)

    def test_add_task_dependency(self):
        """Teste l'ajout d'une dépendance entre tâches."""
        # Ajouter deux tâches
        self.state.add_task(self.test_task1)
        self.state.add_task(self.test_task2)
        
        # Ajouter une dépendance
        result = self.state.add_task_dependency(self.test_task1["id"], self.test_task2["id"])
        self.assertTrue(result)
        self.assertIn(self.test_task2["id"], self.state.task_dependencies[self.test_task1["id"]])
        
        # Tester avec des IDs de tâche invalides
        result = self.state.add_task_dependency("invalid-id", self.test_task2["id"])
        self.assertFalse(result)
        
        result = self.state.add_task_dependency(self.test_task1["id"], "invalid-id")
        self.assertFalse(result)

    def test_update_task_progress(self):
        """Teste la mise à jour de la progression d'une tâche."""
        # Ajouter une tâche
        self.state.add_task(self.test_task1)
        
        # Mettre à jour la progression
        result = self.state.update_task_progress(self.test_task1["id"], 0.5)
        self.assertTrue(result)
        self.assertEqual(self.state.task_progress[self.test_task1["id"]], 0.5)
        
        # Tester avec une progression > 1.0
        result = self.state.update_task_progress(self.test_task1["id"], 1.5)
        self.assertTrue(result)
        self.assertEqual(self.state.task_progress[self.test_task1["id"]], 1.0)
        
        # Tester avec une progression < 0.0
        result = self.state.update_task_progress(self.test_task1["id"], -0.5)
        self.assertTrue(result)
        self.assertEqual(self.state.task_progress[self.test_task1["id"]], 0.0)
        
        # Tester avec un ID de tâche invalide
        result = self.state.update_task_progress("invalid-id", 0.5)
        self.assertFalse(result)
        
        # Tester la mise à jour automatique du statut à 100%
        self.state.assign_task(self.test_task1["id"], "agent-001")
        result = self.state.update_task_progress(self.test_task1["id"], 1.0)
        self.assertTrue(result)
        self.assertIn(self.test_task1, self.state.tasks["completed"])

    def test_add_intermediate_result(self):
        """Teste l'ajout d'un résultat intermédiaire."""
        # Ajouter une tâche
        self.state.add_task(self.test_task1)
        
        # Ajouter un résultat intermédiaire
        result = self.state.add_intermediate_result(self.test_task1["id"], {"partial_result": "Sophisme détecté"})
        self.assertTrue(result)
        self.assertEqual(self.state.intermediate_results[self.test_task1["id"]], {"partial_result": "Sophisme détecté"})
        
        # Tester avec un ID de tâche invalide
        result = self.state.add_intermediate_result("invalid-id", {"partial_result": "Test"})
        self.assertFalse(result)

    def test_add_rhetorical_analysis_result(self):
        """Teste l'ajout d'un résultat d'analyse rhétorique."""
        # Ajouter une tâche
        self.state.add_task(self.test_task1)
        
        # Ajouter un résultat d'analyse rhétorique
        result = self.state.add_rhetorical_analysis_result(
            self.test_task1["id"], 
            "complex_fallacy_analyses", 
            self.test_rhetorical_result
        )
        self.assertTrue(result)
        self.assertEqual(
            self.state.rhetorical_analysis_results["complex_fallacy_analyses"][self.test_task1["id"]], 
            self.test_rhetorical_result
        )
        
        # Tester avec un ID de tâche invalide
        result = self.state.add_rhetorical_analysis_result(
            "invalid-id", 
            "complex_fallacy_analyses", 
            self.test_rhetorical_result
        )
        self.assertFalse(result)
        
        # Tester avec un type de résultat invalide
        result = self.state.add_rhetorical_analysis_result(
            self.test_task1["id"], 
            "invalid_type", 
            self.test_rhetorical_result
        )
        self.assertFalse(result)

    def test_get_rhetorical_analysis_result(self):
        """Teste la récupération d'un résultat d'analyse rhétorique."""
        # Ajouter une tâche et un résultat
        self.state.add_task(self.test_task1)
        self.state.add_rhetorical_analysis_result(
            self.test_task1["id"], 
            "complex_fallacy_analyses", 
            self.test_rhetorical_result
        )
        
        # Récupérer le résultat par tâche
        result = self.state.get_rhetorical_analysis_result("complex_fallacy_analyses", self.test_task1["id"])
        self.assertEqual(result, self.test_rhetorical_result)
        
        # Récupérer tous les résultats d'un type
        results = self.state.get_rhetorical_analysis_result("complex_fallacy_analyses")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[self.test_task1["id"]], self.test_rhetorical_result)
        
        # Tester avec un type invalide
        result = self.state.get_rhetorical_analysis_result("invalid_type")
        self.assertIsNone(result)
        
        # Tester avec un ID de tâche invalide
        result = self.state.get_rhetorical_analysis_result("complex_fallacy_analyses", "invalid-id")
        self.assertIsNone(result)

    def test_add_conflict(self):
        """Teste l'ajout d'un conflit."""
        self.state.add_conflict(self.test_conflict)
        self.assertEqual(len(self.state.identified_conflicts), 1)
        self.assertEqual(self.state.identified_conflicts[0], self.test_conflict)

    def test_resolve_conflict(self):
        """Teste la résolution d'un conflit."""
        # Ajouter un conflit
        self.state.add_conflict(self.test_conflict)
        
        # Résoudre le conflit
        result = self.state.resolve_conflict(self.test_conflict["id"], self.test_resolution)
        self.assertTrue(result)
        self.assertTrue(self.state.identified_conflicts[0]["resolved"])
        self.assertEqual(self.state.identified_conflicts[0]["resolution"], self.test_resolution)
        
        # Tester avec un ID de conflit invalide
        result = self.state.resolve_conflict("invalid-id", self.test_resolution)
        self.assertFalse(result)

    def test_update_agent_utilization(self):
        """Teste la mise à jour de l'utilisation d'un agent."""
        self.state.update_agent_utilization("agent-001", 0.75)
        self.assertEqual(self.state.tactical_metrics["agent_utilization"]["agent-001"], 0.75)
        
        # Tester avec une utilisation > 1.0
        self.state.update_agent_utilization("agent-001", 1.5)
        self.assertEqual(self.state.tactical_metrics["agent_utilization"]["agent-001"], 1.0)
        
        # Tester avec une utilisation < 0.0
        self.state.update_agent_utilization("agent-001", -0.5)
        self.assertEqual(self.state.tactical_metrics["agent_utilization"]["agent-001"], 0.0)

    def test_log_tactical_action(self):
        """Teste l'enregistrement d'une action tactique."""
        self.state.log_tactical_action(self.test_action)
        self.assertEqual(len(self.state.tactical_actions_log), 1)
        self.assertEqual(self.state.tactical_actions_log[0], self.test_action)

    def test_update_task_completion_rate(self):
        """Teste la mise à jour du taux de complétion des tâches."""
        # Ajouter deux tâches
        self.state.add_task(self.test_task1)
        self.state.add_task(self.test_task2)
        
        # Mettre à jour le statut d'une tâche
        self.state.update_task_status(self.test_task1["id"], "completed")
        
        # Appeler explicitement la méthode de mise à jour
        self.state._update_task_completion_rate()
        
        # Vérifier le taux de complétion
        self.assertEqual(self.state.tactical_metrics["task_completion_rate"], 0.5)
        
        # Cas où il n'y a pas de tâches
        state = TacticalState()
        state._update_task_completion_rate()
        self.assertEqual(state.tactical_metrics["task_completion_rate"], 0.0)

    def test_update_conflict_resolution_rate(self):
        """Teste la mise à jour du taux de résolution des conflits."""
        # Ajouter deux conflits
        self.state.add_conflict(self.test_conflict)
        self.state.add_conflict({
            "id": "conflict-002",
            "description": "Autre conflit",
            "involved_tasks": ["task-001"],
            "severity": "low"
        })
        
        # Résoudre un conflit
        self.state.resolve_conflict(self.test_conflict["id"], self.test_resolution)
        
        # Vérifier le taux de résolution
        self.assertEqual(self.state.tactical_metrics["conflict_resolution_rate"], 0.5)
        
        # Cas où il n'y a pas de conflits
        state = TacticalState()
        state._update_conflict_resolution_rate()
        self.assertEqual(state.tactical_metrics["conflict_resolution_rate"], 1.0)

    def test_get_pending_tasks(self):
        """Teste la récupération des tâches en attente."""
        # Ajouter deux tâches
        self.state.add_task(self.test_task1)
        self.state.add_task(self.test_task2, "in_progress")
        
        # Récupérer les tâches en attente
        pending_tasks = self.state.get_pending_tasks()
        self.assertEqual(len(pending_tasks), 1)
        self.assertEqual(pending_tasks[0], self.test_task1)

    def test_get_tasks_for_agent(self):
        """Teste la récupération des tâches assignées à un agent."""
        # Ajouter deux tâches
        self.state.add_task(self.test_task1)
        self.state.add_task(self.test_task2)
        
        # Assigner les tâches
        self.state.assign_task(self.test_task1["id"], "agent-001")
        self.state.assign_task(self.test_task2["id"], "agent-002")
        
        # Récupérer les tâches pour agent-001
        agent_tasks = self.state.get_tasks_for_agent("agent-001")
        self.assertEqual(len(agent_tasks), 1)
        self.assertEqual(agent_tasks[0]["id"], self.test_task1["id"])
        self.assertEqual(agent_tasks[0]["status"], "pending")
        
        # Mettre à jour le statut et la progression
        self.state.update_task_status(self.test_task1["id"], "in_progress")
        self.state.update_task_progress(self.test_task1["id"], 0.75)
        
        # Vérifier que les changements sont reflétés
        agent_tasks = self.state.get_tasks_for_agent("agent-001")
        self.assertEqual(agent_tasks[0]["status"], "in_progress")
        self.assertEqual(agent_tasks[0]["progress"], 0.75)

    def test_get_task_dependencies(self):
        """Teste la récupération des dépendances d'une tâche."""
        # Ajouter deux tâches
        self.state.add_task(self.test_task1)
        self.state.add_task(self.test_task2)
        
        # Ajouter une dépendance
        self.state.add_task_dependency(self.test_task1["id"], self.test_task2["id"])
        
        # Récupérer les dépendances
        dependencies = self.state.get_task_dependencies(self.test_task1["id"])
        self.assertEqual(len(dependencies), 1)
        self.assertEqual(dependencies[0], self.test_task2["id"])
        
        # Tester avec un ID de tâche invalide
        dependencies = self.state.get_task_dependencies("invalid-id")
        self.assertEqual(len(dependencies), 0)

    def test_get_snapshot(self):
        """Teste la récupération d'un instantané de l'état tactique."""
        # Ajouter des données
        self.state.add_assigned_objective(self.test_objective)
        self.state.add_task(self.test_task1)
        self.state.add_task(self.test_task2, "in_progress")
        self.state.assign_task(self.test_task1["id"], "agent-001")
        self.state.add_conflict(self.test_conflict)
        self.state.resolve_conflict(self.test_conflict["id"], self.test_resolution)
        
        # Récupérer l'instantané
        snapshot = self.state.get_snapshot()
        
        # Vérifier les données
        self.assertEqual(snapshot["objectives_count"], 1)
        self.assertEqual(snapshot["tasks"]["pending"], 1)
        self.assertEqual(snapshot["tasks"]["in_progress"], 1)
        self.assertEqual(snapshot["task_assignments_count"], 1)
        self.assertEqual(snapshot["conflicts"]["total"], 1)
        self.assertEqual(snapshot["conflicts"]["resolved"], 1)

    def test_to_json(self):
        """Teste la conversion de l'état tactique en JSON."""
        # Ajouter des données
        self.state.add_assigned_objective(self.test_objective)
        self.state.add_task(self.test_task1)
        
        # Convertir en JSON
        json_str = self.state.to_json()
        
        # Vérifier que c'est un JSON valide
        json_dict = json.loads(json_str)
        self.assertIsInstance(json_dict, dict)
        self.assertIn("assigned_objectives", json_dict)
        self.assertEqual(len(json_dict["assigned_objectives"]), 1)
        self.assertEqual(json_dict["assigned_objectives"][0], self.test_objective)

    def test_from_json(self):
        """Teste la création d'un état tactique à partir de JSON."""
        # Créer un état avec des données
        original_state = TacticalState()
        original_state.add_assigned_objective(self.test_objective)
        original_state.add_task(self.test_task1)
        original_state.add_task(self.test_task2, "in_progress")
        original_state.assign_task(self.test_task1["id"], "agent-001")
        
        # Convertir en JSON
        json_str = original_state.to_json()
        
        # Créer un nouvel état à partir du JSON
        new_state = TacticalState.from_json(json_str)
        
        # Vérifier que les données sont correctes
        self.assertEqual(len(new_state.assigned_objectives), 1)
        self.assertEqual(new_state.assigned_objectives[0], self.test_objective)
        self.assertEqual(len(new_state.tasks["pending"]), 1)
        self.assertEqual(new_state.tasks["pending"][0], self.test_task1)
        self.assertEqual(len(new_state.tasks["in_progress"]), 1)
        self.assertEqual(new_state.tasks["in_progress"][0], self.test_task2)
        self.assertEqual(new_state.task_assignments[self.test_task1["id"]], "agent-001")
        
        # Tester avec un JSON incomplet
        partial_json = '{"assigned_objectives": []}'
        partial_state = TacticalState.from_json(partial_json)
        self.assertEqual(len(partial_state.assigned_objectives), 0)
        self.assertEqual(len(partial_state.tasks["pending"]), 0)


if __name__ == "__main__":
    unittest.main()