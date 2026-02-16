import pytest
import json
import asyncio
import os
import sys

# Add the project root to the Python path to allow for absolute imports
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, root_dir)

import semantic_kernel as sk
from argumentation_analysis.agents.factory import AgentFactory, AgentType
from argumentation_analysis.core.llm_service import create_llm_service

pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Tests require OPENAI_API_KEY for real LLM agent integration",
)

# --- Test Data Loading ---


def load_test_cases():
    """Loads test cases from the JSON file."""
    test_data_path = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_data_path, "r") as f:
        return json.load(f)


# --- Pytest Fixtures ---


@pytest.fixture(scope="module")
def agent_factory():
    """Fixture to initialize and provide the AgentFactory."""
    kernel = sk.Kernel()
    llm_service_id = "default"
    try:
        llm_service = create_llm_service(
            service_id=llm_service_id, model_id="test_model", force_authentic=True
        )
        kernel.add_service(llm_service)
    except Exception as e:
        pytest.fail(f"LLM service setup failed: {e}")
    return AgentFactory(kernel, llm_service_id)


@pytest.fixture(scope="module", params=load_test_cases(), ids=lambda tc: tc["id"])
def test_case(request):
    """Fixture to provide each test case one by one."""
    return request.param


# --- Parameterized Integration Test ---


@pytest.mark.parametrize("agent_type", list(AgentType))
def test_agent_performance(agent_factory, agent_type, test_case):
    """
    Parametrized test to run each agent against each test case.
    """
    # Known broken agent types: METHODICAL_AUDITOR and PARALLEL_EXPLORER have
    # GuidingPlugin.__init__() missing 'kernel' arg (plugin loaded via from_directory),
    # INFORMAL_FALLACY uses model_id="test_model" which doesn't exist at OpenAI.
    _broken_types = {AgentType.METHODICAL_AUDITOR, AgentType.PARALLEL_EXPLORER, AgentType.INFORMAL_FALLACY}
    if agent_type in _broken_types:
        pytest.xfail(
            f"{agent_type.name}: plugin loading TypeError or invalid model_id in test environment"
        )

    # Arrange
    agent = agent_factory.create_agent(agent_type)
    input_text = test_case["text"]
    expected_fallacies = set(test_case["expected_fallacies"])

    # Act
    result = asyncio.run(agent.analyze_text(input_text))

    # Assert
    # 1. Check for valid response structure
    assert result is not None, "Agent returned a null result."
    assert "summary" in result, "Response is missing 'summary' key."
    assert "findings" in result, "Response is missing 'findings' key."

    # For the placeholder agent, we don't need to check further
    if agent_type == AgentType.RESEARCH_ASSISTANT:
        assert (
            result["summary"]
            == "This agent is a placeholder and is not yet implemented."
        )
        return

    # 2. Check if findings are plausible
    if not expected_fallacies:
        # If no fallacies are expected, we can't make a strong assertion on findings,
        # but we can check that it didn't return an error.
        print(
            f"Agent {agent_type.name} on {test_case['id']} produced summary: {result['summary']}"
        )
    else:
        assert result[
            "findings"
        ], f"Agent {agent_type.name} found no fallacies where {len(expected_fallacies)} were expected."

        # 3. Check if expected fallacies are detected
        # We check for a subset, as the agent might find other plausible ones.
        if agent_type == AgentType.SHERLOCK_JTMS:
            # Sherlock produces 'hypotheses', not 'fallacies'. We just check that it produced some.
            assert (
                len(result["findings"]) > 0
            ), "SherlockJTMSAgent should produce at least one hypothesis."
        else:
            found_fallacies = {
                finding["fallacy_name"] for finding in result["findings"]
            }

            # Normalize for comparison
            found_fallacies_normalized = {
                name.replace("_", " ").lower() for name in found_fallacies
            }
            expected_fallacies_normalized = {
                name.replace("_", " ").lower() for name in expected_fallacies
            }

            assert expected_fallacies_normalized.issubset(found_fallacies_normalized), (
                f"Agent {agent_type.name} failed to find all expected fallacies for {test_case['id']}. "
                f"Expected: {expected_fallacies_normalized}, Found: {found_fallacies_normalized}"
            )
