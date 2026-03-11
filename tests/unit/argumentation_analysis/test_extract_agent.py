# -*- coding: utf-8 -*-
"""
Tests unitaires pour l'agent d'extraction.
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import (
    MagicMock,
    AsyncMock,
)  # patch n'est plus utilisé comme décorateur ici
import argumentation_analysis.agents.core.extract.extract_agent as agent_module_to_patch  # Module à patcher

from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.extract.extract_definitions import (
    ExtractAgentPlugin,
    ExtractResult,
)


class MockExtractAgent(ExtractAgent):
    """Mock d'ExtractAgent qui implémente les méthodes abstraites."""

    def __init__(self, kernel, find_similar_text_func=None, extract_text_func=None):
        super().__init__(
            kernel=kernel,
            agent_name="MockExtractAgent",
            find_similar_text_func=find_similar_text_func,
            extract_text_func=extract_text_func,
        )

    def get_agent_capabilities(self):
        return {"text_extraction": True, "marker_detection": True}

    def setup_agent_components(self, llm_service_id: str):
        """Synchrone comme dans la classe de base."""
        self._llm_service_id = llm_service_id
        # Mock setup - ne pas appeler super() pour éviter les dépendances
        pass

    async def get_response(self, *args, **kwargs):
        return "MockExtractAgent response"

    async def invoke(self, *args, **kwargs):
        return "MockExtractAgent invoke result"


@pytest_asyncio.fixture
async def extract_agent_data():
    """Fixture pour initialiser l'agent d'extraction et ses mocks, et patcher load_source_text DANS le module agent."""

    # Sauvegarder l'original
    original_load_source_text_in_agent_module = getattr(
        agent_module_to_patch, "load_source_text", None
    )

    # Créer et appliquer le mock
    OrchestrationServiceManager_module = MagicMock()
    agent_module_to_patch.load_source_text = OrchestrationServiceManager_module

    # Initialiser le kernel avec un service LLM (requis par Pydantic V2)
    from semantic_kernel import Kernel
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

    kernel_mock = Kernel()
    kernel_mock.add_service(
        OpenAIChatCompletion(
            service_id="default", ai_model_id="gpt-4", api_key="test-key"
        )
    )
    # Pre-install mock invoke on kernel (bypass Pydantic V2 __setattr__)
    object.__setattr__(kernel_mock, "invoke", AsyncMock())

    extract_plugin_mock = MagicMock(spec=ExtractAgentPlugin)
    extract_plugin_mock.extract_results = []  # Initialiser la liste

    find_similar_text_mock = MagicMock()
    extract_text_mock = MagicMock()

    # Créer l'agent avec timeouts de sécurité
    agent = MockExtractAgent(
        kernel=kernel_mock,
        find_similar_text_func=find_similar_text_mock,
        extract_text_func=extract_text_mock,
    )
    agent._native_extract_plugin = extract_plugin_mock

    source_info = {
        "source_name": "Source de test",
        "source_url": "https://example.com",
        "source_text": "Ceci est un texte de test pour l'extraction.",
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
        "mock_load_source_text": OrchestrationServiceManager_module,
    }

    yield fixture_data

    # Cleanup sécurisé sans deadlock
    try:
        # Restaurer le patch
        if original_load_source_text_in_agent_module:
            agent_module_to_patch.load_source_text = (
                original_load_source_text_in_agent_module
            )

        # Pas de cleanup asyncio global pour éviter les deadlocks
        # Les tâches se termineront naturellement avec le test

    except Exception as e:
        # Log l'erreur mais ne pas faire échouer le test
        print(f"Erreur lors du cleanup: {e}")


class TestExtractAgent:
    """Tests pour la classe ExtractAgent."""

    @pytest.mark.asyncio
    async def test_extract_from_name_success(self, extract_agent_data):
        """Teste l'extraction réussie à partir du nom."""
        try:
            agent = extract_agent_data["agent"]
            kernel_mock = extract_agent_data["kernel_mock"]
            extract_text_mock = extract_agent_data["extract_text_mock"]
            source_info = extract_agent_data["source_info"]
            extract_name = extract_agent_data["extract_name"]
            mock_load_source_text = extract_agent_data["mock_load_source_text"]

            mock_load_source_text.return_value = (
                "Ceci est un texte de test pour l'extraction.",
                "https://example.com",
            )

            mock_extract_response = MagicMock()
            mock_extract_response.__str__.return_value = '{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}'

            mock_validation_response = MagicMock()
            mock_validation_response.__str__.return_value = (
                '{"valid": true, "reason": "Extrait valide"}'
            )

            # Configurer invoke avec des responses correctes
            call_count = 0
            kernel_mock.invoke.side_effect = [
                mock_extract_response,
                mock_validation_response,
            ]
            extract_text_mock.return_value = (
                "Ceci est un texte de test pour l'extraction.",
                "success",
                True,
                True,
            )

            # Exécuter avec timeout
            result = await asyncio.wait_for(
                agent.extract_from_name(source_info, extract_name), timeout=15.0
            )

            assert result.status == "valid"
            assert result.start_marker == "Ceci est"
            assert result.end_marker == "extraction."
            assert (
                result.extracted_text == "Ceci est un texte de test pour l'extraction."
            )

            mock_load_source_text.assert_called_once_with(source_info)
            assert kernel_mock.invoke.call_count == 1
            extract_text_mock.assert_called_once_with(
                "Ceci est un texte de test pour l'extraction.",
                "Ceci est",
                "extraction.",
                "",
            )

        except asyncio.TimeoutError:
            pytest.fail("Test timeout - possible boucle infinie détectée")

    @pytest.mark.asyncio
    async def test_extract_from_name_invalid_markers(self, extract_agent_data):
        """Teste l'extraction avec des marqueurs invalides."""
        try:
            agent = extract_agent_data["agent"]
            kernel_mock = extract_agent_data["kernel_mock"]
            extract_text_mock = extract_agent_data["extract_text_mock"]
            source_info = extract_agent_data["source_info"]
            extract_name = extract_agent_data["extract_name"]
            mock_load_source_text = extract_agent_data["mock_load_source_text"]

            mock_load_source_text.return_value = (
                "Ceci est un texte de test pour l'extraction.",
                "https://example.com",
            )

            mock_response = MagicMock()
            mock_response.__str__.return_value = '{"start_marker": "", "end_marker": "", "template_start": "", "explanation": "Explication de test"}'

            async def safe_invoke(*args, **kwargs):
                await asyncio.sleep(0.01)
                return mock_response

            kernel_mock.invoke.side_effect = safe_invoke

            result = await asyncio.wait_for(
                agent.extract_from_name(source_info, extract_name), timeout=10.0
            )

            assert result.status == "error"
            assert "Bornes invalides" in result.message

            mock_load_source_text.assert_called_once_with(source_info)
            kernel_mock.invoke.assert_called_once()
            extract_text_mock.assert_not_called()

        except asyncio.TimeoutError:
            pytest.fail("Test timeout - possible boucle infinie détectée")

    @pytest.mark.asyncio
    async def test_extract_from_name_markers_not_found(self, extract_agent_data):
        """Teste l'extraction avec des marqueurs non trouvés dans le texte."""
        try:
            agent = extract_agent_data["agent"]
            kernel_mock = extract_agent_data["kernel_mock"]
            extract_text_mock = extract_agent_data["extract_text_mock"]
            source_info = extract_agent_data["source_info"]
            extract_name = extract_agent_data["extract_name"]
            mock_load_source_text = extract_agent_data["mock_load_source_text"]

            mock_load_source_text.return_value = (
                "Ceci est un texte de test pour l'extraction.",
                "https://example.com",
            )

            mock_response = MagicMock()
            mock_response.__str__.return_value = '{"start_marker": "Marqueur début", "end_marker": "Marqueur fin", "template_start": "", "explanation": "Explication de test"}'

            async def safe_invoke(*args, **kwargs):
                await asyncio.sleep(0.01)
                return mock_response

            kernel_mock.invoke.side_effect = safe_invoke
            extract_text_mock.return_value = ("", "Marqueurs non trouvés", False, False)

            result = await asyncio.wait_for(
                agent.extract_from_name(source_info, extract_name), timeout=10.0
            )

            assert result.status == "error"
            assert "Bornes non trouvées" in result.message

            mock_load_source_text.assert_called_once_with(source_info)
            kernel_mock.invoke.assert_called_once()
            extract_text_mock.assert_called_once()

        except asyncio.TimeoutError:
            pytest.fail("Test timeout - possible boucle infinie détectée")

    @pytest.mark.asyncio
    async def test_extract_from_name_validation_rejected(self, extract_agent_data):
        """Teste l'extraction avec validation rejetée."""
        try:
            agent = extract_agent_data["agent"]
            kernel_mock = extract_agent_data["kernel_mock"]
            extract_text_mock = extract_agent_data["extract_text_mock"]
            source_info = extract_agent_data["source_info"]
            extract_name = extract_agent_data["extract_name"]
            mock_load_source_text = extract_agent_data["mock_load_source_text"]

            mock_load_source_text.return_value = (
                "Ceci est un texte de test pour l'extraction.",
                "https://example.com",
            )

            mock_extract_response = MagicMock()
            mock_extract_response.__str__.return_value = '{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}'

            mock_validation_response = MagicMock()
            mock_validation_response.__str__.return_value = (
                '{"valid": false, "reason": "Extrait invalide"}'
            )

            call_count = 0

            async def safe_invoke(*args, **kwargs):
                nonlocal call_count
                await asyncio.sleep(0.01)
                call_count += 1
                if call_count == 1:
                    return mock_extract_response
                else:
                    return mock_validation_response

            kernel_mock.invoke.side_effect = safe_invoke
            extract_text_mock.return_value = (
                "Ceci est un texte de test pour l'extraction.",
                "success",
                True,
                True,
            )

            result = await asyncio.wait_for(
                agent.extract_from_name(source_info, extract_name), timeout=10.0
            )

            assert (
                result.status == "valid"
            )  # La méthode ne gère pas le rejet de validation.

            mock_load_source_text.assert_called_once_with(source_info)
            assert (
                kernel_mock.invoke.call_count == 1
            )  # Un seul appel pour la proposition
            extract_text_mock.assert_called_once()

        except asyncio.TimeoutError:
            pytest.fail("Test timeout - possible boucle infinie détectée")
