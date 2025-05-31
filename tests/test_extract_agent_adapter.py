#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module orchestration.hierarchical.operational.adapters.extract_agent_adapter.
"""

import pytest
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock, Mock # Mock est toujours utilisé pour les instances de mock_extract_agent etc.
import asyncio
import logging

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestExtractAgentAdapter")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
sys.path.append(os.path.abspath('..'))

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState


# Mock pour ExtractAgent
class MockExtractAgent:
    def __init__(self, extract_agent=None, validation_agent=None, extract_plugin=None):
        self.extract_agent = extract_agent or Mock()
        self.validation_agent = validation_agent or Mock()
        self.extract_plugin = extract_plugin or Mock()
        self.state = Mock()
        self.state.task_dependencies = {}
        self.state.tasks = {}
        
        self.extract_text = AsyncMock(return_value={
            "status": "success",
            "extracts": [
                {
                    "id": "extract-1",
                    "text": "Ceci est un extrait de test",
                    "source": "test-source",
                    "confidence": 0.9
                }
            ]
        })
        
        self.validate_extracts = AsyncMock(return_value={
            "status": "success",
            "valid_extracts": [
                {
                    "id": "extract-1",
                    "text": "Ceci est un extrait de test",
                    "source": "test-source",
                    "confidence": 0.9,
                    "validation_score": 0.95
                }
            ]
        })
        
        self.preprocess_text = AsyncMock(return_value={
            "status": "success",
            "preprocessed_text": "Ceci est un texte prétraité",
            "metadata": {
                "word_count": 5,
                "language": "fr"
            }
        })

        self.extract_from_name = AsyncMock(return_value=MagicMock(
            status="valid",
            message="Extraction réussie simulée par extract_from_name",
            explanation="Mock explanation",
            start_marker="<MOCK_START>",
            end_marker="<MOCK_END>",
            template_start="<MOCK_TEMPLATE_START>",
            extracted_text="Texte extrait simulé via extract_from_name"
        ))
        
    def process_extract(self, *args, **kwargs):
        return {"status": "success", "data": []}
    
    def validate_extract(self, *args, **kwargs):
        return True


class MockValidationAgent:
    """Mock pour ValidationAgent."""
    
    def __init__(self):
        self.extract_text = AsyncMock(return_value={
            "status": "success",
            "extracts": [
                {
                    "id": "extract-1",
                    "text": "Ceci est un extrait de test",
                    "source": "test-source",
                    "confidence": 0.9
                }
            ]
        })
        
        self.validate_extracts = AsyncMock(return_value={
            "status": "success",
            "valid_extracts": [
                {
                    "id": "extract-1",
                    "text": "Ceci est un extrait de test",
                    "source": "test-source",
                    "confidence": 0.9,
                    "validation_score": 0.95
                }
            ]
        })
        
        self.preprocess_text = AsyncMock(return_value={
            "status": "success",
            "preprocessed_text": "Ceci est un texte prétraité",
            "metadata": {
                "word_count": 5,
                "language": "fr"
            }
        })


# Mock pour setup_extract_agent
async def mock_setup_extract_agent():
    """Mock pour la fonction setup_extract_agent."""
    kernel = MagicMock()
    extract_agent = MockExtractAgent(
        extract_agent=Mock(),
        validation_agent=Mock(),
        extract_plugin=Mock()
    )
    return kernel, extract_agent


class TestExtractAgentAdapter:
    """Tests unitaires pour l'adaptateur d'agent d'extraction."""

    @pytest.fixture(autouse=True)
    async def setup_adapter(self, mocker):
        """Initialisation avant chaque test."""
        # Créer les mocks
        self.mock_extract_agent = Mock()
        self.mock_validation_agent = Mock()
        self.mock_extract_plugin = Mock()

        # Configuration des mocks pour les tests
        self.mock_extract_agent.process_extract.return_value = {"status": "success"}
        self.mock_validation_agent.validate.return_value = True
        self.mock_extract_plugin.extract.return_value = []
        self.mock_extract_plugin.process_text.return_value = {"status": "success", "data": []}
        self.mock_extract_plugin.get_supported_formats.return_value = ["txt", "pdf", "docx"]
        # Créer un état opérationnel mock
        self.operational_state = OperationalState()

        # Patcher setup_extract_agent
        mocker.patch('argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.setup_extract_agent',
                                         side_effect=mock_setup_extract_agent)

        # Créer l'adaptateur d'agent d'extraction
        self.adapter = ExtractAgentAdapter(name="TestExtractAgent", operational_state=self.operational_state)

        await self.adapter.initialize()

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Teste l'initialisation de l'adaptateur d'agent d'extraction."""
        assert self.adapter is not None
        assert self.adapter.name == "TestExtractAgent"
        assert self.adapter.operational_state == self.operational_state
        assert self.adapter.extract_agent is not None
        assert self.adapter.kernel is not None
        assert self.adapter.initialized is True

    @pytest.mark.asyncio
    async def test_get_capabilities(self):
        """Teste la méthode get_capabilities."""
        capabilities = self.adapter.get_capabilities()
        assert isinstance(capabilities, list)
        assert "text_extraction" in capabilities
        assert "preprocessing" in capabilities
        assert "extract_validation" in capabilities

    @pytest.mark.asyncio
    async def test_can_process_task(self):
        """Teste la méthode can_process_task."""
        task_can_process = {
            "id": "task-1",
            "description": "Extraire le texte",
            "required_capabilities": ["text_extraction"]
        }
        assert self.adapter.can_process_task(task_can_process) is True

        task_cannot_process = {
            "id": "task-2",
            "description": "Analyser les sophismes",
            "required_capabilities": ["fallacy_detection"]
        }
        assert self.adapter.can_process_task(task_cannot_process) is False

    @pytest.mark.asyncio
    async def test_process_task_extract_text(self):
        """Teste la méthode process_task pour l'extraction de texte."""
        task = {
            "id": "task-1",
            "description": "Extraire le texte",
            "text_extracts": [{
                "id": "input-extract-1",
                "content": "Ceci est un texte à extraire",
                "source": "test-source"
            }],
            "techniques": [{
                "name": "relevant_segment_extraction",
                "parameters": {}
            }]
        }
        result = await self.adapter.process_task(task)
        assert result["status"] == "completed"
        assert "outputs" in result
        outputs = result["outputs"]
        assert "extracted_segments" in outputs
        assert len(outputs["extracted_segments"]) == 1
        extracted_segment = outputs["extracted_segments"][0]
        assert extracted_segment["extract_id"] == "input-extract-1"
        assert extracted_segment["extracted_text"] == "Texte extrait simulé via extract_from_name"
        self.adapter.extract_agent.extract_from_name.assert_called_once_with(
            {"source_name": "test-source", "source_text": "Ceci est un texte à extraire"},
            "input-extract-1"
        )

    @pytest.mark.asyncio
    async def test_process_task_validate_extracts(self):
        """Teste la méthode process_task pour la validation d'extraits."""
        task = {
            "id": "task-2",
            "description": "Valider les extraits",
            "text_extracts": [{
                "id": "extract-to-validate-1",
                "content": "Ceci est un extrait à valider",
                "source": "test-source"
            }],
            "techniques": [{
                "name": "non_existent_validation_technique",
                "parameters": {}
            }]
        }
        result = await self.adapter.process_task(task)
        assert result["status"] == "completed_with_issues"
        assert "issues" in result
        assert len(result["issues"]) > 0
        issue = result["issues"][0]
        assert issue["type"] == "unsupported_technique"
        assert "non_existent_validation_technique" in issue["description"]
        self.adapter.extract_agent.validate_extracts.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_task_preprocess_text(self):
        """Teste la méthode process_task pour le prétraitement de texte."""
        task = {
            "id": "task-3",
            "description": "Prétraiter le texte",
            "text_extracts": [{
                "id": "input-text-preprocess-1",
                "content": "Ceci est un texte à prétraiter avec des mots comme le et la",
                "source": "test-source-preprocess"
            }],
            "techniques": [{
                "name": "text_normalization",
                "parameters": {"remove_stopwords": True}
            }]
        }
        result = await self.adapter.process_task(task)
        assert result["status"] == "completed"
        assert "outputs" in result
        outputs = result["outputs"]
        assert "normalized_text" in outputs
        assert len(outputs["normalized_text"]) == 1
        normalized_output = outputs["normalized_text"][0]
        assert normalized_output["extract_id"] == "input-text-preprocess-1"
        assert normalized_output["normalized_text"] == "Ceci texte à prétraiter avec mots comme"
        self.adapter.extract_agent.preprocess_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_task_unknown_capability(self):
        """Teste la méthode process_task pour une capacité inconnue."""
        task = {
            "id": "task-4",
            "description": "Tâche inconnue",
            "text_extracts": [{
                "id": "input-unknown-1",
                "content": "Texte pour capacité inconnue",
                "source": "test-source-unknown"
            }],
            "techniques": [{
                "name": "very_unknown_technique",
                "parameters": {}
            }]
        }
        result = await self.adapter.process_task(task)
        assert result["status"] == "completed_with_issues"
        assert "issues" in result
        assert len(result["issues"]) > 0
        issue = result["issues"][0]
        assert issue["type"] == "unsupported_technique"
        assert "very_unknown_technique" in issue["description"]

    @pytest.mark.asyncio
    async def test_process_task_missing_parameters(self):
        """Teste la méthode process_task avec des paramètres manquants."""
        task = {
            "id": "task-5",
            "description": "Extraire le texte avec paramètres manquants pour la technique",
            "text_extracts": [],
            "techniques": [{
                "name": "relevant_segment_extraction"
            }]
        }
        result = await self.adapter.process_task(task)
        assert result["status"] == "failed"
        assert "issues" in result
        assert len(result["issues"]) > 0
        issue = result["issues"][0]
        assert issue["type"] == "execution_error"
        assert "Aucun extrait de texte fourni dans la tâche." in issue["description"]
        assert "outputs" in result
        assert result["outputs"] == {}

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Teste la méthode shutdown."""
        result = await self.adapter.shutdown()
        assert result is True
        assert self.adapter.initialized is False
        assert self.adapter.extract_agent is None
        assert self.adapter.kernel is None