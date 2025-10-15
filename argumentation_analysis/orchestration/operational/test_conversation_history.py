import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from argumentation_analysis.orchestration.operational.direct_executor import (
    DirectOperationalExecutor,
)
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet


@pytest.mark.asyncio
async def test_execute_logic_agent_with_chat_history():
    """
    Test case to verify that the DirectOperationalExecutor's _execute_logic_agent
    method uses the logic_agent's invoke_single method when chat_history is provided.
    """
    # Arrange
    mock_belief_set = PropositionalBeliefSet(content="a", propositions=["a"])
    mock_logic_agent = MagicMock()
    mock_logic_agent.invoke_single = AsyncMock(
        return_value=(mock_belief_set, "Processed with history")
    )
    mock_logic_agent.text_to_belief_set = AsyncMock()

    mock_kernel = MagicMock()

    with patch(
        "argumentation_analysis.orchestration.operational.direct_executor.logger"
    ) as mock_logger:
        with patch.object(
            DirectOperationalExecutor, "__init__", lambda s, kernel: None
        ):
            executor = DirectOperationalExecutor(kernel=mock_kernel)

        executor.logic_agent = mock_logic_agent

        chat_history = [
            {"role": "user", "content": "Initial user query"},
            {"role": "assistant", "content": "Initial assistant response"},
        ]
        text_input = "This should be ignored"
        extract_results = {}  # Not used by _execute_logic_agent in this path

        # Act
        result = await executor._execute_logic_agent(
            text_input, extract_results, chat_history=chat_history
        )

        # Assert
        mock_logic_agent.invoke_single.assert_awaited_once_with(
            chat_history=chat_history
        )
        mock_logic_agent.text_to_belief_set.assert_not_awaited()

        assert result["status"] == "completed"
        assert result["logic_analysis"] == mock_belief_set.to_dict()
        assert result["message"] == "Processed with history"
        mock_logger.info.assert_any_call(
            "Utilisation de l'historique de conversation pour l'analyse logique."
        )
