import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from argumentation_analysis.orchestration.analysis_runner import run_analysis, AgentChatException

@pytest_asyncio.fixture
async def mock_llm_service():
    """Fixture for a mocked LLM service."""
    service = AsyncMock()
    service.service_id = "test_llm_service"
    return service

@pytest.mark.asyncio
@patch('argumentation_analysis.orchestration.analysis_runner.RhetoricalAnalysisState')
@patch('argumentation_analysis.orchestration.analysis_runner.StateManagerPlugin')
@patch('argumentation_analysis.orchestration.analysis_runner.sk.Kernel')
@patch('argumentation_analysis.orchestration.analysis_runner.ProjectManagerAgent')
@patch('argumentation_analysis.orchestration.analysis_runner.InformalAnalysisAgent')
@patch('argumentation_analysis.orchestration.analysis_runner.ExtractAgent')
async def test_run_analysis_success(
    mock_extract_agent,
    mock_informal_agent,
    mock_pm_agent,
    mock_kernel,
    mock_state_manager_plugin,
    mock_rhetorical_analysis_state,
    mock_llm_service
):
    """
    Tests the successful execution of the analysis orchestration,
    verifying that all components are created and configured as expected.
    """
    test_text = "This is a test text."

    # --- Act ---
    result = await run_analysis(text_content=test_text, llm_service=mock_llm_service)

    # --- Assert ---
    # 1. State and Plugin creation
    mock_rhetorical_analysis_state.assert_called_once_with(initial_text=test_text)
    state_instance = mock_rhetorical_analysis_state.return_value
    mock_state_manager_plugin.assert_called_once_with(state_instance)
    plugin_instance = mock_state_manager_plugin.return_value

    # 2. Kernel creation and setup
    mock_kernel.assert_called_once()
    kernel_instance = mock_kernel.return_value
    kernel_instance.add_service.assert_called_once_with(mock_llm_service)
    kernel_instance.add_plugin.assert_called_once_with(plugin_instance, plugin_name="StateManager")

    # 3. Agent instantiation and setup
    mock_pm_agent.assert_called_once_with(kernel=kernel_instance, agent_name="ProjectManagerAgent_Refactored")
    mock_pm_agent.return_value.setup_agent_components.assert_called_once_with(llm_service_id=mock_llm_service.service_id)

    mock_informal_agent.assert_called_once_with(kernel=kernel_instance, agent_name="InformalAnalysisAgent_Refactored")
    mock_informal_agent.return_value.setup_agent_components.assert_called_once_with(llm_service_id=mock_llm_service.service_id)

    mock_extract_agent.assert_called_once_with(kernel=kernel_instance, agent_name="ExtractAgent_Refactored")
    mock_extract_agent.return_value.setup_agent_components.assert_called_once_with(llm_service_id=mock_llm_service.service_id)

    # 4. Final result
    assert result == {"status": "success", "message": "Analyse terminée"}

@pytest.mark.asyncio
async def test_run_analysis_invalid_llm_service():
    """
    Tests that a ValueError is raised with the correct message
    when the LLM service is invalid.
    """
    invalid_service = MagicMock()
    del invalid_service.service_id  # Make it invalid

    with pytest.raises(ValueError, match="Un service LLM valide est requis."):
        await run_analysis(text_content="test", llm_service=invalid_service)

@pytest.mark.asyncio
@patch('argumentation_analysis.orchestration.analysis_runner.ProjectManagerAgent', side_effect=Exception("Agent Initialization Failed"))
async def test_run_analysis_agent_setup_exception(mock_pm_agent_raises_exception, mock_llm_service):
    """
    Tests that a general exception during agent setup is caught
    and returned in the result dictionary.
    """
    # --- Act ---
    result = await run_analysis(text_content="test", llm_service=mock_llm_service)

    # --- Assert ---
    assert result["status"] == "error"
    assert result["message"] == "Agent Initialization Failed"