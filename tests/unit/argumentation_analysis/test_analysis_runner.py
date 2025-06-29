# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests unitaires pour le `AnalysisRunner`.

Ce module contient les tests unitaires pour la classe `AnalysisRunner`,
qui orchestre l'analyse argumentative d'un texte.
"""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from argumentation_analysis.orchestration.analysis_runner import AnalysisRunner
from argumentation_analysis.config.settings import AppSettings


class TestAnalysisRunner(unittest.IsolatedAsyncioTestCase):
    """Suite de tests pour la classe `AnalysisRunner`."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.mock_settings = MagicMock(spec=AppSettings)
        # Configurez les attributs nécessaires sur mock_settings si le constructeur de AnalysisRunner les utilise
        self.mock_settings.service_manager = MagicMock()
        self.mock_settings.service_manager.default_llm_service_id = "test_service"
        
        # Le constructeur de AnalysisRunner crée un kernel et une factory, nous devons patcher cela
        with patch('argumentation_analysis.orchestration.analysis_runner.KernelBuilder.create_kernel') as mock_create_kernel, \
             patch('argumentation_analysis.orchestration.analysis_runner.AgentFactory') as mock_agent_factory:
            
            self.runner = AnalysisRunner(settings=self.mock_settings)
        
        self.test_text = "Ceci est un texte de test pour l'analyse."

    @patch('argumentation_analysis.orchestration.analysis_runner.AgentGroupChat', new_callable=AsyncMock)
    async def test_run_analysis_calls_group_chat(self, mock_agent_group_chat_class):
        """
        Teste que `run_analysis` initialise et invoque correctement AgentGroupChat.
        """
        # Configurer le mock pour l'instance de AgentGroupChat
        mock_chat_instance = mock_agent_group_chat_class.return_value
        # Simuler la réponse de l'invocation du chat
        mock_chat_instance.invoke.return_value = self.mock_async_iterator([MagicMock()])
        
        # Mocker la factory d'agent sur l'instance du runner
        self.runner.factory = MagicMock()
        mock_manager = MagicMock()
        mock_fallacy = MagicMock()
        self.runner.factory.create_project_manager_agent.return_value = mock_manager
        self.runner.factory.create_informal_fallacy_agent.return_value = mock_fallacy

        # Exécuter la méthode
        result = await self.runner.run_analysis(self.test_text)

        # Assertions
        self.runner.factory.create_project_manager_agent.assert_called_once()
        self.runner.factory.create_informal_fallacy_agent.assert_called_once()
        
        mock_agent_group_chat_class.assert_called_once()
        # Vérifier que le chat a été invoqué
        mock_chat_instance.invoke.assert_awaited_once()
        
        # Vérifier que le résultat contient le message initial et les messages du chat
        self.assertEqual(len(result), 2)

    def mock_async_iterator(self, items):
        """Crée un itérateur asynchrone à partir d'une liste d'éléments."""
        async def _iterator():
            for item in items:
                yield item
        return _iterator()

if __name__ == '__main__':
    unittest.main()