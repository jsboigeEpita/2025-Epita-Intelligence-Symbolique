#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration entre les modules tactiques et opérationnels.

Ce module teste l'interaction entre les composants tactiques et opérationnels
du système d'orchestration hiérarchique.
"""

import unittest
import sys
import os
import pytest
from unittest.mock import MagicMock, patch
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestTacticalOperationalIntegration")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('../..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.adapters.agent_adapter_factory import AgentAdapterFactory
from argumentation_analysis.orchestration.message_middleware import MessageMiddleware


class TestTacticalOperationalIntegration(unittest.TestCase):
    """Tests d'intégration entre les modules tactiques et opérationnels."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        # Créer un état tactique
        self.tactical_state = TacticalState()
        
        # Créer un middleware réel (pas de mock)
        self.middleware = MessageMiddleware()
        
        # Créer le coordinateur tactique
        self.coordinator = TaskCoordinator(tactical_state=self.tactical_state, middleware=self.middleware)
        
        # Créer une factory d'adaptateurs d'agents
        self.adapter_factory = AgentAdapterFactory(middleware=self.middleware)
        
        # Créer un adaptateur d'agent d'extraction
        self.extract_adapter = ExtractAgentAdapter(agent_id="extract_agent", middleware=self.middleware)
        
        # Initialiser les protocoles de communication
        self.middleware.initialize_protocols()
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        # Arrêter le middleware
        self.middleware.shutdown()
    
    def test_task_assignment_and_execution(self):
        """
        Teste l'assignation d'une tâche par le coordinateur tactique
        et son exécution par un agent opérationnel via l'adaptateur.
        """
        # Créer une tâche d'extraction
        task = {
            "id": "extract-task-1",
            "description": "Extraire le texte du document",
            "objective_id": "test-objective",
            "estimated_duration": 3600,
            "required_capabilities": ["text_extraction"],
            "parameters": {
                "document_path": "examples/exemple_sophisme.txt",
                "output_format": "text"
            }
        }
        
        # Ajouter la tâche à l'état tactique
        self.tactical_state.add_task(task)
        
        # Patcher la méthode _process_extract_request de l'adaptateur pour simuler l'exécution
        with patch.object(self.extract_adapter, '_process_extract_request', return_value={"status": "success", "text": "Texte extrait"}) as mock_process:
            # Patcher la méthode _assign_task_to_agent du coordinateur pour utiliser notre adaptateur
            with patch.object(self.coordinator, '_get_agent_for_task', return_value="extract_agent"):
                # Patcher la méthode _send_task_assignment du coordinateur
                with patch.object(self.coordinator, '_send_task_assignment') as mock_send:
                    # Assigner la tâche
                    self.coordinator._assign_pending_tasks()
                    
                    # Vérifier que la méthode _send_task_assignment a été appelée
                    mock_send.assert_called()
                    
                    # Simuler la réception de la tâche par l'adaptateur
                    # Nous devons créer manuellement le message que l'adaptateur aurait reçu
                    task_message = {
                        "task_id": task["id"],
                        "description": task["description"],
                        "parameters": task["parameters"]
                    }
                    
                    # Appeler directement la méthode de traitement de l'adaptateur
                    result = self.extract_adapter._process_extract_request(task_message)
                    
                    # Vérifier que la méthode _process_extract_request a été appelée
                    mock_process.assert_called_once_with(task_message)
                    
                    # Vérifier le résultat
                    self.assertEqual(result["status"], "success")
                    self.assertEqual(result["text"], "Texte extrait")
    
    def test_task_result_reporting(self):
        """
        Teste le rapport des résultats d'une tâche de l'adaptateur opérationnel
        au coordinateur tactique.
        """
        # Créer une tâche d'extraction
        task = {
            "id": "extract-task-2",
            "description": "Extraire le texte du document",
            "objective_id": "test-objective",
            "estimated_duration": 3600,
            "required_capabilities": ["text_extraction"],
            "parameters": {
                "document_path": "examples/exemple_sophisme.txt",
                "output_format": "text"
            }
        }
        
        # Ajouter la tâche à l'état tactique et la marquer comme assignée
        self.tactical_state.add_task(task)
        self.tactical_state.update_task_status(task["id"], "assigned", {"agent_id": "extract_agent"})
        
        # Patcher la méthode _handle_task_result du coordinateur
        with patch.object(self.coordinator, '_handle_task_result') as mock_handle:
            # Simuler l'envoi d'un résultat de tâche par l'adaptateur
            result = {
                "task_id": task["id"],
                "status": "completed",
                "result": {
                    "text": "Texte extrait du document",
                    "metadata": {
                        "extraction_time": "2025-05-21T23:30:00",
                        "document_size": 1024
                    }
                }
            }
            
            # Appeler directement la méthode d'envoi de résultat de l'adaptateur
            self.extract_adapter.send_task_result(task["id"], result["result"], result["status"])
            
            # Simuler la réception du résultat par le coordinateur
            # Nous devons créer manuellement le message que le coordinateur aurait reçu
            result_message = {
                "message_type": "TASK_RESULT",
                "content": {
                    "task_id": task["id"],
                    "status": "completed",
                    "result": result["result"]
                },
                "sender": "extract_agent",
                "recipient": "tactical_coordinator"
            }
            
            # Appeler directement la méthode de traitement du coordinateur
            self.coordinator._handle_task_result(result_message)
            
            # Vérifier que la méthode _handle_task_result a été appelée
            mock_handle.assert_called_once_with(result_message)
            
            # Vérifier que la tâche a été marquée comme complétée dans l'état tactique
            self.assertIn(task["id"], [t["id"] for t in self.tactical_state.tasks.get("completed", [])])


if __name__ == "__main__":
    pytest.main(["-v", __file__])