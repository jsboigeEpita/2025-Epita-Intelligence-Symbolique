import pytest
import json
import asyncio
import os
import sys

# Add the project root to the Python path to allow for absolute imports
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, root_dir)

import semantic_kernel as sk
from semantic_kernel.functions.function_result import FunctionResult

from argumentation_analysis.agents.factory import AgentFactory, AgentType
from argumentation_analysis.core.llm_service import create_llm_service

# #1988: ces tests appellent de vrais agents ChatCompletionAgent (preuve :
# 3 POST réels openrouter par SHERLOCK_JTMS avec un .env réel). Ils doivent
# vivre dans la lane requires_api — dans la lane gratuite ils ne passaient
# que par le chemin dégradé d'une clé factice. Marquer n'est pas taire,
# c'est router (anti-pendule #3).
pytestmark = [
    pytest.mark.requires_api,
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Tests require OPENAI_API_KEY for real LLM agent integration",
    ),
]

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
        # #3273 — no hardcoded model_id: the factory resolves the environment's
        # default (OPENAI_CHAT_MODEL_ID). "test_model" does not exist at OpenAI
        # (the removed INFORMAL xfail said so itself), and every call made
        # through it answered 404 model_not_found (record run 40607307597:
        # 9/9 SHERLOCK calls) — the SHERLOCK variants passed by swallowing it.
        llm_service = create_llm_service(
            service_id=llm_service_id, force_authentic=True
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
    # Arrange
    agent = agent_factory.create_agent(agent_type)
    input_text = test_case["text"]

    # Act
    result = asyncio.run(agent.analyze_text(input_text))

    # Assert — #3280(b): the family has NO single contract. Each agent's
    # return shape is documented in its own analyze_text docstring and
    # asserted here as documented. The former uniform mapping assertion
    # ("summary"/"findings" on every family) never passed for INFORMAL: its
    # analysis is free-text prose and no layer authors structured findings
    # (the identification plugin exposes no @kernel_function), so the
    # expected_fallacies subset check died with that fabricated contract.
    # Content-level fallacy verification for a free-text agent requires
    # authored structure — declined in #3280 with a caller census — or a
    # phrasing dictionary, which would be a heuristic guessing at French.
    assert result is not None, "Agent returned a null result."

    if agent_type == AgentType.SHERLOCK_JTMS:
        # SherlockJTMSAgent's contract (sherlock_jtms_agent.py analyze_text):
        # a mapping {"summary", "details", "findings"} where findings are
        # JTMS hypotheses — no fallacy_name, nothing in its pipeline
        # authors that field.
        assert "summary" in result, "SherlockJTMSAgent contract: missing 'summary'."
        assert "findings" in result, "SherlockJTMSAgent contract: missing 'findings'."
        assert (
            len(result["findings"]) > 0
        ), "SherlockJTMSAgent should produce at least one hypothesis."
        print(f"[{test_case['id']}] Sherlock summary: {result['summary']}")
    else:
        # InformalFallacyAgent's contract (concrete_agents/
        # informal_fallacy_agent.py analyze_text): the raw kernel
        # completion — the FunctionResult of invoke_prompt, whose value is
        # the analysis prose. Unwrapped here exactly as the production
        # consumer does (informal_agent_adapter.py:202-217).
        content = result.value if isinstance(result, FunctionResult) else result
        if isinstance(content, list):
            content = content[-1] if content else None
        final_content = getattr(content, "content", content)
        prose = str(final_content).strip() if final_content is not None else ""
        assert prose, (
            "InformalFallacyAgent contract: the completion prose is empty — "
            "the analysis did not happen."
        )
        print(f"[{test_case['id']}] Informal completion: {prose[:200]}")
