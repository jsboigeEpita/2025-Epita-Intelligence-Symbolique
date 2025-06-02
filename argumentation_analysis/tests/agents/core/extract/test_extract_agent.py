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
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
from argumentation_analysis.agents.core.extract.extract_definitions import ExtractAgentPlugin, ExtractResult
from semantic_kernel.connectors.ai.chat_completion_client_base import ChatCompletionClientBase
from semantic_kernel import Kernel # Importer Kernel pour spec
from semantic_kernel.functions.function_result import FunctionResult


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
        # Mock pour le kernel Semantic Kernel
        self.mock_sk_kernel = MagicMock(spec=Kernel)
        
        # Mocker les méthodes du kernel qui seront appelées par setup_agent_components
        self.mock_sk_kernel.add_plugin = MagicMock()
        self.mock_sk_kernel.add_function = MagicMock()
        self.mock_sk_kernel.get_prompt_execution_settings_from_service_id = MagicMock(return_value=MagicMock(name="prompt_execution_settings"))

        # Initialiser l'agent avec le kernel mocké
        self.agent = ExtractAgent(kernel=self.mock_sk_kernel)
        
        # Appeler setup_agent_components.
        # ExtractAgentPlugin sera instancié à l'intérieur.
        # Nous allons mocker cette instanciation pour contrôler le plugin natif.
        self.mock_native_plugin_instance = MagicMock(spec=ExtractAgentPlugin)
        with patch('argumentation_analysis.agents.core.extract.extract_agent.ExtractAgentPlugin', return_value=self.mock_native_plugin_instance) as mock_plugin_class:
            self.agent.setup_agent_components(llm_service_id="test_llm_service_id")

        # Les fonctions utilitaires comme extract_text_with_markers sont importées dans extract_agent.py
        # et devront être patchées là si nécessaire pour les tests.
        # self.extract_text_mock = MagicMock() # Sera utilisé pour patcher la fonction globale

        self.source_info = {
            "source_name": "Source de test",
            "source_url": "https://example.com",
            "source_text": "Ceci est un texte de test pour l'extraction."
            # Note: source_text est ici pour info, mais load_source_text sera mocké
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
    @patch('argumentation_analysis.agents.core.extract.extract_agent.extract_text_with_markers')
    def test_extract_from_name_success(self, mock_extract_text_with_markers, mock_load_source_text):
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock pour sk_kernel.invoke
        # Il sera appelé deux fois : une pour l'extraction, une pour la validation.
        async def mock_invoke_side_effect(*args, **kwargs):
            invoked_plugin_name = kwargs.get('plugin_name')
            invoked_function_name = kwargs.get('function_name')
            
            if invoked_plugin_name == self.agent.name and invoked_function_name == ExtractAgent.EXTRACT_SEMANTIC_FUNCTION_NAME:
                # Réponse pour l'extraction
                response_mock = MagicMock()
                response_mock.__str__ = MagicMock(return_value='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
                return response_mock
            elif invoked_plugin_name == self.agent.name and invoked_function_name == ExtractAgent.VALIDATE_SEMANTIC_FUNCTION_NAME:
                # Réponse pour la validation
                response_mock = MagicMock()
                response_mock.__str__ = MagicMock(return_value='{"valid": true, "reason": "Extrait valide"}')
                return response_mock
            raise AssertionError(f"Appel inattendu à sk_kernel.invoke: {kwargs}")

        self.mock_sk_kernel.invoke = AsyncMock(side_effect=mock_invoke_side_effect)
        
        # Configurer le mock pour extract_text_with_markers (anciennement self.extract_text_mock)
        mock_extract_text_with_markers.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.start_marker, "Ceci est")
        self.assertEqual(result.end_marker, "extraction.")
        self.assertEqual(result.extracted_text, "Ceci est un texte de test pour l'extraction.")
        
        mock_load_source_text.assert_called_once_with(self.source_info)
        
        # Vérifier les appels à sk_kernel.invoke
        self.assertEqual(self.mock_sk_kernel.invoke.call_count, 2)
        # Vérifier le premier appel (extraction)
        extract_call_args = self.mock_sk_kernel.invoke.call_args_list[0]
        self.assertEqual(extract_call_args.kwargs['plugin_name'], self.agent.name)
        self.assertEqual(extract_call_args.kwargs['function_name'], ExtractAgent.EXTRACT_SEMANTIC_FUNCTION_NAME)
        # Vérifier le second appel (validation)
        validate_call_args = self.mock_sk_kernel.invoke.call_args_list[1]
        self.assertEqual(validate_call_args.kwargs['plugin_name'], self.agent.name)
        self.assertEqual(validate_call_args.kwargs['function_name'], ExtractAgent.VALIDATE_SEMANTIC_FUNCTION_NAME)

        mock_extract_text_with_markers.assert_called_once_with(
            "Ceci est un texte de test pour l'extraction.", "Ceci est", "extraction.", ""
        )

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    @patch('argumentation_analysis.agents.core.extract.extract_agent.extract_text_with_markers')
    def test_extract_from_name_large_text(self, mock_extract_text_with_markers, mock_load_source_text):
        large_text = "Ceci est un texte volumineux pour tester l'extraction. " * 500
        mock_load_source_text.return_value = (large_text, "https://example.com")

        # Mocker les méthodes du plugin natif (maintenant self.mock_native_plugin_instance)
        self.mock_native_plugin_instance.extract_blocks.return_value = [{"block": "Bloc 1", "start_pos": 0, "end_pos": 500}, {"block": "Bloc 2", "start_pos": 450, "end_pos": 950}]
        self.mock_native_plugin_instance.search_text_dichotomically.return_value = [{"match": "test", "position": 100, "context": "contexte", "block_start": 0, "block_end": 500}]
        
        # Configurer le mock pour sk_kernel.invoke
        async def mock_invoke_side_effect(*args, **kwargs):
            invoked_plugin_name = kwargs.get('plugin_name')
            invoked_function_name = kwargs.get('function_name')
            if invoked_plugin_name == self.agent.name and invoked_function_name == ExtractAgent.EXTRACT_SEMANTIC_FUNCTION_NAME:
                response_mock = MagicMock()
                response_mock.__str__ = MagicMock(return_value='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
                return response_mock
            elif invoked_plugin_name == self.agent.name and invoked_function_name == ExtractAgent.VALIDATE_SEMANTIC_FUNCTION_NAME:
                response_mock = MagicMock()
                response_mock.__str__ = MagicMock(return_value='{"valid": true, "reason": "Extrait valide"}')
                return response_mock
            raise AssertionError(f"Appel inattendu à sk_kernel.invoke: {kwargs}")
        self.mock_sk_kernel.invoke = AsyncMock(side_effect=mock_invoke_side_effect)
        
        # Configurer le mock pour extract_text_with_markers
        mock_extract_text_with_markers.return_value = ("Extrait de texte", "success", True, True)
        
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        
        self.assertEqual(result.status, "valid")
        mock_load_source_text.assert_called_once_with(self.source_info)
        
        # Vérifier les appels aux méthodes du plugin natif
        self.mock_native_plugin_instance.extract_blocks.assert_called_once()
        self.mock_native_plugin_instance.search_text_dichotomically.assert_called() # Peut être appelé plusieurs fois
        
        # Vérifier les appels à sk_kernel.invoke
        self.assertEqual(self.mock_sk_kernel.invoke.call_count, 2)
        
        mock_extract_text_with_markers.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    @patch('argumentation_analysis.core.utils.text_utils.extract_text_with_markers') # Correction de l'emplacement du patch
    def test_extract_from_name_json_error(self, mock_extract_text_with_markers, mock_load_source_text):
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock pour sk_kernel.invoke pour simuler une réponse non-JSON
        async def mock_invoke_side_effect(*args, **kwargs):
            invoked_plugin_name = kwargs.get('plugin_name')
            invoked_function_name = kwargs.get('function_name')
            kernel_arguments = kwargs.get('arguments', {})

            if invoked_plugin_name == self.agent.plugin_name and invoked_function_name == ExtractAgent.EXTRACT_SEMANTIC_FUNCTION_NAME:
                # Réponse non-JSON pour l'extraction
                response_mock = MagicMock(spec=FunctionResult)
                response_mock.value = 'Réponse non-JSON avec "start_marker": "Ceci est", "end_marker": "extraction.", "explanation": "Explication"'
                response_mock.__str__ = lambda self_mock: self_mock.value # Assurer que str(response_mock) retourne la string
                return response_mock
            elif invoked_plugin_name == self.agent.plugin_name and invoked_function_name == ExtractAgent.VALIDATE_SEMANTIC_FUNCTION_NAME:
                # Réponse valide pour la validation (peut être appelée ou non selon l'échec)
                response_mock = MagicMock(spec=FunctionResult)
                response_mock.value = '{"valid": true, "reason": "Extrait valide"}'
                response_mock.__str__ = lambda self_mock: self_mock.value
                return response_mock
            # Gérer l'appel au plugin natif si nécessaire (ne devrait pas arriver dans ce test si l'erreur JSON est première)
            elif invoked_plugin_name == ExtractAgentPlugin.PLUGIN_NAME:
                 # Simuler le comportement du plugin natif si besoin, ou juste retourner un mock
                native_response_mock = MagicMock()
                # ... configurer le mock pour le plugin natif ...
                return native_response_mock

            raise AssertionError(f"Appel inattendu à sk_kernel.invoke: plugin_name='{invoked_plugin_name}', function_name='{invoked_function_name}', args='{kernel_arguments}'")

        self.mock_sk_kernel.invoke = AsyncMock(side_effect=mock_invoke_side_effect)
        
        # extract_text_with_markers ne devrait pas être appelé si l'invoke initial échoue à parser le JSON.
        # On s'attend à ce que l'erreur JSON se produise lors du traitement de la réponse de EXTRACT_SEMANTIC_FUNCTION_NAME.
        
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        
        self.assertEqual(result.status, "error")
        self.assertIn("Erreur lors du parsing de la réponse JSON", result.error_message)
        mock_load_source_text.assert_called_once_with(self.source_info)
        
        # Vérifier que la fonction sémantique d'extraction a été appelée
        # On ne peut plus utiliser assert_any_call facilement avec AsyncMock et side_effect complexe.
        # On vérifie que invoke a été appelé au moins une fois.
        self.mock_sk_kernel.invoke.assert_called()
        
        # Vérifier que la première tentative d'appel était bien pour l'extraction
        # Cela peut être fragile si d'autres appels invoke se produisent avant pour une raison quelconque.
        # S'assurer que le side_effect est assez robuste ou que les tests sont bien isolés.
        if self.mock_sk_kernel.invoke.call_args_list: # Vérifier s'il y a eu des appels
            first_call_args = self.mock_sk_kernel.invoke.call_args_list[0]
            self.assertEqual(first_call_args.kwargs.get('plugin_name'), self.agent.plugin_name)
            self.assertEqual(first_call_args.kwargs.get('function_name'), ExtractAgent.EXTRACT_SEMANTIC_FUNCTION_NAME)
        else:
            self.fail("self.mock_sk_kernel.invoke n'a pas été appelé.")

        mock_extract_text_with_markers.assert_not_called()
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


# La classe TestSetupExtractAgent est supprimée car la fonction setup_extract_agent n'existe plus.
# Les tests pour l'initialisation de ExtractAgent devront être intégrés différemment si nécessaire,
# potentiellement en testant directement le constructeur et la méthode setup_agent_components.

if __name__ == "__main__":
    unittest.main()