# -*- coding: utf-8 -*-
"""
Tests pour l'interface entre les niveaux stratégique et tactique.
"""

import unittest
from unittest.mock import MagicMock, patch
import json
from datetime import datetime

from argumentation_analysis.orchestration.hierarchical.strategic.state import StrategicState
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import StrategicTacticalInterface
from argumentation_analysis.core.communication import (
    MessageMiddleware, StrategicAdapter, TacticalAdapter,
    ChannelType, MessagePriority, Message, MessageType, AgentLevel
)


class TestStrategicTacticalInterface(unittest.TestCase):
    """Tests pour la classe StrategicTacticalInterface."""
    
    def setUp(self):
        """Initialise les objets nécessaires pour les tests."""
        # Créer des mocks pour les états
        self.mock_strategic_state = MagicMock(spec=StrategicState)
        self.mock_tactical_state = MagicMock(spec=TacticalState)
        
        # Créer un mock pour le middleware
        self.mock_middleware = MagicMock(spec=MessageMiddleware)
        
        # Créer des mocks pour les adaptateurs
        self.mock_strategic_adapter = MagicMock(spec=StrategicAdapter)
        self.mock_tactical_adapter = MagicMock(spec=TacticalAdapter)
        
        # Configurer le mock du middleware pour retourner les adaptateurs mockés
        self.mock_middleware.get_adapter.side_effect = lambda agent_id, level: (
            self.mock_strategic_adapter if level == AgentLevel.STRATEGIC else self.mock_tactical_adapter
        )
        
        # Configurer les mocks
        self.mock_strategic_state.strategic_plan = {
            "phases": [
                {
                    "id": "phase-1",
                    "objectives": ["obj-1", "obj-2"]
                },
                {
                    "id": "phase-2",
                    "objectives": ["obj-3"]
                }
            ],
            "success_criteria": {
                "phase-1": "Critères de succès pour la phase 1",
                "phase-2": "Critères de succès pour la phase 2"
            },
            "priorities": {
                "primary": "argument_identification",
                "secondary": "fallacy_detection"
            }
        }
        
        self.mock_strategic_state.global_objectives = [
            {
                "id": "obj-1",
                "description": "Identifier les arguments principaux",
                "priority": "high"
            },
            {
                "id": "obj-2",
                "description": "Détecter les sophismes dans le texte",
                "priority": "medium"
            },
            {
                "id": "obj-3",
                "description": "Analyser la structure logique des arguments",
                "priority": "low"
            }
        ]
        
        self.mock_strategic_state.global_metrics = {
            "progress": 0.4,
            "quality": 0.7,
            "resource_utilization": 0.6
        }
        
        self.mock_strategic_state.resource_allocation = {
            "agent_assignments": {
                "agent-1": ["obj-1"],
                "agent-2": ["obj-2", "obj-3"]
            }
        }
        
        # Créer l'interface avec les mocks
        self.interface = StrategicTacticalInterface(
            strategic_state=self.mock_strategic_state,
            tactical_state=self.mock_tactical_state,
            middleware=self.mock_middleware
        )
        
        # Remplacer les adaptateurs de l'interface par nos mocks
        self.interface.strategic_adapter = self.mock_strategic_adapter
        self.interface.tactical_adapter = self.mock_tactical_adapter
    
    def test_translate_objectives(self):
        """Teste la traduction des objectifs stratégiques en directives tactiques."""
        # Définir les objectifs à traduire
        objectives = [
            {
                "id": "obj-1",
                "description": "Identifier les arguments principaux",
                "priority": "high"
            },
            {
                "id": "obj-2",
                "description": "Détecter les sophismes dans le texte",
                "priority": "medium"
            }
        ]
        
        # Appeler la méthode à tester
        result = self.interface.translate_objectives(objectives)
        
        # Vérifier que la méthode send_directive a été appelée
        self.mock_strategic_adapter.send_directive.assert_called()
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("objectives", result)
        self.assertIn("global_context", result)
        self.assertIn("control_parameters", result)
        
        # Vérifier que les objectifs ont été enrichis
        self.assertEqual(len(result["objectives"]), 2)
        for obj in result["objectives"]:
            self.assertIn("context", obj)
            self.assertIn("global_plan_phase", obj["context"])
            self.assertIn("related_objectives", obj["context"])
            self.assertIn("priority_level", obj["context"])
            self.assertIn("success_criteria", obj["context"])
    
    def test_process_tactical_report(self):
        """Teste le traitement d'un rapport tactique."""
        # Définir un rapport tactique
        tactical_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_progress": 0.6,
            "tasks_summary": {
                "total": 10,
                "completed": 6,
                "in_progress": 2,
                "pending": 1,
                "failed": 1
            },
            "progress_by_objective": {
                "obj-1": {
                    "total_tasks": 5,
                    "completed_tasks": 4,
                    "progress": 0.8
                },
                "obj-2": {
                    "total_tasks": 3,
                    "completed_tasks": 2,
                    "progress": 0.7
                },
                "obj-3": {
                    "total_tasks": 2,
                    "completed_tasks": 0,
                    "progress": 0.1
                }
            },
            "issues": [
                {
                    "type": "blocked_task",
                    "description": "Tâche bloquée par une dépendance échouée",
                    "severity": "high",
                    "task_id": "task-1",
                    "objective_id": "obj-3",
                    "blocked_by": ["task-2"]
                },
                {
                    "type": "conflict",
                    "description": "Conflit entre résultats",
                    "severity": "medium",
                    "involved_tasks": ["task-3", "task-4"]
                }
            ],
            "conflicts": {
                "total": 2,
                "resolved": 1
            },
            "metrics": {
                "agent_utilization": {
                    "agent-1": 0.9,
                    "agent-2": 0.5
                }
            }
        }
        
        # Configurer le mock pour get_pending_reports
        self.mock_strategic_adapter.get_pending_reports.return_value = []
        
        # Appeler la méthode à tester
        result = self.interface.process_tactical_report(tactical_report)
        
        # Vérifier que la méthode get_pending_reports a été appelée
        self.mock_strategic_adapter.get_pending_reports.assert_called_once()
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("metrics", result)
        self.assertIn("issues", result)
        self.assertIn("adjustments", result)
        self.assertIn("progress_by_objective", result)
        
        # Vérifier les métriques
        self.assertIn("progress", result["metrics"])
        self.assertIn("quality_indicators", result["metrics"])
        self.assertIn("resource_utilization", result["metrics"])
        
        # Vérifier les problèmes stratégiques
        self.assertIsInstance(result["issues"], list)
        self.assertTrue(len(result["issues"]) > 0)
        
        # Vérifier les ajustements
        self.assertIn("plan_updates", result["adjustments"])
        self.assertIn("resource_reallocation", result["adjustments"])
        self.assertIn("objective_modifications", result["adjustments"])
        
        # Vérifier que la méthode update_global_metrics a été appelée
        self.mock_strategic_state.update_global_metrics.assert_called_once()
    
    def test_determine_phase_for_objective(self):
        """Teste la détermination de la phase pour un objectif."""
        # Définir un objectif
        objective = {
            "id": "obj-1",
            "description": "Identifier les arguments principaux",
            "priority": "high"
        }
        
        # Appeler la méthode à tester
        result = self.interface._determine_phase_for_objective(objective)
        
        # Vérifier le résultat
        self.assertEqual(result, "phase-1")
        
        # Tester avec un objectif inconnu
        unknown_objective = {
            "id": "obj-unknown",
            "description": "Objectif inconnu",
            "priority": "medium"
        }
        
        result = self.interface._determine_phase_for_objective(unknown_objective)
        self.assertEqual(result, "unknown")
    
    def test_find_related_objectives(self):
        """Teste la recherche d'objectifs liés."""
        # Définir un objectif
        objective = {
            "id": "obj-1",
            "description": "Identifier les arguments principaux",
            "priority": "high"
        }
        
        # Définir tous les objectifs
        all_objectives = [
            objective,
            {
                "id": "obj-2",
                "description": "Détecter les sophismes dans les arguments",
                "priority": "medium"
            },
            {
                "id": "obj-3",
                "description": "Analyser la structure logique",
                "priority": "low"
            }
        ]
        
        # Appeler la méthode à tester
        result = self.interface._find_related_objectives(objective, all_objectives)
        
        # Vérifier le résultat
        self.assertIsInstance(result, list)
        self.assertIn("obj-2", result)  # Car "arguments" est présent dans les deux descriptions
        self.assertNotIn("obj-3", result)  # Car pas de mots-clés communs
    
    def test_translate_priority(self):
        """Teste la traduction de la priorité stratégique."""
        # Tester avec différentes priorités
        high_result = self.interface._translate_priority("high")
        medium_result = self.interface._translate_priority("medium")
        low_result = self.interface._translate_priority("low")
        unknown_result = self.interface._translate_priority("unknown")
        
        # Vérifier les résultats
        self.assertIsInstance(high_result, dict)
        self.assertIn("urgency", high_result)
        self.assertIn("resource_allocation", high_result)
        self.assertIn("quality_threshold", high_result)
        
        self.assertEqual(high_result["urgency"], "high")
        self.assertEqual(medium_result["urgency"], "medium")
        self.assertEqual(low_result["urgency"], "low")
        
        # La priorité inconnue devrait être traitée comme "medium"
        self.assertEqual(unknown_result["urgency"], "medium")
    
    def test_extract_success_criteria(self):
        """Teste l'extraction des critères de succès."""
        # Définir un objectif
        objective = {
            "id": "obj-1",
            "description": "Identifier les arguments principaux",
            "priority": "high"
        }
        
        # Appeler la méthode à tester
        result = self.interface._extract_success_criteria(objective)
        
        # Vérifier le résultat
        self.assertIsInstance(result, dict)
        self.assertIn("criteria", result)
        self.assertIn("threshold", result)
        self.assertEqual(result["criteria"], "Critères de succès pour la phase 1")
        
        # Tester avec un objectif sans critères de succès définis
        unknown_objective = {
            "id": "obj-unknown",
            "description": "Objectif inconnu",
            "priority": "medium"
        }
        
        result = self.interface._extract_success_criteria(unknown_objective)
        self.assertIsInstance(result, dict)
        self.assertIn("criteria", result)
        self.assertIn("threshold", result)
        # Devrait utiliser les critères par défaut
        self.assertEqual(result["criteria"], "Complétion satisfaisante de l'objectif")
    
    def test_determine_current_phase(self):
        """Teste la détermination de la phase actuelle."""
        # Configurer le mock pour différentes valeurs de progression
        
        # Phase initiale (progress < 0.3)
        self.mock_strategic_state.global_metrics = {"progress": 0.2}
        result = self.interface._determine_current_phase()
        self.assertEqual(result, "initial")
        
        # Phase intermédiaire (0.3 <= progress < 0.7)
        self.mock_strategic_state.global_metrics = {"progress": 0.5}
        result = self.interface._determine_current_phase()
        self.assertEqual(result, "intermediate")
        
        # Phase finale (progress >= 0.7)
        self.mock_strategic_state.global_metrics = {"progress": 0.8}
        result = self.interface._determine_current_phase()
        self.assertEqual(result, "final")
    
    def test_determine_primary_focus(self):
        """Teste la détermination du focus principal."""
        # Le focus devrait être déterminé en fonction des objectifs
        result = self.interface._determine_primary_focus()
        
        # Avec les objectifs définis dans setUp, le focus devrait être "argument_identification"
        self.assertEqual(result, "argument_identification")
        
        # Modifier les objectifs pour changer le focus
        self.mock_strategic_state.global_objectives = [
            {
                "id": "obj-1",
                "description": "Détecter les sophismes dans le texte",
                "priority": "high"
            },
            {
                "id": "obj-2",
                "description": "Détecter d'autres sophismes",
                "priority": "high"
            },
            {
                "id": "obj-3",
                "description": "Identifier quelques arguments",
                "priority": "low"
            }
        ]
        
        result = self.interface._determine_primary_focus()
        self.assertEqual(result, "fallacy_detection")


    def test_request_tactical_status(self):
        """Teste la demande de statut tactique."""
        # Configurer le mock pour request_tactical_status
        expected_response = {
            "status": "ok",
            "progress": 0.5
        }
        self.mock_strategic_adapter.request_tactical_status.return_value = expected_response
        
        # Appeler la méthode à tester
        result = self.interface.request_tactical_status(timeout=5.0)
        
        # Vérifier le résultat
        self.assertEqual(result, expected_response)
        
        # Vérifier que la méthode request_tactical_status a été appelée
        self.mock_strategic_adapter.request_tactical_status.assert_called_once_with(
            recipient_id="tactical_coordinator",
            timeout=5.0
        )
    
    def test_send_strategic_adjustment(self):
        """Teste l'envoi d'un ajustement stratégique."""
        # Définir un ajustement
        adjustment = {
            "plan_updates": {
                "phase-1": {
                    "priority": "high"
                }
            },
            "urgent": True
        }
        
        # Configurer le mock pour send_directive
        self.mock_strategic_adapter.send_directive.return_value = "message-id-123"
        
        # Appeler la méthode à tester
        result = self.interface.send_strategic_adjustment(adjustment)
        
        # Vérifier le résultat
        self.assertTrue(result)
        
        # Vérifier que la méthode send_directive a été appelée
        self.mock_strategic_adapter.send_directive.assert_called_once_with(
            directive_type="strategic_adjustment",
            content=adjustment,
            recipient_id="tactical_coordinator",
            priority=MessagePriority.HIGH
        )
    
    def test_map_priority_to_enum(self):
        """Teste la conversion de priorité textuelle en énumération."""
        # Tester avec différentes priorités
        self.assertEqual(self.interface._map_priority_to_enum("high"), MessagePriority.HIGH)
        self.assertEqual(self.interface._map_priority_to_enum("medium"), MessagePriority.NORMAL)
        self.assertEqual(self.interface._map_priority_to_enum("low"), MessagePriority.LOW)
        self.assertEqual(self.interface._map_priority_to_enum("unknown"), MessagePriority.NORMAL)


if __name__ == "__main__":
    unittest.main()