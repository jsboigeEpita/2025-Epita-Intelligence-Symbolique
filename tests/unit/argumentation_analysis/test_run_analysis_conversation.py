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
@patch(
    "argumentation_analysis.orchestration.analysis_runner_v2.RhetoricalAnalysisState"
)
@patch("argumentation_analysis.orchestration.analysis_runner_v2.StateManagerPlugin")
@patch("argumentation_analysis.orchestration.analysis_runner_v2.AgentFactory")
@patch("argumentation_analysis.orchestration.analysis_runner_v2.AgentGroupChat")
async def test_run_analysis_v2_success_simplified(
    mock_group_chat,
    mock_agent_factory,
    mock_state_manager_plugin,
    mock_rhetorical_analysis_state,
    mock_llm_service,
):
    """
    Tests a simplified successful execution of the analysis orchestration v2.
    """
    test_text = "This is a test text."

    # --- Act ---
    runner = AnalysisRunnerV2(llm_service=mock_llm_service)

    # Mock the 3 phase methods that run_analysis actually calls
    with patch.object(
        runner, "_setup_orchestration", new_callable=AsyncMock
    ) as mock_setup, patch.object(
        runner, "_run_phase_1_informal_analysis", new_callable=AsyncMock
    ), patch.object(
        runner, "_run_phase_2_formal_analysis", new_callable=AsyncMock
    ), patch.object(
        runner, "_run_phase_3_synthesis_coordination", new_callable=AsyncMock
    ):
        # Mock shared_state.to_json() used by run_analysis after phases
        runner.shared_state = MagicMock()
        runner.shared_state.to_json.return_value = "{}"
        runner.chat_history = []
        result = await runner.run_analysis(text_content=test_text)

    # --- Assert ---
    mock_setup.assert_awaited_once()

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_run_analysis_v2_no_llm_service():
    """
    Tests that AnalysisV2Exception is raised if no LLM service is provided.
    """
    runner = AnalysisRunnerV2()  # No service provided here
    with pytest.raises(
        Exception, match="Un service LLM doit être fourni pour l'analyse."
    ):
        await runner.run_analysis(text_content="test")
