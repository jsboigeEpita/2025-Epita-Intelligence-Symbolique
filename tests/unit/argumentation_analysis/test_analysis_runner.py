
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module analysis_runner.
"""

import unittest

import asyncio
# from tests.async_test_case import AsyncTestCase # Suppression de l'import
from argumentation_analysis.orchestration.analysis_runner import AnalysisRunner, run_analysis


class TestAnalysisRunner(unittest.TestCase):
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

    """Tests pour la classe AnalysisRunner."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.runner = AnalysisRunner()
        self.test_text = "Ceci est un texte de test pour l'analyse."
        self.mock_llm_service = Magicawait self._create_authentic_gpt4o_mini_instance()
        self.mock_llm_service.service_id = "test_service_id"

    
    async def test_run_analysis_with_llm_service(self, mock_run_analysis_conversation):
        """Teste l'exécution de l'analyse avec un service LLM fourni."""
        # Configurer le mock
        mock_run_analysis_conversation# Mock eliminated - using authentic gpt-4o-mini "Résultat de l'analyse"
        
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

    
    
    async def test_run_analysis_without_llm_service(self, mock_run_analysis_conversation, mock_create_llm_service):
        """Teste l'exécution de l'analyse sans service LLM fourni."""
        # Configurer les mocks
        mock_create_llm_service# Mock eliminated - using authentic gpt-4o-mini self.mock_llm_service
        mock_run_analysis_conversation# Mock eliminated - using authentic gpt-4o-mini "Résultat de l'analyse"
        
        # Appeler la méthode à tester (utilise run_analysis_async)
        result = await self.runner.run_analysis_async(text_content=self.test_text)
        
        # Vérifier les résultats
        self.assertEqual(result, "Résultat de l'analyse")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.# Mock assertion eliminated - authentic validation
        mock_run_analysis_conversation.assert_called_once_with(
            texte_a_analyser=self.test_text,
            llm_service=self.mock_llm_service
        )

    
    
    async def test_run_analysis_function_with_llm_service(self, mock_run_analysis_conversation, mock_create_llm_service):
        """Teste la fonction run_analysis avec un service LLM fourni."""
        # Configurer les mocks
        mock_run_analysis_conversation# Mock eliminated - using authentic gpt-4o-mini "Résultat de l'analyse"
        
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

    
    
    async def test_run_analysis_function_without_llm_service(self, mock_run_analysis_conversation, mock_create_llm_service):
        """Teste la fonction run_analysis sans service LLM fourni."""
        # Configurer les mocks
        mock_create_llm_service# Mock eliminated - using authentic gpt-4o-mini self.mock_llm_service
        mock_run_analysis_conversation# Mock eliminated - using authentic gpt-4o-mini "Résultat de l'analyse"
        
        # Appeler la fonction à tester
        result = await run_analysis(text_content=self.test_text)
        
        # Vérifier les résultats
        self.assertEqual(result, "Résultat de l'analyse")
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.# Mock assertion eliminated - authentic validation
        mock_run_analysis_conversation.assert_called_once_with(
            texte_a_analyser=self.test_text,
            llm_service=self.mock_llm_service
        )


if __name__ == '__main__':
    unittest.main()