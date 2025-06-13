
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le module orchestration.hierarchical.operational.adapters.extract_agent_adapter.
"""

import pytest
import pytest_asyncio
import sys
import os

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

# Configuration pytest-asyncio pour éviter les conflits d'event loop
pytestmark = pytest.mark.asyncio

# Configurer le logging pour les tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestExtractAgentAdapter")

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import des modules à tester
from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter, ExtractAgent
from argumentation_analysis.orchestration.hierarchical.operational.state import OperationalState


# Mock pour ExtractAgent
class MockExtractAgent(AsyncMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.extract_from_name = AsyncMock(return_value=MagicMock(
            status="valid",
            message="Extraction réussie simulée par extract_from_name",
            explanation="Mock explanation",
            start_marker="<MOCK_START>",
            end_marker="<MOCK_END>",
            template_start="<MOCK_TEMPLATE_START>",
            extracted_text="Texte extrait simulé via extract_from_name"
        ))
        self.setup_agent_components = AsyncMock(return_value=None)
        self.preprocess_text = AsyncMock(return_value={
            "status": "success",
            "preprocessed_text": "Ceci est un texte prétraité",
        })
        self.validate_extracts = AsyncMock(return_value={"status": "success", "valid_extracts": []})


# @pytest.mark.skip(reason="Ce fichier de test est obsolète et remplacé par tests/orchestration/hierarchical/operational/adapters/test_extract_agent_adapter.py")
class TestExtractAgentAdapter:
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

    """Tests unitaires pour l'adaptateur d'agent d'extraction."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_adapter(self):
        """Initialisation avant chaque test."""
        self.mock_kernel = MagicMock()
        self.mock_llm_service_id = "mock_service_id"
        self.operational_state = OperationalState()

        # Le mock pour l'agent qui sera retourné par le constructeur patché
        self.mock_agent_instance = MockExtractAgent()

        # Patcher le constructeur de ExtractAgent
        self.patcher = patch(
            'argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter.ExtractAgent',
            return_value=self.mock_agent_instance
        )
        self.MockExtractAgentClass = self.patcher.start()

        # Créer l'adaptateur
        self.adapter = ExtractAgentAdapter(name="TestExtractAgent", operational_state=self.operational_state)
        
        # Initialiser l'adaptateur avec les mocks
        await self.adapter.initialize(kernel=self.mock_kernel, llm_service_id=self.mock_llm_service_id)

        yield

        # Cleanup AsyncIO tasks before stopping patches
        # try:
        #     tasks = [task for task in asyncio.all_tasks() if not task.done()]
        #     if tasks:
        #         logger.warning(f"Nettoyage de {len(tasks)} tâches asyncio non terminées.")
        #         await asyncio.gather(*tasks, return_exceptions=True)
        # except Exception as e:
        #     logger.error(f"Erreur lors du nettoyage des tâches asyncio: {e}")
        #     pass

        # Nettoyage après chaque test
        self.patcher.stop()

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Teste l'initialisation de l'adaptateur d'agent d'extraction."""
        assert self.adapter is not None
        assert self.adapter.name == "TestExtractAgent"
        assert self.adapter.operational_state == self.operational_state
        assert self.adapter.agent is not None
        assert self.adapter.agent == self.mock_agent_instance
        assert self.adapter.kernel == self.mock_kernel
        assert self.adapter.initialized is True
        # Vérifier que ExtractAgent a été appelé correctement
        self.MockExtractAgentClass.assert_called_once_with(kernel=self.mock_kernel, agent_name="TestExtractAgent_ExtractAgent")
        # Vérifier que setup_agent_components a été appelé
        self.mock_agent_instance.setup_agent_components.assert_awaited_once_with(llm_service_id=self.mock_llm_service_id)

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
        self.adapter.agent.extract_from_name.assert_called_once_with(
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
        self.adapter.agent.validate_extracts.assert_not_called()

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
        # La logique de normalisation est maintenant dans l'adaptateur, pas dans un agent mocké
        assert "le" not in normalized_output["normalized_text"].lower().split()
        assert "la" not in normalized_output["normalized_text"].lower().split()
        self.adapter.agent.preprocess_text.assert_not_called()

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
        # En cas d'échec, le dictionnaire d'outputs est vide.
        assert result["outputs"] == {}

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Teste la méthode shutdown."""
        result = await self.adapter.shutdown()
        assert result is True
        assert self.adapter.initialized is False
        assert self.adapter.agent is None
        assert self.adapter.kernel is None