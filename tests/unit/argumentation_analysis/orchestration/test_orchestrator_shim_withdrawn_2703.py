"""#2703: the ``Orchestrator`` shim and the runner that drove it stay withdrawn.

``orchestration/orchestrator.py`` was archived by #215 (2026-03-24) and left
as a shim whose ``run_analysis_async`` raised ``NotImplementedError``. Its two
importers were test tooling: a worker that no test launched (retired by
#2700), and ``tests/utils/scenario_runner.py``, whose one caller, a triage
test, discarded the result under an xfail reason the call never reached.
The scenarios they named are checked hermetically in
``tests/integration/logical_agents/``.
"""

from tests.support.withdrawn_modules import still_importable


def test_the_orchestrator_shim_is_withdrawn():
    # #2436: the repository's withdrawal check, which a leftover
    # ``__pycache__`` cannot turn red.
    assert not still_importable("argumentation_analysis.orchestration.orchestrator")


def test_the_scenario_runner_is_withdrawn():
    assert not still_importable("tests.utils.scenario_runner")
