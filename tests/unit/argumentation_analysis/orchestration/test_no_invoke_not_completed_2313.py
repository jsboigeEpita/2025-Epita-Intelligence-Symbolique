# -*- coding: utf-8 -*-
"""#2313 — a no-invoke-capable provider must not count as completed.

Measured on the #2296 post-wiring real run: a capability whose (only)
registered provider carries no ``invoke`` callable logged « has no invoke
callable, output will be None » and then counted ``completed (0.00s)`` —
the aggregate said 17 completed / 0 degraded while ``belief_sets`` stayed
0. #1019 canonical shape: the status writer and its reader (the executor
accounting, every gate calibrated on ``degraded == 0``) never meet.

Status decision (per the issue's DoD): the no-invoke case is a WIRING
defect — providers exist, none is runnable. It reuses the existing
vocabulary exactly as the retry-exhausted exception path does:
``FAILED`` + ``degraded=phase.optional`` (optional ⇒ loud but non-fatal;
required ⇒ loud and sinking). Distinct from both neighbours:
``SKIPPED`` = no provider registered at all (absence), and ``COMPLETED``
= a real invoke ran, whatever the output (a measurement, even an empty
one — the over-correction guard).
"""

from argumentation_analysis.core.capability_registry import (
    ComponentRegistration,
    ComponentType,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowExecutor,
    WorkflowPhase,
)


class _FakeRegistry:
    def __init__(self, providers):
        self._providers = providers

    def find_for_capability(self, capability):
        return list(self._providers)


def _dead_plugin(capability: str = "nl_extraction") -> ComponentRegistration:
    return ComponentRegistration(
        name="dead_plugin",
        component_type=ComponentType.PLUGIN,
        capabilities=[capability],
    )


async def _empty_invoke(input_text: str, context: dict) -> None:
    return None


def _empty_service(capability: str = "nl_extraction") -> ComponentRegistration:
    return ComponentRegistration(
        name="empty_service",
        component_type=ComponentType.SERVICE,
        capabilities=[capability],
        invoke=_empty_invoke,
    )


class TestNoInvokeIsNotCompleted:
    async def test_optional_phase_without_invoke_is_not_completed(self):
        registry = _FakeRegistry([_dead_plugin()])
        executor = WorkflowExecutor(registry)
        phase = WorkflowPhase(
            name="text_to_kb", capability="nl_extraction", optional=True
        )
        _name, result, _output = await executor._execute_phase(
            phase, "text_to_kb", "texte", {}
        )
        assert result.status.value != "completed", (
            "#2313: a wiring defect (no invoke-capable provider) counted as "
            "completed flatters every degraded==0 gate — the #2296 shape"
        )

    async def test_optional_no_invoke_is_degraded_failed(self):
        registry = _FakeRegistry([_dead_plugin()])
        executor = WorkflowExecutor(registry)
        phase = WorkflowPhase(
            name="text_to_kb", capability="nl_extraction", optional=True
        )
        _name, result, _output = await executor._execute_phase(
            phase, "text_to_kb", "texte", {}
        )
        assert result.status.value == "failed"
        assert result.degraded is True, (
            "optional ⇒ the documented degraded-flag contract (failed, "
            "orchestrator continues, consumers MUST surface it)"
        )
        assert result.error and "invoke" in result.error.lower()

    async def test_required_no_invoke_fails_loud(self):
        registry = _FakeRegistry([_dead_plugin("some_cap")])
        executor = WorkflowExecutor(registry)
        phase = WorkflowPhase(name="p", capability="some_cap", optional=False)
        _name, result, _output = await executor._execute_phase(phase, "p", "texte", {})
        assert result.status.value == "failed"
        assert result.degraded is False

    async def test_foundational_no_invoke_still_fails_terminal(self):
        # Pre-existing behavior pinned: fact_extraction without invoke was
        # already FAILED terminal — the fix must not regress it.
        registry = _FakeRegistry([_dead_plugin("fact_extraction")])
        executor = WorkflowExecutor(registry)
        phase = WorkflowPhase(
            name="extract", capability="fact_extraction", optional=False
        )
        _name, result, _output = await executor._execute_phase(
            phase, "extract", "texte", {}
        )
        assert result.status.value == "failed"
        assert result.terminal is True


class TestNoConflation:
    async def test_invoked_empty_output_stays_completed(self):
        # Over-correction control: an invoke that RAN and returned None is a
        # real measurement (ran and found nothing) — completed, not failed.
        registry = _FakeRegistry([_empty_service()])
        executor = WorkflowExecutor(registry)
        phase = WorkflowPhase(
            name="text_to_kb", capability="nl_extraction", optional=True
        )
        _name, result, _output = await executor._execute_phase(
            phase, "text_to_kb", "texte", {}
        )
        assert result.status.value == "completed"
        assert result.degraded is False

    async def test_no_provider_at_all_stays_skipped(self):
        # Non-conflation pin: SKIPPED is the registered-absence case — the
        # no-invoke wiring defect must not silently reuse it.
        registry = _FakeRegistry([])
        executor = WorkflowExecutor(registry)
        phase = WorkflowPhase(
            name="text_to_kb", capability="nl_extraction", optional=True
        )
        _name, result, _output = await executor._execute_phase(
            phase, "text_to_kb", "texte", {}
        )
        assert result.status.value == "skipped"
        assert result.degraded is False
