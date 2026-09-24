"""#2346: a phase that hangs must not erase the phases that finished beside it.

Phases of one DAG level run under one ``asyncio.gather``, and their results
were stored only once the whole level had returned. A run bounded from outside
(``asyncio.wait_for`` around the executor, as ``compare_orchestration_modes``
does with ``--max-wall-seconds``) that hit its budget while one phase hung
therefore lost every sibling that had already finished: nothing reached the
state, although the work was done.
"""

import asyncio

import pytest

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowExecutor,
    PhaseStatus,
)


async def _fast(text, ctx):
    return {"done": text}


async def _hang(text, ctx):
    await asyncio.sleep(3600)


def _executor():
    registry = CapabilityRegistry()
    registry.register(
        "fast_a", ComponentType.SERVICE, capabilities=["cap_a"], invoke=_fast
    )
    registry.register(
        "fast_b", ComponentType.SERVICE, capabilities=["cap_b"], invoke=_fast
    )
    registry.register(
        "hanging", ComponentType.SERVICE, capabilities=["cap_hang"], invoke=_hang
    )
    return WorkflowExecutor(registry)


def _workflow():
    # One level: the three phases have no dependency between them.
    return (
        WorkflowBuilder("torn_level")
        .add_phase("a", capability="cap_a")
        .add_phase("hang", capability="cap_hang")
        .add_phase("b", capability="cap_b")
        .build()
    )


class _State:
    def __init__(self):
        self.written = []


def _writer(name):
    def write(output, state, ctx):
        state.written.append((name, output))

    return write


async def _run_until_budget(executor, state, checkpoints):
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            executor.execute(
                _workflow(),
                "text",
                state=state,
                state_writers={"cap_a": _writer("a"), "cap_b": _writer("b")},
                checkpoint_callback=lambda results, ctx: checkpoints.append(
                    {name: r.status for name, r in results.items()}
                ),
            ),
            timeout=0.5,
        )


async def test_finished_siblings_reach_the_state():
    state = _State()
    await _run_until_budget(_executor(), state, [])
    assert state.written == [("a", {"done": "text"}), ("b", {"done": "text"})]


async def test_the_checkpoint_counts_only_what_finished():
    checkpoints = []
    await _run_until_budget(_executor(), _State(), checkpoints)
    assert checkpoints, "the torn level never reached its checkpoint"
    last = checkpoints[-1]
    assert last["a"] == PhaseStatus.COMPLETED
    assert last["b"] == PhaseStatus.COMPLETED
    assert "hang" not in last


async def test_an_unbounded_level_still_waits_for_every_phase():
    """Control: without an outside budget, the level returns all its phases."""

    async def slow(text, ctx):
        await asyncio.sleep(0.05)
        return {"slow": True}

    registry = CapabilityRegistry()
    registry.register("a", ComponentType.SERVICE, capabilities=["cap_a"], invoke=_fast)
    registry.register("s", ComponentType.SERVICE, capabilities=["cap_s"], invoke=slow)
    workflow = (
        WorkflowBuilder("whole_level")
        .add_phase("a", capability="cap_a")
        .add_phase("s", capability="cap_s")
        .build()
    )
    results = await WorkflowExecutor(registry).execute(workflow, "text")
    assert results["a"].status == PhaseStatus.COMPLETED
    assert results["s"].status == PhaseStatus.COMPLETED
