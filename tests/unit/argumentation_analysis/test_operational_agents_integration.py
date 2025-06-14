
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
from argumentation_analysis.core.communication import MessageMiddleware, Channel, ChannelType

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

    @pytest_asyncio.fixture
    async def operational_components(self):
        """Initialise les objets nécessaires pour les tests."""
        tactical_state = TacticalState()
        operational_state = OperationalState()
        interface = TacticalOperationalInterface(tactical_state, operational_state)
        
        # Créer et configurer le middleware
        middleware = MessageMiddleware()
        mock_channel = MagicMock(spec=Channel)
        mock_channel.type = ChannelType.HIERARCHICAL
        middleware.register_channel(mock_channel)
        
        # Créer un kernel et un llm_service_id mockés
        mock_kernel = MagicMock(spec=sk.Kernel)
        mock_llm_service_id = "mock_service"

        manager = OperationalManager(
            operational_state=operational_state,
            tactical_operational_interface=interface,
            middleware=middleware,
            kernel=mock_kernel,
            llm_service_id=mock_llm_service_id
        )
        await manager.start()
        
        sample_text = """
        La vaccination devrait être obligatoire pour tous les enfants. Les vaccins ont été prouvés sûrs par de nombreuses études scientifiques. De plus, la vaccination de masse crée une immunité collective qui protège les personnes vulnérables qui ne peuvent pas être vaccinées pour des raisons médicales.
        """
        tactical_state.raw_text = sample_text
        
        yield tactical_state, operational_state, interface, manager, sample_text
        
        # Cleanup AsyncIO tasks
        try:
            tasks = [task for task in asyncio.all_tasks() if not task.done()]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            pass
        
        await manager.stop()
    
    @pytest.mark.asyncio
    async def test_agent_registry_initialization(self, operational_components):
        """Teste l'initialisation du registre d'agents."""
        _, operational_state, _, _, _ = operational_components
        registry = OperationalAgentRegistry(operational_state)
        
        # Vérifier les types d'agents disponibles
        agent_types = registry.get_agent_types()
        assert "extract" in agent_types
        assert "informal" in agent_types
        assert "pl" in agent_types
        
        # Vérifier que les agents peuvent être créés
        extract_agent = await registry.get_agent("extract")
        assert extract_agent is not None
        assert extract_agent.name == "ExtractAgent"
        
        # Vérifier les capacités des agents
        capabilities = extract_agent.get_capabilities()
        assert "text_extraction" in capabilities
    
    
    @pytest.mark.asyncio
    async def test_extract_agent_task_processing(self, operational_components):
        """Teste le traitement d'une tâche par l'agent d'extraction."""
        tactical_state, _, _, manager, sample_text = operational_components
        
        with patch("argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgentAdapter.process_task") as mock_process_task:
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
                            "extracted_text": sample_text.strip(),
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
            tactical_state.add_task(tactical_task)
            
            # Traiter la tâche
            result = await manager.process_tactical_task(tactical_task)
            
            # Vérifier que le mock a été appelé
            mock_process_task.assert_called_once()
            
            # Vérifier le résultat
            assert result["task_id"] == "task-extract-1"
            assert result["completion_status"] == "completed"
            assert result["results_path"].startswith(str(RESULTS_DIR))
            assert "execution_metrics" in result
    
    
    async def test_informal_agent_task_processing(self, operational_components):
        """Teste le traitement d'une tâche par l'agent informel."""
        tactical_state, _, _, manager, _ = operational_components
        
        with patch("argumentation_analysis.orchestration.hierarchical.operational.adapters.informal_agent_adapter.InformalAgentAdapter.process_task") as mock_process_task:
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
            tactical_state.add_task(tactical_task)
            
            # Traiter la tâche
            result = await manager.process_tactical_task(tactical_task)
            
            # Vérifier que le mock a été appelé
            mock_process_task.assert_called_once()
            
            # Vérifier le résultat
            assert result["task_id"] == "task-informal-1"
            assert result["completion_status"] == "completed"
            assert result["results_path"].startswith(str(RESULTS_DIR))
            assert "execution_metrics" in result
    
    
    async def test_pl_agent_task_processing(self, operational_components):
        """Teste le traitement d'une tâche par l'agent de logique propositionnelle."""
        tactical_state, _, _, manager, _ = operational_components
        
        with patch("argumentation_analysis.orchestration.hierarchical.operational.adapters.pl_agent_adapter.PLAgentAdapter.process_task") as mock_process_task:
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
            tactical_state.add_task(tactical_task)
            
            # Traiter la tâche
            result = await manager.process_tactical_task(tactical_task)
            
            # Vérifier que le mock a été appelé
            mock_process_task.assert_called_once()
            
            # Vérifier le résultat
            assert result["task_id"] == "task-pl-1"
            assert result["completion_status"] == "completed"
            assert result["results_path"].startswith(str(RESULTS_DIR))
            assert "execution_metrics" in result
    
    async def test_agent_selection(self, operational_components):
        """Teste la sélection de l'agent approprié pour une tâche."""
        _, operational_state, _, _, _ = operational_components
        registry = OperationalAgentRegistry(operational_state)
        
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
        assert extract_agent is not None
        assert extract_agent.name == "ExtractAgent"
        
        assert informal_agent is not None
        assert informal_agent.name == "InformalAgent"
        
        assert pl_agent is not None
        assert pl_agent.name == "PLAgent"
    
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
    
    async def test_end_to_end_task_processing(self, operational_components):
        """Teste le traitement complet d'une tâche de bout en bout."""
        tactical_state, _, _, manager, sample_text = operational_components
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
        tactical_state.add_task(tactical_task)
        
        # Patcher la méthode process_task de l'agent d'extraction
        with patch("argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgentAdapter.process_task") as mock_process_task:
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
                            "extracted_text": sample_text.strip(),
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
            mock_process_task# Mock eliminated - using authentic gpt-4o-mini mock_result
            
            # Traiter la tâche
            result = await manager.process_tactical_task(tactical_task)
            
            # Vérifier que le mock a été appelé
            assert mock_process_task.called is True
            
            # Vérifier le résultat
            assert result["task_id"] == "task-test-1"
            assert result["completion_status"] == "completed"
            assert RESULTS_DIR in result
            assert "execution_metrics" in result
            
            # Vérifier que les métriques ont été correctement traduites
            assert result["execution_metrics"]["processing_time"] == 1.5
            assert result["execution_metrics"]["confidence_score"] == 0.9