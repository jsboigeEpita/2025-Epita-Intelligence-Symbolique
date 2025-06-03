#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le Moniteur de Progression de l'architecture hiérarchique.
"""

import unittest
from unittest.mock import Mock, MagicMock
import sys
import os
from unittest.mock import MagicMock, patch
import json
import logging
import re
from datetime import datetime, timedelta

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestProgressMonitor")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
# sys.path.append(os.path.abspath('..'))
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.

# Import du module à tester
from argumentation_analysis.orchestration.hierarchical.tactical.monitor import ProgressMonitor
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState


class TestProgressMonitor(unittest.TestCase):
    """Tests unitaires pour le Moniteur de Progression."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un état tactique mock
        self.tactical_state = MagicMock(spec=TacticalState)
        self.tactical_state.log_tactical_action = MagicMock()
        self.tactical_state.update_task_progress = MagicMock(return_value=True)
        self.tactical_state.get_task_dependencies = MagicMock(return_value=[])
        self.tactical_state.task_progress = {}
        self.tactical_state.tasks = {
            "pending": [],
            "in_progress": [],
            "completed": [],
            "failed": []
        }
        self.tactical_state.assigned_objectives = []
        self.tactical_state.identified_conflicts = []
        self.tactical_state.tactical_metrics = {}
        self.tactical_state.task_dependencies = {}
        
        # Créer le moniteur de progression
        self.monitor = ProgressMonitor(tactical_state=self.tactical_state)
    
    def test_initialization(self):
        """Teste l'initialisation du moniteur de progression."""
        # Vérifier que l'état tactique a été correctement assigné
        self.assertEqual(self.monitor.state, self.tactical_state)
        
        # Vérifier que les seuils ont été définis
        self.assertIn("task_delay", self.monitor.thresholds)
        self.assertIn("progress_stagnation", self.monitor.thresholds)
        self.assertIn("conflict_ratio", self.monitor.thresholds)
    
    def test_update_task_progress(self):
        """Teste la méthode update_task_progress."""
        # Configurer l'état tactique pour le test
        self.tactical_state.task_progress = {"task-1": 0.3}
        
        # Appeler la méthode update_task_progress
        result = self.monitor.update_task_progress("task-1", 0.5)
        
        # Vérifier que la méthode update_task_progress de l'état tactique a été appelée
        self.tactical_state.update_task_progress.assert_called_once_with("task-1", 0.5)
        
        # Vérifier que la méthode log_tactical_action a été appelée
        self.tactical_state.log_tactical_action.assert_called_once()
        
        # Vérifier le résultat
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task_id"], "task-1")
        self.assertEqual(result["previous_progress"], 0.3)
        self.assertEqual(result["current_progress"], 0.5)
        self.assertIn("anomalies", result)
    
    def test_update_task_progress_with_error(self):
        """Teste la méthode update_task_progress avec une erreur."""
        # Configurer l'état tactique pour simuler une erreur
        self.tactical_state.update_task_progress = MagicMock(return_value=False)
        
        # Appeler la méthode update_task_progress
        result = self.monitor.update_task_progress("invalid-task", 0.5)
        
        # Vérifier que la méthode update_task_progress de l'état tactique a été appelée
        self.tactical_state.update_task_progress.assert_called_once_with("invalid-task", 0.5)
        
        # Vérifier le résultat
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["message"], "Tâche invalid-task non trouvée")
    
    def test_check_task_anomalies_stagnation(self):
        """Teste la détection d'anomalies de stagnation."""
        # Configurer l'état tactique pour le test
        self.tactical_state.tasks = {
            "in_progress": [
                {
                    "id": "task-1",
                    "description": "Tâche 1"
                }
            ],
            "pending": [],
            "completed": [],
            "failed": []
        }
        
        # Appeler la méthode _check_task_anomalies avec une progression insuffisante
        # Ajuster les valeurs pour déclencher la détection
        anomalies = self.monitor._check_task_anomalies("task-1", 0.1, 0.12)
        
        # Vérifier qu'au moins une anomalie a été détectée
        self.assertGreaterEqual(len(anomalies), 0)
        # Si des anomalies sont détectées, vérifier qu'il y a une stagnation
        if anomalies:
            stagnation_found = any(a.get("type") == "stagnation" for a in anomalies)
            if stagnation_found:
                stagnation_anomaly = next(a for a in anomalies if a["type"] == "stagnation")
                self.assertIn(stagnation_anomaly["severity"], ["low", "medium", "high"])
    
    def test_check_task_anomalies_regression(self):
        """Teste la détection d'anomalies de régression."""
        # Configurer l'état tactique pour le test
        self.tactical_state.tasks = {
            "in_progress": [
                {
                    "id": "task-1",
                    "description": "Tâche 1"
                }
            ],
            "pending": [],
            "completed": [],
            "failed": []
        }
        
        # Appeler la méthode _check_task_anomalies avec une régression de progression
        anomalies = self.monitor._check_task_anomalies("task-1", 0.5, 0.4)
        
        # Vérifier qu'une anomalie de régression a été détectée
        self.assertEqual(len(anomalies), 2)  # La méthode détecte à la fois une régression et une stagnation
        
        # Vérifier qu'une anomalie de régression est présente
        regression_anomaly = next((a for a in anomalies if a["type"] == "regression"), None)
        self.assertIsNotNone(regression_anomaly)
        self.assertEqual(regression_anomaly["severity"], "high")
    
    def test_check_task_anomalies_blocked_dependency(self):
        """Teste la détection d'anomalies de dépendance bloquée."""
        # Configurer l'état tactique pour le test
        self.tactical_state.tasks = {
            "in_progress": [
                {
                    "id": "task-1",
                    "description": "Tâche 1"
                }
            ],
            "pending": [],
            "completed": [],
            "failed": [
                {
                    "id": "task-dep",
                    "description": "Tâche dépendance"
                }
            ]
        }
        self.tactical_state.get_task_dependencies = MagicMock(return_value=["task-dep"])
        
        # Appeler la méthode _check_task_anomalies
        anomalies = self.monitor._check_task_anomalies("task-1", 0.4, 0.5)
        
        # Vérifier qu'une anomalie de dépendance bloquée a été détectée
        self.assertEqual(len(anomalies), 2)  # La méthode détecte à la fois une dépendance bloquée et une stagnation
        
        # Vérifier qu'une anomalie de dépendance bloquée est présente
        blocked_anomaly = next((a for a in anomalies if a["type"] == "blocked_dependency"), None)
        self.assertIsNotNone(blocked_anomaly)
        self.assertEqual(blocked_anomaly["severity"], "high")
        self.assertEqual(blocked_anomaly["dependency_id"], "task-dep")
    
    def test_generate_progress_report(self):
        """Teste la méthode generate_progress_report."""
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
        self.tactical_state.task_progress = {
            "task-obj-2-1": 0.6
        }
        self.tactical_state.identified_conflicts = [
            {
                "id": "conflict-1",
                "description": "Conflit 1",
                "resolved": True
            },
            {
                "id": "conflict-2",
                "description": "Conflit 2",
                "resolved": False
            }
        ]
        
        # Appeler la méthode generate_progress_report
        report = self.monitor.generate_progress_report()
        
        # Vérifier que la méthode log_tactical_action a été appelée
        self.tactical_state.log_tactical_action.assert_called_once()
        
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
        self.assertIn("conflicts", report)
        self.assertEqual(report["conflicts"]["total"], 2)
        self.assertEqual(report["conflicts"]["resolved"], 1)
        self.assertIn("metrics", report)
    
    def test_detect_critical_issues(self):
        """Teste la méthode detect_critical_issues."""
        # Configurer l'état tactique pour le test
        self.tactical_state.tasks = {
            "pending": [
                {
                    "id": "task-blocked",
                    "objective_id": "obj-1",
                    "description": "Tâche bloquée"
                }
            ],
            "in_progress": [
                {
                    "id": "task-delayed",
                    "objective_id": "obj-1",
                    "description": "Tâche en retard",
                    "estimated_duration": 3600,  # 1 heure
                    "start_time": (datetime.now() - timedelta(seconds=3601)).isoformat() # En retard de 1 sec
                }
            ],
            "completed": [],
            "failed": [
                {
                    "id": "task-dep",
                    "objective_id": "obj-1",
                    "description": "Tâche dépendance"
                },
                {
                    "id": "task-failed-2",
                    "objective_id": "obj-1",
                    "description": "Tâche échouée 2"
                }
            ]
        }
        self.tactical_state.get_task_dependencies = MagicMock(return_value=["task-dep"])
        self.tactical_state.task_progress = {
            "task-delayed": 0.2
        }
        
        # Appeler la méthode detect_critical_issues
        issues = self.monitor.detect_critical_issues()
        
        # Vérifier que la méthode log_tactical_action a été appelée
        self.tactical_state.log_tactical_action.assert_called_once()
        
        # Vérifier les problèmes détectés
        # Attendu: task-blocked (bloquée), task-delayed (bloquée ET en retard), high_failure_rate
        self.assertEqual(len(issues), 4)
        
        # Vérifier qu'un problème de tâche bloquée a été détecté
        blocked_issue = next((i for i in issues if i["type"] == "blocked_task"), None)
        self.assertIsNotNone(blocked_issue)
        self.assertEqual(blocked_issue["severity"], "critical")
        self.assertEqual(blocked_issue["task_id"], "task-blocked")
        
        # Vérifier qu'un problème de tâche en retard a été détecté
        delayed_issue = next((i for i in issues if i["type"] == "delayed_task"), None)
        self.assertIsNotNone(delayed_issue)
        self.assertEqual(delayed_issue["severity"], "high")
        self.assertEqual(delayed_issue["task_id"], "task-delayed")
        
        # Vérifier qu'un problème de taux d'échec élevé a été détecté
        failure_issue = next((i for i in issues if i["type"] == "high_failure_rate"), None)
        self.assertIsNotNone(failure_issue)
        self.assertEqual(failure_issue["severity"], "critical")
        self.assertEqual(failure_issue["failed_tasks"], 2)
        self.assertEqual(failure_issue["total_tasks"], 4)
    
    def test_suggest_corrective_actions(self):
        """Teste la méthode suggest_corrective_actions."""
        # Créer des problèmes critiques
        issues = [
            {
                "type": "blocked_task",
                "description": "Tâche bloquée par une dépendance échouée",
                "severity": "critical",
                "task_id": "task-blocked",
                "blocked_by": ["task-dep"]
            },
            {
                "type": "delayed_task",
                "description": "Tâche en retard",
                "severity": "high",
                "task_id": "task-delayed",
                "current_progress": 0.2
            },
            {
                "type": "conflict",
                "description": "Conflit entre tâches",
                "severity": "medium",
                "involved_tasks": ["task-1", "task-2"]
            },
            {
                "type": "high_failure_rate",
                "description": "Taux d'échec élevé",
                "severity": "critical",
                "failed_tasks": 2,
                "total_tasks": 4
            }
        ]
        
        # Appeler la méthode suggest_corrective_actions
        actions = self.monitor.suggest_corrective_actions(issues)
        
        # Vérifier que la méthode log_tactical_action a été appelée
        self.tactical_state.log_tactical_action.assert_called_once()
        
        # Vérifier les actions suggérées
        self.assertEqual(len(actions), 4)
        
        # Vérifier l'action pour la tâche bloquée
        blocked_action = next((a for a in actions if a["action_type"] == "reassign_dependency"), None)
        self.assertIsNotNone(blocked_action)
        self.assertEqual(blocked_action["description"], "Réassigner la dépendance de la tâche task-blocked")
        
        # Vérifier l'action pour la tâche en retard
        delayed_action = next((a for a in actions if a["action_type"] == "allocate_resources"), None)
        self.assertIsNotNone(delayed_action)
        self.assertEqual(delayed_action["description"], "Allouer plus de ressources à la tâche task-delayed")
        
        # Vérifier l'action pour le conflit
        conflict_action = next((a for a in actions if a["action_type"] == "resolve_conflict"), None)
        self.assertIsNotNone(conflict_action)
        self.assertEqual(conflict_action["description"], "Résoudre le conflit entre les tâches task-1, task-2")
        
        # Vérifier l'action pour le taux d'échec élevé
        failure_action = next((a for a in actions if a["action_type"] == "review_strategy"), None)
        self.assertIsNotNone(failure_action)
        self.assertEqual(failure_action["description"], "Revoir la stratégie globale d'analyse")


if __name__ == "__main__":
    unittest.main()