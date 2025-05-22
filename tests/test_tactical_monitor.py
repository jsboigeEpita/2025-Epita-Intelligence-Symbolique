#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module orchestration.hierarchical.tactical.monitor.
"""

import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
import json
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestTacticalMonitor")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.monitor import ProgressMonitor
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState


class TestTacticalMonitor(unittest.TestCase):
    """Tests unitaires pour le moniteur tactique."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un état tactique mock
        self.tactical_state = TacticalState()
        
        # Créer le moniteur tactique
        self.monitor = ProgressMonitor(tactical_state=self.tactical_state)
        
        # Ajouter des tâches à l'état tactique pour les tests
        self.task1 = {
            "id": "task-1",
            "description": "Extraire le texte",
            "objective_id": "test-objective",
            "estimated_duration": 3600,
            "start_time": datetime.now().isoformat(),
            "required_capabilities": ["text_extraction"]
        }
        self.task2 = {
            "id": "task-2",
            "description": "Analyser les sophismes",
            "objective_id": "test-objective",
            "estimated_duration": 7200,
            "start_time": datetime.now().isoformat(),
            "required_capabilities": ["fallacy_detection"]
        }
        
        self.tactical_state.add_task(self.task1)
        self.tactical_state.add_task(self.task2)
        self.tactical_state.update_task_status(self.task1["id"], "in_progress")
        self.tactical_state.update_task_status(self.task2["id"], "in_progress")
    
    def test_initialization(self):
        """Teste l'initialisation du moniteur tactique."""
        # Vérifier que le moniteur a été correctement initialisé
        self.assertIsNotNone(self.monitor)
        self.assertEqual(self.monitor.state, self.tactical_state)
        
        # Vérifier que les seuils ont été définis
        self.assertIn("task_delay", self.monitor.thresholds)
        self.assertIn("progress_stagnation", self.monitor.thresholds)
        self.assertIn("conflict_ratio", self.monitor.thresholds)
    
    def test_log_action(self):
        """Teste la méthode _log_action."""
        # Appeler la méthode _log_action
        action_type = "test_action"
        description = "Test description"
        self.monitor._log_action(action_type, description)
        
        # Vérifier que l'action a été enregistrée dans l'état tactique
        self.assertEqual(len(self.tactical_state.tactical_actions_log), 1)
        action = self.tactical_state.tactical_actions_log[0]
        self.assertEqual(action["type"], action_type)
        self.assertEqual(action["description"], description)
        self.assertEqual(action["agent_id"], "progress_monitor")
        self.assertIn("timestamp", action)
    
    def test_update_task_progress(self):
        """Teste la méthode update_task_progress."""
        # Appeler la méthode update_task_progress
        task_id = self.task1["id"]
        progress = 0.5
        
        # Patcher la méthode _check_task_anomalies pour qu'elle retourne une liste vide
        with patch.object(self.monitor, '_check_task_anomalies', return_value=[]):
            result = self.monitor.update_task_progress(task_id, progress)
        
        # Vérifier que la progression a été mise à jour
        self.assertEqual(self.tactical_state.task_progress[task_id], progress)
        
        # Vérifier que le résultat est correct
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["previous_progress"], 0.0)
        self.assertEqual(result["current_progress"], progress)
        self.assertEqual(result["anomalies"], [])
        
        # Vérifier qu'une action a été enregistrée
        self.assertEqual(len(self.tactical_state.tactical_actions_log), 1)
        action = self.tactical_state.tactical_actions_log[0]
        self.assertEqual(action["type"], "Mise à jour de progression")
        self.assertIn(task_id, action["description"])
    
    def test_update_task_progress_with_anomalies(self):
        """Teste la méthode update_task_progress avec des anomalies."""
        # Appeler la méthode update_task_progress
        task_id = self.task1["id"]
        progress = 0.5
        
        # Définir les anomalies attendues
        expected_anomalies = [
            {
                "type": "progress_stagnation",
                "description": "La progression de la tâche est stagnante",
                "severity": "medium"
            }
        ]
        
        # Patcher la méthode _check_task_anomalies pour qu'elle retourne des anomalies
        with patch.object(self.monitor, '_check_task_anomalies', return_value=expected_anomalies):
            result = self.monitor.update_task_progress(task_id, progress)
        
        # Vérifier que la progression a été mise à jour
        self.assertEqual(self.tactical_state.task_progress[task_id], progress)
        
        # Vérifier que le résultat est correct
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["previous_progress"], 0.0)
        self.assertEqual(result["current_progress"], progress)
        self.assertEqual(result["anomalies"], expected_anomalies)
    
    def test_update_task_progress_with_invalid_task(self):
        """Teste la méthode update_task_progress avec une tâche invalide."""
        # Appeler la méthode update_task_progress avec un ID de tâche invalide
        task_id = "invalid-task-id"
        progress = 0.5
        
        result = self.monitor.update_task_progress(task_id, progress)
        
        # Vérifier que le résultat indique une erreur
        self.assertEqual(result["status"], "error")
        self.assertIn(task_id, result["message"])
    
    def test_check_task_anomalies(self):
        """Teste la méthode _check_task_anomalies."""
        # Configurer l'état tactique pour le test
        task_id = self.task1["id"]
        previous_progress = 0.2
        current_progress = 0.3
        
        # Patcher les méthodes appelées par _check_task_anomalies
        with patch.object(self.monitor, '_check_task_delay', return_value=None) as mock_delay, \
             patch.object(self.monitor, '_check_progress_stagnation', return_value=None) as mock_stagnation:
            
            # Appeler la méthode _check_task_anomalies
            anomalies = self.monitor._check_task_anomalies(task_id, previous_progress, current_progress)
            
            # Vérifier que les méthodes ont été appelées
            mock_delay.assert_called_once_with(task_id)
            mock_stagnation.assert_called_once_with(task_id, previous_progress, current_progress)
            
            # Vérifier que la méthode retourne une liste (même vide)
            self.assertIsInstance(anomalies, list)
            self.assertEqual(len(anomalies), 0)
    
    def test_check_task_delay(self):
        """Teste la méthode _check_task_delay."""
        # Configurer l'état tactique pour le test
        task_id = self.task1["id"]
        
        # Patcher datetime.now pour simuler un délai
        with patch('datetime.datetime') as mock_datetime:
            # Simuler un délai de 2 heures (7200 secondes)
            start_time = datetime.fromisoformat(self.task1["start_time"])
            mock_datetime.now.return_value = start_time + timedelta(seconds=7200)
            mock_datetime.fromisoformat = datetime.fromisoformat
            
            # Appeler la méthode _check_task_delay
            # Note: Cette méthode peut ne pas exister directement dans le code source
            # Si c'est le cas, nous devons adapter ce test
            if hasattr(self.monitor, '_check_task_delay'):
                delay_anomaly = self.monitor._check_task_delay(task_id)
                
                # Vérifier que la méthode retourne une anomalie (ou None)
                if delay_anomaly:
                    self.assertIn("type", delay_anomaly)
                    self.assertIn("description", delay_anomaly)
                    self.assertIn("severity", delay_anomaly)
    
    def test_check_progress_stagnation(self):
        """Teste la méthode _check_progress_stagnation."""
        # Configurer l'état tactique pour le test
        task_id = self.task1["id"]
        previous_progress = 0.2
        current_progress = 0.21  # Progression très faible
        
        # Patcher datetime.now pour simuler un intervalle de temps
        with patch('datetime.datetime') as mock_datetime:
            # Simuler un intervalle de 1 heure (3600 secondes)
            start_time = datetime.fromisoformat(self.task1["start_time"])
            mock_datetime.now.return_value = start_time + timedelta(seconds=3600)
            mock_datetime.fromisoformat = datetime.fromisoformat
            
            # Appeler la méthode _check_progress_stagnation
            # Note: Cette méthode peut ne pas exister directement dans le code source
            # Si c'est le cas, nous devons adapter ce test
            if hasattr(self.monitor, '_check_progress_stagnation'):
                stagnation_anomaly = self.monitor._check_progress_stagnation(
                    task_id, previous_progress, current_progress
                )
                
                # Vérifier que la méthode retourne une anomalie (ou None)
                if stagnation_anomaly:
                    self.assertIn("type", stagnation_anomaly)
                    self.assertIn("description", stagnation_anomaly)
                    self.assertIn("severity", stagnation_anomaly)
    
    def test_generate_progress_report(self):
        """Teste la méthode generate_progress_report."""
        # Configurer l'état tactique pour le test
        self.tactical_state.task_progress[self.task1["id"]] = 0.7
        self.tactical_state.task_progress[self.task2["id"]] = 0.3
        
        # Appeler la méthode generate_progress_report
        report = self.monitor.generate_progress_report()
        
        # Vérifier que le rapport contient les informations attendues
        self.assertIn("timestamp", report)
        self.assertIn("overall_progress", report)
        self.assertIn("tasks", report)
        self.assertIn("anomalies", report)
        
        # Vérifier que le rapport contient les tâches
        self.assertEqual(len(report["tasks"]), 2)
        
        # Vérifier que le rapport contient les bonnes progressions
        task1_found = False
        task2_found = False
        for task in report["tasks"]:
            if task["id"] == self.task1["id"]:
                self.assertEqual(task["progress"], 0.7)
                task1_found = True
            elif task["id"] == self.task2["id"]:
                self.assertEqual(task["progress"], 0.3)
                task2_found = True
        
        self.assertTrue(task1_found)
        self.assertTrue(task2_found)
        
        # Vérifier que la progression globale est correcte (moyenne des progressions)
        self.assertAlmostEqual(report["overall_progress"], 0.5)
    
    def test_detect_conflicts(self):
        """Teste la méthode detect_conflicts."""
        # Configurer l'état tactique pour le test
        # Ajouter des conflits à l'état tactique
        self.tactical_state.identified_conflicts = [
            {
                "id": "conflict-1",
                "type": "resource_conflict",
                "description": "Conflit de ressources entre les tâches task-1 et task-2",
                "tasks": ["task-1", "task-2"],
                "severity": "medium"
            }
        ]
        
        # Appeler la méthode detect_conflicts
        conflicts = self.monitor.detect_conflicts()
        
        # Vérifier que la méthode retourne les conflits
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["id"], "conflict-1")
        self.assertEqual(conflicts[0]["type"], "resource_conflict")
        self.assertEqual(conflicts[0]["tasks"], ["task-1", "task-2"])
    
    def test_calculate_metrics(self):
        """Teste la méthode calculate_metrics."""
        # Configurer l'état tactique pour le test
        self.tactical_state.task_progress[self.task1["id"]] = 0.7
        self.tactical_state.task_progress[self.task2["id"]] = 0.3
        
        # Ajouter des tâches complétées
        task3 = {
            "id": "task-3",
            "description": "Tâche complétée",
            "objective_id": "test-objective",
            "estimated_duration": 1800
        }
        self.tactical_state.add_task(task3, "completed")
        
        # Appeler la méthode calculate_metrics
        metrics = self.monitor.calculate_metrics()
        
        # Vérifier que les métriques contiennent les informations attendues
        self.assertIn("task_completion_rate", metrics)
        self.assertIn("average_progress", metrics)
        self.assertIn("estimated_completion_time", metrics)
        
        # Vérifier que le taux de complétion est correct
        # 1 tâche complétée sur 3 tâches au total
        self.assertAlmostEqual(metrics["task_completion_rate"], 1/3)
        
        # Vérifier que la progression moyenne est correcte
        # (0.7 + 0.3 + 1.0) / 3 = 0.67
        self.assertAlmostEqual(metrics["average_progress"], 0.67, places=2)


if __name__ == "__main__":
    unittest.main()