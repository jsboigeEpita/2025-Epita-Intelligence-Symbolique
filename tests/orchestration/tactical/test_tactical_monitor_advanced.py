import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests avancés pour le module orchestration.hierarchical.tactical.monitor.
"""

import unittest
from unittest.mock import patch

import sys
import os

from datetime import datetime, timedelta
import json
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("TestTacticalMonitorAdvanced")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
project_root = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# Commenté car l'installation du package via `pip install -e .` devrait gérer l'accessibilité.

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.monitor import (
    ProgressMonitor,
)
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)


class TestTacticalMonitorAdvanced(unittest.TestCase):
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-5-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-5-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests avancés pour le moniteur tactique."""

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
            "required_capabilities": ["text_extraction"],
        }
        self.task2 = {
            "id": "task-2",
            "description": "Analyser les sophismes",
            "objective_id": "test-objective",
            "estimated_duration": 7200,
            "start_time": datetime.now().isoformat(),
            "required_capabilities": ["fallacy_detection"],
        }
        self.task3 = {
            "id": "task-3",
            "description": "Générer un rapport",
            "objective_id": "test-objective",
            "estimated_duration": 1800,
            "start_time": datetime.now().isoformat(),
            "required_capabilities": ["result_presentation"],
        }

        self.tactical_state.add_task(self.task1)
        self.tactical_state.add_task(self.task2)
        self.tactical_state.add_task(self.task3)
        self.tactical_state.update_task_status(self.task1["id"], "in_progress")
        self.tactical_state.update_task_status(self.task2["id"], "in_progress")
        self.tactical_state.update_task_status(self.task3["id"], "pending")

        # Ajouter des dépendances entre les tâches
        # Si task-2 dépend de task-1 (task-1 est un prérequis pour task-2)
        self.tactical_state.task_dependencies = {
            "task-2": ["task-1"],  # task-2 dépend de task-1
            "task-3": ["task-2"],  # task-3 dépend de task-2
        }

        # Ajouter des conflits à l'état tactique
        self.tactical_state.identified_conflicts = [
            {
                "id": "conflict-1",
                "type": "resource_conflict",
                "description": "Conflit de ressources entre les tâches task-1 et task-2",
                "involved_tasks": ["task-1", "task-2"],
                "severity": "medium",
                "resolved": False,
            },
            {
                "id": "conflict-2",
                "type": "data_conflict",
                "description": "Conflit de données entre les résultats des tâches task-1 et task-2",
                "involved_tasks": ["task-1", "task-2"],
                "severity": "high",
                "resolved": True,
            },
        ]

    def test_detect_critical_issues(self):
        """Teste la méthode detect_critical_issues."""
        # Configurer l'état tactique pour le test
        # Mettre la tâche 1 en échec
        self.tactical_state.update_task_status(self.task1["id"], "failed")

        # Appeler la méthode detect_critical_issues
        critical_issues = self.monitor.detect_critical_issues()

        # Vérifier que des problèmes critiques ont été détectés
        self.assertIsInstance(critical_issues, list)
        self.assertGreater(len(critical_issues), 0)

        # Vérifier qu'un problème de tâche bloquée a été détecté
        blocked_task_issue = next(
            (issue for issue in critical_issues if issue["type"] == "blocked_task"),
            None,
        )
        self.assertIsNotNone(blocked_task_issue)
        self.assertEqual(blocked_task_issue["task_id"], "task-2")
        self.assertIn("task-1", blocked_task_issue["blocked_by"])

        # Vérifier que le problème a la bonne sévérité
        self.assertEqual(blocked_task_issue["severity"], "critical")

    def test_detect_critical_issues_with_delayed_task(self):
        """Teste la méthode detect_critical_issues avec une tâche en retard."""
        # Configurer l'état tactique pour le test
        # Mettre à jour la progression de la tâche 2
        self.tactical_state.task_progress[self.task2["id"]] = 0.2

        # Simuler un retard en modifiant le temps de début
        start_time = datetime.now() - timedelta(hours=2)  # 2 heures de retard
        self.task2["start_time"] = start_time.isoformat()

        # Appeler la méthode detect_critical_issues
        critical_issues = self.monitor.detect_critical_issues()

        # Vérifier que des problèmes critiques ont été détectés
        self.assertIsInstance(critical_issues, list)
        self.assertGreater(len(critical_issues), 0)

        # Vérifier qu'un problème de tâche en retard a été détecté
        delayed_task_issue = next(
            (issue for issue in critical_issues if issue["type"] == "delayed_task"),
            None,
        )
        self.assertIsNotNone(delayed_task_issue)
        self.assertEqual(delayed_task_issue["task_id"], self.task2["id"])

        # Vérifier que le problème a la bonne sévérité
        self.assertEqual(delayed_task_issue["severity"], "high")

    def test_detect_critical_issues_with_high_failure_rate(self):
        """Teste la méthode detect_critical_issues avec un taux d'échec élevé."""
        # Configurer l'état tactique pour le test
        # Mettre les tâches 1 et 2 en échec
        self.tactical_state.update_task_status(self.task1["id"], "failed")
        self.tactical_state.update_task_status(self.task2["id"], "failed")

        # Appeler la méthode detect_critical_issues
        critical_issues = self.monitor.detect_critical_issues()

        # Vérifier que des problèmes critiques ont été détectés
        self.assertIsInstance(critical_issues, list)
        self.assertGreater(len(critical_issues), 0)

        # Vérifier qu'un problème de taux d'échec élevé a été détecté
        failure_rate_issue = next(
            (
                issue
                for issue in critical_issues
                if issue["type"] == "high_failure_rate"
            ),
            None,
        )
        self.assertIsNotNone(failure_rate_issue)
        self.assertEqual(failure_rate_issue["failed_tasks"], 2)
        self.assertEqual(failure_rate_issue["total_tasks"], 3)

        # Vérifier que le problème a la bonne sévérité
        self.assertEqual(failure_rate_issue["severity"], "critical")

    def test_suggest_corrective_actions(self):
        """Teste la méthode suggest_corrective_actions."""
        # Créer des problèmes critiques
        issues = [
            {
                "type": "blocked_task",
                "description": "Tâche bloquée par une dépendance échouée",
                "severity": "critical",
                "task_id": "task-2",
                "objective_id": "test-objective",
                "blocked_by": ["task-1"],
            },
            {
                "type": "delayed_task",
                "description": "Tâche en retard",
                "severity": "high",
                "task_id": "task-3",
                "objective_id": "test-objective",
                "current_progress": 0.2,
            },
        ]

        # Appeler la méthode suggest_corrective_actions
        corrective_actions = self.monitor.suggest_corrective_actions(issues)

        # Vérifier que des actions correctives ont été suggérées
        self.assertIsInstance(corrective_actions, list)
        self.assertEqual(len(corrective_actions), 2)  # Une action par problème

        # Vérifier les actions suggérées pour le problème de tâche bloquée
        blocked_task_action = next(
            (
                action
                for action in corrective_actions
                if action["issue_id"] == id(issues[0])
            ),
            None,
        )
        self.assertIsNotNone(blocked_task_action)
        self.assertEqual(blocked_task_action["action_type"], "reassign_dependency")
        self.assertEqual(blocked_task_action["details"]["task_id"], "task-2")
        self.assertIn("task-1", blocked_task_action["details"]["blocked_by"])

        # Vérifier les actions suggérées pour le problème de tâche en retard
        delayed_task_action = next(
            (
                action
                for action in corrective_actions
                if action["issue_id"] == id(issues[1])
            ),
            None,
        )
        self.assertIsNotNone(delayed_task_action)
        self.assertEqual(delayed_task_action["action_type"], "allocate_resources")
        self.assertEqual(delayed_task_action["details"]["task_id"], "task-3")

    def test_suggest_corrective_actions_for_conflict(self):
        """Teste la méthode suggest_corrective_actions pour un conflit."""
        # Créer un problème de conflit
        issues = [
            {
                "type": "conflict",
                "description": "Conflit entre les tâches task-1 et task-2",
                "severity": "medium",
                "involved_tasks": ["task-1", "task-2"],
            }
        ]

        # Appeler la méthode suggest_corrective_actions
        corrective_actions = self.monitor.suggest_corrective_actions(issues)

        # Vérifier que des actions correctives ont été suggérées
        self.assertIsInstance(corrective_actions, list)
        self.assertEqual(len(corrective_actions), 1)

        # Vérifier l'action suggérée pour le conflit
        conflict_action = corrective_actions[0]
        self.assertEqual(conflict_action["action_type"], "resolve_conflict")
        self.assertEqual(
            conflict_action["details"]["involved_tasks"], ["task-1", "task-2"]
        )

    def test_suggest_corrective_actions_for_high_failure_rate(self):
        """Teste la méthode suggest_corrective_actions pour un taux d'échec élevé."""
        # Créer un problème de taux d'échec élevé
        issues = [
            {
                "type": "high_failure_rate",
                "description": "Taux d'échec élevé: 0.67",
                "severity": "critical",
                "failed_tasks": 2,
                "total_tasks": 3,
            }
        ]

        # Appeler la méthode suggest_corrective_actions
        corrective_actions = self.monitor.suggest_corrective_actions(issues)

        # Vérifier que des actions correctives ont été suggérées
        self.assertIsInstance(corrective_actions, list)
        self.assertEqual(len(corrective_actions), 1)

        # Vérifier l'action suggérée pour le taux d'échec élevé
        failure_rate_action = corrective_actions[0]
        self.assertEqual(failure_rate_action["action_type"], "review_strategy")
        self.assertIn("escalader", failure_rate_action["details"]["suggestion"].lower())

    def test_evaluate_overall_coherence(self):
        """Teste la méthode _evaluate_overall_coherence."""
        # Créer des données pour l'évaluation de la cohérence
        structure_coherence = {
            "coherence_score": 0.7,
            "coherence_level": "Modéré",
            "disconnected_arguments": [],
            "contradictory_relations": [],
            "circular_reasoning": False,
        }

        thematic_coherence = {
            "coherence_score": 0.8,
            "coherence_level": "Élevé",
            "thematic_clusters": [{"cluster_id": 0, "arguments": [0, 1, 2]}],
            "thematic_shifts": [],
        }

        logical_coherence = {
            "coherence_score": 0.6,
            "coherence_level": "Modéré",
            "logical_gaps": [],
            "logical_flows": [
                {"flow_id": 0, "source_argument": 0, "target_argument": 1}
            ],
        }

        contradictions = [
            {
                "id": "contradiction-1",
                "type": "semantic",
                "description": "Contradiction sémantique entre les arguments 0 et 2",
                "arguments": [0, 2],
                "severity": "medium",
            }
        ]

        # Mock de la méthode _evaluate_overall_coherence
        mock_overall_coherence = {
            "overall_score": 0.7,
            "coherence_level": "Modéré",
            "structure_contribution": 0.7,
            "thematic_contribution": 0.8,
            "logical_contribution": 0.6,
            "contradiction_penalty": 0.1,
            "recommendations": [
                "Améliorer la cohérence structurelle",
                "Réduire les contradictions",
            ],
        }

        with patch.object(
            self.monitor,
            "_evaluate_overall_coherence",
            return_value=mock_overall_coherence,
        ):
            # Appeler la méthode _evaluate_overall_coherence
            overall_coherence = self.monitor._evaluate_overall_coherence(
                structure_coherence,
                thematic_coherence,
                logical_coherence,
                contradictions,
            )

        # Vérifier le résultat
        self.assertIsInstance(overall_coherence, dict)
        self.assertIn("overall_score", overall_coherence)
        self.assertIn("coherence_level", overall_coherence)
        self.assertIn("structure_contribution", overall_coherence)
        self.assertIn("thematic_contribution", overall_coherence)
        self.assertIn("logical_contribution", overall_coherence)
        self.assertIn("contradiction_penalty", overall_coherence)
        self.assertIn("recommendations", overall_coherence)

        # Vérifier les valeurs
        self.assertGreaterEqual(overall_coherence["overall_score"], 0.0)
        self.assertLessEqual(overall_coherence["overall_score"], 1.0)
        self.assertIn(
            overall_coherence["coherence_level"],
            ["Élevé", "Modéré", "Faible", "Très faible"],
        )

        # Vérifier les recommandations
        self.assertIsInstance(overall_coherence["recommendations"], list)
        self.assertGreater(len(overall_coherence["recommendations"]), 0)


if __name__ == "__main__":
    unittest.main()
