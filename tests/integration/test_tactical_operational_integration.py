#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests d'intégration entre les modules tactiques et opérationnels.

Ce module teste l'interaction entre les composants tactiques et opérationnels
du système d'orchestration hiérarchique.
"""

import unittest
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import logging

import semantic_kernel as sk
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import TaskCoordinator
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState # Ajouté
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.core.communication import MessageMiddleware
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent # Ajouté

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestTacticalOperationalIntegration")


@pytest.mark.skip(reason="Ce test est obsolète et nécessite une refonte majeure pour refléter l'architecture actuelle avec OperationalManager et la gestion asynchrone.")
class TestTacticalOperationalIntegration(unittest.IsolatedAsyncioTestCase): # Modifié pour IsolatedAsyncioTestCase
    """Tests d'intégration (conceptuels) entre les modules tactiques et opérationnels."""
    
    async def asyncSetUp(self): # Modifié pour asyncSetUp
        """Initialisation asynchrone avant chaque test."""
        self.tactical_state = TacticalState()
        self.middleware = MessageMiddleware()
        self.coordinator = TaskCoordinator(tactical_state=self.tactical_state, middleware=self.middleware)
        
        self.operational_state = MagicMock(spec=OperationalState) # Mock OperationalState
        self.mock_kernel = MagicMock(spec=sk.Kernel)
        self.mock_kernel.invoke = AsyncMock() # Pour les appels de l'agent
        self.llm_service_id = "test_llm_service"

        # Instanciation directe de l'adaptateur
        self.extract_adapter = ExtractAgentAdapter(
            operational_state=self.operational_state,
            middleware=self.middleware,
            agent_id="extract_agent_01" # L'agent_id est maintenant géré par l'OperationalManager
        )
        # L'initialisation de l'agent interne se fait via initialize()
        # Pour les tests, nous allons mocker l'agent interne directement après l'initialisation de l'adaptateur.
        
        # Simuler l'initialisation de l'adaptateur et de son agent interne
        # Normalement, cela serait fait par l'OperationalManager
        with patch.object(ExtractAgentAdapter, '_create_agent', return_value=MagicMock(spec=ExtractAgent)) as mock_create_agent:
            mock_internal_agent = mock_create_agent.return_value
            mock_internal_agent.setup_agent_components = AsyncMock()
            mock_internal_agent.extract_from_name = AsyncMock(return_value={"status": "success", "text": "Texte extrait simulé"})
            
            await self.extract_adapter.initialize(kernel=self.mock_kernel, llm_service_id=self.llm_service_id)
            # Remplacer l'agent réel par un mock après l'initialisation pour contrôler son comportement
            self.extract_adapter.agent = mock_internal_agent


    async def asyncTearDown(self): # Modifié pour asyncTearDown
        """Nettoyage après chaque test."""
        # self.middleware.shutdown() # Si applicable
        pass
    
    async def test_task_assignment_and_execution(self):
        """
        Teste (conceptuellement) l'assignation d'une tâche et son exécution.
        NOTE: Ce test est simplifié et ne reflète pas entièrement le flux via OperationalManager.
        """
        await self.asyncSetUp() # Appel explicite car unittest.TestCase ne le fait pas pour IsolatedAsyncioTestCase

        task_data_for_coordinator = {
            "id": "extract-task-1", "description": "Extraire le texte du document",
            "objective_id": "test-objective", "estimated_duration": 3600,
            "required_capabilities": ["text_extraction"], # Doit correspondre à ExtractAgent.get_agent_capabilities()
            "parameters": {"document_path": "examples/exemple_sophisme.txt", "output_format": "text", "extraction_type": "text_extraction"} # Ajout extraction_type
        }
        self.tactical_state.add_task(task_data_for_coordinator)
        
        # Simuler que le coordinateur assigne la tâche.
        # Dans la vraie implémentation, _assign_pending_tasks publie un message.
        # Ici, on va directement simuler l'appel à l'adaptateur.
        
        # L'OperationalManager recevrait un message et appellerait process_task sur l'adaptateur.
        # On simule cet appel.
        task_payload_for_adapter = {
            "task_id": task_data_for_coordinator["id"],
            "agent_type": "extract", # Ou le type d'agent spécifique
            "parameters": task_data_for_coordinator["parameters"]
        }

        # Mocker la méthode de l'agent qui sera appelée par l'adaptateur
        self.extract_adapter.agent.extract_from_name.return_value = {"status": "success", "text": "Texte extrait par mock"}

        result = await self.extract_adapter.process_task(task_payload_for_adapter)
        
        self.extract_adapter.agent.extract_from_name.assert_called_once_with(
            document_path="examples/exemple_sophisme.txt",
            output_format="text",
            extraction_type="text_extraction" # Assurez-vous que cela correspond à ce que l'agent attend
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["text"], "Texte extrait par mock")
        
        await self.asyncTearDown() # Appel explicite

    async def test_task_result_reporting(self):
        """
        Teste (conceptuellement) le rapport des résultats d'une tâche au coordinateur.
        NOTE: Ce test est simplifié. Normalement, l'OperationalManager enverrait le résultat.
        """
        await self.asyncSetUp() # Appel explicite

        task_id = "extract-task-2"
        task_for_state = {
            "id": task_id, "description": "Extraire le texte du document 2",
            "objective_id": "test-objective-2", "estimated_duration": 1800,
            "required_capabilities": ["text_extraction"],
            "parameters": {"document_path": "examples/another_doc.txt", "output_format": "json", "extraction_type": "entity_extraction"}
        }
        self.tactical_state.add_task(task_for_state)
        self.tactical_state.update_task_status(task_id, "assigned", {"agent_id": self.extract_adapter.agent_id})
        
        # Simuler la réception d'un message de résultat par le coordinateur
        # Ce message serait construit et envoyé par l'OperationalManager via le middleware
        result_payload_from_agent = {
            "entities": [{"type": "PERSON", "text": "John Doe"}],
            "metadata": {"source": "another_doc.txt"}
        }
        
        # Le message que le coordinateur attend via sa méthode _handle_task_result
        # (qui est un callback pour les messages du middleware)
        result_message_for_coordinator = {
            "message_type": "TASK_RESULT", # Défini dans MessageMiddleware ou constantes
            "content": {"task_id": task_id, "status": "completed", "result": result_payload_from_agent},
            "sender": self.extract_adapter.agent_id,
            "recipient": "tactical_coordinator" # Ou l'ID du coordinateur
        }
        
        with patch.object(self.coordinator, '_handle_task_result') as mock_handle_result_on_coordinator:
            # Simuler l'arrivée du message au coordinateur (appel direct de sa méthode de gestion)
            self.coordinator._handle_task_result(result_message_for_coordinator)
            
            mock_handle_result_on_coordinator.assert_called_once_with(result_message_for_coordinator)
        
        # Vérifier que le TacticalState a été mis à jour par _handle_task_result
        updated_task = self.tactical_state.get_task_by_id(task_id)
        self.assertEqual(updated_task["status"], "completed")
        self.assertEqual(updated_task["result"], result_payload_from_agent)
        self.assertIn(task_id, [t["id"] for t in self.tactical_state.tasks.get("completed", [])])
        
        await self.asyncTearDown() # Appel explicite


if __name__ == "__main__":
    pytest.main(["-v", __file__])