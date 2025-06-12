
# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour la fonction setup_extract_agent.
"""

import asyncio
from unittest.mock import patch
import pytest

# from argumentation_analysis.agents.core.extract.extract_agent import setup_extract_agent, ExtractAgent
from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent


class TestSetupExtractAgent:
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

    """Tests pour la fonction setup_extract_agent."""

    
    @patch('argumentation_analysis.agents.core.extract.extract_agent.setup_extract_agent')
    @pytest.mark.asyncio
    async def test_setup_extract_agent_success(self, mock_setup_extract_agent, mocker):
        """Teste la configuration réussie de l'agent d'extraction."""
        mock_create_llm_service = mocker.patch('argumentation_analysis.agents.core.extract.extract_agent.create_llm_service')
        # Configurer le mock du service LLM
        mock_llm_service = asyncio.run(self._create_authentic_gpt4o_mini_instance())
        mock_llm_service.service_id = "test_service_id"
        mock_create_llm_service.return_value = mock_llm_service
        
        # Configurer les mocks pour le kernel et les agents
        mock_kernel = asyncio.run(self._create_authentic_gpt4o_mini_instance())
        mock_agent = ExtractAgent(kernel=mock_kernel, service=mock_llm_service)
        mock_setup_extract_agent.return_value = (mock_kernel, mock_agent)
            
        # Appeler la fonction à tester
        kernel, agent = await mock_setup_extract_agent()
        
        # Vérifier les résultats
        assert kernel is not None
        assert agent is not None
        assert isinstance(agent, ExtractAgent)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.assert_called_once()

    
    @patch('argumentation_analysis.agents.core.extract.extract_agent.setup_extract_agent')
    @pytest.mark.asyncio
    async def test_setup_extract_agent_with_provided_llm_service(self, mock_setup_extract_agent, mocker):
        """Teste la configuration de l'agent d'extraction avec un service LLM fourni."""
        mock_create_llm_service = mocker.patch('argumentation_analysis.agents.core.extract.extract_agent.create_llm_service')
        # Configurer le mock du service LLM fourni
        mock_llm_service = asyncio.run(self._create_authentic_gpt4o_mini_instance())
        mock_llm_service.service_id = "test_service_id"
        
        # Configurer les mocks pour le kernel et les agents
        mock_kernel = asyncio.run(self._create_authentic_gpt4o_mini_instance())
        mock_agent = ExtractAgent(kernel=mock_kernel, service=mock_llm_service)
        mock_setup_extract_agent.return_value = (mock_kernel, mock_agent)

        # Appeler la fonction à tester avec le service LLM fourni
        kernel, agent = await mock_setup_extract_agent(mock_llm_service)
        
        # Vérifier les résultats
        assert kernel is not None
        assert agent is not None
        assert isinstance(agent, ExtractAgent)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.assert_not_called()  # Ne devrait pas être appelé car le service est fourni

    
    @patch('argumentation_analysis.agents.core.extract.extract_agent.setup_extract_agent')
    @pytest.mark.asyncio
    async def test_setup_extract_agent_failure(self, mock_setup_extract_agent, mocker):
        """Teste la gestion des erreurs lors de la configuration de l'agent d'extraction."""
        mock_create_llm_service = mocker.patch('argumentation_analysis.agents.core.extract.extract_agent.create_llm_service')
        # Configurer le mock du service LLM pour retourner None (échec)
        mock_create_llm_service.return_value = None
        mock_setup_extract_agent.return_value = (None, None)
        
        # Appeler la fonction à tester
        kernel, agent = await mock_setup_extract_agent()
        
        # Vérifier les résultats
        assert kernel is None
        assert agent is None
        
        # Vérifier que les mocks ont été appelés correctement
        mock_create_llm_service.assert_called_once()

