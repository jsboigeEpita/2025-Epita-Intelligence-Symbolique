# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module extract_agent.

Ce module contient les tests unitaires pour les classes et fonctions définies dans le module
agents.core.extract.extract_agent.
"""

import unittest
import asyncio
import json
import re
from unittest.mock import MagicMock, patch, AsyncMock
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent, setup_extract_agent
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractAgentPlugin, ExtractResult
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel import Kernel # Importer Kernel pour spec


class AsyncTestCase(unittest.TestCase):
    """Classe de base pour les tests asynchrones."""
    
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        self.loop.close()
    
    def _run_async_test(self, coro):
        return self.loop.run_until_complete(coro)


class TestExtractAgent(AsyncTestCase):
    """Tests pour la classe ExtractAgent."""

    def setUp(self):
        super().setUp()
        self.extract_agent_mock = MagicMock()
        self.validation_agent_mock = MagicMock()
        self.extract_plugin_mock = MagicMock(spec=ExtractAgentPlugin)
        self.find_similar_text_mock = MagicMock()
        self.extract_text_mock = MagicMock()
        self.agent = ExtractAgent(
            extract_agent=self.extract_agent_mock,
            validation_agent=self.validation_agent_mock,
            extract_plugin=self.extract_plugin_mock,
            find_similar_text_func=self.find_similar_text_mock,
            extract_text_func=self.extract_text_mock
        )
        self.source_info = {
            "source_name": "Source de test",
            "source_url": "https://example.com",
            "source_text": "Ceci est un texte de test pour l'extraction."
        }
        self.extract_name = "Extrait de test"

    def _create_async_iterator(self, items):
        class AsyncIterator:
            def __init__(self, items):
                self.items = items
                self.index = 0
            def __aiter__(self):
                return self
            async def __anext__(self):
                if self.index < len(self.items):
                    item = self.items[self.index]
                    self.index += 1
                    return item
                else:
                    raise StopAsyncIteration
        return AsyncIterator(items)

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_success(self, mock_load_source_text):
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        self.extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        mock_validation_response = MagicMock(content='{"valid": true, "reason": "Extrait valide"}')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.start_marker, "Ceci est")
        self.assertEqual(result.end_marker, "extraction.")
        self.assertEqual(result.extracted_text, "Ceci est un texte de test pour l'extraction.")
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_called_once_with(
            "Ceci est un texte de test pour l'extraction.", "Ceci est", "extraction.", ""
        )
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_large_text(self, mock_load_source_text):
        large_text = "Ceci est un texte volumineux pour tester l'extraction. " * 500
        mock_load_source_text.return_value = (large_text, "https://example.com")
        self.extract_plugin_mock.extract_blocks.return_value = [{"block": "Bloc 1", "start_pos": 0, "end_pos": 500}, {"block": "Bloc 2", "start_pos": 450, "end_pos": 950}]
        self.extract_plugin_mock.search_text_dichotomically.return_value = [{"match": "test", "position": 100, "context": "contexte", "block_start": 0, "block_end": 500}]
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        self.extract_text_mock.return_value = ("Extrait de texte", "success", True, True)
        mock_validation_response = MagicMock(content='{"valid": true, "reason": "Extrait valide"}')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        self.assertEqual(result.status, "valid")
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_plugin_mock.extract_blocks.assert_called_once()
        self.extract_plugin_mock.search_text_dichotomically.assert_called()
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_called_once()
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_json_error(self, mock_load_source_text):
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        mock_response = MagicMock(content='Réponse non-JSON avec "start_marker": "Ceci est", "end_marker": "extraction.", "explanation": "Explication"')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        self.extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        mock_validation_response = MagicMock(content='{"valid": true, "reason": "Extrait valide"}')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        self.assertEqual(result.start_marker, "Ceci est")
        self.assertEqual(result.end_marker, "extraction.")
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_validation_json_error(self, mock_load_source_text):
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        self.extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        mock_validation_response = MagicMock(content='Réponse non-JSON avec "valid": true, "reason": "Extrait valide"')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        self.assertEqual(result.status, "valid")
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_agent_error(self, mock_load_source_text):
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        self.extract_agent_mock.invoke = MagicMock(side_effect=Exception("Erreur de l'agent"))
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        self.assertEqual(result.status, "error")
        self.assertIn("Erreur lors de l'invocation de l'agent d'extraction", result.message)
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_not_called()
        self.validation_agent_mock.assert_not_called()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_validation_error(self, mock_load_source_text):
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        self.extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        self.validation_agent_mock.invoke = MagicMock(side_effect=Exception("Erreur de validation"))
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        self.assertEqual(result.status, "error")
        self.assertIn("Erreur lors de l'invocation de l'agent de validation", result.message)
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_called_once()
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_repair_extract_invalid_markers(self, mock_load_source_text):
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        self.extract_text_mock.return_value = ("", "Marqueurs non trouvés", False, False)
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        mock_validation_response = MagicMock(content='{"valid": true, "reason": "Extrait valide"}')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        extract_definitions = [{"source_name": "Source de test", "source_url": "https://example.com", "extracts": [{"extract_name": "Extrait de test", "start_marker": "Marqueur invalide", "end_marker": "Autre marqueur invalide"}]}]
        self.extract_text_mock.side_effect = [("", "Marqueurs non trouvés", False, False), ("Ceci est un texte de test pour l'extraction.", "success", True, True)]
        result = self._run_async_test(self.agent.repair_extract(extract_definitions, 0, 0))
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.start_marker, "Ceci est")
        self.assertEqual(result.end_marker, "extraction.")
        mock_load_source_text.assert_called_with(extract_definitions[0])
        self.assertEqual(mock_load_source_text.call_count, 2)
        self.extract_text_mock.assert_called()
        self.assertEqual(self.extract_text_mock.call_count, 2)
        self.extract_agent_mock.invoke.assert_called_once()
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_repair_extract_source_not_found(self, mock_load_source_text):
        mock_load_source_text.return_value = (None, "https://example.com")
        extract_definitions = [{"source_name": "Source de test", "source_url": "https://example.com", "extracts": [{"extract_name": "Extrait de test", "start_marker": "Début", "end_marker": "Fin"}]}]
        result = self._run_async_test(self.agent.repair_extract(extract_definitions, 0, 0))
        self.assertEqual(result.status, "error")
        self.assertIn("Impossible de charger le texte source", result.message)
        mock_load_source_text.assert_called_once_with(extract_definitions[0])
        self.extract_text_mock.assert_not_called()
        self.extract_agent_mock.invoke.assert_not_called()
        self.validation_agent_mock.assert_not_called()

    def test_update_extract_markers_invalid_result(self):
        result = ExtractResult(source_name="Source de test", extract_name="Extrait de test", status="error", message="Erreur lors de l'extraction", start_marker="Début", end_marker="Fin")
        extract_definitions = [{"source_name": "Source de test", "extracts": [{"extract_name": "Extrait de test", "start_marker": "Ancien début", "end_marker": "Ancienne fin"}]}]
        success = self._run_async_test(self.agent.update_extract_markers(extract_definitions, 0, 0, result))
        self.assertFalse(success)
        self.assertEqual(extract_definitions[0]["extracts"][0]["start_marker"], "Ancien début")
        self.assertEqual(extract_definitions[0]["extracts"][0]["end_marker"], "Ancienne fin")

    def test_update_extract_markers_invalid_indices(self):
        result = ExtractResult(source_name="Source de test", extract_name="Extrait de test", status="valid", message="Extraction réussie", start_marker="Nouveau début", end_marker="Nouvelle fin", template_start="Template")
        extract_definitions = [{"source_name": "Source de test", "extracts": [{"extract_name": "Extrait de test", "start_marker": "Ancien début", "end_marker": "Ancienne fin"}]}]
        success = self._run_async_test(self.agent.update_extract_markers(extract_definitions, 1, 0, result))
        self.assertFalse(success)
        success = self._run_async_test(self.agent.update_extract_markers(extract_definitions, 0, 1, result))
        self.assertFalse(success)

    def test_add_new_extract_invalid_result(self):
        result = ExtractResult(source_name="Source de test", extract_name="Nouvel extrait", status="error", message="Erreur lors de l'extraction", start_marker="Début", end_marker="Fin")
        extract_definitions = [{"source_name": "Source de test", "extracts": []}]
        success, extract_idx = self._run_async_test(self.agent.add_new_extract(extract_definitions, 0, "Nouvel extrait", result))
        self.assertFalse(success)
        self.assertEqual(extract_idx, -1)
        self.assertEqual(len(extract_definitions[0]["extracts"]), 0)

    def test_add_new_extract_invalid_source_index(self):
        result = ExtractResult(source_name="Source de test", extract_name="Nouvel extrait", status="valid", message="Extraction réussie", start_marker="Début", end_marker="Fin", template_start="Template")
        extract_definitions = [{"source_name": "Source de test", "extracts": []}]
        success, extract_idx = self._run_async_test(self.agent.add_new_extract(extract_definitions, 1, "Nouvel extrait", result))
        self.assertFalse(success)
        self.assertEqual(extract_idx, -1)
        self.assertEqual(len(extract_definitions[0]["extracts"]), 0)


class TestSetupExtractAgent(AsyncTestCase):
    """Tests pour la fonction setup_extract_agent."""

    @patch('argumentation_analysis.agents.core.extract.extract_agent.create_llm_service')
    @patch('argumentation_analysis.agents.core.extract.extract_agent.sk.Kernel') 
    @patch('argumentation_analysis.agents.core.extract.extract_agent.ChatCompletionAgent') # Patcher la référence locale
    def test_setup_extract_agent_success(self, mock_chat_agent, mock_kernel_class, mock_create_llm_service):
        """Teste la configuration réussie de l'agent d'extraction."""
        mock_llm_service = MagicMock(spec=ChatCompletionClientBase)
        mock_llm_service.service_id = "mocked_service_id" 
        mock_llm_service.ai_model_id = "mocked_ai_model_id"
        mock_create_llm_service.return_value = mock_llm_service
        
        mock_kernel_instance = MagicMock(spec=Kernel) 
        mock_kernel_class.return_value = mock_kernel_instance 
        mock_prompt_settings = MagicMock() 
        mock_kernel_instance.get_prompt_execution_settings_from_service_id.return_value = mock_prompt_settings
        
        mock_extract_agent = MagicMock()
        mock_validation_agent = MagicMock()
        mock_chat_agent.side_effect = [mock_extract_agent, mock_validation_agent]
        
        kernel, agent = self._run_async_test(setup_extract_agent()) # Appel sans llm_service
        
        self.assertIs(kernel, mock_kernel_instance) 
        self.assertIsInstance(agent, ExtractAgent)
        mock_create_llm_service.assert_called_once()
        mock_kernel_class.assert_called_once() 
        mock_kernel_instance.add_service.assert_any_call(mock_llm_service)
        self.assertEqual(mock_chat_agent.call_count, 2)

    @patch('argumentation_analysis.agents.core.extract.extract_agent.create_llm_service')
    def test_setup_extract_agent_llm_service_error(self, mock_create_llm_service):
        """Teste la configuration de l'agent d'extraction avec une erreur de service LLM."""
        mock_create_llm_service.return_value = None
        
        kernel, agent = self._run_async_test(setup_extract_agent())
        
        self.assertIsNone(kernel)
        self.assertIsNone(agent)
        mock_create_llm_service.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.sk.Kernel') 
    @patch('argumentation_analysis.agents.core.extract.extract_agent.ChatCompletionAgent') # Patcher la référence locale
    def test_setup_extract_agent_with_custom_llm_service(self, mock_chat_agent, mock_kernel_class):
        """Teste la configuration de l'agent d'extraction avec un service LLM personnalisé."""
        mock_llm_service = MagicMock(spec=ChatCompletionClientBase)
        mock_llm_service.service_id = "custom_service" 
        mock_llm_service.ai_model_id = "custom_ai_model_id"
        
        mock_kernel_instance = MagicMock(spec=Kernel) 
        mock_kernel_class.return_value = mock_kernel_instance 
        mock_prompt_settings = MagicMock()
        mock_kernel_instance.get_prompt_execution_settings_from_service_id.return_value = mock_prompt_settings
            
        mock_extract_agent = MagicMock()
        mock_validation_agent = MagicMock()
        mock_chat_agent.side_effect = [mock_extract_agent, mock_validation_agent]
            
        kernel, agent = self._run_async_test(setup_extract_agent(llm_service=mock_llm_service))
            
        self.assertIs(kernel, mock_kernel_instance) 
        self.assertIsInstance(agent, ExtractAgent)
        mock_kernel_class.assert_called_once() 
        mock_kernel_instance.add_service.assert_any_call(mock_llm_service)
        self.assertEqual(mock_chat_agent.call_count, 2)


if __name__ == "__main__":
    unittest.main()