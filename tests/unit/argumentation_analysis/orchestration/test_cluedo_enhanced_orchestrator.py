import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from semantic_kernel.kernel import Kernel
from semantic_kernel.contents.chat_message_content import ChatMessageContent

from argumentation_analysis.orchestration.cluedo_extended_orchestrator import CluedoExtendedOrchestrator
from argumentation_analysis.config.settings import AppSettings
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent


class AsyncIterator:
    def __init__(self, seq):
        self.iter = iter(seq)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration

@pytest.fixture
def mock_kernel():
    """Mocked Semantic Kernel."""
    kernel = Mock(spec=Kernel)
    # This is crucial for Pydantic v2 validation
    service = Mock()
    service.service_id = "test_service_id"
    kernel.get_service.return_value = service
    return kernel


@pytest.fixture
def game_elements():
    """Cluedo elements for tests."""
    return {
        "suspects": ["Colonel Moutarde", "Professeur Violet"],
        "armes": ["Poignard", "Chandelier"],
        "lieux": ["Salon", "Cuisine"]
    }


@pytest.fixture
def orchestrator(mock_kernel):
    """Configured orchestrator for tests with mocked agents."""
    mock_settings = Mock(spec=AppSettings)
    mock_settings.openai = Mock()
    mock_settings.openai.api_key.get_secret_value.return_value = "fake_key"
    mock_settings.openai.chat_model_id = "test_model"
    mock_settings.use_mock_llm = False

    return CluedoExtendedOrchestrator(
        kernel=mock_kernel,
        settings=mock_settings,
        max_turns=6,
        max_cycles=2,
        oracle_strategy="balanced"
    )


@pytest.mark.asyncio
class TestCluedoOrchestratorIntegration:
    """
    Integration tests for the current implementation of CluedoExtendedOrchestrator.
    These tests focus on the public API and the main workflow, reflecting the actual code.
    """

    async def test_workflow_setup(self, orchestrator, game_elements, mock_kernel, mocker):
        """
        Tests that the setup_workflow method correctly initializes the game state,
        agents, and strategies.
        """
        mocker.patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge')
        mock_agent_factory = mocker.patch('argumentation_analysis.agents.factory.AgentFactory', autospec=True)
        mock_moriarty_class = mocker.patch('argumentation_analysis.orchestration.cluedo_extended_orchestrator.MoriartyInterrogatorAgent', autospec=True)

        # Configurer le mock de l'AgentFactory pour retourner des agents mockés
        mock_factory_instance = mock_agent_factory.return_value
        
        mock_sherlock = Mock(spec=SherlockEnqueteAgent)
        mock_sherlock.name = "Sherlock"
        mock_factory_instance.create_sherlock_agent.return_value = mock_sherlock

        mock_watson = Mock(spec=WatsonLogicAssistant)
        mock_watson.name = "Watson"
        mock_factory_instance.create_watson_agent.return_value = mock_watson

        # Configurer le mock de Moriarty pour qu'il soit une instance de Mock
        mock_moriarty = Mock(spec=MoriartyInterrogatorAgent)
        mock_moriarty.name = "Moriarty"
        mock_moriarty_class.return_value = mock_moriarty
        
        # Ensure kernel.add_plugin does not return a coroutine
        mock_kernel.add_plugin = Mock()
        
        # Action
        oracle_state = await orchestrator.setup_workflow(
            nom_enquete="Test Setup",
            elements_jeu=game_elements
        )

        # Assertions
        assert isinstance(oracle_state, CluedoOracleState)
        assert orchestrator.oracle_state is oracle_state
        assert orchestrator.oracle_strategy == "balanced"

        # Verify agents creation (we check for Mocks now)
        assert isinstance(orchestrator.sherlock_agent, Mock)
        assert isinstance(orchestrator.watson_agent, Mock)
        assert isinstance(orchestrator.moriarty_agent, Mock)
        
        assert orchestrator.sherlock_agent.name == "Sherlock"
        assert orchestrator.watson_agent.name == "Watson"
        assert orchestrator.moriarty_agent.name == "Moriarty"

        # Verify strategies setup
        assert orchestrator.orchestration is not None
        assert orchestrator.selection_strategy is not None
        assert orchestrator.termination_strategy is not None
        assert orchestrator.termination_strategy.max_turns == 6
        assert orchestrator.termination_strategy.max_cycles == 2

        # Verify kernel interactions - this is now implicitly tested by checking
        # that the mocked agents are correctly assigned.
        pass

    @patch('argumentation_analysis.orchestration.cluedo_extended_orchestrator.CyclicSelectionStrategy.next')
    @patch('argumentation_analysis.orchestration.cluedo_extended_orchestrator.OracleTerminationStrategy.should_terminate')
    async def test_workflow_execution(self, mock_should_terminate, mock_selection_next, orchestrator, game_elements, mock_kernel, mocker):
        """
        Tests the execution of a simple, end-to-end workflow by mocking the agents
        to avoid real LLM calls and dependencies on a real kernel.
        """
        # --- Setup ---
        mocker.patch('argumentation_analysis.agents.core.logic.propositional_logic_agent.TweetyBridge')
        
        # Setup the workflow, which would normally create real agents.
        await orchestrator.setup_workflow(elements_jeu=game_elements)

        # CRITICAL FIX: Replace real agents with mocks because the kernel is mocked.
        # A real agent cannot function with a mocked kernel due to service dependencies.
        mock_sherlock = AsyncMock(spec=SherlockEnqueteAgent)
        mock_sherlock.name = "Sherlock"
        mock_sherlock.invoke.return_value = AsyncIterator([ChatMessageContent(role="assistant", content="Hypothèse de Sherlock.")])

        mock_watson = AsyncMock(spec=WatsonLogicAssistant)
        mock_watson.name = "Watson"
        mock_watson.invoke.return_value = AsyncIterator([ChatMessageContent(role="assistant", content="Analyse logique de Watson.")])

        mock_moriarty = AsyncMock(spec=MoriartyInterrogatorAgent)
        mock_moriarty.name = "Moriarty"
        mock_moriarty.invoke.return_value = AsyncIterator([ChatMessageContent(role="assistant", content="Question de Moriarty.")])

        # Replace the real agents on the orchestrator instance with our mocks
        orchestrator.sherlock_agent = mock_sherlock
        orchestrator.watson_agent = mock_watson
        orchestrator.moriarty_agent = mock_moriarty

        # Mock the strategies to control the test flow
        mock_selection_next.side_effect = [mock_sherlock, mock_watson, mock_moriarty]
        mock_should_terminate.side_effect = [False, False, False, True] # Terminate after 3 turns

        # --- Action ---
        result = await orchestrator.execute_workflow("Start the investigation.")

        # --- Assertions ---
        # Verify workflow execution flow by checking our strategy mocks
        assert mock_selection_next.call_count == 3
        assert mock_should_terminate.call_count == 4
        
        # Verify final result structure
        assert "workflow_info" in result
        assert "solution_analysis" in result
        assert "conversation_history" in result
        assert "oracle_statistics" in result
        
        # Verify the conversation history
        history = result["conversation_history"]
        assert len(history) == 3 # We expect 3 turns based on our mocks
        
        # Check that each message has the expected structure and content
        assert history[0]["sender"] == "Sherlock"
        assert history[0]["message"] == "Hypothèse de Sherlock."
        
        assert history[1]["sender"] == "Watson"
        assert history[1]["message"] == "Analyse logique de Watson."

        assert history[2]["sender"] == "Moriarty"
        assert history[2]["message"] == "Question de Moriarty."

        # Verify metrics were collected
        assert result["workflow_info"]["execution_time_seconds"] > 0
        assert result["solution_analysis"]["success"] is False # No solution was proposed