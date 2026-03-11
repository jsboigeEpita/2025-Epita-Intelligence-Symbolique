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
