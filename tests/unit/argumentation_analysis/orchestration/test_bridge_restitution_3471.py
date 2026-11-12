"""The hierarchical planner can request its own restitution phases (#3471)."""

import pytest

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)
from argumentation_analysis.orchestration.hierarchical.hierarchy_bridge import (
    objectives_to_workflow,
)
from argumentation_analysis.orchestration.hierarchical.orchestrator import (
    RESTITUTION_OBJECTIVE,
    HierarchicalOrchestrator,
    run_hierarchical_analysis,
)
from argumentation_analysis.orchestration.state_writers import (
    CAPABILITY_STATE_WRITERS,
)
from argumentation_analysis.orchestration.unified_pipeline import setup_registry

ACTS = ("act1_framing", "act2_narrative", "act3_conclusion")


def _manager(objectives):
    """A strategic tier that returns exactly the objectives it is given."""

    class Manager:
        def initialize_analysis(self, text):
            return {"objectives": objectives}

        def evaluate_final_results(self, results):
            return {"conclusion": "done"}

    return Manager()


def _recording_registry(calls):
    registry = CapabilityRegistry()
    for capability in ACTS + ("deep_synthesis",):

        async def invoke(*args, _capability=capability, **kwargs):
            calls.append(_capability)
            return {_capability: _capability}

        registry.register(
            name=capability,
            component_type=ComponentType.SERVICE,
            capabilities=[capability],
            invoke=invoke,
            metadata={},
        )
    return registry


def _phase_capabilities(workflow):
    return [phase.capability for phase in workflow.phases]


def test_restitution_objective_builds_native_ordered_act_phases():
    registry = setup_registry()
    workflow = objectives_to_workflow([dict(RESTITUTION_OBJECTIVE)], registry)
    phases = workflow.phases
    assert [phase.capability for phase in phases] == list(ACTS)
    assert phases[1].depends_on == [phases[0].name]
    assert phases[2].depends_on == [phases[1].name]
    assert not workflow.metadata["unresolved_capabilities"]
    # The executor writes a phase's output into the state through the table
    # keyed by capability (workflow_dsl.py). An act the table does not know
    # would run and leave the reader with nothing.
    for phase in phases:
        assert phase.capability in CAPABILITY_STATE_WRITERS


async def test_bridge_plans_its_own_acts_without_any_harness_append():
    """The witness #3471 asks for: the plan itself ends with the three acts."""
    calls = []
    result = await HierarchicalOrchestrator(
        _recording_registry(calls),
        _manager([dict(RESTITUTION_OBJECTIVE)]),
    ).analyze("synthetic text")

    assert calls == list(ACTS)
    assert result["summary"]["completed"] == 3
    assert result["unresolved_capabilities"] == {}


async def test_bridge_persists_ordered_acts_through_real_state_writers():
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState
    from argumentation_analysis.reporting.restitution.pipeline_adapter import (
        build_restitution_acts,
    )

    calls = []
    state = UnifiedAnalysisState("Texte synthétique.")
    result = await HierarchicalOrchestrator(
        _recording_registry(calls), _manager([dict(RESTITUTION_OBJECTIVE)])
    ).analyze("Texte synthétique.", state=state, state_writers=CAPABILITY_STATE_WRITERS)
    assert result["summary"]["completed"] == 3
    assert calls == list(ACTS)
    acts = build_restitution_acts(state)
    assert [acts.act1_framing, acts.act2_narrative, acts.act3_conclusion] == list(ACTS)


async def test_acts_are_added_only_when_the_caller_asks():
    calls = []
    objectives = [
        {
            "id": "synthesis",
            "description": "Synthèse finale",
            "priority": "high",
        }
    ]

    without = await HierarchicalOrchestrator(
        _recording_registry(calls), _manager(list(objectives))
    ).analyze("synthetic text")
    assert calls == ["deep_synthesis"]
    assert without["summary"]["completed"] == 1

    calls.clear()
    with_acts = await HierarchicalOrchestrator(
        _recording_registry(calls), _manager(list(objectives))
    ).analyze("synthetic text", include_restitution=True)
    assert calls == ["deep_synthesis", *ACTS]
    assert with_acts["summary"]["completed"] == 4


async def test_explicit_restitution_objective_is_not_added_twice():
    calls = []
    result = await HierarchicalOrchestrator(
        _recording_registry(calls), _manager([dict(RESTITUTION_OBJECTIVE)])
    ).analyze("synthetic text", include_restitution=True)
    assert calls == list(ACTS)
    assert result["summary"]["completed"] == 3


def test_opt_in_flag_adds_the_objective_after_the_strategic_ones():
    objectives = [
        {"id": "synthesis", "description": "Synthèse finale", "priority": "high"}
    ]
    workflow = objectives_to_workflow(
        [*objectives, dict(RESTITUTION_OBJECTIVE)], setup_registry()
    )
    assert _phase_capabilities(workflow) == ["deep_synthesis", *ACTS]


async def test_delegation_mode_rejects_the_restitution_request():
    with pytest.raises(ValueError, match="cannot plan the restitution acts"):
        await run_hierarchical_analysis(
            "synthetic text",
            mode="delegation",
            include_restitution=True,
        )
