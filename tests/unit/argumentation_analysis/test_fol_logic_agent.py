import pytest
from unittest.mock import MagicMock, AsyncMock
from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent
from argumentation_analysis.agents.core.logic.fol_logic_agent import FOLLogicAgent
from argumentation_analysis.agents.core.logic.belief_set import FirstOrderBeliefSet


@pytest.mark.asyncio
class TestFOLLogicAgent:
    """
    Unit tests for the refactored FOLLogicAgent.
    These tests focus on the new BaseLogicAgent architecture.
    """

    @pytest.fixture
    def fol_agent(self):
        """Provides a FOLLogicAgent instance with a real kernel + mock service."""
        from semantic_kernel import Kernel
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        kernel = Kernel()
        kernel.add_service(
            OpenAIChatCompletion(
                service_id="default",
                ai_model_id="gpt-4",
                api_key="test-key"
            )
        )
        return FOLLogicAgent(kernel=kernel)

    async def test_agent_initialization(self, fol_agent):
        """Tests that the agent is initialized correctly."""
        assert isinstance(fol_agent, FOLLogicAgent)
        assert isinstance(fol_agent, BaseLogicAgent)
        assert fol_agent.name == "FOLLogicAgent"
        assert fol_agent.logic_type == "first_order"

    async def test_process_translation_task_success(self, fol_agent):
        """
        Tests a successful translation task through the process_task method.
        """
        # Mock the state manager
        mock_state_manager = MagicMock()
        mock_state_manager.get_current_state_snapshot.return_value = {
            "raw_text": "All cats are mammals."
        }
        mock_state_manager.add_belief_set.return_value = "bs_123"

        # Mock the agent's internal text_to_belief_set method to return a valid BeliefSet
        # Use object.__setattr__ to bypass Pydantic V2 __setattr__ validation
        mock_belief_set = FirstOrderBeliefSet(content="forall X: (Cat(X) => Mammal(X))")
        object.__setattr__(fol_agent, 'text_to_belief_set', AsyncMock(
            return_value=(mock_belief_set, "Conversion successful")
        ))

        task_id = "task_1"
        task_description = "Traduire le texte en Belief Set"

        # Execute the task
        result = await fol_agent.process_task(
            task_id, task_description, mock_state_manager
        )

        # Assertions
        assert result["status"] == "success"
        assert result["belief_set_id"] == "bs_123"
        fol_agent.text_to_belief_set.assert_awaited_once_with("All cats are mammals.")
        mock_state_manager.add_belief_set.assert_called_once_with(
            logic_type="first_order", content="forall X: (Cat(X) => Mammal(X))"
        )
        mock_state_manager.add_answer.assert_called_once()


class TestFirstOrderBeliefSet:
    """
    Unit tests for the FirstOrderBeliefSet class.
    """

    def test_belief_set_initialization(self):
        """Tests that the belief set can be initialized."""
        content = "forall X: (P(X) => Q(X))"
        belief_set = FirstOrderBeliefSet(content=content)
        assert belief_set.content == content
        assert belief_set.logic_type == "first_order"
