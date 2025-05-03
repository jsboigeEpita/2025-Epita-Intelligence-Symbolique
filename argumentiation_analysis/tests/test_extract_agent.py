"""
Tests unitaires pour l'agent d'extraction.
"""

import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from agents.core.extract.extract_agent import ExtractAgent
from agents.core.extract.extract_definitions import ExtractAgentPlugin, ExtractResult
from tests.async_test_case import AsyncTestCase


class TestExtractAgent(AsyncTestCase):
    """Tests pour la classe ExtractAgent."""

    def setUp(self):
        """Initialisation avant chaque test."""
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

    @patch('agents.core.extract.extract_agent.load_source_text')
    async def test_extract_from_name_success(self, mock_load_source_text):
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
        result = await self.agent.extract_from_name(self.source_info, self.extract_name)
        
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

    @patch('agents.core.extract.extract_agent.load_source_text')
    async def test_extract_from_name_invalid_markers(self, mock_load_source_text):
        """Teste l'extraction avec des marqueurs invalides."""
        # Configurer les mocks
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock de l'agent d'extraction pour retourner une réponse JSON avec des marqueurs vides
        mock_response = MagicMock(content='{"start_marker": "", "end_marker": "", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        
        # Appeler la méthode à tester
        result = await self.agent.extract_from_name(self.source_info, self.extract_name)
        
        # Vérifier les résultats
        self.assertEqual(result.status, "error")
        self.assertIn("Bornes invalides", result.message)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_not_called()
        self.validation_agent_mock.assert_not_called()

    @patch('agents.core.extract.extract_agent.load_source_text')
    async def test_extract_from_name_markers_not_found(self, mock_load_source_text):
        """Teste l'extraction avec des marqueurs non trouvés dans le texte."""
        # Configurer les mocks
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock de l'agent d'extraction pour retourner une réponse JSON
        mock_response = MagicMock(content='{"start_marker": "Marqueur début", "end_marker": "Marqueur fin", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        
        # Configurer le mock de l'extraction de texte pour indiquer que les marqueurs n'ont pas été trouvés
        self.extract_text_mock.return_value = ("", "Marqueurs non trouvés", False, False)
        
        # Appeler la méthode à tester
        result = await self.agent.extract_from_name(self.source_info, self.extract_name)
        
        # Vérifier les résultats
        self.assertEqual(result.status, "error")
        self.assertIn("Bornes non trouvées", result.message)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_called_once()
        self.validation_agent_mock.assert_not_called()

    @patch('agents.core.extract.extract_agent.load_source_text')
    async def test_extract_from_name_validation_rejected(self, mock_load_source_text):
        """Teste l'extraction avec validation rejetée."""
        # Configurer les mocks
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock de l'agent d'extraction pour retourner une réponse JSON
        mock_response = MagicMock(content='{"start_marker": "Ceci est", "end_marker": "extraction.", "template_start": "", "explanation": "Explication de test"}')
        async_iter = self._create_async_iterator([mock_response])
        self.extract_agent_mock.invoke = MagicMock(return_value=async_iter)
        
        # Configurer le mock de l'extraction de texte
        self.extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        # Configurer le mock de l'agent de validation pour rejeter l'extrait
        mock_validation_response = MagicMock(content='{"valid": false, "reason": "Extrait invalide"}')
        async_validation_iter = self._create_async_iterator([mock_validation_response])
        self.validation_agent_mock.invoke = MagicMock(return_value=async_validation_iter)
        
        # Appeler la méthode à tester
        result = await self.agent.extract_from_name(self.source_info, self.extract_name)
        
        # Vérifier les résultats
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.message, "Extrait rejeté: Extrait invalide")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once_with(self.source_info)
        self.extract_agent_mock.invoke.assert_called_once()
        self.extract_text_mock.assert_called_once()
        self.validation_agent_mock.invoke.assert_called_once()

    @patch('agents.core.extract.extract_agent.load_source_text')
    async def test_repair_extract_valid(self, mock_load_source_text):
        """Teste la réparation d'un extrait valide."""
        # Configurer les mocks
        mock_load_source_text.return_value = ("Ceci est un texte de test pour l'extraction.", "https://example.com")
        
        # Configurer le mock de l'extraction de texte pour indiquer que les marqueurs sont valides
        self.extract_text_mock.return_value = ("Ceci est un texte de test pour l'extraction.", "success", True, True)
        
        # Créer des définitions d'extraits de test
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
        
        # Appeler la méthode à tester
        result = await self.agent.repair_extract(extract_definitions, 0, 0)
        
        # Vérifier les résultats
        self.assertEqual(result.status, "valid")
        self.assertEqual(result.message, "Extrait valide. Aucune correction nécessaire.")
        self.assertEqual(result.extracted_text, "Ceci est un texte de test pour l'extraction.")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_load_source_text.assert_called_once()
        self.extract_text_mock.assert_called_once()
        self.extract_agent_mock.invoke.assert_not_called()
        self.validation_agent_mock.invoke.assert_not_called()

    @patch('agents.core.extract.extract_agent.load_source_text')
    async def test_update_extract_markers(self, mock_load_source_text):
        """Teste la mise à jour des marqueurs d'un extrait."""
        # Configurer le mock extract_results
        self.extract_plugin_mock.extract_results = []
        # Créer des définitions d'extraits de test
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
        
        # Créer un résultat d'extraction valide
        result = ExtractResult(
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
        
        # Appeler la méthode à tester
        success = await self.agent.update_extract_markers(extract_definitions, 0, 0, result)
        
        # Vérifier les résultats
        self.assertTrue(success)
        self.assertEqual(extract_definitions[0]["extracts"][0]["start_marker"], "Nouveau début")
        self.assertEqual(extract_definitions[0]["extracts"][0]["end_marker"], "Nouvelle fin")
        self.assertEqual(extract_definitions[0]["extracts"][0]["template_start"], "Template")
        
        # Vérifier que les résultats ont été enregistrés
        self.assertTrue(len(self.extract_plugin_mock.extract_results) > 0)

    async def test_add_new_extract(self):
        """Teste l'ajout d'un nouvel extrait."""
        # Configurer le mock extract_results
        self.extract_plugin_mock.extract_results = []
        # Créer des définitions d'extraits de test
        extract_definitions = [
            {
                "source_name": "Source de test",
                "source_url": "https://example.com",
                "extracts": []
            }
        ]
        
        # Créer un résultat d'extraction valide
        result = ExtractResult(
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
        
        # Appeler la méthode à tester
        success, extract_idx = await self.agent.add_new_extract(extract_definitions, 0, "Nouvel extrait", result)
        
        # Vérifier les résultats
        self.assertTrue(success)
        self.assertEqual(extract_idx, 0)
        self.assertEqual(len(extract_definitions[0]["extracts"]), 1)
        self.assertEqual(extract_definitions[0]["extracts"][0]["extract_name"], "Nouvel extrait")
        self.assertEqual(extract_definitions[0]["extracts"][0]["start_marker"], "Début")
        self.assertEqual(extract_definitions[0]["extracts"][0]["end_marker"], "Fin")
        self.assertEqual(extract_definitions[0]["extracts"][0]["template_start"], "Template")
        
        # Vérifier que les résultats ont été enregistrés
        self.assertTrue(len(self.extract_plugin_mock.extract_results) > 0)

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


if __name__ == '__main__':
    unittest.main()