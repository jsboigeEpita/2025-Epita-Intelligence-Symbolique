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


class AsyncTestCase(unittest.TestCase):
    """Classe de base pour les tests asynchrones."""
    
    def setUp(self):
        """Initialisation avant chaque test."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """Nettoyage après chaque test."""
        self.loop.close()
    
    def _run_async_test(self, coro):
        """Exécute un test asynchrone."""
        return self.loop.run_until_complete(coro)


class TestExtractAgent(AsyncTestCase):
    """Tests pour la classe ExtractAgent."""

    def setUp(self):
        """Initialisation avant chaque test."""
        super().setUp()
        
        # Créer des mocks pour les dépendances
        self.extract_agent_mock = MagicMock()
        self.validation_agent_mock = MagicMock()
        self.extract_plugin_mock = MagicMock(spec=ExtractAgentPlugin)
        self.find_similar_text_mock = MagicMock()
        self.extract_text_mock = MagicMock()
        
        # Créer l'agent d'extraction avec les mocks
        self.agent = ExtractAgent(
            extract_agent=self.extract_agent_mock,
            validation_agent=self.validation_agent_mock,
            extract_plugin=self.extract_plugin_mock,
            find_similar_text_func=self.find_similar_text_mock,
            extract_text_func=self.extract_text_mock
        )
        
        # Données de test
        self.source_info = {
            "source_name": "Source de test",
            "source_url": "https://example.com",
            "source_text": "Ceci est un texte de test pour l'extraction."
        }
        self.extract_name = "Extrait de test"

    def _create_async_iterator(self, items):
        """Crée un itérateur asynchrone à partir d'une liste d'éléments."""
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
        """Teste l'extraction réussie à partir du nom."""
        # Configurer les mocks
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock de l'agent d'extraction pour retourner une réponse JSON
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        
        # Configurer le mock de l'extraction de texte
        self.extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        # Configurer le mock de l'agent de validation
        mock_validation_response = MagicMock(content='{"valid": true, "reason": "Extrait valide"}')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        
        # Appeler la méthode à tester
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        
        # Vérifier les résultats
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.start_marker, "Ceci est")
        self.assertEqual(result.end_marker, "extraction.")
        self.assertEqual(result.extracted_text, "Ceci est un texte de test pour l'extraction.")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_called_once_with(
            "Ceci est un texte de test pour l'extraction.", 
            "Ceci est", 
            "extraction.", 
            ""
        )
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_large_text(self, mock_load_source_text):
        """Teste l'extraction à partir du nom avec un texte volumineux."""
        # Créer un texte volumineux
        large_text = "Ceci est un texte volumineux pour tester l'extraction. " * 500
        
        # Configurer les mocks
        mock_load_source_text.return_value = (large_text, "https://example.com")
        
        # Configurer le mock du plugin d'extraction
        self.extract_plugin_mock.extract_blocks.return_value = [
            {"block": "Bloc 1", "start_pos": 0, "end_pos": 500},
            {"block": "Bloc 2", "start_pos": 450, "end_pos": 950}
        ]
        self.extract_plugin_mock.search_text_dichotomically.return_value = [
            {"match": "test", "position": 100, "context": "contexte", "block_start": 0, "block_end": 500}
        ]
        
        # Configurer le mock de l'agent d'extraction pour retourner une réponse JSON
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        
        # Configurer le mock de l'extraction de texte
        self.extract_text_mock.return_value = ("Extrait de texte", "success", True, True)
        
        # Configurer le mock de l'agent de validation
        mock_validation_response = MagicMock(content='{"valid": true, "reason": "Extrait valide"}')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        
        # Appeler la méthode à tester
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        
        # Vérifier les résultats
        self.assertEqual(result.status, "valid")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_plugin_mock.extract_blocks.assert_called_once()
        self.extract_plugin_mock.search_text_dichotomically.assert_called()
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_called_once()
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_json_error(self, mock_load_source_text):
        """Teste l'extraction avec une erreur de parsing JSON."""
        # Configurer les mocks
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock de l'agent d'extraction pour retourner une réponse non-JSON
        mock_response = MagicMock(content='Réponse non-JSON avec "start_marker": "Ceci est", "end_marker": "extraction.", "explanation": "Explication"')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        
        # Configurer le mock de l'extraction de texte
        self.extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        # Configurer le mock de l'agent de validation
        mock_validation_response = MagicMock(content='{"valid": true, "reason": "Extrait valide"}')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        
        # Appeler la méthode à tester
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        
        # Vérifier que l'extraction a réussi malgré l'erreur de parsing JSON
        self.assertEqual(result.start_marker, "Ceci est")
        self.assertEqual(result.end_marker, "extraction.")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_validation_json_error(self, mock_load_source_text):
        """Teste l'extraction avec une erreur de parsing JSON dans la validation."""
        # Configurer les mocks
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock de l'agent d'extraction pour retourner une réponse JSON
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        
        # Configurer le mock de l'extraction de texte
        self.extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        # Configurer le mock de l'agent de validation pour retourner une réponse non-JSON
        mock_validation_response = MagicMock(content='Réponse non-JSON avec "valid": true, "reason": "Extrait valide"')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        
        # Appeler la méthode à tester
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        
        # Vérifier que la validation a réussi malgré l'erreur de parsing JSON
        self.assertEqual(result.status, "valid")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_agent_error(self, mock_load_source_text):
        """Teste l'extraction avec une erreur de l'agent d'extraction."""
        # Configurer les mocks
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock de l'agent d'extraction pour lever une exception
        self.extract_agent_mock.invoke = MagicMock(side_effect=Exception("Erreur de l'agent"))
        
        # Appeler la méthode à tester
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        
        # Vérifier les résultats
        self.assertEqual(result.status, "error")
        self.assertIn("Erreur lors de l'invocation de l'agent d'extraction", result.message)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_not_called()
        self.validation_agent_mock.assert_not_called()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_extract_from_name_validation_error(self, mock_load_source_text):
        """Teste l'extraction avec une erreur de l'agent de validation."""
        # Configurer les mocks
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock de l'agent d'extraction pour retourner une réponse JSON
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        
        # Configurer le mock de l'extraction de texte
        self.extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        # Configurer le mock de l'agent de validation pour lever une exception
        self.validation_agent_mock.invoke = MagicMock(side_effect=Exception("Erreur de validation"))
        
        # Appeler la méthode à tester
        result = self._run_async_test(self.agent.extract_from_name(self.source_info, self.extract_name))
        
        # Vérifier les résultats
        self.assertEqual(result.status, "error")
        self.assertIn("Erreur lors de l'invocation de l'agent de validation", result.message)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_called_once()
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_repair_extract_invalid_markers(self, mock_load_source_text):
        """Teste la réparation d'un extrait avec des marqueurs invalides."""
        # Configurer les mocks
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock de l'extraction de texte pour indiquer que les marqueurs sont invalides
        self.extract_text_mock.return_value = ("", "Marqueurs non trouvés", False, False)
        
        # Configurer le mock de l'agent d'extraction pour retourner une réponse JSON
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        
        # Configurer le mock de l'agent de validation
        mock_validation_response = MagicMock(content='{"valid": true, "reason": "Extrait valide"}')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        
        # Créer des définitions d'extraits de test
        extract_definitions = [
            {
                "source_name": "Source de test",
                "source_url": "https://example.com",
                "extracts": [
                    {
                        "extract_name": "Extrait de test",
                        "start_marker": "Marqueur invalide",
                        "end_marker": "Autre marqueur invalide"
                    }
                ]
            }
        ]
        
        # Configurer le mock de l'extraction de texte pour la deuxième tentative
        self.extract_text_mock.side_effect = [
            ("", "Marqueurs non trouvés", False, False),  # Première tentative (échec)
            ("Ceci est un texte de test pour l'extraction.", "success", True, True)  # Deuxième tentative (succès)
        ]
        
        # Appeler la méthode à tester
        result = self._run_async_test(self.agent.repair_extract(extract_definitions, 0, 0))
        
        # Vérifier les résultats
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.start_marker, "Ceci est")
        self.assertEqual(result.end_marker, "extraction.")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_with(extract_definitions[0])
        self.assertEqual(mock_load_source_text.call_count, 2)
        self.extract_text_mock.assert_called()
        self.assertEqual(self.extract_text_mock.call_count, 2)
        self.extract_agent_mock.invoke.assert_called_once()
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('argumentation_analysis.agents.core.extract.extract_agent.load_source_text')
    def test_repair_extract_source_not_found(self, mock_load_source_text):
        """Teste la réparation d'un extrait avec une source non trouvée."""
        # Configurer les mocks
        mock_load_source_text.return_value = (None, "https://example.com")
        
        # Créer des définitions d'extraits de test
        extract_definitions = [
            {
                "source_name": "Source de test",
                "source_url": "https://example.com",
                "extracts": [
                    {
                        "extract_name": "Extrait de test",
                        "start_marker": "Début",
                        "end_marker": "Fin"
                    }
                ]
            }
        ]
        
        # Appeler la méthode à tester
        result = self._run_async_test(self.agent.repair_extract(extract_definitions, 0, 0))
        
        # Vérifier les résultats
        self.assertEqual(result.status, "error")
        self.assertIn("Impossible de charger le texte source", result.message)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once_with(extract_definitions[0])
        self.extract_text_mock.assert_not_called()
        self.extract_agent_mock.invoke.assert_not_called()
        self.validation_agent_mock.assert_not_called()

    def test_update_extract_markers_invalid_result(self):
        """Teste la mise à jour des marqueurs avec un résultat invalide."""
        # Créer un résultat d'extraction invalide
        result = ExtractResult(
            source_name="Source de test",
            extract_name="Extrait de test",
            status="error",
            message="Erreur lors de l'extraction",
            start_marker="Début",
            end_marker="Fin"
        )
        
        # Créer des définitions d'extraits de test
        extract_definitions = [
            {
                "source_name": "Source de test",
                "extracts": [
                    {
                        "extract_name": "Extrait de test",
                        "start_marker": "Ancien début",
                        "end_marker": "Ancienne fin"
                    }
                ]
            }
        ]
        
        # Appeler la méthode à tester
        success = self._run_async_test(self.agent.update_extract_markers(extract_definitions, 0, 0, result))
        
        # Vérifier les résultats
        self.assertFalse(success)
        
        # Vérifier que les marqueurs n'ont pas été mis à jour
        self.assertEqual(extract_definitions[0]["extracts"][0]["start_marker"], "Ancien début")
        self.assertEqual(extract_definitions[0]["extracts"][0]["end_marker"], "Ancienne fin")

    def test_update_extract_markers_invalid_indices(self):
        """Teste la mise à jour des marqueurs avec des indices invalides."""
        # Créer un résultat d'extraction valide
        result = ExtractResult(
            source_name="Source de test",
            extract_name="Extrait de test",
            status="valid",
            message="Extraction réussie",
            start_marker="Nouveau début",
            end_marker="Nouvelle fin",
            template_start="Template"
        )
        
        # Créer des définitions d'extraits de test
        extract_definitions = [
            {
                "source_name": "Source de test",
                "extracts": [
                    {
                        "extract_name": "Extrait de test",
                        "start_marker": "Ancien début",
                        "end_marker": "Ancienne fin"
                    }
                ]
            }
        ]
        
        # Tester avec un index de source invalide
        success = self._run_async_test(self.agent.update_extract_markers(extract_definitions, 1, 0, result))
        self.assertFalse(success)
        
        # Tester avec un index d'extrait invalide
        success = self._run_async_test(self.agent.update_extract_markers(extract_definitions, 0, 1, result))
        self.assertFalse(success)

    def test_add_new_extract_invalid_result(self):
        """Teste l'ajout d'un nouvel extrait avec un résultat invalide."""
        # Créer un résultat d'extraction invalide
        result = ExtractResult(
            source_name="Source de test",
            extract_name="Nouvel extrait",
            status="error",
            message="Erreur lors de l'extraction",
            start_marker="Début",
            end_marker="Fin"
        )
        
        # Créer des définitions d'extraits de test
        extract_definitions = [
            {
                "source_name": "Source de test",
                "extracts": []
            }
        ]
        
        # Appeler la méthode à tester
        success, extract_idx = self._run_async_test(self.agent.add_new_extract(extract_definitions, 0, "Nouvel extrait", result))
        
        # Vérifier les résultats
        self.assertFalse(success)
        self.assertEqual(extract_idx, -1)
        
        # Vérifier que l'extrait n'a pas été ajouté
        self.assertEqual(len(extract_definitions[0]["extracts"]), 0)

    def test_add_new_extract_invalid_source_index(self):
        """Teste l'ajout d'un nouvel extrait avec un index de source invalide."""
        # Créer un résultat d'extraction valide
        result = ExtractResult(
            source_name="Source de test",
            extract_name="Nouvel extrait",
            status="valid",
            message="Extraction réussie",
            start_marker="Début",
            end_marker="Fin",
            template_start="Template"
        )
        
        # Créer des définitions d'extraits de test
        extract_definitions = [
            {
                "source_name": "Source de test",
                "extracts": []
            }
        ]
        
        # Appeler la méthode à tester avec un index de source invalide
        success, extract_idx = self._run_async_test(self.agent.add_new_extract(extract_definitions, 1, "Nouvel extrait", result))
        
        # Vérifier les résultats
        self.assertFalse(success)
        self.assertEqual(extract_idx, -1)
        
        # Vérifier que l'extrait n'a pas été ajouté
        self.assertEqual(len(extract_definitions[0]["extracts"]), 0)


class TestSetupExtractAgent(AsyncTestCase):
    """Tests pour la fonction setup_extract_agent."""

    @patch('argumentation_analysis.agents.core.extract.extract_agent.create_llm_service')
    @patch('semantic_kernel.Kernel')
    @patch('semantic_kernel.agents.ChatCompletionAgent')
    def test_setup_extract_agent_success(self, mock_chat_agent, mock_kernel, mock_create_llm_service):
        """Teste la configuration réussie de l'agent d'extraction."""
        # Configurer les mocks
        mock_llm_service = MagicMock()
        mock_create_llm_service.return_value = mock_llm_service
        
        mock_kernel_instance = MagicMock()
        mock_kernel.return_value = mock_kernel_instance
        mock_kernel_instance.get_prompt_execution_settings_from_service_id.return_value = {}
        
        mock_extract_agent = MagicMock()
        mock_validation_agent = MagicMock()
        mock_chat_agent.side_effect = [mock_extract_agent, mock_validation_agent]
        
        # Appeler la fonction à tester
        kernel, agent = self._run_async_test(setup_extract_agent())
        
        # Vérifier les résultats
        self.assertEqual(kernel, mock_kernel_instance)
        self.assertIsInstance(agent, ExtractAgent)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.assert_called_once()
        mock_kernel.assert_called_once()
        mock_kernel_instance.add_service.assert_called_once_with(mock_llm_service)
        self.assertEqual(mock_chat_agent.call_count, 2)

    @patch('argumentation_analysis.agents.core.extract.extract_agent.create_llm_service')
    def test_setup_extract_agent_llm_service_error(self, mock_create_llm_service):
        """Teste la configuration de l'agent d'extraction avec une erreur de service LLM."""
        # Configurer les mocks
        mock_create_llm_service.return_value = None
        
        # Appeler la fonction à tester
        kernel, agent = self._run_async_test(setup_extract_agent())
        
        # Vérifier les résultats
        self.assertIsNone(kernel)
        self.assertIsNone(agent)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.assert_called_once()

    def test_setup_extract_agent_with_custom_llm_service(self):
        """Teste la configuration de l'agent d'extraction avec un service LLM personnalisé."""
        # Créer un mock pour le service LLM
        mock_llm_service = MagicMock()
        mock_llm_service.service_id = "custom_service"
        
        # Appeler la fonction à tester
        with patch('semantic_kernel.Kernel') as mock_kernel, \
             patch('semantic_kernel.agents.ChatCompletionAgent') as mock_chat_agent:
            
            mock_kernel_instance = MagicMock()
            mock_kernel.return_value = mock_kernel_instance
            mock_kernel_instance.get_prompt_execution_settings_from_service_id.return_value = {}
            
            mock_extract_agent = MagicMock()
            mock_validation_agent = MagicMock()
            mock_chat_agent.side_effect = [mock_extract_agent, mock_validation_agent]
            
            kernel, agent = self._run_async_test(setup_extract_agent(mock_llm_service))
            
            # Vérifier les résultats
            self.assertEqual(kernel, mock_kernel_instance)
            self.assertIsInstance(agent, ExtractAgent)
            
            # Vérifier que les mocks ont été appelés correctement
            mock_kernel.assert_called_once()
            mock_kernel_instance.add_service.assert_called_once_with(mock_llm_service)
            self.assertEqual(mock_chat_agent.call_count, 2)


if __name__ == "__main__":
    unittest.main()