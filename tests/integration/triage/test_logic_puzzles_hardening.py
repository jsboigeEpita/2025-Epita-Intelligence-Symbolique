import os
import sys
import pytest
from unittest.mock import MagicMock
from tests.utils.scenario_runner import run_scenario_from_file

_jpype_is_mocked = isinstance(sys.modules.get("jpype"), MagicMock)

pytestmark = [
    pytest.mark.skipif(
        not os.getenv("OPENAI_API_KEY"),
        reason="Tests require OPENAI_API_KEY for logic puzzle scenario execution",
    ),
    pytest.mark.xfail(
        reason="InformalFallacyAgent.invoke_single() signature mismatch with AgentGroupChat invocation",
        strict=False,
    ),
    pytest.mark.skipif(
        _jpype_is_mocked,
        reason="Scenario runner requires real JVM (jpype mocked by --disable-jvm-session)",
    ),
]


@pytest.mark.real_jpype
# #1988 (résiduel): this test routes to Orchestrator.run_analysis_async via
# tests/utils/scenario_runner.py, which fires real LLM POSTs when the key
# is present. The pytestmark skipif alone does not deselect from the gate
# filter (cf. #1988/#1993 shape) — requires_api routes the test to the API
# lane. The xfail strict=False captures the known InformalFallacyAgent
# signature mismatch in CI; both markers can co-exist.
@pytest.mark.requires_api
@pytest.mark.parametrize(
    "scenario_path",
    [
        "tests/fixtures/scenarios/contradictory_scenario.json",
        "tests/fixtures/scenarios/ambiguous_scenario.json",
    ],
)
def test_logical_agent_hardening_scenarios(scenario_path):
    """
    Test a hardening scenario from a file.
    """
    run_scenario_from_file(scenario_path)
