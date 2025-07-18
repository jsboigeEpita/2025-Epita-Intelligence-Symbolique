import pytest
import pytest_asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from argumentation_analysis.orchestration.analysis_runner_v2 import AnalysisRunnerV2

@pytest.fixture
def mock_llm_service():
    """Fixture for a mocked LLM service."""
    service = AsyncMock()
    service.service_id = "test_llm_service"
    return service

@pytest.mark.asyncio
@patch('argumentation_analysis.orchestration.analysis_runner_v2.RhetoricalAnalysisState')
@patch('argumentation_analysis.orchestration.analysis_runner_v2.StateManagerPlugin')
@patch('argumentation_analysis.orchestration.analysis_runner_v2.AgentFactory')
@patch('argumentation_analysis.orchestration.analysis_runner_v2.AgentGroupChat')
@pytest.mark.skip(reason="Temporarily disabled due to fatal jpype error")
async def test_run_analysis_v2_success_simplified(
    mock_group_chat,
    mock_agent_factory,
    mock_state_manager_plugin,
    mock_rhetorical_analysis_state,
    mock_llm_service
):
    """
    Tests a simplified successful execution of the analysis orchestration v2.
    """
    async def run_test():
        test_text = "This is a test text."

    # --- Act ---
    runner = AnalysisRunnerV2(llm_service=mock_llm_service)
    
    # Mocking the internal methods to avoid running the full complex flow
    with patch.object(runner, '_setup_orchestration', new_callable=AsyncMock) as mock_setup, \
         patch.object(runner, '_execute_conversation_phase', new_callable=AsyncMock) as mock_exec_phase:
        
        result = await runner.run_analysis(text_content=test_text)

    # --- Assert ---
    mock_setup.assert_awaited_once()
    assert mock_exec_phase.await_count == 3  # Ensure all 3 phases are called
    
    assert result['status'] == 'success'

@pytest.mark.asyncio
async def test_run_analysis_v2_no_llm_service():
    """
    Tests that AnalysisV2Exception is raised if no LLM service is provided.
    """
    runner = AnalysisRunnerV2()  # No service provided here
    with pytest.raises(Exception, match="Un service LLM doit être fourni pour l'analyse."):
         await runner.run_analysis(text_content="test")
