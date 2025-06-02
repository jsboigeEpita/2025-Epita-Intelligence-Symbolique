# -*- coding: utf-8 -*-
"""
Tests d'intégration pour les interactions entre les différents niveaux hiérarchiques.

Ce module contient des tests d'intégration qui vérifient les interactions entre
les niveaux stratégique, tactique et opérationnel de l'architecture hiérarchique.
"""

import unittest
import asyncio
import logging
from unittest.mock import MagicMock, patch
from datetime import datetime

# Utiliser la fonction setup_import_paths pour résoudre les problèmes d'imports relatifs
from argumentation_analysis.tests import setup_import_paths
setup_import_paths()

from argumentation_analysis.orchestration.hierarchical.strategic.state import StrategicState
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState

from argumentation_analysis.orchestration.hierarchical.interfaces.strategic_tactical import StrategicTacticalInterface
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface

from argumentation_analysis.orchestration.hierarchical.strategic.manager import StrategicManager
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TacticalCoordinator
from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager

from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter import InformalAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter import PLAgentAdapter

from argumentation_analysis.tests.async_test_case import AsyncTestCase


class TestHierarchicalInteraction(AsyncTestCase):
    """Tests d'intégration pour les interactions entre les niveaux hiérarchiques."""
    
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
    
    async def test_strategic_to_tactical_communication(self):
        """Teste la communication du niveau stratégique vers le niveau tactique."""
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
                }
            ],
            "success_criteria": {
                "phase-1": "Identification complète des arguments",
                "phase-2": "Détection des sophismes avec confiance > 0.7"
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
        
        # Vérifier que les objectifs ont été correctement traduits
        self.assertEqual(len(tactical_directives["objectives"]), 2)
        self.assertEqual(tactical_directives["objectives"][0]["id"], "obj-1")
        self.assertEqual(tactical_directives["objectives"][1]["id"], "obj-2")
        
        # 4. Vérifier que les directives ont été ajoutées à l'état tactique
        self.tactical_state.update_directives(tactical_directives)
        self.assertIsNotNone(self.tactical_state.directives)
        self.assertEqual(len(self.tactical_state.directives["objectives"]), 2)

    async def test_tactical_to_operational_communication(self):
        """Teste la communication du niveau tactique vers le niveau opérationnel."""
        # 1. Créer des tâches tactiques
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
            }
        ]
        
        # Ajouter les tâches à l'état tactique
        for task in tasks:
            self.tactical_state.add_task(task)
        
        # 2. Traduire les tâches tactiques en tâches opérationnelles
        operational_tasks = []
        for task in tasks:
            op_task = self.tactical_operational_interface.translate_task(task)
            operational_tasks.append(op_task)
        
        # Vérifier que les tâches opérationnelles sont correctes
        self.assertEqual(len(operational_tasks), 2)
        for op_task in operational_tasks:
            self.assertIn("id", op_task)
            self.assertIn("tactical_task_id", op_task)
            self.assertIn("techniques", op_task)
            self.assertIn("parameters", op_task)
        
        # 3. Ajouter les tâches opérationnelles à l'état opérationnel
        for op_task in operational_tasks:
            self.operational_state.add_task(op_task)
        
        # Vérifier que les tâches ont été ajoutées à l'état opérationnel
        self.assertEqual(len(self.operational_state.tasks), 2)
        self.assertIn(operational_tasks[0]["id"], self.operational_state.tasks)
        self.assertIn(operational_tasks[1]["id"], self.operational_state.tasks)

    async def test_operational_to_tactical_communication(self):
        """Teste la communication du niveau opérationnel vers le niveau tactique."""
        # 1. Créer une tâche tactique
        task = {
            "id": "task-1",
            "description": "Extraire les segments de texte contenant des arguments potentiels",
            "objective_id": "obj-1",
            "estimated_duration": "short",
            "required_capabilities": ["text_extraction"],
            "priority": "high"
        }
        
        # Ajouter la tâche à l'état tactique
        self.tactical_state.add_task(task)
        
        # 2. Traduire la tâche tactique en tâche opérationnelle
        op_task = self.tactical_operational_interface.translate_task(task)
        
        # Ajouter la tâche opérationnelle à l'état opérationnel
        self.operational_state.add_task(op_task)
        
        # 3. Exécuter la tâche opérationnelle
        result = await self.extract_agent.process_task(op_task)
        
        # 4. Traiter le résultat opérationnel au niveau tactique
        tactical_result = self.tactical_operational_interface.process_operational_result(result)
        
        # Vérifier que le résultat tactique est correct
        self.assertIn("task_id", tactical_result)
        self.assertEqual(tactical_result["task_id"], "task-1")
        self.assertIn("completion_status", tactical_result)
        self.assertEqual(tactical_result["completion_status"], "completed")
        
        # 5. Ajouter le résultat à l'état tactique
        self.tactical_state.add_result(tactical_result)
        
        # Vérifier que le résultat a été ajouté à l'état tactique
        self.assertIn("task-1", self.tactical_state.results)
        self.assertEqual(self.tactical_state.results["task-1"]["completion_status"], "completed")

    async def test_tactical_to_strategic_communication(self):
        """Teste la communication du niveau tactique vers le niveau stratégique."""
        # 1. Créer un rapport tactique
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
        
        # 2. Traiter le rapport tactique au niveau stratégique
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
        
        # 3. Ajouter le rapport à l'état stratégique
        self.strategic_state.update_progress_report(strategic_report)
        
        # Vérifier que le rapport a été ajouté à l'état stratégique
        self.assertIsNotNone(self.strategic_state.progress_report)
        self.assertEqual(self.strategic_state.progress_report["metrics"]["progress"], 0.8)

    async def test_full_hierarchical_interaction(self):
        """Teste l'interaction complète entre les trois niveaux hiérarchiques."""
        # 1. Niveau stratégique: Définir des objectifs
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
            }
        ]
        
        for objective in objectives:
            self.strategic_state.add_objective(objective)
        
        # 2. Niveau stratégique -> Niveau tactique: Traduire les objectifs en directives
        tactical_directives = self.strategic_tactical_interface.translate_objectives(objectives)
        self.tactical_state.update_directives(tactical_directives)
        
        # 3. Niveau tactique: Créer des tâches
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
            }
        ]
        
        for task in tasks:
            self.tactical_state.add_task(task)
        
        # 4. Niveau tactique -> Niveau opérationnel: Traduire les tâches
        operational_tasks = []
        for task in tasks:
            op_task = self.tactical_operational_interface.translate_task(task)
            operational_tasks.append(op_task)
            self.operational_state.add_task(op_task)
        
        # 5. Niveau opérationnel: Exécuter les tâches
        operational_results = []
        for op_task in operational_tasks:
            if "text_extraction" in op_task.get("techniques", [{}])[0].get("name", ""):
                result = await self.extract_agent.process_task(op_task)
            else:
                result = await self.informal_agent.process_task(op_task)
            operational_results.append(result)
            self.operational_state.add_result(result)
        
        # 6. Niveau opérationnel -> Niveau tactique: Traiter les résultats
        tactical_results = []
        for op_result in operational_results:
            tac_result = self.tactical_operational_interface.process_operational_result(op_result)
            tactical_results.append(tac_result)
            self.tactical_state.add_result(tac_result)
        
        # 7. Niveau tactique: Créer un rapport
        tactical_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_progress": 1.0,
            "tasks_summary": {
                "total": 2,
                "completed": 2,
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
                    "InformalAgent": 0.6
                }
            }
        }
        
        # 8. Niveau tactique -> Niveau stratégique: Traiter le rapport
        strategic_report = self.strategic_tactical_interface.process_tactical_report(tactical_report)
        self.strategic_state.update_progress_report(strategic_report)
        
        # 9. Niveau stratégique: Évaluer les résultats et ajuster le plan si nécessaire
        self.strategic_state.evaluate_objectives()
        
        # Vérifier que tous les objectifs sont marqués comme atteints
        for objective_id in ["obj-1", "obj-2"]:
            self.assertTrue(self.strategic_state.is_objective_achieved(objective_id))
        
        # Vérifier que le rapport de progression indique 100%
        self.assertEqual(self.strategic_state.progress_report["metrics"]["progress"], 1.0)


if __name__ == "__main__":
    unittest.main()