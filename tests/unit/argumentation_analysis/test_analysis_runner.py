# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module analysis_runner.
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
# from tests.async_test_case import AsyncTestCase # Suppression de l'import
from argumentation_analysis.orchestration.analysis_runner import AnalysisRunner, run_analysis


class TestAnalysisRunner(unittest.TestCase):
    """Tests pour la classe AnalysisRunner."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.runner = AnalysisRunner()
        self.test_text = "Ceci est un texte de test pour l'analyse."
        self.mock_llm_service = MagicMock()
        self.mock_llm_service.service_id = "test_service_id"

    @patch('argumentation_analysis.orchestration.analysis_runner.run_analysis_conversation')
    async def test_run_analysis_with_llm_service(self, mock_run_analysis_conversation):
        """Teste l'exécution de l'analyse avec un service LLM fourni."""
        # Configurer le mock
        mock_run_analysis_conversation.return_value = "Résultat de l'analyse"
        
        # Appeler la méthode à tester (utilise run_analysis_async)
        result = await self.runner.run_analysis_async(
            text_content=self.test_text,
            llm_service=self.mock_llm_service
        )
        
        # Vérifier les résultats
        self.assertEqual(result, "Résultat de l'analyse")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_run_analysis_conversation.assert_called_once_with(
            texte_a_analyser=self.test_text,
            llm_service=self.mock_llm_service
        )

    @patch('argumentation_analysis.core.llm_service.create_llm_service')
    @patch('argumentation_analysis.orchestration.analysis_runner.run_analysis_conversation')
    async def test_run_analysis_without_llm_service(self, mock_run_analysis_conversation, mock_create_llm_service):
        """Teste l'exécution de l'analyse sans service LLM fourni."""
        # Configurer les mocks
        mock_create_llm_service.return_value = self.mock_llm_service
        mock_run_analysis_conversation.return_value = "Résultat de l'analyse"
        
        # Appeler la méthode à tester (utilise run_analysis_async)
        result = await self.runner.run_analysis_async(text_content=self.test_text)
        
        # Vérifier les résultats
        self.assertEqual(result, "Résultat de l'analyse")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.assert_called_once()
        mock_run_analysis_conversation.assert_called_once_with(
            texte_a_analyser=self.test_text,
            llm_service=self.mock_llm_service
        )

    @patch('argumentation_analysis.core.llm_service.create_llm_service')
    @patch('argumentation_analysis.orchestration.analysis_runner.run_analysis_conversation')
    async def test_run_analysis_function_with_llm_service(self, mock_run_analysis_conversation, mock_create_llm_service):
        """Teste la fonction run_analysis avec un service LLM fourni."""
        # Configurer les mocks
        mock_run_analysis_conversation.return_value = "Résultat de l'analyse"
        
        # Appeler la fonction à tester
        result = await run_analysis(
            text_content=self.test_text,
            llm_service=self.mock_llm_service
        )
        
        # Vérifier les résultats
        self.assertEqual(result, "Résultat de l'analyse")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.assert_not_called()
        mock_run_analysis_conversation.assert_called_once_with(
            texte_a_analyser=self.test_text,
            llm_service=self.mock_llm_service
        )

    @patch('argumentation_analysis.core.llm_service.create_llm_service')
    @patch('argumentation_analysis.orchestration.analysis_runner.run_analysis_conversation')
    async def test_run_analysis_function_without_llm_service(self, mock_run_analysis_conversation, mock_create_llm_service):
        """Teste la fonction run_analysis sans service LLM fourni."""
        # Configurer les mocks
        mock_create_llm_service.return_value = self.mock_llm_service
        mock_run_analysis_conversation.return_value = "Résultat de l'analyse"
        
        # Appeler la fonction à tester
        result = await run_analysis(text_content=self.test_text)
        
        # Vérifier les résultats
        self.assertEqual(result, "Résultat de l'analyse")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.assert_called_once()
        mock_run_analysis_conversation.assert_called_once_with(
            texte_a_analyser=self.test_text,
            llm_service=self.mock_llm_service
        )


if __name__ == '__main__':
    unittest.main()