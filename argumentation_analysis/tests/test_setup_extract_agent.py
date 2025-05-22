"""
Tests unitaires pour la fonction setup_extract_agent.
"""

import unittest
from unittest.mock import patch, MagicMock
import asyncio
from tests.async_test_case import AsyncTestCase
from argumentation_analysis.agents.core.extract.extract_agent import setup_extract_agent, ExtractAgent


class TestSetupExtractAgent(AsyncTestCase):
    """Tests pour la fonction setup_extract_agent."""

    @patch('argumentation_analysis.agents.core.extract.extract_agent.create_llm_service')
    async def test_setup_extract_agent_success(self, mock_create_llm_service):
        """Teste la configuration réussie de l'agent d'extraction."""
        # Configurer le mock du service LLM
        mock_llm_service = MagicMock()
        mock_llm_service.service_id = "test_service_id"
        mock_create_llm_service.return_value = mock_llm_service
        
        # Configurer les mocks pour le kernel et les agents
        with patch('semantic_kernel.Kernel') as mock_kernel_class:
            mock_kernel = MagicMock()
            mock_kernel_class.return_value = mock_kernel
            
            mock_settings = MagicMock()
            mock_kernel.get_prompt_execution_settings_from_service_id.return_value = mock_settings
            
            # Appeler la fonction à tester
            kernel, agent = await setup_extract_agent()
            
            # Vérifier les résultats
            self.assertIsNotNone(kernel)
            self.assertIsNotNone(agent)
            self.assertIsInstance(agent, ExtractAgent)
            
            # Vérifier que les mocks ont été appelés correctement
            mock_create_llm_service.assert_called_once()
            mock_kernel.add_service.assert_called_once_with(mock_llm_service)
            mock_kernel.get_prompt_execution_settings_from_service_id.assert_called_once_with(mock_llm_service.service_id)

    @patch('argumentation_analysis.agents.core.extract.extract_agent.create_llm_service')
    async def test_setup_extract_agent_with_provided_llm_service(self, mock_create_llm_service):
        """Teste la configuration de l'agent d'extraction avec un service LLM fourni."""
        # Configurer le mock du service LLM fourni
        mock_llm_service = MagicMock()
        mock_llm_service.service_id = "test_service_id"
        
        # Configurer les mocks pour le kernel et les agents
        with patch('semantic_kernel.Kernel') as mock_kernel_class:
            mock_kernel = MagicMock()
            mock_kernel_class.return_value = mock_kernel
            
            mock_settings = MagicMock()
            mock_kernel.get_prompt_execution_settings_from_service_id.return_value = mock_settings
            
            # Appeler la fonction à tester avec le service LLM fourni
            kernel, agent = await setup_extract_agent(mock_llm_service)
            
            # Vérifier les résultats
            self.assertIsNotNone(kernel)
            self.assertIsNotNone(agent)
            self.assertIsInstance(agent, ExtractAgent)
            
            # Vérifier que les mocks ont été appelés correctement
            mock_create_llm_service.assert_not_called()  # Ne devrait pas être appelé car le service est fourni
            mock_kernel.add_service.assert_called_once_with(mock_llm_service)
            mock_kernel.get_prompt_execution_settings_from_service_id.assert_called_once_with(mock_llm_service.service_id)

    @patch('argumentation_analysis.agents.core.extract.extract_agent.create_llm_service')
    async def test_setup_extract_agent_failure(self, mock_create_llm_service):
        """Teste la gestion des erreurs lors de la configuration de l'agent d'extraction."""
        # Configurer le mock du service LLM pour retourner None (échec)
        mock_create_llm_service.return_value = None
        
        # Appeler la fonction à tester
        kernel, agent = await setup_extract_agent()
        
        # Vérifier les résultats
        self.assertIsNone(kernel)
        self.assertIsNone(agent)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.assert_called_once()


if __name__ == '__main__':
    unittest.main()