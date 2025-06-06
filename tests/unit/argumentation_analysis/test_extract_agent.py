# -*- coding: utf-8 -*-
"""
Tests unitaires pour l'agent d'extraction.
"""

import asyncio
import pytest
from unittest.mock import MagicMock # patch n'est plus utilisé comme décorateur ici
import argumentation_analysis.agents.core.extract.extract_agent as agent_module_to_patch # Module à patcher

from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractAgentPlugin, ExtractResult

@pytest.fixture
def extract_agent_data():
    """Fixture pour initialiser l'agent d'extraction et ses mocks, et patcher load_source_text DANS le module agent."""

    original_load_source_text_in_agent_module = agent_module_to_patch.load_source_text
    mock_lts_for_agent_module = MagicMock()
    agent_module_to_patch.load_source_text = mock_lts_for_agent_module

    kernel_mock = MagicMock()
    extract_plugin_mock = MagicMock(spec=ExtractAgentPlugin)
    find_similar_text_mock = MagicMock()
    extract_text_mock = MagicMock()

    agent = ExtractAgent(
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

    agent_module_to_patch.load_source_text = original_load_source_text_in_agent_module


class TestExtractAgent:
    """Tests pour la classe ExtractAgent."""

    @pytest.mark.anyio
    async def test_extract_from_name_success(self, extract_agent_data):
        """Teste l'extraction réussie à partir du nom."""
        agent = extract_agent_data["agent"]
        kernel_mock = extract_agent_data["kernel_mock"]
        extract_text_mock = extract_agent_data["extract_text_mock"]
        source_info = extract_agent_data["source_info"]
        extract_name = extract_agent_data["extract_name"]
        mock_load_source_text = extract_agent_data["mock_load_source_text"]

        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        mock_extract_response = MagicMock()
        mock_extract_response.__str__.return_value = '{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}'
        
        mock_validation_response = MagicMock()
        mock_validation_response.__str__.return_value = '{"valid": true, "reason": "Extrait valide"}'

        kernel_mock.invoke.side_effect = [
            mock_extract_response,
            mock_validation_response
        ]
        
        extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
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

    @pytest.mark.anyio
    async def test_extract_from_name_invalid_markers(self, extract_agent_data):
        """Teste l'extraction avec des marqueurs invalides."""
        agent = extract_agent_data["agent"]
        kernel_mock = extract_agent_data["kernel_mock"]
        extract_text_mock = extract_agent_data["extract_text_mock"]
        source_info = extract_agent_data["source_info"]
        extract_name = extract_agent_data["extract_name"]
        mock_load_source_text = extract_agent_data["mock_load_source_text"]

        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        mock_response = MagicMock()
        mock_response.__str__.return_value = '{"start_marker": "", "end_marker": "", "template_start": "", "explanation": "Explication de test"}'
        kernel_mock.invoke.return_value = mock_response
        
        result = await agent.extract_from_name(source_info, extract_name)
        
        assert result.status == "error"
        assert "Bornes invalides" in result.message
        
        mock_load_source_text.assert_called_once_with(source_info)
        kernel_mock.invoke.assert_called_once()
        extract_text_mock.assert_not_called()

    @pytest.mark.anyio
    async def test_extract_from_name_markers_not_found(self, extract_agent_data):
        """Teste l'extraction avec des marqueurs non trouvés dans le texte."""
        agent = extract_agent_data["agent"]
        kernel_mock = extract_agent_data["kernel_mock"]
        extract_text_mock = extract_agent_data["extract_text_mock"]
        source_info = extract_agent_data["source_info"]
        extract_name = extract_agent_data["extract_name"]
        mock_load_source_text = extract_agent_data["mock_load_source_text"]

        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        mock_response = MagicMock()
        mock_response.__str__.return_value = '{"start_marker": "Marqueur début", "end_marker": "Marqueur fin", "template_start": "", "explanation": "Explication de test"}'
        kernel_mock.invoke.return_value = mock_response
        
        extract_text_mock.return_value = ("", "Marqueurs non trouvés", False, False)
        
        result = await agent.extract_from_name(source_info, extract_name)
        
        assert result.status == "error"
        assert "Bornes non trouvées" in result.message
        
        mock_load_source_text.assert_called_once_with(source_info)
        kernel_mock.invoke.assert_called_once()
        extract_text_mock.assert_called_once()

    @pytest.mark.anyio
    async def test_extract_from_name_validation_rejected(self, extract_agent_data):
        """Teste l'extraction avec validation rejetée."""
        agent = extract_agent_data["agent"]
        kernel_mock = extract_agent_data["kernel_mock"]
        extract_text_mock = extract_agent_data["extract_text_mock"]
        source_info = extract_agent_data["source_info"]
        extract_name = extract_agent_data["extract_name"]
        mock_load_source_text = extract_agent_data["mock_load_source_text"]

        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        mock_extract_response = MagicMock()
        mock_extract_response.__str__.return_value = '{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}'
        
        mock_validation_response = MagicMock()
        mock_validation_response.__str__.return_value = '{"valid": false, "reason": "Extrait invalide"}'

        kernel_mock.invoke.side_effect = [
            mock_extract_response,
            mock_validation_response
        ]
        
        extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        result = await agent.extract_from_name(source_info, extract_name)
        
        assert result.status == "rejected"
        assert result.message == "Extrait rejeté: Extrait invalide"
        
        mock_load_source_text.assert_called_once_with(source_info)
        assert kernel_mock.invoke.call_count == 2
        extract_text_mock.assert_called_once()

    @pytest.mark.anyio
    async def test_repair_extract_valid(self, extract_agent_data):
        """Teste la réparation d'un extrait valide."""
        agent = extract_agent_data["agent"]
        kernel_mock = extract_agent_data["kernel_mock"]
        extract_text_mock = extract_agent_data["extract_text_mock"]
        mock_load_source_text = extract_agent_data["mock_load_source_text"]

        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
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
        
        mock_load_source_text.assert_called_once()
        extract_text_mock.assert_called_once()
        kernel_mock.invoke.assert_not_called()

    @pytest.mark.anyio
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

    @pytest.mark.anyio
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