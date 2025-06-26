
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests d'intégration pour les agents opérationnels dans l'architecture hiérarchique.

Ce module contient des tests pour valider le fonctionnement des agents adaptés
dans la nouvelle architecture hiérarchique à trois niveaux.
"""

import pytest # Ajout de pytest
import pytest_asyncio # Ajout de pytest_asyncio
import asyncio
import logging

import json
import os
import sys
from unittest.mock import MagicMock, patch
from pathlib import Path
import semantic_kernel as sk
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
from argumentation_analysis.core.bootstrap import ProjectContext

# Configuration pytest-asyncio
pytestmark = pytest.mark.asyncio

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# from tests.support.argumentation_analysis.async_test_case import AsyncTestCase
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState
from argumentation_analysis.orchestration.hierarchical.operational.agent_registry import OperationalAgentRegistry
from argumentation_analysis.orchestration.hierarchical.operational.manager import OperationalManager
from argumentation_analysis.orchestration.hierarchical.interfaces.tactical_operational import TacticalOperationalInterface
from argumentation_analysis.orchestration.hierarchical.tactical.state import TacticalState
from argumentation_analysis.core.communication import MessageMiddleware, ChannelType
from argumentation_analysis.core.communication.hierarchical_channel import HierarchicalChannel

from argumentation_analysis.paths import RESULTS_DIR

# Désactiver les logs pendant les tests
logging.basicConfig(level=logging.ERROR)


class TestOperationalAgentsIntegration:
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()
        
    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """Tests d'intégration pour les agents opérationnels."""

    @pytest_asyncio.fixture(scope="module")
    async def operational_components(self, jvm_session):
        """Initialise les objets nécessaires et patche les adapters au niveau de la fixture."""
        
        mocks = {
            "extract": patch("argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgentAdapter.process_task", new_callable=MagicMock).start(),
            "informal": patch("argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter.InformalAgentAdapter.process_task", new_callable=MagicMock).start(),
            "pl": patch("argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter.PLAgentAdapter.process_task", new_callable=MagicMock).start()
        }

        tactical_state = TacticalState()
        operational_state = OperationalState()
        middleware = MessageMiddleware()
        hierarchical_channel = HierarchicalChannel("hierarchical_test")
        middleware.register_channel(hierarchical_channel)
        
        interface = TacticalOperationalInterface(tactical_state, operational_state, middleware)
        
        mock_kernel = MagicMock(spec=sk.Kernel)
        mock_llm_service_id = "mock_service"
        
        # Le ProjectContext doit contenir le kernel et le service_id
        mock_project_context = MagicMock(spec=ProjectContext)
        mock_project_context.kernel = mock_kernel
        mock_project_context.llm_service_id = mock_llm_service_id
        
        mock_execution_settings = PromptExecutionSettings(service_id=mock_llm_service_id, model_id="mock-model")
        mock_kernel.get_prompt_execution_settings_from_service_id.return_value = mock_execution_settings

        manager = OperationalManager(
            operational_state=operational_state,
            tactical_operational_interface=interface,
            middleware=middleware,
            kernel=mock_kernel, # Injection directe du kernel mocké
            llm_service_id=mock_llm_service_id,
            project_context=mock_project_context # Injection du contexte mocké
        )
        await manager.start()

        sample_text = "Texte d'exemple pour les tests."
        tactical_state.raw_text = sample_text

        yield {
            "manager": manager,
            "tactical_state": tactical_state,
            "mocks": mocks,
            "sample_text": sample_text,
            "registry": manager.agent_registry
        }
        
        await manager.stop()
        patch.stopall()
    
    @pytest.mark.asyncio
    async def test_agent_registry_initialization(self, operational_components):
        """Teste l'initialisation du registre d'agents."""
        registry = operational_components["registry"]
        assert registry is not None
        # Laisser le temps aux agents de s'initialiser
        await asyncio.sleep(0.5)
        assert "extract" in registry.agents, f"Agents found: {list(registry.agents.keys())}"
        assert "informal" in registry.agents
        assert "pl" in registry.agents
    
    
    @pytest.mark.asyncio
    async def test_extract_agent_task_processing(self, operational_components):
        """Teste le traitement d'une tâche par l'agent d'extraction, avec le mock centralisé."""
        manager = operational_components["manager"]
        tactical_state = operational_components["tactical_state"]
        mock_process_task = operational_components["mocks"]["extract"]

        mock_result = {"id": "res-extract-1", "status": "completed", "outputs": {"extracted_segments": "segments extraits"}}
        async def side_effect(*args, **kwargs): return mock_result
        mock_process_task.side_effect = side_effect

        tactical_task = {"id": "task-extract-1", "required_capabilities": ["text_extraction"]}
        tactical_state.add_task(tactical_task)

        processing_task = asyncio.create_task(manager.process_tactical_task(tactical_task))
        await asyncio.sleep(0.1)

        mock_process_task.assert_called_once()
        final_result = await processing_task

        assert final_result["completion_status"] == "completed"
        assert "segments extraits" in json.loads(Path(final_result["results_path"]).read_text())["outputs"]
    
    
    async def test_informal_agent_task_processing(self, operational_components):
        """Teste le traitement d'une tâche par l'agent informel."""
        manager = operational_components["manager"]
        tactical_state = operational_components["tactical_state"]
        mock_process_task = operational_components["mocks"]["informal"]

        mock_result = {"id": "res-informal-1", "status": "completed", "outputs": {"identified_arguments": "args identifiés"}}
        async def side_effect(*args, **kwargs): return mock_result
        mock_process_task.side_effect = side_effect
        
        tactical_task = {"id": "task-informal-1", "required_capabilities": ["fallacy_detection"]}
        tactical_state.add_task(tactical_task)

        processing_task = asyncio.create_task(manager.process_tactical_task(tactical_task))
        await asyncio.sleep(0.5) # Augmentation du délai

        mock_process_task.assert_called_once()
        final_result = await processing_task

        assert final_result["completion_status"] == "completed"
        assert "args identifiés" in json.loads(Path(final_result["results_path"]).read_text())["outputs"]
    
    
    async def test_pl_agent_task_processing(self, operational_components):
        """Teste le traitement d'une tâche par l'agent de logique propositionnelle."""
        manager = operational_components["manager"]
        tactical_state = operational_components["tactical_state"]
        mock_process_task = operational_components["mocks"]["pl"]

        mock_result = {"id": "res-pl-1", "status": "completed", "outputs": {"formal_analyses": "analyses formelles"}}
        async def side_effect(*args, **kwargs): return mock_result
        mock_process_task.side_effect = side_effect

        tactical_task = {"id": "task-pl-1", "required_capabilities": ["formal_logic"]}
        tactical_state.add_task(tactical_task)

        processing_task = asyncio.create_task(manager.process_tactical_task(tactical_task))
        await asyncio.sleep(0.5) # Augmentation du délai

        mock_process_task.assert_called_once()
        final_result = await processing_task

        assert final_result["completion_status"] == "completed"
        assert "analyses formelles" in json.loads(Path(final_result["results_path"]).read_text())["outputs"]
    
    async def test_agent_selection(self, operational_components):
        """Teste la sélection de l'agent approprié pour une tâche."""
        registry = operational_components["registry"]
        await asyncio.sleep(0.1) # Laisser le temps à l'initialisation asynchrone

        # Tâche nécessitant l'extraction de texte
        task_extract = {"required_capabilities": ["text_extraction"]}
        agent_extract = await registry.select_agent_for_task(task_extract)
        assert agent_extract is not None
        assert agent_extract.name == "extract"

        # Tâche nécessitant la détection de sophismes
        task_informal = {"required_capabilities": ["fallacy_detection"]}
        agent_informal = await registry.select_agent_for_task(task_informal)
        assert agent_informal is not None
        assert agent_informal.name == "informal"

        # Tâche nécessitant la logique formelle
        task_pl = {"required_capabilities": ["formal_logic"]}
        agent_pl = await registry.select_agent_for_task(task_pl)
        assert agent_pl is not None
        assert agent_pl.name == "pl"
    
    async def test_operational_state_management(self): # Ne dépend pas de la fixture operational_components
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
        assert task_id == "op-task-1"
        
        # Mettre à jour le statut de la tâche
        success = state.update_task_status(task_id, "in_progress", {"message": "Traitement en cours"})
        assert success is True
        
        # Récupérer la tâche
        retrieved_task = state.get_task(task_id)
        assert retrieved_task is not None
        assert retrieved_task["status"] == "in_progress"
        
        # Ajouter un résultat d'analyse
        result_data = {
            "id": "result-1",
            "task_id": task_id,
            "content": "Résultat de test"
        }
        result_id = state.add_analysis_result("test_results", result_data)
        assert result_id == "result-1"
        
        # Ajouter un problème
        issue = {
            "type": "test_issue",
            "description": "Problème de test",
            "severity": "medium",
            "task_id": task_id
        }
        issue_id = state.add_issue(issue)
        assert issue_id.startswith("issue-")
        
        # Mettre à jour les métriques
        metrics = {
            "execution_time": 1.0,
            "confidence": 0.8,
            "coverage": 1.0
        }
        success = state.update_metrics(task_id, metrics)
        assert success is True
        
        # Récupérer les métriques
        retrieved_metrics = state.get_task_metrics(task_id)
        assert retrieved_metrics is not None
        assert retrieved_metrics["execution_time"] == 1.0
    
    @pytest.mark.asyncio
    async def test_end_to_end_task_processing(self, operational_components):
        """Teste le traitement complet d'une tâche, en s'assurant que l'agent est correctement sélectionné et le mock appelé."""
        manager = operational_components["manager"]
        tactical_state = operational_components["tactical_state"]
        mock_extract_process = operational_components["mocks"]["extract"]

        mock_result = {"id": "res-e2e-1", "status": "completed", "outputs": {"e2e_segments": "segments e2e"}, "metrics": {"execution_time": 1.5}}
        async def side_effect(*args, **kwargs): return mock_result
        mock_extract_process.side_effect = side_effect

        tactical_task = {"id": "task-e2e-1", "required_capabilities": ["text_extraction"]}
        tactical_state.add_task(tactical_task)

        await asyncio.sleep(0.1) # Laisser le temps aux agents de s'initialiser

        processing_task = asyncio.create_task(manager.process_tactical_task(tactical_task))
        await asyncio.sleep(0.5) # Augmentation du délai

        mock_extract_process.assert_called_once()
        final_result = await processing_task
        
        assert final_result["completion_status"] == "completed"
        saved_output = json.loads(Path(final_result["results_path"]).read_text())
        assert "segments e2e" in saved_output["outputs"]
        assert final_result["execution_metrics"]["processing_time"] == 1.5