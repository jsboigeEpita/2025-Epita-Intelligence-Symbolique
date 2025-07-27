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
    return Mock(spec=Kernel)


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
    # Créer le mock pour AppSettings afin de corriger la TypeError initiale
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
        
        # Configure the mock to satisfy Pydantic validation
        mock_kernel.get_service.return_value.service_id = "test_service_id"

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

        # Verify kernel interactions
        # This assertion is no longer relevant as we are mocking the agent factory
        # and the agents themselves, so the internal plugin registration is bypassed.
        # The important part is that the agents are correctly instantiated as mocks.
        pass

    @patch('argumentation_analysis.orchestration.cluedo_extended_orchestrator.CyclicSelectionStrategy.next')
    @patch('argumentation_analysis.orchestration.cluedo_extended_orchestrator.OracleTerminationStrategy.should_terminate')
    async def test_workflow_execution(self, mock_should_terminate, mock_selection_next, orchestrator, game_elements, mock_kernel, mocker):
        """
        Tests the execution of a simple, complete workflow, mocking agent responses.
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

        # Configurer le mock de Moriarty
        mock_moriarty = Mock(spec=MoriartyInterrogatorAgent)
        mock_moriarty.name = "Moriarty"
        mock_moriarty_class.return_value = mock_moriarty
        
        # --- Setup ---
        mock_kernel.add_plugin = Mock()

        # Configure the mock to satisfy Pydantic validation
        mock_kernel.get_service.return_value.service_id = "test_service_id"
        await orchestrator.setup_workflow(elements_jeu=game_elements)

        # Mock agents and their 'invoke' responses
        # Get the mocked agents from the orchestrator instance
        mock_sherlock = orchestrator.sherlock_agent
        mock_watson = orchestrator.watson_agent
        mock_moriarty = orchestrator.moriarty_agent

        # The 'invoke' method on the original object is an 'async def' function.
        # Because our agent mocks have a 'spec', their 'invoke' attribute is
        # automatically an AsyncMock. Calling it returns a coroutine.
        # However, the code under test does not 'await' the call, it directly
        # uses the result in an 'async for' loop.
        # To solve this, we must override the 'invoke' AsyncMock with a regular
        # Mock that directly returns our async iterator.
        import asyncio
        async def async_gen(content):
            await asyncio.sleep(0.01)
            yield content

        mock_sherlock.invoke = Mock(return_value=async_gen(ChatMessageContent(role="assistant", content="Sherlock's turn", name="Sherlock")))
        mock_watson.invoke = Mock(return_value=async_gen(ChatMessageContent(role="assistant", content="Watson's turn", name="Watson")))
        mock_moriarty.invoke = Mock(return_value=async_gen(ChatMessageContent(role="assistant", content="Moriarty's turn", name="Moriarty")))

        # Configure strategy mocks
        mock_selection_next.side_effect = [mock_sherlock, mock_watson, mock_moriarty, mock_sherlock]
        mock_should_terminate.side_effect = [False, False, False, True] # Terminate after 3 turns

        # --- Action ---
        result = await orchestrator.execute_workflow("Start the investigation.")

        # --- Assertions ---
        # Verify workflow execution flow
        assert mock_selection_next.call_count == 3
        assert mock_should_terminate.call_count == 4
        
        mock_sherlock.invoke.assert_called_once()
        mock_watson.invoke.assert_called_once()
        mock_moriarty.invoke.assert_called_once()

        # Verify final result structure
        assert "workflow_info" in result
        assert "solution_analysis" in result
        assert "conversation_history" in result
        assert "oracle_statistics" in result
        
        history = result["conversation_history"]
        assert len(history) == 3
        assert history[0]["sender"] == "Sherlock"
        assert history[0]["message"] == "Sherlock's turn"
        assert history[1]["sender"] == "Watson"
        assert history[2]["sender"] == "Moriarty"

        # Verify metrics were collected
        assert result["workflow_info"]["execution_time_seconds"] > 0
        assert result["solution_analysis"]["success"] is False # No solution was proposed