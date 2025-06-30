import pytest
from tests.utils.scenario_runner import run_scenario_from_file

@pytest.mark.real_jpype
@pytest.mark.parametrize("scenario_path", [
    "tests/fixtures/scenarios/contradictory_scenario.json",
    "tests/fixtures/scenarios/ambiguous_scenario.json",
])
def test_logical_agent_hardening_scenarios(scenario_path):
    """
    Test a hardening scenario from a file.
    """
    run_scenario_from_file(scenario_path)