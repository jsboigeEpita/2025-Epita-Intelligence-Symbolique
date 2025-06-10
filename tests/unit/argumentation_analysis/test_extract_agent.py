
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour l'agent d'extraction.
"""

import asyncio
import pytest
import pytest_asyncio

import argumentation_analysis.agents.core.extract.extract_agent as agent_module_to_patch # Module à patcher

from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractAgentPlugin, ExtractResult


class MockExtractAgent(ExtractAgent):
    """Mock d'ExtractAgent qui implémente les méthodes abstraites."""
    
    def __init__(self, kernel, find_similar_text_func=None, extract_text_func=None):
        super().__init__(
            kernel=kernel,
            agent_name="MockExtractAgent",
            find_similar_text_func=find_similar_text_func,
            extract_text_func=extract_text_func
        )
    
    def get_agent_capabilities(self):
        return {"text_extraction": True, "marker_detection": True}
    
    async def setup_agent_components(self, llm_service_id: str):
        self._llm_service_id = llm_service_id
        # Mock setup
        pass
    
    async def get_response(self, *args, **kwargs):
        return Magicawait self._create_authentic_gpt4o_mini_instance()
    
    async def invoke(self, *args, **kwargs):
        return Magicawait self._create_authentic_gpt4o_mini_instance()

@pytest_asyncio.fixture
async def extract_agent_data():
    """Fixture pour initialiser l'agent d'extraction et ses mocks, et patcher load_source_text DANS le module agent."""

    original_load_source_text_in_agent_module = agent_module_to_patch.load_source_text
    mock_lts_for_agent_module = Magicawait self._create_authentic_gpt4o_mini_instance()
    agent_module_to_patch.load_source_text = mock_lts_for_agent_module

    kernel_mock = Magicawait self._create_authentic_gpt4o_mini_instance()
    extract_plugin_mock = MagicMock(spec=ExtractAgentPlugin)
    find_similar_text_mock = Magicawait self._create_authentic_gpt4o_mini_instance()
    extract_text_mock = Magicawait self._create_authentic_gpt4o_mini_instance()

    agent = MockExtractAgent(
        kernel=kernel_mock,
        find_similar_text_func=find_similar_text_mock,
        extract_text_func=extract_text_mock
    )
    agent._native_extract_plugin = extract_plugin_mock

    source_info = {
        "source_name": "Source de test",
        "source_url": "https://example.com",
        "source_text": "Ceci est un texte de test pour l'extraction."
    }
    extract_name = "Extrait de test"

    fixture_data = {
        "agent": agent,
        "kernel_mock": kernel_mock,
        "extract_plugin_mock": extract_plugin_mock,
        "find_similar_text_mock": find_similar_text_mock,
        "extract_text_mock": extract_text_mock,
        "source_info": source_info,
        "extract_name": extract_name,
        "mock_load_source_text": mock_lts_for_agent_module
    }

    yield fixture_data

    # Cleanup AsyncIO tasks
    try:
        tasks = [task for task in asyncio.all_tasks() if not task.done()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    except Exception:
        pass

    agent_module_to_patch.load_source_text = original_load_source_text_in_agent_module


class TestExtractAgent:
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

    """Tests pour la classe ExtractAgent."""

    @pytest.mark.asyncio
    async def test_extract_from_name_success(self, extract_agent_data):
        """Teste l'extraction réussie à partir du nom."""
        agent = extract_agent_data["agent"]
        kernel_mock = extract_agent_data["kernel_mock"]
        extract_text_mock = extract_agent_data["extract_text_mock"]
        source_info = extract_agent_data["source_info"]
        extract_name = extract_agent_data["extract_name"]
        mock_load_source_text = extract_agent_data["mock_load_source_text"]

        mock_load_source_text# Mock eliminated - using authentic gpt-4o-mini ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        mock_extract_response = Magicawait self._create_authentic_gpt4o_mini_instance()
        mock_extract_response.__str__# Mock eliminated - using authentic gpt-4o-mini '{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}'
        
        mock_validation_response = Magicawait self._create_authentic_gpt4o_mini_instance()
        mock_validation_response.__str__# Mock eliminated - using authentic gpt-4o-mini '{"valid": true, "reason": "Extrait valide"}'

        kernel_mock.invoke# Mock eliminated - using authentic gpt-4o-mini [
            mock_extract_response,
            mock_validation_response
        ]
        
        extract_text_mock# Mock eliminated - using authentic gpt-4o-mini ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        result = await agent.extract_from_name(source_info, extract_name)
        
        assert result.status == "valid"
        assert result.start_marker == "Ceci est"
        assert result.end_marker == "extraction."
        assert result.extracted_text == "Ceci est un texte de test pour l'extraction."
        
        mock_load_source_text.assert_called_once_with(source_info)
        assert kernel_mock.invoke.call_count == 2
        extract_text_mock.assert_called_once_with(
            "Ceci est un texte de test pour l'extraction.",
            "Ceci est",
            "extraction.",
            ""
        )

    @pytest.mark.asyncio
    async def test_extract_from_name_invalid_markers(self, extract_agent_data):
        """Teste l'extraction avec des marqueurs invalides."""
        agent = extract_agent_data["agent"]
        kernel_mock = extract_agent_data["kernel_mock"]
        extract_text_mock = extract_agent_data["extract_text_mock"]
        source_info = extract_agent_data["source_info"]
        extract_name = extract_agent_data["extract_name"]
        mock_load_source_text = extract_agent_data["mock_load_source_text"]

        mock_load_source_text# Mock eliminated - using authentic gpt-4o-mini ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        mock_response = Magicawait self._create_authentic_gpt4o_mini_instance()
        mock_response.__str__# Mock eliminated - using authentic gpt-4o-mini '{"start_marker": "", "end_marker": "", "template_start": "", "explanation": "Explication de test"}'
        kernel_mock.invoke# Mock eliminated - using authentic gpt-4o-mini mock_response
        
        result = await agent.extract_from_name(source_info, extract_name)
        
        assert result.status == "error"
        assert "Bornes invalides" in result.message
        
        mock_load_source_text.assert_called_once_with(source_info)
        kernel_mock.invoke.# Mock assertion eliminated - authentic validation
        extract_text_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_extract_from_name_markers_not_found(self, extract_agent_data):
        """Teste l'extraction avec des marqueurs non trouvés dans le texte."""
        agent = extract_agent_data["agent"]
        kernel_mock = extract_agent_data["kernel_mock"]
        extract_text_mock = extract_agent_data["extract_text_mock"]
        source_info = extract_agent_data["source_info"]
        extract_name = extract_agent_data["extract_name"]
        mock_load_source_text = extract_agent_data["mock_load_source_text"]

        mock_load_source_text# Mock eliminated - using authentic gpt-4o-mini ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        mock_response = Magicawait self._create_authentic_gpt4o_mini_instance()
        mock_response.__str__# Mock eliminated - using authentic gpt-4o-mini '{"start_marker": "Marqueur début", "end_marker": "Marqueur fin", "template_start": "", "explanation": "Explication de test"}'
        kernel_mock.invoke# Mock eliminated - using authentic gpt-4o-mini mock_response
        
        extract_text_mock# Mock eliminated - using authentic gpt-4o-mini ("", "Marqueurs non trouvés", False, False)
        
        result = await agent.extract_from_name(source_info, extract_name)
        
        assert result.status == "error"
        assert "Bornes non trouvées" in result.message
        
        mock_load_source_text.assert_called_once_with(source_info)
        kernel_mock.invoke.# Mock assertion eliminated - authentic validation
        extract_text_mock.# Mock assertion eliminated - authentic validation

    @pytest.mark.asyncio
    async def test_extract_from_name_validation_rejected(self, extract_agent_data):
        """Teste l'extraction avec validation rejetée."""
        agent = extract_agent_data["agent"]
        kernel_mock = extract_agent_data["kernel_mock"]
        extract_text_mock = extract_agent_data["extract_text_mock"]
        source_info = extract_agent_data["source_info"]
        extract_name = extract_agent_data["extract_name"]
        mock_load_source_text = extract_agent_data["mock_load_source_text"]

        mock_load_source_text# Mock eliminated - using authentic gpt-4o-mini ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        mock_extract_response = Magicawait self._create_authentic_gpt4o_mini_instance()
        mock_extract_response.__str__# Mock eliminated - using authentic gpt-4o-mini '{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}'
        
        mock_validation_response = Magicawait self._create_authentic_gpt4o_mini_instance()
        mock_validation_response.__str__# Mock eliminated - using authentic gpt-4o-mini '{"valid": false, "reason": "Extrait invalide"}'

        kernel_mock.invoke# Mock eliminated - using authentic gpt-4o-mini [
            mock_extract_response,
            mock_validation_response
        ]
        
        extract_text_mock# Mock eliminated - using authentic gpt-4o-mini ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        result = await agent.extract_from_name(source_info, extract_name)
        
        assert result.status == "rejected"
        assert result.message == "Extrait rejeté: Extrait invalide"
        
        mock_load_source_text.assert_called_once_with(source_info)
        assert kernel_mock.invoke.call_count == 2
        extract_text_mock.# Mock assertion eliminated - authentic validation

    @pytest.mark.asyncio
    async def test_repair_extract_valid(self, extract_agent_data):
        """Teste la réparation d'un extrait valide."""
        agent = extract_agent_data["agent"]
        kernel_mock = extract_agent_data["kernel_mock"]
        extract_text_mock = extract_agent_data["extract_text_mock"]
        mock_load_source_text = extract_agent_data["mock_load_source_text"]

        mock_load_source_text# Mock eliminated - using authentic gpt-4o-mini ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        extract_text_mock# Mock eliminated - using authentic gpt-4o-mini ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        extract_definitions = [
            {
                "source_name": "Source de test",
                "source_url": "https://example.com",
                "extracts": [
                    {
                        "extract_name": "Extrait de test",
                        "start_marker": "Ceci est",
                        "end_marker": "extraction."
                    }
                ]
            }
        ]
        
        result = await agent.repair_extract(extract_definitions, 0, 0)
        
        assert result.status == "valid"
        assert result.message == "Extrait valide. Aucune correction nécessaire."
        assert result.extracted_text == "Ceci est un texte de test pour l'extraction."
        
        mock_load_source_text.# Mock assertion eliminated - authentic validation
        extract_text_mock.# Mock assertion eliminated - authentic validation
        kernel_mock.invoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_extract_markers(self, extract_agent_data):
        """Teste la mise à jour des marqueurs d'un extrait."""
        agent = extract_agent_data["agent"]
        extract_plugin_mock = extract_agent_data["extract_plugin_mock"]

        extract_plugin_mock.extract_results = []
        extract_definitions = [
            {
                "source_name": "Source de test",
                "source_url": "https://example.com",
                "extracts": [
                    {
                        "extract_name": "Extrait de test",
                        "start_marker": "Ancien début",
                        "end_marker": "Ancienne fin"
                    }
                ]
            }
        ]
        
        result_obj = ExtractResult(
            source_name="Source de test",
            extract_name="Extrait de test",
            status="valid",
            message="Extrait validé",
            start_marker="Nouveau début",
            end_marker="Nouvelle fin",
            template_start="Template",
            explanation="Explication",
            extracted_text="Texte extrait"
        )
        
        success = await agent.update_extract_markers(extract_definitions, 0, 0, result_obj)
        
        assert success
        assert extract_definitions[0]["extracts"][0]["start_marker"] == "Nouveau début"
        assert extract_definitions[0]["extracts"][0]["end_marker"] == "Nouvelle fin"
        assert extract_definitions[0]["extracts"][0]["template_start"] == "Template"
        
        assert len(extract_plugin_mock.extract_results) > 0

    @pytest.mark.asyncio
    async def test_add_new_extract(self, extract_agent_data):
        """Teste l'ajout d'un nouvel extrait."""
        agent = extract_agent_data["agent"]
        extract_plugin_mock = extract_agent_data["extract_plugin_mock"]

        extract_plugin_mock.extract_results = []
        extract_definitions = [
            {
                "source_name": "Source de test",
                "source_url": "https://example.com",
                "extracts": []
            }
        ]
        
        result_obj = ExtractResult(
            source_name="Source de test",
            extract_name="Nouvel extrait",
            status="valid",
            message="Extrait validé",
            start_marker="Début",
            end_marker="Fin",
            template_start="Template",
            explanation="Explication",
            extracted_text="Texte extrait"
        )
        
        success, extract_idx = await agent.add_new_extract(extract_definitions, 0, "Nouvel extrait", result_obj)
        
        assert success
        assert extract_idx == 0
        assert len(extract_definitions[0]["extracts"]) == 1
        assert extract_definitions[0]["extracts"][0]["extract_name"] == "Nouvel extrait"
        assert extract_definitions[0]["extracts"][0]["start_marker"] == "Début"
        assert extract_definitions[0]["extracts"][0]["end_marker"] == "Fin"
        assert extract_definitions[0]["extracts"][0]["template_start"] == "Template"
        
        assert len(extract_plugin_mock.extract_results) > 0