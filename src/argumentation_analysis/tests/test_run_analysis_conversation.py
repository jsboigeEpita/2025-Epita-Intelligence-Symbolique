# -*- coding: utf-8 -*-
"""
Tests unitaires pour la fonction run_analysis_conversation du module analysis_runner.
"""

import pytest # Ajout de pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
# from tests.async_test_case import AsyncTestCase # Suppression de l'import
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation


class TestRunAnalysisConversation:
    """Tests pour la fonction run_analysis_conversation."""

    @pytest.fixture
    def run_analysis_components(self):
        """Fixture pour initialiser les composants de test."""
        test_text = "Ceci est un texte de test pour l'analyse."
        mock_llm_service = MagicMock()
        mock_llm_service.service_id = "test_service_id"
        return test_text, mock_llm_service

    @patch('argumentation_analysis.orchestration.analysis_runner.RhetoricalAnalysisState')
    @patch('argumentation_analysis.orchestration.analysis_runner.StateManagerPlugin')
    @patch('argumentation_analysis.orchestration.analysis_runner.sk.Kernel')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_pm_kernel')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_informal_kernel')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_pl_kernel')
    @patch('argumentation_analysis.orchestration.analysis_runner.setup_extract_agent')
    @patch('argumentation_analysis.orchestration.analysis_runner.SimpleTerminationStrategy')
    @patch('argumentation_analysis.orchestration.analysis_runner.BalancedParticipationStrategy')
    @patch('argumentation_analysis.orchestration.analysis_runner.AgentGroupChat')
    @patch('argumentation_analysis.orchestration.analysis_runner.ChatCompletionAgent')
    async def test_run_analysis_conversation_success(
        self,
        mock_chat_completion_agent,
        mock_agent_group_chat,
        mock_balanced_participation_strategy,
        mock_simple_termination_strategy,
        mock_setup_extract_agent,
        mock_setup_pl_kernel,
        mock_setup_informal_kernel,
        mock_setup_pm_kernel,
        mock_kernel_class,
        mock_state_manager_plugin,
        mock_rhetorical_analysis_state,
        run_analysis_components # Ajout de la fixture
    ):
        """Teste l'exécution réussie de la fonction run_analysis_conversation."""
        test_text, mock_llm_service = run_analysis_components
        # Configurer les mocks
        mock_state = MagicMock()
        mock_rhetorical_analysis_state.return_value = mock_state
        
        mock_state_manager = MagicMock()
        mock_state_manager_plugin.return_value = mock_state_manager
        
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel
        
        mock_settings = MagicMock()
        mock_kernel.get_prompt_execution_settings_from_service_id.return_value = mock_settings
        
        mock_extract_kernel = MagicMock()
        mock_extract_agent = MagicMock()
        mock_setup_extract_agent.return_value = (mock_extract_kernel, mock_extract_agent)
        
        # Configurer les mocks pour les agents
        mock_pm_agent = MagicMock()
        mock_informal_agent = MagicMock()
        mock_pl_agent = MagicMock()
        mock_extract_agent_instance = MagicMock()
        
        mock_chat_completion_agent.side_effect = [
            mock_pm_agent,
            mock_informal_agent,
            mock_pl_agent,
            mock_extract_agent_instance
        ]
        
        # Configurer les mocks pour les stratégies
        mock_termination_strategy = MagicMock()
        mock_simple_termination_strategy.return_value = mock_termination_strategy
        
        mock_selection_strategy = MagicMock()
        mock_balanced_participation_strategy.return_value = mock_selection_strategy
        
        # Configurer le mock pour AgentGroupChat
        mock_group_chat = MagicMock()
        mock_agent_group_chat.return_value = mock_group_chat
        
        # Configurer le mock pour l'historique du chat
        mock_history = MagicMock()
        mock_group_chat.history = mock_history
        mock_history.add_user_message = MagicMock()
        mock_history.messages = []
        
        # Configurer le mock pour invoke
        mock_message = MagicMock()
        mock_message.name = "TestAgent"
        mock_message.role.name = "ASSISTANT"
        mock_message.content = "Réponse de test"
        mock_message.tool_calls = []
        
        # Créer un itérateur asynchrone pour simuler le comportement de invoke
        async def mock_invoke():
            yield mock_message
        
        mock_group_chat.invoke = mock_invoke
        
        # Appeler la fonction à tester
        await run_analysis_conversation(
            texte_a_analyser=test_text,
            llm_service=mock_llm_service
        )
        
        # Vérifier que les mocks ont été appelés correctement
        mock_rhetorical_analysis_state.assert_called_once_with(initial_text=test_text)
        mock_state_manager_plugin.assert_called_once_with(mock_state)
        mock_kernel_class.assert_called_once()
        mock_kernel.add_service.assert_called_once_with(mock_llm_service)
        mock_kernel.add_plugin.assert_called_once()
        mock_setup_pm_kernel.assert_called_once_with(mock_kernel, mock_llm_service)
        mock_setup_informal_kernel.assert_called_once_with(mock_kernel, mock_llm_service)
        mock_setup_pl_kernel.assert_called_once_with(mock_kernel, mock_llm_service)
        mock_setup_extract_agent.assert_called_once_with(mock_llm_service)
        mock_kernel.get_prompt_execution_settings_from_service_id.assert_called_once_with(mock_llm_service.service_id)
        assert mock_chat_completion_agent.call_count == 4
        mock_simple_termination_strategy.assert_called_once_with(mock_state, max_steps=15)
        mock_balanced_participation_strategy.assert_called_once()
        mock_agent_group_chat.assert_called_once()
        mock_history.add_user_message.assert_called_once()

    @patch('argumentation_analysis.orchestration.analysis_runner.RhetoricalAnalysisState')
    async def test_run_analysis_conversation_invalid_llm_service(self, mock_rhetorical_analysis_state, run_analysis_components):
        """Teste la gestion des erreurs avec un service LLM invalide."""
        test_text, _ = run_analysis_components
        # Configurer un service LLM invalide
        invalid_llm_service = MagicMock()
        delattr(invalid_llm_service, 'service_id')
        
        # Appeler la fonction à tester et vérifier qu'elle lève une exception
        with pytest.raises(ValueError):
            await run_analysis_conversation(
                texte_a_analyser=test_text,
                llm_service=invalid_llm_service
            )
        
        # Vérifier que RhetoricalAnalysisState n'a pas été appelé
        mock_rhetorical_analysis_state.assert_not_called()

    @patch('argumentation_analysis.orchestration.analysis_runner.RhetoricalAnalysisState')
    @patch('argumentation_analysis.orchestration.analysis_runner.StateManagerPlugin')
    @patch('argumentation_analysis.orchestration.analysis_runner.sk.Kernel')
    @patch('argumentation_analysis.orchestration.analysis_runner.AgentChatException', Exception)
    async def test_run_analysis_conversation_agent_chat_exception(
        self,
        mock_kernel_class,
        mock_state_manager_plugin,
        mock_rhetorical_analysis_state,
        run_analysis_components # Ajout de la fixture
    ):
        """Teste la gestion des erreurs AgentChatException."""
        test_text, mock_llm_service = run_analysis_components
        # Configurer les mocks
        mock_state = MagicMock()
        mock_rhetorical_analysis_state.return_value = mock_state
        
        mock_state_manager = MagicMock()
        mock_state_manager_plugin.return_value = mock_state_manager
        
        mock_kernel = MagicMock()
        mock_kernel_class.return_value = mock_kernel
        
        # Configurer le mock pour lever une exception
        mock_kernel.add_service.side_effect = Exception("Chat is already complete")
        
        # Appeler la fonction à tester
        await run_analysis_conversation(
            texte_a_analyser=test_text,
            llm_service=mock_llm_service
        )
        
        # Vérifier que les mocks ont été appelés correctement
        mock_rhetorical_analysis_state.assert_called_once_with(initial_text=test_text)
        mock_state_manager_plugin.assert_called_once_with(mock_state)
        mock_kernel_class.assert_called_once()
        mock_kernel.add_service.assert_called_once_with(mock_llm_service)


# if __name__ == '__main__': # Supprimé car pytest gère l'exécution
#     unittest.main()