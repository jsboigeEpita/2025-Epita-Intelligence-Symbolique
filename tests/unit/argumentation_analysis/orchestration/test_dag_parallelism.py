"""Tests verifying DAG-level parallelism in WorkflowExecutor (#505).

The executor already uses asyncio.gather() to run independent phases
within a DAG level concurrently. These tests verify this behavior.
"""

import asyncio
import time
from unittest.mock import MagicMock, AsyncMock

import pytest

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowExecutor,
)


@pytest.fixture
def parallel_registry():
    """Registry with slow async invoke callables for parallelism testing."""
    registry = MagicMock()

    async def slow_invoke_A(input_text, ctx):
        await asyncio.sleep(0.1)
        return {"phase": "A", "slept": 0.1}

    async def slow_invoke_B(input_text, ctx):
        await asyncio.sleep(0.1)
        return {"phase": "B", "slept": 0.1}

    async def slow_invoke_C(input_text, ctx):
        await asyncio.sleep(0.1)
        return {"phase": "C", "slept": 0.1}

    async def slow_invoke_D(input_text, ctx):
        await asyncio.sleep(0.1)
        return {"phase": "D", "slept": 0.1}

    invokers = {
        "cap_A": slow_invoke_A,
        "cap_B": slow_invoke_B,
        "cap_C": slow_invoke_C,
        "cap_D": slow_invoke_D,
    }

    def find_for_capability(cap):
        provider = MagicMock()
        provider.invoke = invokers.get(cap)
        provider.name = f"provider_{cap}"
        return [provider] if provider.invoke else []

    registry.find_for_capability = find_for_capability
    return registry


class TestDAGParallelism:
    """Verify phases at same DAG level execute concurrently."""

    async def test_parallel_phases_run_concurrently(self, parallel_registry):
        """Two independent phases (A, B) should run in ~0.1s not ~0.2s."""
        wf = (
            WorkflowBuilder("test_parallel")
            .add_phase("A", capability="cap_A")
            .add_phase("B", capability="cap_B")
            .build()
        )

        executor = WorkflowExecutor(parallel_registry)
        start = time.perf_counter()
        results = await executor.execute(wf, "test input")
        elapsed = time.perf_counter() - start

        assert results["A"].status.value == "completed"
        assert results["B"].status.value == "completed"
        # Sequential would be ~0.2s; parallel should be ~0.1s + overhead
        assert elapsed < 0.25, f"Phases did not run concurrently: {elapsed:.3f}s"

    async def test_diamond_dag_parallel(self, parallel_registry):
        """Diamond DAG: A → B,C → D. B and C should run concurrently."""
        wf = (
            WorkflowBuilder("test_diamond")
            .add_phase("A", capability="cap_A")
            .add_phase("B", capability="cap_B", depends_on=["A"])
            .add_phase("C", capability="cap_C", depends_on=["A"])
            .add_phase("D", capability="cap_D", depends_on=["B", "C"])
            .build()
        )

        executor = WorkflowExecutor(parallel_registry)
        start = time.perf_counter()
        results = await executor.execute(wf, "test input")
        elapsed = time.perf_counter() - start

        for name in ["A", "B", "C", "D"]:
            assert results[name].status.value == "completed", f"{name} not completed"

        # Sequential: 4 * 0.1 = 0.4s. Parallel: A(0.1) + B+C(0.1) + D(0.1) = 0.3s
        # Allow overhead; must be less than sequential 0.4s
        assert elapsed < 0.4, f"Diamond DAG not parallelized: {elapsed:.3f}s"

    async def test_execution_order_groups(self, parallel_registry):
        """Verify get_execution_order produces correct level groups."""
        wf = (
            WorkflowBuilder("test_order")
            .add_phase("A", capability="cap_A")
            .add_phase("B", capability="cap_B", depends_on=["A"])
            .add_phase("C", capability="cap_C", depends_on=["A"])
            .add_phase("D", capability="cap_D", depends_on=["B", "C"])
            .build()
        )

        levels = wf.get_execution_order()
        assert levels == [["A"], ["B", "C"], ["D"]]

    async def test_state_writers_no_race(self, parallel_registry):
        """Parallel phases writing to different state fields should not conflict."""
        state = MagicMock()
        state.field_A = None
        state.field_B = None

        def writer_A(output, st, ctx):
            st.field_A = output.get("phase")

        def writer_B(output, st, ctx):
            st.field_B = output.get("phase")

        wf = (
            WorkflowBuilder("test_state_race")
            .add_phase("A", capability="cap_A")
            .add_phase("B", capability="cap_B")
            .build()
        )

        executor = WorkflowExecutor(parallel_registry)
        await executor.execute(
            wf,
            "test input",
            state=state,
            state_writers={"cap_A": writer_A, "cap_B": writer_B},
        )

        assert state.field_A == "A"
        assert state.field_B == "B"
