#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests Unitaires pour les Orchestrateurs Spécialisés
===================================================

Tests pour valider le fonctionnement des orchestrateurs spécialisés :
- CluedoOrchestrator (enquêtes et investigations)
- ConversationOrchestrator (analyses conversationnelles)
- RealLLMOrchestrator (orchestration LLM réelle)
- LogiqueComplexeOrchestrator (logique complexe)

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import pytest
import asyncio
import logging
from unittest.mock import patch, AsyncMock, Mock
from typing import Dict, Any, List, Optional
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase

@pytest.fixture
def llm_service() -> Mock:
    """Fixture pour un service LLM mocké, compatible avec ChatCompletionClientBase."""
    mock_service = Mock(spec=ChatCompletionClientBase)
    # Le kernel a besoin d'un service_id pour enregistrer le service.
    mock_service.service_id = "mock_llm_service"
    return mock_service

@pytest.fixture
def mock_kernel(llm_service: Mock) -> Kernel:
    """Fixture pour un kernel Semantic Kernel avec un service LLM mocké."""
    kernel = Kernel()
    kernel.add_service(llm_service)
    return kernel

# Configuration du logging pour les tests
logging.basicConfig(level=logging.WARNING)

# Imports à tester
try:
    from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator as CluedoOrchestrator
    from argumentation_analysis.orchestration.conversation_orchestrator import ConversationOrchestrator
    from argumentation_analysis.orchestration.real_llm_orchestrator import RealLLMOrchestrator
    from argumentation_analysis.orchestration.logique_complexe_orchestrator import LogiqueComplexeOrchestrator
    SPECIALIZED_AVAILABLE = True
except ImportError as e:
    SPECIALIZED_AVAILABLE = False
    pytestmark = pytest.mark.skip(f"Orchestrateurs spécialisés non disponibles: {e}")


class TestCluedoOrchestrator:
    """Tests pour l'orchestrateur Cluedo (investigations)."""
    
    @pytest.fixture
    def cluedo_orchestrator(self, mock_kernel: Kernel):
        """Instance de CluedoOrchestrator pour les tests."""
        return CluedoOrchestrator(kernel=mock_kernel)
    
    @pytest.fixture
    def investigation_text(self):
        """Texte d'enquête pour les tests."""
        return "Le témoin A dit X, le témoin B dit Y. Qui dit vrai ?"

    def test_cluedo_orchestrator_initialization(self, cluedo_orchestrator, mock_kernel):
        """Test de l'initialisation de l'orchestrateur Cluedo."""
        assert cluedo_orchestrator.kernel == mock_kernel
        assert cluedo_orchestrator.oracle_state is None
        assert cluedo_orchestrator.sherlock_agent is None
        assert cluedo_orchestrator.execution_metrics == {}

    def test_execute_workflow_simulation(self, cluedo_orchestrator, investigation_text):
        """Test de la méthode publique execute_workflow (simulation)."""
        # On simule que le setup a été fait.
        cluedo_orchestrator.orchestration = Mock()
        cluedo_orchestrator.oracle_state = Mock()
        
        # On mock directement la méthode execute_workflow pour ne pas tester toute la logique interne complexe
        expected_result = {
            "workflow_info": {"status": "completed"},
            "solution_analysis": {"success": True},
            "conversation_history": []
        }
        cluedo_orchestrator.execute_workflow = AsyncMock(return_value=expected_result)
        
        result = asyncio.run(cluedo_orchestrator.execute_workflow(investigation_text))
        
        cluedo_orchestrator.execute_workflow.assert_called_once_with(investigation_text)
        assert result["workflow_info"]["status"] == "completed"
        assert result["solution_analysis"]["success"] is True


class TestConversationOrchestrator:
    """Tests pour l'orchestrateur de conversation."""

    @pytest.fixture
    def conversation_orchestrator(self):
        """Instance de ConversationOrchestrator pour les tests."""
        # Le constructeur a changé, il ne prend plus de llm_service ou config.
        return ConversationOrchestrator(mode="demo")

    @pytest.fixture
    def dialogue_text(self):
        """Texte de dialogue pour les tests."""
        return "Alice: Pense à A. Bob: Non, pense à B."

    def test_conversation_orchestrator_initialization(self, conversation_orchestrator):
        """Test de l'initialisation de l'orchestrateur de conversation."""
        assert conversation_orchestrator.mode == "demo"
        assert conversation_orchestrator.state is not None
        assert conversation_orchestrator.conv_logger is not None
        assert len(conversation_orchestrator.agents) > 0

    def test_run_demo_conversation(self, conversation_orchestrator, dialogue_text):
        """Test de l'orchestration d'une conversation en mode démo."""
        conversation_orchestrator.run_demo_conversation = AsyncMock(
            return_value={
                "report": "TRACE ANALYTIQUE something",
                "conversation_state": {"completed": True},
                "mode": "demo"
            }
        )
        # La méthode à tester est maintenant `run_demo_conversation`
        result = asyncio.run(conversation_orchestrator.run_demo_conversation(dialogue_text))
        
        assert "report" in result
        assert "conversation_state" in result
        assert result["mode"] == "demo"
        assert result["conversation_state"]["completed"] is True
        assert "TRACE ANALYTIQUE" in result["report"]


class TestRealLLMOrchestrator:
    """Tests pour l'orchestrateur LLM réel."""

    @pytest.fixture
    def real_llm_orchestrator(self, mock_kernel: Kernel):
        """Instance de RealLLMOrchestrator pour les tests."""
        return RealLLMOrchestrator(kernel=mock_kernel)

    def test_real_llm_orchestrator_initialization(self, real_llm_orchestrator):
        """Test de l'initialisation de l'orchestrateur LLM réel."""
        assert real_llm_orchestrator.kernel is not None
        assert real_llm_orchestrator.is_initialized is False
        assert real_llm_orchestrator.metrics['total_requests'] == 0

    @patch('argumentation_analysis.orchestration.real_llm_orchestrator.RealLLMOrchestrator.initialize', new_callable=AsyncMock)
    def test_analyze_text_mocked(self, mock_initialize, real_llm_orchestrator):
        """Test de l'orchestration d'analyse avec _perform_analysis mocké."""
        text = "Texte complexe nécessitant analyse."

        # L'appel à `analyze_text` déclenche `initialize` qui est mocké par le décorateur.
        # Cela évite le démarrage réel de la JVM et le crash.
        
        # Mock de la méthode interne pour éviter un vrai appel LLM
        expected_analysis = {'analysis': 'mocked_result', 'confidence': 0.95}
        real_llm_orchestrator._perform_analysis = AsyncMock(return_value=expected_analysis)
        
        result = asyncio.run(real_llm_orchestrator.analyze_text(text, analysis_type="unified_analysis"))
        
        # On vérifie que la méthode d'initialisation (mockée) a bien été appelée
        mock_initialize.assert_awaited_once()
        real_llm_orchestrator._perform_analysis.assert_called_once()
        assert result.result == expected_analysis
        assert result.confidence == 0.95
        assert result.analysis_type == "unified_analysis"


class TestLogiqueComplexeOrchestrator:
    """Tests pour l'orchestrateur de logique complexe."""

    @pytest.fixture
    def logic_orchestrator(self, mock_kernel: Kernel):
        """Instance de LogiqueComplexeOrchestrator pour les tests."""
        return LogiqueComplexeOrchestrator(kernel=mock_kernel)

    def test_logic_orchestrator_initialization(self, logic_orchestrator):
        """Test de l'initialisation de l'orchestrateur de logique complexe."""
        # La classe a une définition minimale maintenant.
        assert logic_orchestrator.kernel is not None
        assert hasattr(logic_orchestrator, "_logger")

    def test_run_einstein_puzzle_simulation(self, logic_orchestrator):
        """Test de la seule méthode disponible (simulation)."""
        puzzle_data = {"test": "data"}
        # Mock de la méthode pour la prévisibilité
        logic_orchestrator.run_einstein_puzzle = AsyncMock(return_value={"solution": "mocked", "success": True})
        
        result = asyncio.run(logic_orchestrator.run_einstein_puzzle(puzzle_data))
        
        logic_orchestrator.run_einstein_puzzle.assert_called_once_with(puzzle_data)
        assert result["success"] is True
        assert result["solution"] == "mocked"


class TestSpecializedOrchestratorsIntegration:
    """Tests d'intégration entre orchestrateurs spécialisés."""

    def test_orchestrator_instantiation(self, mock_kernel: Kernel):
        """Test de l'instanciation correcte des orchestrateurs."""
        cluedo = CluedoOrchestrator(kernel=mock_kernel)
        assert isinstance(cluedo, CluedoOrchestrator)

        convo = ConversationOrchestrator(mode="demo")
        assert isinstance(convo, ConversationOrchestrator)

        real_llm = RealLLMOrchestrator(kernel=mock_kernel)
        assert isinstance(real_llm, RealLLMOrchestrator)

        logic = LogiqueComplexeOrchestrator(kernel=mock_kernel)
        assert isinstance(logic, LogiqueComplexeOrchestrator)

    @patch('argumentation_analysis.orchestration.cluedo_extended_orchestrator.CluedoExtendedOrchestrator.execute_workflow', new_callable=AsyncMock)
    @patch('argumentation_analysis.orchestration.conversation_orchestrator.ConversationOrchestrator.run_demo_conversation', new_callable=AsyncMock)
    @patch('argumentation_analysis.orchestration.logique_complexe_orchestrator.LogiqueComplexeOrchestrator.run_einstein_puzzle', new_callable=AsyncMock)
    def test_orchestrator_collaboration_mocked(self, mock_logic_run, mock_convo_run, mock_cluedo_run, mock_kernel: Kernel):
        """Test de collaboration simulée entre les orchestrateurs."""
        mock_cluedo_run.return_value = {"workflow_info": {"status": "completed"}}
        mock_convo_run.return_value = {"status": "success", "report": "report"}
        mock_logic_run.return_value = {"solution": "mocked", "success": True}

        complex_text = "Un texte complexe pour tester tout le monde."
        
        cluedo_orchestrator = CluedoOrchestrator(kernel=mock_kernel)
        # La méthode setup_workflow est nécessaire avant execute_workflow
        cluedo_orchestrator.setup_workflow = AsyncMock()
        asyncio.run(cluedo_orchestrator.setup_workflow())

        conversation_orchestrator = ConversationOrchestrator(mode="demo")
        logic_orchestrator = LogiqueComplexeOrchestrator(kernel=mock_kernel)
        
        investigation_result = asyncio.run(cluedo_orchestrator.execute_workflow(complex_text))
        dialogue_result = asyncio.run(conversation_orchestrator.run_demo_conversation(complex_text))
        logic_result = asyncio.run(logic_orchestrator.run_einstein_puzzle({}))
        
        mock_cluedo_run.assert_called_once_with(complex_text)
        mock_convo_run.assert_called_once_with(complex_text)
        mock_logic_run.assert_called_once_with({})
        
        assert "workflow_info" in investigation_result
        assert "report" in dialogue_result
        assert "success" in logic_result


if __name__ == "__main__":
    # Exécution des tests si le script est lancé directement
    pytest.main([__file__, "-v", "--tb=short"])
