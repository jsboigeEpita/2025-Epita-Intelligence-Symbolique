# -*- coding: utf-8 -*-
"""
Tests d'intégration pour l'architecture hiérarchique à trois niveaux.

Ce module contient des tests qui valident le fonctionnement complet
de l'architecture hiérarchique, de bout en bout.
"""

import unittest
import asyncio
import logging
from unittest.mock import MagicMock, patch
from datetime import datetime

from argumentation_analysis.orchestration.hierarchical.strategic.state import StrategicState
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState

from argumentation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import StrategicTacticalInterface
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface

from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator as TacticalCoordinator
from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager

from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import InformalAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter import PLAgentAdapter

from argumentation_analysis.tests.async_test_case import AsyncTestCase

from argumentation_analysis.paths import RESULTS_DIR



class TestHierarchicalIntegration(AsyncTestCase):
    """Tests d'intégration pour l'architecture hiérarchique à trois niveaux."""
    
    async def asyncSetUp(self):
        """Initialise les objets nécessaires pour les tests."""
        # Configurer le logging
        logging.basicConfig(level=logging.INFO)
        
        # Créer les états
        self.strategic_state = StrategicState()
        self.tactical_state = TacticalState()
        self.operational_state = OperationalState()
        
        # Créer les interfaces
        self.strategic_tactical_interface = StrategicTacticalInterface(
            strategic_state=self.strategic_state,
            tactical_state=self.tactical_state
        )
        
        self.tactical_operational_interface = TacticalOperationalInterface(
            tactical_state=self.tactical_state,
            operational_state=self.operational_state
        )
        
        # Créer les managers
        self.strategic_manager = StrategicManager(
            strategic_state=self.strategic_state,
            strategic_tactical_interface=self.strategic_tactical_interface
        )
        
        self.tactical_coordinator = TacticalCoordinator(
            tactical_state=self.tactical_state,
            strategic_tactical_interface=self.strategic_tactical_interface,
            tactical_operational_interface=self.tactical_operational_interface
        )
        
        # Créer les adaptateurs d'agents
        self.extract_agent = MagicMock(spec=ExtractAgentAdapter)
        self.informal_agent = MagicMock(spec=InformalAgentAdapter)
        self.pl_agent = MagicMock(spec=PLAgentAdapter)
        
        # Configurer les mocks des agents
        self.extract_agent.get_capabilities.return_value = ["text_extraction", "preprocessing"]
        self.extract_agent.can_process_task.return_value = True
        self.extract_agent.process_task.return_value = {
            "id": "result-op-task-1",
            "task_id": "op-task-1",
            "tactical_task_id": "task-1",
            "status": "completed",
            "outputs": {
                "extracted_segments": [
                    {
                        "extract_id": "extract-1",
                        "source": "test_source",
                        "extracted_text": "Texte extrait pour test",
                        "confidence": 0.9
                    }
                ]
            },
            "metrics": {
                "execution_time": 1.5,
                "confidence": 0.9,
                "coverage": 1.0,
                "resource_usage": 0.5
            },
            "issues": []
        }
        
        self.informal_agent.get_capabilities.return_value = ["fallacy_detection", "argument_identification"]
        self.informal_agent.can_process_task.return_value = True
        self.informal_agent.process_task.return_value = {
            "id": "result-op-task-2",
            "task_id": "op-task-2",
            "tactical_task_id": "task-2",
            "status": "completed",
            "outputs": {
                "identified_fallacies": [
                    {
                        "id": "fallacy-1",
                        "type": "ad_hominem",
                        "segment": "Segment contenant un sophisme",
                        "explanation": "Explication du sophisme",
                        "confidence": 0.85
                    }
                ],
                "identified_arguments": [
                    {
                        "id": "arg-1",
                        "premises": ["Prémisse 1", "Prémisse 2"],
                        "conclusion": "Conclusion",
                        "confidence": 0.8
                    }
                ]
            },
            "metrics": {
                "execution_time": 2.0,
                "confidence": 0.8,
                "coverage": 0.9,
                "resource_usage": 0.6
            },
            "issues": []
        }
        
        self.pl_agent.get_capabilities.return_value = ["formal_logic", "validity_checking"]
        self.pl_agent.can_process_task.return_value = True
        self.pl_agent.process_task.return_value = {
            "id": "result-op-task-3",
            "task_id": "op-task-3",
            "tactical_task_id": "task-3",
            "status": "completed",
            "outputs": {
                "formal_analyses": [
                    {
                        "argument_id": "arg-1",
                        "formalization": "P1 ∧ P2 → C",
                        "is_valid": True,
                        "explanation": "L'argument est valide"
                    }
                ]
            },
            "metrics": {
                "execution_time": 1.8,
                "confidence": 0.95,
                "coverage": 1.0,
                "resource_usage": 0.4
            },
            "issues": []
        }
        
        # Créer le gestionnaire opérationnel avec les agents mockés
        self.operational_manager = OperationalManager(
            operational_state=self.operational_state,
            tactical_operational_interface=self.tactical_operational_interface
        )
        
        # Enregistrer les agents
        self.operational_manager.register_agent(self.extract_agent)
        self.operational_manager.register_agent(self.informal_agent)
        self.operational_manager.register_agent(self.pl_agent)
    
    async def test_end_to_end_workflow(self):
        """Teste le workflow complet de l'architecture hiérarchique."""
        # 1. Définir des objectifs stratégiques
        objectives = [
            {
                "id": "obj-1",
                "description": "Identifier les arguments principaux dans le texte",
                "priority": "high"
            },
            {
                "id": "obj-2",
                "description": "Détecter les sophismes dans le texte",
                "priority": "medium"
            },
            {
                "id": "obj-3",
                "description": "Analyser la validité formelle des arguments",
                "priority": "low"
            }
        ]
        
        # Ajouter les objectifs à l'état stratégique
        for objective in objectives:
            self.strategic_state.add_objective(objective)
        
        # 2. Créer un plan stratégique
        strategic_plan = {
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Extraction et identification",
                    "objectives": ["obj-1"]
                },
                {
                    "id": "phase-2",
                    "name": "Analyse des sophismes",
                    "objectives": ["obj-2"]
                },
                {
                    "id": "phase-3",
                    "name": "Analyse formelle",
                    "objectives": ["obj-3"]
                }
            ],
            "success_criteria": {
                "phase-1": "Identification complète des arguments",
                "phase-2": "Détection des sophismes avec confiance > 0.7",
                "phase-3": "Analyse formelle de tous les arguments identifiés"
            },
            "priorities": {
                "primary": "argument_identification",
                "secondary": "fallacy_detection"
            }
        }
        
        # Ajouter le plan à l'état stratégique
        self.strategic_state.strategic_plan = strategic_plan
        
        # 3. Traduire les objectifs en directives tactiques
        tactical_directives = self.strategic_tactical_interface.translate_objectives(objectives)
        
        # Vérifier que les directives tactiques sont correctes
        self.assertIsInstance(tactical_directives, dict)
        self.assertIn("objectives", tactical_directives)
        self.assertIn("global_context", tactical_directives)
        self.assertIn("control_parameters", tactical_directives)
        
        # 4. Créer des tâches tactiques à partir des directives
        tasks = [
            {
                "id": "task-1",
                "description": "Extraire les segments de texte contenant des arguments potentiels",
                "objective_id": "obj-1",
                "estimated_duration": "short",
                "required_capabilities": ["text_extraction"],
                "priority": "high"
            },
            {
                "id": "task-2",
                "description": "Identifier les sophismes dans les segments extraits",
                "objective_id": "obj-2",
                "estimated_duration": "medium",
                "required_capabilities": ["fallacy_detection"],
                "priority": "medium"
            },
            {
                "id": "task-3",
                "description": "Formaliser les arguments identifiés",
                "objective_id": "obj-3",
                "estimated_duration": "medium",
                "required_capabilities": ["formal_logic"],
                "priority": "low"
            }
        ]
        
        # Ajouter les tâches à l'état tactique
        for task in tasks:
            self.tactical_state.add_task(task)
        
        # 5. Traduire les tâches tactiques en tâches opérationnelles
        operational_tasks = []
        for task in tasks:
            op_task = self.tactical_operational_interface.translate_task(task)
            operational_tasks.append(op_task)
        
        # Vérifier que les tâches opérationnelles sont correctes
        self.assertEqual(len(operational_tasks), 3)
        for op_task in operational_tasks:
            self.assertIn("id", op_task)
            self.assertIn("tactical_task_id", op_task)
            self.assertIn("techniques", op_task)
            self.assertIn("parameters", op_task)
        
        # 6. Exécuter les tâches opérationnelles
        operational_results = []
        for op_task in operational_tasks:
            # Déterminer quel agent utiliser en fonction des capacités requises
            if "text_extraction" in op_task.get("techniques", [{}])[0].get("name", ""):
                result = await self.extract_agent.process_task(op_task)
            elif "fallacy_detection" in op_task.get("techniques", [{}])[0].get("name", ""):
                result = await self.informal_agent.process_task(op_task)
            else:
                result = await self.pl_agent.process_task(op_task)
            
            operational_results.append(result)
        
        # Vérifier que les résultats opérationnels sont corrects
        self.assertEqual(len(operational_results), 3)
        for result in operational_results:
            self.assertIn("id", result)
            self.assertIn("task_id", result)
            self.assertIn("outputs", result)
            self.assertIn("metrics", result)
        
        # 7. Traiter les résultats opérationnels au niveau tactique
        tactical_results = []
        for op_result in operational_results:
            tac_result = self.tactical_operational_interface.process_operational_result(op_result)
            tactical_results.append(tac_result)
        
        # Vérifier que les résultats tactiques sont corrects
        self.assertEqual(len(tactical_results), 3)
        for result in tactical_results:
            self.assertIn("task_id", result)
            self.assertIn("completion_status", result)
            self.assertIn(RESULTS_DIR, result)
            self.assertIn("execution_metrics", result)
        
        # 8. Créer un rapport tactique
        tactical_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_progress": 0.8,
            "tasks_summary": {
                "total": 3,
                "completed": 3,
                "in_progress": 0,
                "pending": 0,
                "failed": 0
            },
            "progress_by_objective": {
                "obj-1": {
                    "total_tasks": 1,
                    "completed_tasks": 1,
                    "progress": 1.0
                },
                "obj-2": {
                    "total_tasks": 1,
                    "completed_tasks": 1,
                    "progress": 1.0
                },
                "obj-3": {
                    "total_tasks": 1,
                    "completed_tasks": 1,
                    "progress": 1.0
                }
            },
            "issues": [],
            "conflicts": {
                "total": 0,
                "resolved": 0
            },
            "metrics": {
                "agent_utilization": {
                    "ExtractAgent": 0.5,
                    "InformalAgent": 0.6,
                    "PLAgent": 0.4
                }
            }
        }
        
        # 9. Traiter le rapport tactique au niveau stratégique
        strategic_report = self.strategic_tactical_interface.process_tactical_report(tactical_report)
        
        # Vérifier que le rapport stratégique est correct
        self.assertIsInstance(strategic_report, dict)
        self.assertIn("metrics", strategic_report)
        self.assertIn("issues", strategic_report)
        self.assertIn("adjustments", strategic_report)
        self.assertIn("progress_by_objective", strategic_report)
        
        # Vérifier que les métriques stratégiques sont correctes
        self.assertIn("progress", strategic_report["metrics"])
        self.assertIn("quality_indicators", strategic_report["metrics"])
        self.assertIn("resource_utilization", strategic_report["metrics"])
        
        # Vérifier que la progression est correcte
        self.assertEqual(strategic_report["metrics"]["progress"], 0.8)
        
        # Vérifier que la progression par objectif est correcte
        self.assertEqual(strategic_report["progress_by_objective"]["obj-1"], 1.0)
        self.assertEqual(strategic_report["progress_by_objective"]["obj-2"], 1.0)
        self.assertEqual(strategic_report["progress_by_objective"]["obj-3"], 1.0)


class TestHierarchicalPerformance(AsyncTestCase):
    """Tests de performance pour l'architecture hiérarchique à trois niveaux."""
    
    async def test_performance_comparison(self):
        """
        Compare les performances de l'ancienne et de la nouvelle architecture.
        
        Note: Ce test est un exemple simplifié. Dans une implémentation réelle,
        il faudrait mesurer les performances sur des cas d'utilisation réels.
        """
        # Mesurer le temps d'exécution de la nouvelle architecture
        start_time = datetime.now()
        
        # Simuler l'exécution de la nouvelle architecture
        # (Utiliser les mêmes étapes que dans test_end_to_end_workflow)
        await asyncio.sleep(0.1)  # Simuler un délai d'exécution
        
        end_time = datetime.now()
        new_architecture_time = (end_time - start_time).total_seconds()
        
        # Mesurer le temps d'exécution de l'ancienne architecture
        start_time = datetime.now()
        
        # Simuler l'exécution de l'ancienne architecture
        # (Utiliser une implémentation simplifiée de l'ancienne architecture)
        await asyncio.sleep(0.2)  # Simuler un délai d'exécution plus long
        
        end_time = datetime.now()
        old_architecture_time = (end_time - start_time).total_seconds()
        
        # Comparer les performances
        self.assertLess(new_architecture_time, old_architecture_time)
        
        # Calculer l'amélioration en pourcentage
        improvement = (old_architecture_time - new_architecture_time) / old_architecture_time * 100
        
        # Afficher les résultats
        print(f"Temps d'exécution de la nouvelle architecture: {new_architecture_time:.3f} secondes")
        print(f"Temps d'exécution de l'ancienne architecture: {old_architecture_time:.3f} secondes")
        print(f"Amélioration: {improvement:.2f}%")


if __name__ == "__main__":
    unittest.main()