"""
Tests d'intégration pour les agents opérationnels dans l'architecture hiérarchique.

Ce module contient des tests pour valider le fonctionnement des agents adaptés
dans la nouvelle architecture hiérarchique à trois niveaux.
"""

import unittest
import asyncio
import logging
from unittest.mock import MagicMock, patch
import json
import os
import sys
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from argumentiation_analysis.tests.async_test_case import AsyncTestCase
from argumentiation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentiation_analysis.orchestration.hierarchical.operational.agent_registry import OperationalAgentRegistry
from argumentiation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentiation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface
from argumentiation_analysis.orchestration.hierarchical.tactical.state import TacticalState

from argumentiation_analysis.paths import RESULTS_DIR



# Désactiver les logs pendant les tests
logging.basicConfig(level=logging.ERROR)


class TestOperationalAgentsIntegration(AsyncTestCase):
    """Tests d'intégration pour les agents opérationnels."""
    
    async def asyncSetUp(self):
        """Initialise les objets nécessaires pour les tests."""
        # Créer les états
        self.tactical_state = TacticalState()
        self.operational_state = OperationalState()
        
        # Créer l'interface tactique-opérationnelle
        self.interface = TacticalOperationalInterface(self.tactical_state, self.operational_state)
        
        # Créer le gestionnaire opérationnel
        self.manager = OperationalManager(self.operational_state, self.interface)
        await self.manager.start()
        
        # Texte d'exemple pour les tests
        self.sample_text = """
        La vaccination devrait être obligatoire pour tous les enfants. Les vaccins ont été prouvés sûrs par de nombreuses études scientifiques. De plus, la vaccination de masse crée une immunité collective qui protège les personnes vulnérables qui ne peuvent pas être vaccinées pour des raisons médicales.
        """
        
        # Ajouter le texte à l'état tactique
        self.tactical_state.raw_text = self.sample_text
    
    async def asyncTearDown(self):
        """Nettoie les objets après les tests."""
        await self.manager.stop()
    
    async def test_agent_registry_initialization(self):
        """Teste l'initialisation du registre d'agents."""
        registry = OperationalAgentRegistry(self.operational_state)
        
        # Vérifier les types d'agents disponibles
        agent_types = registry.get_agent_types()
        self.assertIn("extract", agent_types)
        self.assertIn("informal", agent_types)
        self.assertIn("pl", agent_types)
        
        # Vérifier que les agents peuvent être créés
        extract_agent = await registry.get_agent("extract")
        self.assertIsNotNone(extract_agent)
        self.assertEqual(extract_agent.name, "ExtractAgent")
        
        # Vérifier les capacités des agents
        capabilities = extract_agent.get_capabilities()
        self.assertIn("text_extraction", capabilities)
    
    @patch("argumentiation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgentAdapter.process_task")
    async def test_extract_agent_task_processing(self, mock_process_task):
        """Teste le traitement d'une tâche par l'agent d'extraction."""
        # Configurer le mock
        mock_result = {
            "id": "result-task-extract-1",
            "task_id": "op-task-extract-1",
            "tactical_task_id": "task-extract-1",
            "status": "completed",
            "outputs": {
                "extracted_segments": [
                    {
                        "extract_id": "extract-1",
                        "source": "sample_text",
                        "start_marker": "La vaccination",
                        "end_marker": "raisons médicales.",
                        "extracted_text": self.sample_text.strip(),
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
        mock_process_task.return_value = mock_result
        
        # Créer une tâche tactique pour l'extraction
        tactical_task = {
            "id": "task-extract-1",
            "description": "Extraire les segments de texte contenant des arguments potentiels",
            "objective_id": "obj-1",
            "estimated_duration": "short",
            "required_capabilities": ["text_extraction"],
            "priority": "high"
        }
        
        # Ajouter la tâche à l'état tactique
        self.tactical_state.add_task(tactical_task)
        
        # Traiter la tâche
        result = await self.manager.process_tactical_task(tactical_task)
        
        # Vérifier que le mock a été appelé
        self.assertTrue(mock_process_task.called)
        
        # Vérifier le résultat
        self.assertEqual(result["task_id"], "task-extract-1")
        self.assertEqual(result["completion_status"], "completed")
        self.assertIn(RESULTS_DIR, result)
        self.assertIn("execution_metrics", result)
    
    @patch("argumentiation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter.InformalAgentAdapter.process_task")
    async def test_informal_agent_task_processing(self, mock_process_task):
        """Teste le traitement d'une tâche par l'agent informel."""
        # Configurer le mock
        mock_result = {
            "id": "result-task-informal-1",
            "task_id": "op-task-informal-1",
            "tactical_task_id": "task-informal-1",
            "status": "completed",
            "outputs": {
                "identified_arguments": [
                    {
                        "extract_id": "extract-1",
                        "source": "sample_text",
                        "premises": [
                            "Les vaccins ont été prouvés sûrs par de nombreuses études scientifiques",
                            "La vaccination de masse crée une immunité collective qui protège les personnes vulnérables"
                        ],
                        "conclusion": "La vaccination devrait être obligatoire pour tous les enfants",
                        "confidence": 0.8
                    }
                ]
            },
            "metrics": {
                "execution_time": 2.0,
                "confidence": 0.8,
                "coverage": 1.0,
                "resource_usage": 0.6
            },
            "issues": []
        }
        mock_process_task.return_value = mock_result
        
        # Créer une tâche tactique pour l'analyse informelle
        tactical_task = {
            "id": "task-informal-1",
            "description": "Identifier les arguments et analyser les sophismes",
            "objective_id": "obj-1",
            "estimated_duration": "medium",
            "required_capabilities": ["argument_identification", "fallacy_detection"],
            "priority": "high"
        }
        
        # Ajouter la tâche à l'état tactique
        self.tactical_state.add_task(tactical_task)
        
        # Traiter la tâche
        result = await self.manager.process_tactical_task(tactical_task)
        
        # Vérifier que le mock a été appelé
        self.assertTrue(mock_process_task.called)
        
        # Vérifier le résultat
        self.assertEqual(result["task_id"], "task-informal-1")
        self.assertEqual(result["completion_status"], "completed")
        self.assertIn(RESULTS_DIR, result)
        self.assertIn("execution_metrics", result)
    
    @patch("argumentiation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter.PLAgentAdapter.process_task")
    async def test_pl_agent_task_processing(self, mock_process_task):
        """Teste le traitement d'une tâche par l'agent de logique propositionnelle."""
        # Configurer le mock
        mock_result = {
            "id": "result-task-pl-1",
            "task_id": "op-task-pl-1",
            "tactical_task_id": "task-pl-1",
            "status": "completed",
            "outputs": {
                "formal_analyses": [
                    {
                        "extract_id": "extract-1",
                        "source": "sample_text",
                        "belief_set": "vaccines_safe\nvaccination_creates_herd_immunity\nherd_immunity_protects_vulnerable\nvaccines_safe && vaccination_creates_herd_immunity && herd_immunity_protects_vulnerable => vaccination_mandatory",
                        "formalism": "propositional_logic",
                        "confidence": 0.8
                    }
                ]
            },
            "metrics": {
                "execution_time": 2.5,
                "confidence": 0.8,
                "coverage": 1.0,
                "resource_usage": 0.7
            },
            "issues": []
        }
        mock_process_task.return_value = mock_result
        
        # Créer une tâche tactique pour l'analyse formelle
        tactical_task = {
            "id": "task-pl-1",
            "description": "Formaliser les arguments en logique propositionnelle et vérifier leur validité",
            "objective_id": "obj-1",
            "estimated_duration": "medium",
            "required_capabilities": ["formal_logic", "validity_checking"],
            "priority": "high"
        }
        
        # Ajouter la tâche à l'état tactique
        self.tactical_state.add_task(tactical_task)
        
        # Traiter la tâche
        result = await self.manager.process_tactical_task(tactical_task)
        
        # Vérifier que le mock a été appelé
        self.assertTrue(mock_process_task.called)
        
        # Vérifier le résultat
        self.assertEqual(result["task_id"], "task-pl-1")
        self.assertEqual(result["completion_status"], "completed")
        self.assertIn(RESULTS_DIR, result)
        self.assertIn("execution_metrics", result)
    
    async def test_agent_selection(self):
        """Teste la sélection de l'agent approprié pour une tâche."""
        registry = OperationalAgentRegistry(self.operational_state)
        
        # Tâche pour l'agent d'extraction
        extract_task = {
            "id": "op-task-extract-1",
            "description": "Extraire les segments de texte contenant des arguments potentiels",
            "required_capabilities": ["text_extraction"],
            "priority": "high"
        }
        
        # Tâche pour l'agent informel
        informal_task = {
            "id": "op-task-informal-1",
            "description": "Identifier les arguments et analyser les sophismes",
            "required_capabilities": ["argument_identification", "fallacy_detection"],
            "priority": "high"
        }
        
        # Tâche pour l'agent de logique propositionnelle
        pl_task = {
            "id": "op-task-pl-1",
            "description": "Formaliser les arguments en logique propositionnelle et vérifier leur validité",
            "required_capabilities": ["formal_logic", "validity_checking"],
            "priority": "high"
        }
        
        # Sélectionner les agents
        extract_agent = await registry.select_agent_for_task(extract_task)
        informal_agent = await registry.select_agent_for_task(informal_task)
        pl_agent = await registry.select_agent_for_task(pl_task)
        
        # Vérifier les agents sélectionnés
        self.assertIsNotNone(extract_agent)
        self.assertEqual(extract_agent.name, "ExtractAgent")
        
        self.assertIsNotNone(informal_agent)
        self.assertEqual(informal_agent.name, "InformalAgent")
        
        self.assertIsNotNone(pl_agent)
        self.assertEqual(pl_agent.name, "PLAgent")
    
    async def test_operational_state_management(self):
        """Teste la gestion de l'état opérationnel."""
        state = OperationalState()
        
        # Ajouter une tâche
        task = {
            "id": "op-task-1",
            "description": "Tâche de test",
            "required_capabilities": ["test"],
            "priority": "medium"
        }
        task_id = state.add_task(task)
        self.assertEqual(task_id, "op-task-1")
        
        # Mettre à jour le statut de la tâche
        success = state.update_task_status(task_id, "in_progress", {"message": "Traitement en cours"})
        self.assertTrue(success)
        
        # Récupérer la tâche
        retrieved_task = state.get_task(task_id)
        self.assertIsNotNone(retrieved_task)
        self.assertEqual(retrieved_task["status"], "in_progress")
        
        # Ajouter un résultat d'analyse
        result_data = {
            "id": "result-1",
            "task_id": task_id,
            "content": "Résultat de test"
        }
        result_id = state.add_analysis_result("test_results", result_data)
        self.assertEqual(result_id, "result-1")
        
        # Ajouter un problème
        issue = {
            "type": "test_issue",
            "description": "Problème de test",
            "severity": "medium",
            "task_id": task_id
        }
        issue_id = state.add_issue(issue)
        self.assertTrue(issue_id.startswith("issue-"))
        
        # Mettre à jour les métriques
        metrics = {
            "execution_time": 1.0,
            "confidence": 0.8,
            "coverage": 1.0
        }
        success = state.update_metrics(task_id, metrics)
        self.assertTrue(success)
        
        # Récupérer les métriques
        retrieved_metrics = state.get_task_metrics(task_id)
        self.assertIsNotNone(retrieved_metrics)
        self.assertEqual(retrieved_metrics["execution_time"], 1.0)
    
    async def test_end_to_end_task_processing(self):
        """Teste le traitement complet d'une tâche de bout en bout."""
        # Cette méthode utilise des mocks pour simuler le comportement des agents
        # mais teste l'intégration complète du gestionnaire opérationnel avec l'interface tactique-opérationnelle
        
        # Créer une tâche tactique
        tactical_task = {
            "id": "task-test-1",
            "description": "Tâche de test pour l'intégration de bout en bout",
            "objective_id": "obj-1",
            "estimated_duration": "short",
            "required_capabilities": ["text_extraction"],  # Utiliser l'agent d'extraction pour ce test
            "priority": "high"
        }
        
        # Ajouter la tâche à l'état tactique
        self.tactical_state.add_task(tactical_task)
        
        # Patcher la méthode process_task de l'agent d'extraction
        with patch("argumentiation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgentAdapter.process_task") as mock_process_task:
            # Configurer le mock
            mock_result = {
                "id": "result-task-test-1",
                "task_id": "op-task-test-1",
                "tactical_task_id": "task-test-1",
                "status": "completed",
                "outputs": {
                    "extracted_segments": [
                        {
                            "extract_id": "extract-1",
                            "source": "sample_text",
                            "start_marker": "La vaccination",
                            "end_marker": "raisons médicales.",
                            "extracted_text": self.sample_text.strip(),
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
            mock_process_task.return_value = mock_result
            
            # Traiter la tâche
            result = await self.manager.process_tactical_task(tactical_task)
            
            # Vérifier que le mock a été appelé
            self.assertTrue(mock_process_task.called)
            
            # Vérifier le résultat
            self.assertEqual(result["task_id"], "task-test-1")
            self.assertEqual(result["completion_status"], "completed")
            self.assertIn(RESULTS_DIR, result)
            self.assertIn("execution_metrics", result)
            
            # Vérifier que les métriques ont été correctement traduites
            self.assertEqual(result["execution_metrics"]["processing_time"], 1.5)
            self.assertEqual(result["execution_metrics"]["confidence_score"], 0.9)


if __name__ == "__main__":
    unittest.main()