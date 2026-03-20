"""
Tests for cross-orchestration loops (Issue #67).

Covers:
- LoopConfig dataclass
- Conditional phases (condition callable)
- Iterative phases (loop_config)
- Input transforms
- WorkflowBuilder extensions (add_conditional_phase, add_loop)
- Pre-built loop workflows (quality_gated, debate_governance, jtms_dung, neural_symbolic)
- Quality-gated end-to-end scenarios
- Edge cases
"""

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from argumentation_analysis.orchestration.workflow_dsl import (
    LoopConfig,
    PhaseResult,
    PhaseStatus,
    WorkflowBuilder,
    WorkflowDefinition,
    WorkflowExecutor,
    WorkflowPhase,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class FakeRegistration:
    """Mimics ComponentRegistration for tests."""

    name: str
    invoke: Optional[Any] = None


def make_registry(*capabilities_map):
    """Build a mock registry from (capability, provider_name, invoke_fn) tuples."""
    registry = MagicMock()
    mapping = {}
    for cap, name, fn in capabilities_map:
        mapping.setdefault(cap, []).append(FakeRegistration(name=name, invoke=fn))

    def find(cap):
        return mapping.get(cap, [])

    registry.find_for_capability = MagicMock(side_effect=find)
    return registry


async def _constant_invoke(value):
    """Return a factory for an async invoke that always returns value."""

    async def invoke(inp, ctx):
        return value

    return invoke


def sync_to_async_invoke(value):
    """Create an async invoke that returns value."""

    async def invoke(inp, ctx):
        return value

    return invoke


# ===========================================================================
# TestLoopConfig
# ===========================================================================


class TestLoopConfig:
    """Tests for LoopConfig dataclass."""

    def test_defaults(self):
        cfg = LoopConfig()
        assert cfg.max_iterations == 3
        assert cfg.convergence_fn is None

    def test_custom_values(self):
        fn = lambda prev, curr: prev == curr
        cfg = LoopConfig(max_iterations=5, convergence_fn=fn)
        assert cfg.max_iterations == 5
        assert cfg.convergence_fn is fn

    def test_convergence_fn_callable(self):
        cfg = LoopConfig(convergence_fn=lambda p, c: True)
        assert cfg.convergence_fn(1, 2) is True


# ===========================================================================
# TestConditionalPhase
# ===========================================================================


class TestConditionalPhase:
    """Tests for condition field on WorkflowPhase."""

    async def test_condition_true_runs_phase(self):
        invoke_fn = AsyncMock(return_value={"result": "ok"})
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = (
            WorkflowBuilder("cond_true")
            .add_phase("p1", capability="cap_a", condition=lambda ctx: True)
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED
        invoke_fn.assert_called_once()

    async def test_condition_false_skips_phase(self):
        invoke_fn = AsyncMock(return_value={"result": "ok"})
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = (
            WorkflowBuilder("cond_false")
            .add_phase("p1", capability="cap_a", condition=lambda ctx: False)
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.SKIPPED
        assert "Condition not met" in results["p1"].error
        invoke_fn.assert_not_called()

    async def test_condition_raises_runs_phase_anyway(self):
        """When condition evaluation raises, phase runs (graceful degradation)."""
        invoke_fn = AsyncMock(return_value="ok")
        registry = make_registry(("cap_a", "prov_a", invoke_fn))

        def bad_condition(ctx):
            raise ValueError("boom")

        wf = (
            WorkflowBuilder("cond_err")
            .add_phase("p1", capability="cap_a", condition=bad_condition)
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED
        invoke_fn.assert_called_once()

    async def test_no_condition_runs_phase(self):
        invoke_fn = AsyncMock(return_value="ok")
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = WorkflowBuilder("no_cond").add_phase("p1", capability="cap_a").build()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED

    async def test_condition_receives_full_context(self):
        """Condition callable receives ctx with input_data and previous phase outputs."""
        captured_ctx = {}
        invoke_fn = AsyncMock(return_value={"score": 5})
        registry = make_registry(
            ("cap_a", "prov_a", invoke_fn),
            ("cap_b", "prov_b", AsyncMock(return_value="b_out")),
        )

        def capture_condition(ctx):
            captured_ctx.update(ctx)
            return True

        wf = (
            WorkflowBuilder("ctx_check")
            .add_phase("p1", capability="cap_a")
            .add_phase(
                "p2", capability="cap_b", condition=capture_condition, depends_on=["p1"]
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        await executor.execute(wf, input_data="hello")
        assert captured_ctx["input_data"] == "hello"
        assert "phase_p1_output" in captured_ctx


# ===========================================================================
# TestLoopExecution
# ===========================================================================


class TestLoopExecution:
    """Tests for iterative phase execution via loop_config."""

    async def test_single_iteration(self):
        invoke_fn = AsyncMock(return_value={"score": 10})
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = (
            WorkflowBuilder("loop_1")
            .add_loop("p1", capability="cap_a", max_iterations=1)
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED
        assert invoke_fn.call_count == 1

    async def test_max_iterations_reached(self):
        invoke_fn = AsyncMock(side_effect=[{"s": 1}, {"s": 2}, {"s": 3}])
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = (
            WorkflowBuilder("loop_max")
            .add_loop("p1", capability="cap_a", max_iterations=3)
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED
        assert invoke_fn.call_count == 3
        assert results["p1"].output == {"s": 3}

    async def test_convergence_stops_early(self):
        invoke_fn = AsyncMock(side_effect=[{"s": 1}, {"s": 5}, {"s": 5}])
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = (
            WorkflowBuilder("loop_conv")
            .add_loop(
                "p1",
                capability="cap_a",
                max_iterations=5,
                convergence_fn=lambda prev, curr: prev == curr,
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED
        # Convergence at iteration 2 (prev={s:5}, curr={s:5})
        assert invoke_fn.call_count == 3

    async def test_convergence_fn_raises_continues(self):
        invoke_fn = AsyncMock(side_effect=[{"s": 1}, {"s": 2}])
        registry = make_registry(("cap_a", "prov_a", invoke_fn))

        def bad_conv(prev, curr):
            raise RuntimeError("convergence error")

        wf = (
            WorkflowBuilder("loop_conv_err")
            .add_loop(
                "p1", capability="cap_a", max_iterations=2, convergence_fn=bad_conv
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED
        assert invoke_fn.call_count == 2

    async def test_loop_stores_iteration_in_context(self):
        captured_iterations = []

        async def tracking_invoke(inp, ctx):
            captured_iterations.append(ctx.get(f"phase_p1_iteration"))
            return {"score": len(captured_iterations)}

        registry = make_registry(("cap_a", "prov_a", tracking_invoke))
        wf = (
            WorkflowBuilder("loop_ctx")
            .add_loop("p1", capability="cap_a", max_iterations=3)
            .build()
        )
        executor = WorkflowExecutor(registry)
        await executor.execute(wf, input_data="test")
        # First call: iteration not yet set (None), then 0, then 1
        assert captured_iterations == [None, 0, 1]

    async def test_loop_with_timeout(self):
        async def slow_invoke(inp, ctx):
            await asyncio.sleep(0.01)
            return "done"

        registry = make_registry(("cap_a", "prov_a", slow_invoke))
        wf = (
            WorkflowBuilder("loop_timeout")
            .add_loop("p1", capability="cap_a", max_iterations=2)
            .build()
        )
        # Set generous timeout — should complete
        wf.phases[0].timeout_seconds = 5.0
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED


# ===========================================================================
# TestInputTransform
# ===========================================================================


class TestInputTransform:
    """Tests for input_transform on WorkflowPhase."""

    async def test_transforms_input(self):
        captured_inputs = []

        async def capturing_invoke(inp, ctx):
            captured_inputs.append(inp)
            return {"processed": inp}

        registry = make_registry(("cap_a", "prov_a", capturing_invoke))
        wf = (
            WorkflowBuilder("transform")
            .add_phase(
                "p1",
                capability="cap_a",
                input_transform=lambda inp, ctx: inp.upper(),
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        await executor.execute(wf, input_data="hello")
        assert captured_inputs == ["HELLO"]

    async def test_transform_raises_uses_original(self):
        captured_inputs = []

        async def capturing_invoke(inp, ctx):
            captured_inputs.append(inp)
            return "ok"

        def bad_transform(inp, ctx):
            raise ValueError("transform error")

        registry = make_registry(("cap_a", "prov_a", capturing_invoke))
        wf = (
            WorkflowBuilder("transform_err")
            .add_phase("p1", capability="cap_a", input_transform=bad_transform)
            .build()
        )
        executor = WorkflowExecutor(registry)
        await executor.execute(wf, input_data="hello")
        assert captured_inputs == ["hello"]  # original input used

    async def test_no_transform_uses_original(self):
        captured_inputs = []

        async def capturing_invoke(inp, ctx):
            captured_inputs.append(inp)
            return "ok"

        registry = make_registry(("cap_a", "prov_a", capturing_invoke))
        wf = WorkflowBuilder("no_transform").add_phase("p1", capability="cap_a").build()
        executor = WorkflowExecutor(registry)
        await executor.execute(wf, input_data="hello")
        assert captured_inputs == ["hello"]


# ===========================================================================
# TestWorkflowBuilderExtensions
# ===========================================================================


class TestWorkflowBuilderExtensions:
    """Tests for WorkflowBuilder convenience methods."""

    def test_add_conditional_phase(self):
        cond = lambda ctx: True
        wf = (
            WorkflowBuilder("b1")
            .add_conditional_phase("p1", capability="cap_a", condition=cond)
            .build()
        )
        assert wf.phases[0].condition is cond

    def test_add_loop(self):
        conv = lambda p, c: p == c
        wf = (
            WorkflowBuilder("b2")
            .add_loop("p1", capability="cap_a", max_iterations=5, convergence_fn=conv)
            .build()
        )
        assert wf.phases[0].loop_config is not None
        assert wf.phases[0].loop_config.max_iterations == 5
        assert wf.phases[0].loop_config.convergence_fn is conv

    def test_chaining(self):
        wf = (
            WorkflowBuilder("chain")
            .add_phase("p1", capability="a")
            .add_conditional_phase("p2", capability="b", condition=lambda c: True)
            .add_loop("p3", capability="c", max_iterations=2)
            .build()
        )
        assert len(wf.phases) == 3

    def test_backward_compat_add_phase(self):
        """Existing add_phase calls (without new kwargs) still work."""
        wf = (
            WorkflowBuilder("compat")
            .add_phase("p1", capability="cap_a", optional=True)
            .build()
        )
        phase = wf.phases[0]
        assert phase.condition is None
        assert phase.loop_config is None
        assert phase.input_transform is None
        assert phase.optional is True


# ===========================================================================
# TestPreBuiltLoopWorkflows
# ===========================================================================


class TestPreBuiltLoopWorkflows:
    """Tests for the 4 pre-built loop workflows in unified_pipeline."""

    def test_quality_gated_validates(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        assert wf.name == "quality_gated_counter"
        assert len(wf.validate()) == 0

    def test_quality_gated_has_condition_on_counter(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        counter = wf.get_phase("counter")
        assert counter is not None
        assert counter.condition is not None

    def test_quality_gated_has_loop_on_recheck(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        recheck = wf.get_phase("quality_recheck")
        assert recheck is not None
        assert recheck.loop_config is not None
        assert recheck.loop_config.max_iterations == 3

    def test_debate_governance_validates(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_debate_governance_loop_workflow,
        )

        wf = build_debate_governance_loop_workflow()
        assert wf.name == "debate_governance_loop"
        assert len(wf.validate()) == 0

    def test_jtms_dung_validates(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_jtms_dung_loop_workflow,
        )

        wf = build_jtms_dung_loop_workflow()
        assert wf.name == "jtms_dung_loop"
        assert len(wf.validate()) == 0

    def test_neural_symbolic_validates(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_neural_symbolic_fallacy_workflow,
        )

        wf = build_neural_symbolic_fallacy_workflow()
        assert wf.name == "neural_symbolic_fallacy"
        assert len(wf.validate()) == 0


# ===========================================================================
# TestQualityGatedEndToEnd
# ===========================================================================


class TestQualityGatedEndToEnd:
    """End-to-end tests for the quality-gated counter-argument workflow."""

    async def test_quality_above_threshold_counter_runs(self):
        quality_invoke = AsyncMock(return_value={"note_finale": 4.5})
        counter_invoke = AsyncMock(
            return_value={
                "suggested_strategy": {"strategy_name": "reductio"},
                "parsed_argument": {},
            }
        )
        registry = make_registry(
            ("argument_quality", "quality_eval", quality_invoke),
            ("counter_argument_generation", "counter_gen", counter_invoke),
        )

        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="Some argument")

        assert results["quality"].status == PhaseStatus.COMPLETED
        assert results["counter"].status == PhaseStatus.COMPLETED
        counter_invoke.assert_called()

    async def test_quality_below_threshold_counter_skipped(self):
        quality_invoke = AsyncMock(return_value={"note_finale": 2.0})
        counter_invoke = AsyncMock(return_value={})
        registry = make_registry(
            ("argument_quality", "quality_eval", quality_invoke),
            ("counter_argument_generation", "counter_gen", counter_invoke),
        )

        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="Weak argument")

        assert results["quality"].status == PhaseStatus.COMPLETED
        assert results["counter"].status == PhaseStatus.SKIPPED
        counter_invoke.assert_not_called()

    async def test_loop_converges(self):
        quality_invoke = AsyncMock(
            side_effect=[
                {"note_finale": 4.0},  # initial quality
                {"note_finale": 7.0},  # recheck iter 0
                {"note_finale": 7.0},  # recheck iter 1 — converges (7 >= 7)
            ]
        )
        counter_invoke = AsyncMock(
            return_value={
                "suggested_strategy": {"strategy_name": "distinction"},
                "parsed_argument": {},
            }
        )
        registry = make_registry(
            ("argument_quality", "quality_eval", quality_invoke),
            ("counter_argument_generation", "counter_gen", counter_invoke),
        )

        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="Some argument")

        assert results["quality_recheck"].status == PhaseStatus.COMPLETED
        # 1 for initial quality + 2 for recheck iterations = 3 total calls
        assert quality_invoke.call_count == 3

    async def test_loop_hits_max_iterations(self):
        quality_invoke = AsyncMock(
            side_effect=[
                {"note_finale": 4.0},  # initial quality
                {"note_finale": 3.0},  # recheck iter 0
                {"note_finale": 2.0},  # recheck iter 1 — 2.0 >= 3.0 False
                {"note_finale": 1.0},  # recheck iter 2 — 1.0 >= 2.0 False → max
            ]
        )
        counter_invoke = AsyncMock(
            return_value={
                "suggested_strategy": {"strategy_name": "concession"},
                "parsed_argument": {},
            }
        )
        registry = make_registry(
            ("argument_quality", "quality_eval", quality_invoke),
            ("counter_argument_generation", "counter_gen", counter_invoke),
        )

        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="Some argument")

        assert results["quality_recheck"].status == PhaseStatus.COMPLETED
        # 1 initial + 3 recheck = 4
        assert quality_invoke.call_count == 4


# ===========================================================================
# TestEdgeCases
# ===========================================================================


class TestEdgeCases:
    """Edge case tests."""

    def test_empty_workflow(self):
        wf = WorkflowBuilder("empty").build()
        assert len(wf.phases) == 0
        assert wf.validate() == []

    async def test_condition_and_loop_on_same_phase(self):
        """A phase with both condition and loop_config."""
        call_count = 0

        async def counting_invoke(inp, ctx):
            nonlocal call_count
            call_count += 1
            return {"v": call_count}

        registry = make_registry(("cap_a", "prov_a", counting_invoke))
        wf = (
            WorkflowBuilder("cond_loop")
            .add_phase(
                "p1",
                capability="cap_a",
                condition=lambda ctx: True,
                loop_config=LoopConfig(max_iterations=2),
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.COMPLETED
        assert call_count == 2

    async def test_condition_false_with_loop_skips(self):
        """When condition is False, loop never executes."""
        invoke_fn = AsyncMock(return_value="x")
        registry = make_registry(("cap_a", "prov_a", invoke_fn))
        wf = (
            WorkflowBuilder("cond_false_loop")
            .add_phase(
                "p1",
                capability="cap_a",
                condition=lambda ctx: False,
                loop_config=LoopConfig(max_iterations=5),
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        assert results["p1"].status == PhaseStatus.SKIPPED
        invoke_fn.assert_not_called()

    async def test_missing_provider_with_condition(self):
        """Missing provider on conditional phase → FAILED (not optional)."""
        registry = make_registry()  # empty
        wf = (
            WorkflowBuilder("no_prov")
            .add_phase("p1", capability="cap_a", condition=lambda ctx: True)
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, input_data="test")
        # Condition is True, but no provider → FAILED
        assert results["p1"].status == PhaseStatus.FAILED


# ===========================================================================
# TestWorkflowCatalog
# ===========================================================================


class TestWorkflowCatalog:
    """Tests for the expanded workflow catalog."""

    def test_catalog_includes_loop_workflows(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )

        # Reset cached catalog
        import argumentation_analysis.orchestration.unified_pipeline as up

        up.WORKFLOW_CATALOG = {}

        catalog = get_workflow_catalog()
        assert "quality_gated" in catalog
        assert "debate_governance" in catalog
        assert "jtms_dung" in catalog
        assert "neural_symbolic" in catalog

    def test_catalog_preserves_original_workflows(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )

        import argumentation_analysis.orchestration.unified_pipeline as up

        up.WORKFLOW_CATALOG = {}

        catalog = get_workflow_catalog()
        assert "light" in catalog
        assert "standard" in catalog
        assert "full" in catalog
