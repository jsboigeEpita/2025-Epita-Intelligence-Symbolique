"""Tests for DAG-level parallel execution in WorkflowExecutor.

Validates that phases at the same DAG level run concurrently via
asyncio.gather(), and that dependency ordering is preserved across levels.
"""

import asyncio
import time
from unittest.mock import MagicMock

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


def _make_slow_invoke(delay: float, result: str = "ok"):
    """Create an async invoke callable with a configurable delay."""

    async def _invoke(text, ctx):
        await asyncio.sleep(delay)
        return result

    return _invoke


class TestParallelPhasesExecuteConcurrently:
    """Verify that independent phases at the same DAG level run in parallel."""

    @pytest.mark.asyncio
    async def test_parallel_phases_faster_than_sequential(self):
        """Three independent phases (0.2s each) should complete in ~0.2s, not ~0.6s."""
        registry = CapabilityRegistry()
        for cap in ["cap_a", "cap_b", "cap_c"]:
            registry.register(
                name=f"comp_{cap}",
                component_type=ComponentType.AGENT,
                capabilities=[cap],
                invoke=_make_slow_invoke(0.2, f"out_{cap}"),
            )

        workflow = (
            WorkflowBuilder("parallel_test")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b")
            .add_phase("c", capability="cap_c")
            .build()
        )

        executor = WorkflowExecutor(registry)
        start = time.time()
        results = await executor.execute(workflow, "input")
        elapsed = time.time() - start

        assert results["a"].status == PhaseStatus.COMPLETED
        assert results["b"].status == PhaseStatus.COMPLETED
        assert results["c"].status == PhaseStatus.COMPLETED
        assert results["a"].output == "out_cap_a"
        assert results["b"].output == "out_cap_b"
        assert results["c"].output == "out_cap_c"
        # Parallel: 0.2s + overhead. Sequential would be > 0.5s.
        assert elapsed < 0.5, f"Expected parallel (<0.5s), got {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_parallel_execution_with_diamond_dag(self):
        """Diamond DAG: A -> (B, C) -> D. B and C should run in parallel."""
        registry = CapabilityRegistry()
        registry.register(
            name="comp_a",
            component_type=ComponentType.AGENT,
            capabilities=["cap_a"],
            invoke=_make_slow_invoke(0.1, "out_a"),
        )
        registry.register(
            name="comp_b",
            component_type=ComponentType.AGENT,
            capabilities=["cap_b"],
            invoke=_make_slow_invoke(0.2, "out_b"),
        )
        registry.register(
            name="comp_c",
            component_type=ComponentType.AGENT,
            capabilities=["cap_c"],
            invoke=_make_slow_invoke(0.2, "out_c"),
        )
        registry.register(
            name="comp_d",
            component_type=ComponentType.AGENT,
            capabilities=["cap_d"],
            invoke=_make_slow_invoke(0.1, "out_d"),
        )

        workflow = (
            WorkflowBuilder("diamond")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b", depends_on=["a"])
            .add_phase("c", capability="cap_c", depends_on=["a"])
            .add_phase("d", capability="cap_d", depends_on=["b", "c"])
            .build()
        )

        executor = WorkflowExecutor(registry)
        start = time.time()
        results = await executor.execute(workflow, "input")
        elapsed = time.time() - start

        assert all(r.status == PhaseStatus.COMPLETED for r in results.values())
        # A(0.1) + max(B,C)(0.2) + D(0.1) = ~0.4s parallel
        # Sequential would be: 0.1 + 0.2 + 0.2 + 0.1 = 0.6s
        assert elapsed < 0.55, f"Expected parallel diamond (<0.55s), got {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_dependency_ordering_preserved(self):
        """Phases at different levels must wait for their dependencies."""
        execution_log = []

        async def logging_invoke(cap_name):
            async def _invoke(text, ctx):
                execution_log.append(f"start_{cap_name}")
                await asyncio.sleep(0.05)
                execution_log.append(f"end_{cap_name}")
                return f"out_{cap_name}"

            return _invoke

        registry = CapabilityRegistry()
        for cap in ["cap_a", "cap_b", "cap_c"]:
            registry.register(
                name=f"comp_{cap}",
                component_type=ComponentType.AGENT,
                capabilities=[cap],
                invoke=await logging_invoke(cap),
            )

        workflow = (
            WorkflowBuilder("deps")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b", depends_on=["a"])
            .add_phase("c", capability="cap_c", depends_on=["b"])
            .build()
        )

        executor = WorkflowExecutor(registry)
        await executor.execute(workflow, "input")

        # Verify strict ordering: a starts before b, b starts before c
        idx_start_a = execution_log.index("start_cap_a")
        idx_start_b = execution_log.index("start_cap_b")
        idx_start_c = execution_log.index("start_cap_c")
        assert idx_start_a < idx_start_b < idx_start_c

    @pytest.mark.asyncio
    async def test_parallel_mixed_success_failure(self):
        """One phase failing at a level should not affect others at same level."""
        registry = CapabilityRegistry()
        registry.register(
            name="comp_ok",
            component_type=ComponentType.AGENT,
            capabilities=["cap_ok"],
            invoke=_make_slow_invoke(0.1, "out_ok"),
        )

        async def failing_invoke(text, ctx):
            await asyncio.sleep(0.05)
            raise RuntimeError("intentional failure")

        registry.register(
            name="comp_fail",
            component_type=ComponentType.AGENT,
            capabilities=["cap_fail"],
            invoke=failing_invoke,
        )
        registry.register(
            name="comp_also_ok",
            component_type=ComponentType.AGENT,
            capabilities=["cap_also_ok"],
            invoke=_make_slow_invoke(0.1, "out_also_ok"),
        )

        workflow = (
            WorkflowBuilder("mixed")
            .add_phase("ok", capability="cap_ok")
            .add_phase("fail", capability="cap_fail")
            .add_phase("also_ok", capability="cap_also_ok")
            .build()
        )

        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "input")

        assert results["ok"].status == PhaseStatus.COMPLETED
        assert results["fail"].status == PhaseStatus.FAILED
        assert "intentional failure" in results["fail"].error
        assert results["also_ok"].status == PhaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_parallel_context_propagation(self):
        """Results from parallel phases should all be available to downstream phases."""
        downstream_ctx = {}

        async def downstream_invoke(text, ctx):
            downstream_ctx.update(ctx)
            return "downstream_done"

        registry = CapabilityRegistry()
        for cap in ["cap_a", "cap_b"]:
            registry.register(
                name=f"comp_{cap}",
                component_type=ComponentType.AGENT,
                capabilities=[cap],
                invoke=_make_slow_invoke(0.05, f"out_{cap}"),
            )
        registry.register(
            name="comp_downstream",
            component_type=ComponentType.AGENT,
            capabilities=["cap_downstream"],
            invoke=downstream_invoke,
        )

        workflow = (
            WorkflowBuilder("ctx_prop")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b")
            .add_phase("downstream", capability="cap_downstream", depends_on=["a", "b"])
            .build()
        )

        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "input")

        assert results["downstream"].status == PhaseStatus.COMPLETED
        assert "phase_a_output" in downstream_ctx
        assert "phase_b_output" in downstream_ctx
        assert downstream_ctx["phase_a_output"] == "out_cap_a"
        assert downstream_ctx["phase_b_output"] == "out_cap_b"

    @pytest.mark.asyncio
    async def test_parallel_with_optional_skipped(self):
        """Skipped optional phases in parallel don't block other phases."""
        registry = CapabilityRegistry()
        registry.register(
            name="comp_present",
            component_type=ComponentType.AGENT,
            capabilities=["cap_present"],
            invoke=_make_slow_invoke(0.1, "out_present"),
        )

        workflow = (
            WorkflowBuilder("opt_skip")
            .add_phase("present", capability="cap_present")
            .add_phase("missing", capability="cap_missing", optional=True)
            .build()
        )

        executor = WorkflowExecutor(registry)
        start = time.time()
        results = await executor.execute(workflow, "input")
        elapsed = time.time() - start

        assert results["present"].status == PhaseStatus.COMPLETED
        assert results["missing"].status == PhaseStatus.SKIPPED
        assert elapsed < 0.25, f"Should complete quickly, got {elapsed:.2f}s"

    @pytest.mark.asyncio
    async def test_state_writers_called_for_parallel_phases(self):
        """State writers should be called for each completed parallel phase."""
        registry = CapabilityRegistry()
        writer_calls = []

        for cap in ["cap_a", "cap_b"]:
            registry.register(
                name=f"comp_{cap}",
                component_type=ComponentType.AGENT,
                capabilities=[cap],
                invoke=_make_slow_invoke(0.05, f"out_{cap}"),
            )

        workflow = (
            WorkflowBuilder("writers")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b")
            .build()
        )

        state = MagicMock()

        def writer_a(output, st, ctx):
            writer_calls.append(("a", output))

        def writer_b(output, st, ctx):
            writer_calls.append(("b", output))

        state_writers = {"cap_a": writer_a, "cap_b": writer_b}

        executor = WorkflowExecutor(registry)
        results = await executor.execute(
            workflow, "input", state=state, state_writers=state_writers
        )

        assert results["a"].status == PhaseStatus.COMPLETED
        assert results["b"].status == PhaseStatus.COMPLETED
        assert len(writer_calls) == 2
        assert ("a", "out_cap_a") in writer_calls
        assert ("b", "out_cap_b") in writer_calls
