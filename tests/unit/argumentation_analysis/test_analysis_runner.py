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
from argumentation_analysis.orchestration.analysis_runner_v2 import AnalysisRunnerV2
from argumentation_analysis.config.settings import AppSettings


class TestAnalysisRunnerV2(unittest.IsolatedAsyncioTestCase):
    """Suite de tests pour la classe `AnalysisRunnerV2`."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.mock_llm_service = MagicMock()
        self.runner = AnalysisRunnerV2(llm_service=self.mock_llm_service)
        self.test_text = "Ceci est un texte de test pour l'analyse."

    @patch('argumentation_analysis.orchestration.analysis_runner_v2.AgentGroupChat', new_callable=MagicMock)
    @patch('argumentation_analysis.orchestration.analysis_runner_v2.AgentFactory')
    @patch('argumentation_analysis.orchestration.analysis_runner_v2.RhetoricalAnalysisState')
    @patch('argumentation_analysis.orchestration.analysis_runner_v2.start_enhanced_pm_capture')
    @patch('argumentation_analysis.orchestration.analysis_runner_v2.stop_enhanced_pm_capture')
    @patch('argumentation_analysis.orchestration.analysis_runner_v2.save_enhanced_pm_report')
    async def test_run_analysis_v2_flow(self, mock_save_report, mock_stop_capture, mock_start_capture, mock_state, mock_factory, mock_chat_class):
        """
        Teste le flux principal de `run_analysis` dans `AnalysisRunnerV2`.
        """
        # --- Arrange ---
        mock_state_instance = mock_state.return_value
        mock_state_instance.to_json.return_value = '{}'  # Retourne un JSON valide

        mock_chat_instance = mock_chat_class.return_value
        mock_chat_instance.invoke = AsyncMock(return_value=self.mock_async_iterator([])) # invoke est une méthode async

        # --- Act ---
        result = await self.runner.run_analysis(self.test_text)

        # --- Assert ---
        mock_start_capture.assert_called_once()
        self.assertTrue(mock_state.called)
        self.assertTrue(mock_factory.called)
        # 3 phases, donc 3 appels à AgentGroupChat
        self.assertEqual(mock_chat_class.call_count, 3)
        self.assertEqual(mock_chat_instance.invoke.await_count, 3)
        mock_stop_capture.assert_called_once()
        mock_save_report.assert_called_once()

        self.assertEqual(result['status'], 'success')

    def mock_async_iterator(self, items):
        """Crée un itérateur asynchrone à partir d'une liste d'éléments."""
        async def _iterator():
            for item in items:
                yield item
        return _iterator()

if __name__ == '__main__':
    unittest.main()