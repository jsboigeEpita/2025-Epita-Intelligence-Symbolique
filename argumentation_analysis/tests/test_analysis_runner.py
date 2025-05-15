"""
Tests unitaires pour le module d'orchestration.
"""

import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent, AgentGroupChat
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
from argumentation_analysis.core.state_manager_plugin import StateManagerPlugin
from tests.async_test_case import AsyncTestCase


class TestAnalysisRunner(AsyncTestCase):
    """Tests pour la fonction run_analysis_conversation."""

    @patch('orchestration.analysis_runner.RhetoricalAnalysisState')
    @patch('orchestration.analysis_runner.StateManagerPlugin')
    @patch('orchestration.analysis_runner.sk.Kernel')
    @patch('orchestration.analysis_runner.setup_pm_kernel')
    @patch('orchestration.analysis_runner.setup_informal_kernel')
    @patch('orchestration.analysis_runner.setup_pl_kernel')
    @patch('orchestration.analysis_runner.setup_extract_agent')
    @patch('orchestration.analysis_runner.ChatCompletionAgent')
    @patch('orchestration.analysis_runner.SimpleTerminationStrategy')
    @patch('orchestration.analysis_runner.DelegatingSelectionStrategy')
    @patch('orchestration.analysis_runner.AgentGroupChat')
    async def test_run_analysis_conversation(
        self, 
        mock_agent_group_chat,
        mock_selection_strategy,
        mock_termination_strategy,
        mock_chat_completion_agent,
        mock_setup_extract_agent,
        mock_setup_pl_kernel,
        mock_setup_informal_kernel,
        mock_setup_pm_kernel,
        mock_kernel,
        mock_state_manager_plugin,
        mock_rhetorical_analysis_state
    ):
        """Teste l'exécution de la conversation d'analyse."""
        # Configurer les mocks
        mock_state = MagicMock(spec=RhetoricalAnalysisState)
        mock_rhetorical_analysis_state.return_value = mock_state
        
        mock_plugin = MagicMock(spec=StateManagerPlugin)
        mock_state_manager_plugin.return_value = mock_plugin
        
        mock_kernel_instance = MagicMock()  # Ne pas utiliser spec=sk.Kernel car sk.Kernel est déjà un mock
        mock_kernel.return_value = mock_kernel_instance
        
        mock_extract_kernel = MagicMock()  # Ne pas utiliser spec=sk.Kernel car sk.Kernel est déjà un mock
        mock_extract_agent = MagicMock(spec=ChatCompletionAgent)
        mock_setup_extract_agent.return_value = (mock_extract_kernel, mock_extract_agent)
        
        mock_pm_agent = MagicMock(spec=ChatCompletionAgent)
        mock_informal_agent = MagicMock(spec=ChatCompletionAgent)
        mock_pl_agent = MagicMock(spec=ChatCompletionAgent)
        mock_extract_agent_instance = MagicMock(spec=ChatCompletionAgent)
        
        mock_chat_completion_agent.side_effect = [
            mock_pm_agent,
            mock_informal_agent,
            mock_pl_agent,
            mock_extract_agent_instance
        ]
        
        mock_termination = MagicMock()
        mock_termination_strategy.return_value = mock_termination
        
        mock_selection = MagicMock()
        mock_selection_strategy.return_value = mock_selection
        
        mock_group_chat = MagicMock(spec=AgentGroupChat)
        mock_agent_group_chat.return_value = mock_group_chat
        
        # Configurer le mock pour invoke
        mock_message1 = MagicMock()
        mock_message1.name = "ProjectManagerAgent"
        mock_message1.role.name = "ASSISTANT"
        mock_message1.content = "Message du PM"
        
        mock_message2 = MagicMock()
        mock_message2.name = "InformalAnalysisAgent"
        mock_message2.role.name = "ASSISTANT"
        mock_message2.content = "Message de l'agent informel"
        
        # Configurer le générateur asynchrone pour invoke
        async def mock_invoke():
            yield mock_message1
            yield mock_message2
        
        mock_group_chat.invoke = mock_invoke
        
        # Configurer le mock pour history
        mock_group_chat.history = MagicMock()
        mock_group_chat.history.add_user_message = MagicMock()
        mock_group_chat.history.messages = [mock_message1, mock_message2]
        
        # Créer un mock pour le service LLM
        llm_service_mock = MagicMock()
        llm_service_mock.service_id = "test_service"
        
        # Appeler la fonction à tester
        await run_analysis_conversation("Texte de test", llm_service_mock)
        
        # Vérifier que les mocks ont été appelés correctement
        mock_rhetorical_analysis_state.assert_called_once_with(initial_text="Texte de test")
        mock_state_manager_plugin.assert_called_once_with(mock_state)
        mock_kernel.assert_called_once()
        mock_kernel_instance.add_service.assert_called_once_with(llm_service_mock)
        mock_kernel_instance.add_plugin.assert_called_once_with(mock_plugin, plugin_name="StateManager")
        
        mock_setup_pm_kernel.assert_called_once_with(mock_kernel_instance, llm_service_mock)
        mock_setup_informal_kernel.assert_called_once_with(mock_kernel_instance, llm_service_mock)
        mock_setup_pl_kernel.assert_called_once_with(mock_kernel_instance, llm_service_mock)
        mock_setup_extract_agent.assert_called_once_with(llm_service_mock)
        
        self.assertEqual(mock_chat_completion_agent.call_count, 4)
        
        mock_termination_strategy.assert_called_once_with(mock_state, max_steps=15)
        mock_selection_strategy.assert_called_once()
        mock_agent_group_chat.assert_called_once_with(
            agents=[mock_pm_agent, mock_informal_agent, mock_pl_agent, mock_extract_agent_instance],
            selection_strategy=mock_selection,
            termination_strategy=mock_termination
        )
        
        mock_group_chat.history.add_user_message.assert_called_once()

    @patch('orchestration.analysis_runner.RhetoricalAnalysisState')
    async def test_run_analysis_conversation_invalid_llm_service(self, mock_rhetorical_analysis_state):
        """Teste l'exécution de la conversation avec un service LLM invalide."""
        # Créer un mock pour le service LLM invalide
        invalid_llm_service = None
        
        # Appeler la fonction à tester et vérifier qu'elle lève une exception
        with self.assertRaises(ValueError):
            await run_analysis_conversation("Texte de test", invalid_llm_service)
        
        # Vérifier que RhetoricalAnalysisState n'a pas été appelé
        mock_rhetorical_analysis_state.assert_not_called()

    @patch('orchestration.analysis_runner.RhetoricalAnalysisState')
    @patch('orchestration.analysis_runner.StateManagerPlugin')
    @patch('orchestration.analysis_runner.sk.Kernel')
    @patch('orchestration.analysis_runner.setup_pm_kernel')
    @patch('orchestration.analysis_runner.setup_informal_kernel')
    @patch('orchestration.analysis_runner.setup_pl_kernel')
    @patch('orchestration.analysis_runner.setup_extract_agent')
    async def test_run_analysis_conversation_agent_chat_exception(
        self,
        mock_setup_extract_agent,
        mock_setup_pl_kernel,
        mock_setup_informal_kernel,
        mock_setup_pm_kernel,
        mock_kernel,
        mock_state_manager_plugin,
        mock_rhetorical_analysis_state
    ):
        """Teste l'exécution de la conversation avec une exception AgentChatException."""
        # Configurer les mocks
        mock_state = MagicMock(spec=RhetoricalAnalysisState)
        mock_rhetorical_analysis_state.return_value = mock_state
        
        mock_plugin = MagicMock(spec=StateManagerPlugin)
        mock_state_manager_plugin.return_value = mock_plugin
        
        mock_kernel_instance = MagicMock()  # Ne pas utiliser spec=sk.Kernel car sk.Kernel est déjà un mock
        mock_kernel.return_value = mock_kernel_instance
        
        mock_extract_kernel = MagicMock()  # Ne pas utiliser spec=sk.Kernel car sk.Kernel est déjà un mock
        mock_extract_agent = MagicMock(spec=ChatCompletionAgent)
        mock_setup_extract_agent.return_value = (mock_extract_kernel, mock_extract_agent)
        
        # Créer un mock pour le service LLM
        llm_service_mock = MagicMock()
        llm_service_mock.service_id = "test_service"
        
        # Configurer le mock pour AgentGroupChat pour lever une exception
        with patch('orchestration.analysis_runner.AgentGroupChat') as mock_agent_group_chat:
            mock_group_chat = MagicMock(spec=AgentGroupChat)
            mock_agent_group_chat.return_value = mock_group_chat
            
            # Configurer le mock pour invoke pour lever une exception
            from semantic_kernel.exceptions import AgentChatException
            mock_group_chat.invoke = AsyncMock(side_effect=AgentChatException("Chat is already complete"))
            
            # Configurer le mock pour history
            mock_group_chat.history = MagicMock()
            mock_group_chat.history.add_user_message = MagicMock()
            mock_group_chat.history.messages = []
            
            # Appeler la fonction à tester
            await run_analysis_conversation("Texte de test", llm_service_mock)
            
            # Vérifier que les mocks ont été appelés correctement
            mock_rhetorical_analysis_state.assert_called_once_with(initial_text="Texte de test")
            mock_state_manager_plugin.assert_called_once_with(mock_state)
            mock_kernel.assert_called_once()
            mock_kernel_instance.add_service.assert_called_once_with(llm_service_mock)
            mock_kernel_instance.add_plugin.assert_called_once_with(mock_plugin, plugin_name="StateManager")
            
            mock_setup_pm_kernel.assert_called_once_with(mock_kernel_instance, llm_service_mock)
            mock_setup_informal_kernel.assert_called_once_with(mock_kernel_instance, llm_service_mock)
            mock_setup_pl_kernel.assert_called_once_with(mock_kernel_instance, llm_service_mock)
            mock_setup_extract_agent.assert_called_once_with(llm_service_mock)
            
            mock_group_chat.invoke.assert_called_once()
            mock_group_chat.history.add_user_message.assert_called_once()


if __name__ == '__main__':
    unittest.main()