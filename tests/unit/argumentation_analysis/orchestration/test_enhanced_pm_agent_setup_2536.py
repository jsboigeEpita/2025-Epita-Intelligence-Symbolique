"""#2536: EnhancedProjectManagerOrchestrator could never set up its agents.

``_setup_enhanced_agents`` opens on ``FunctionChoiceBehavior.Auto(...)``, a
name the module never imported. The NameError fired before the first agent was
built, and ``setup_enhanced_orchestration``'s ``except`` turned it into
``return False``: the orchestrator reported a failed setup and never said why.
"""

import warnings
from unittest.mock import MagicMock, create_autospec

import pytest
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.function_choice_behavior import (
    FunctionChoiceBehavior,
    FunctionChoiceType,
)

from argumentation_analysis.orchestration import enhanced_pm_analysis_runner

AGENT_CLASSES = (
    "ProjectManagerAgent",
    "InformalAnalysisAgent",
    "ModalLogicAgent",
    "ExtractAgent",
)


@pytest.fixture
def orchestrator(monkeypatch):
    for name in AGENT_CLASSES:
        monkeypatch.setattr(enhanced_pm_analysis_runner, name, MagicMock(name=name))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        orchestrator = enhanced_pm_analysis_runner.EnhancedProjectManagerOrchestrator(
            llm_service=MagicMock(service_id="svc_2536")
        )
    orchestrator.kernel = create_autospec(Kernel, instance=True)
    return orchestrator


async def test_agent_setup_turns_on_automatic_function_calling(orchestrator):
    settings = (
        orchestrator.kernel.get_prompt_execution_settings_from_service_id.return_value
    )

    await orchestrator._setup_enhanced_agents()

    behavior = settings.function_choice_behavior
    assert isinstance(behavior, FunctionChoiceBehavior)
    assert behavior.type_ == FunctionChoiceType.AUTO
    assert set(orchestrator.agents) == {
        "ProjectManager",
        "InformalAnalysis",
        "ModalLogic",
        "Extract",
    }
