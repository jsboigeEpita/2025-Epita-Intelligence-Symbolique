# -*- coding: utf-8 -*-
"""
Tests for WorkflowExecutor real invocation via invoke callables.

Covers: invoke callable dispatch, fallback when invoke=None, error handling,
downstream context chaining, timeout support, and integration with real components.
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

# ============================================================
# Basic invoke callable dispatch
# ============================================================


class TestInvokeCallableDispatch:
    @pytest.mark.asyncio
    async def test_invoke_callable_is_called(self):
        """When a component has an invoke callable, it is called with input_data."""
        calls = []

        async def fake_invoke(text, ctx):
            calls.append(text)
            return {"score": 0.85}

        registry = CapabilityRegistry()
        registry.register(
            name="test_comp",
            component_type=ComponentType.AGENT,
            capabilities=["test_cap"],
            invoke=fake_invoke,
        )

        workflow = (
            WorkflowBuilder("test").add_phase("p1", capability="test_cap").build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "hello world")

        assert results["p1"].status == PhaseStatus.COMPLETED
        assert results["p1"].output == {"score": 0.85}
        assert calls == ["hello world"]

    @pytest.mark.asyncio
    async def test_invoke_callable_receives_context(self):
        """Invoke callable receives the context dict."""
        received_ctx = {}

        async def capture_invoke(text, ctx):
            received_ctx.update(ctx)
            return {"ok": True}

        registry = CapabilityRegistry()
        registry.register(
            name="ctx_comp",
            component_type=ComponentType.AGENT,
            capabilities=["ctx_cap"],
            invoke=capture_invoke,
        )

        workflow = WorkflowBuilder("test").add_phase("p1", capability="ctx_cap").build()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(
            workflow, "test", context={"extra_key": "extra_value"}
        )

        assert results["p1"].status == PhaseStatus.COMPLETED
        assert received_ctx.get("extra_key") == "extra_value"
        assert received_ctx.get("input_data") == "test"

    @pytest.mark.asyncio
    async def test_invoke_returns_string_output(self):
        """Invoke callable can return non-dict outputs."""

        async def string_invoke(text, ctx):
            return f"Processed: {text}"

        registry = CapabilityRegistry()
        registry.register(
            name="str_comp",
            component_type=ComponentType.SERVICE,
            capabilities=["str_cap"],
            invoke=string_invoke,
        )

        workflow = WorkflowBuilder("test").add_phase("p1", capability="str_cap").build()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "input")

        assert results["p1"].output == "Processed: input"


# ============================================================
# Fallback when invoke=None
# ============================================================


class TestInvokeNoneFallback:
    @pytest.mark.asyncio
    async def test_no_invoke_returns_none_output(self):
        """When invoke is None, phase completes with output=None."""
        registry = CapabilityRegistry()
        registry.register_agent(
            "legacy_comp", type("X", (), {}), capabilities=["legacy_cap"]
        )

        workflow = (
            WorkflowBuilder("test").add_phase("p1", capability="legacy_cap").build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "test")

        assert results["p1"].status == PhaseStatus.COMPLETED
        assert results["p1"].output is None
        assert results["p1"].component_used == "legacy_comp"


# ============================================================
# Error handling
# ============================================================


class TestInvokeErrorHandling:
    @pytest.mark.asyncio
    async def test_invoke_failure_marks_phase_failed(self):
        """When invoke raises, the phase is marked FAILED."""

        async def failing_invoke(text, ctx):
            raise RuntimeError("Boom!")

        registry = CapabilityRegistry()
        registry.register(
            name="crasher",
            component_type=ComponentType.AGENT,
            capabilities=["crash_cap"],
            invoke=failing_invoke,
        )

        workflow = (
            WorkflowBuilder("test").add_phase("p1", capability="crash_cap").build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "test")

        assert results["p1"].status == PhaseStatus.FAILED
        assert "Boom!" in results["p1"].error

    @pytest.mark.asyncio
    async def test_invoke_value_error(self):
        """ValueError during invoke is captured."""

        async def bad_invoke(text, ctx):
            raise ValueError("Invalid input")

        registry = CapabilityRegistry()
        registry.register(
            name="bad_comp",
            component_type=ComponentType.SERVICE,
            capabilities=["bad_cap"],
            invoke=bad_invoke,
        )

        workflow = WorkflowBuilder("test").add_phase("p1", capability="bad_cap").build()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "test")

        assert results["p1"].status == PhaseStatus.FAILED
        assert "Invalid input" in results["p1"].error


# ============================================================
# Context chaining between phases
# ============================================================


class TestContextChaining:
    @pytest.mark.asyncio
    async def test_downstream_phase_receives_upstream_output(self):
        """Downstream phases can access upstream outputs via context."""

        async def phase_a_invoke(text, ctx):
            return {"quality_score": 0.9}

        async def phase_b_invoke(text, ctx):
            upstream = ctx.get("phase_a_output", {})
            score = (
                upstream.get("quality_score", 0) if isinstance(upstream, dict) else 0
            )
            return {"counter_based_on": score}

        registry = CapabilityRegistry()
        registry.register(
            "comp_a", ComponentType.AGENT, capabilities=["cap_a"], invoke=phase_a_invoke
        )
        registry.register(
            "comp_b", ComponentType.AGENT, capabilities=["cap_b"], invoke=phase_b_invoke
        )

        workflow = (
            WorkflowBuilder("chain")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b", depends_on=["a"])
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "test text")

        assert results["a"].output == {"quality_score": 0.9}
        assert results["b"].output["counter_based_on"] == 0.9

    @pytest.mark.asyncio
    async def test_phase_result_stored_in_context(self):
        """PhaseResult is accessible in context as phase_{name}_result."""
        context_snapshot = {}

        async def phase_b_invoke(text, ctx):
            context_snapshot["a_result"] = ctx.get("phase_a_result")
            return {"done": True}

        async def phase_a_invoke(text, ctx):
            return {"value": 42}

        registry = CapabilityRegistry()
        registry.register(
            "a", ComponentType.AGENT, capabilities=["cap_a"], invoke=phase_a_invoke
        )
        registry.register(
            "b", ComponentType.AGENT, capabilities=["cap_b"], invoke=phase_b_invoke
        )

        workflow = (
            WorkflowBuilder("chain")
            .add_phase("a", capability="cap_a")
            .add_phase("b", capability="cap_b", depends_on=["a"])
            .build()
        )
        executor = WorkflowExecutor(registry)
        await executor.execute(workflow, "test")

        a_result = context_snapshot["a_result"]
        assert a_result.status == PhaseStatus.COMPLETED
        assert a_result.output == {"value": 42}


# ============================================================
# Timeout support
# ============================================================


class TestTimeoutSupport:
    @pytest.mark.asyncio
    async def test_timeout_triggers_failure(self):
        """Phase with timeout fails if invoke takes too long."""

        async def slow_invoke(text, ctx):
            await asyncio.sleep(10)
            return {"done": True}

        registry = CapabilityRegistry()
        registry.register(
            "slow", ComponentType.SERVICE, capabilities=["slow_cap"], invoke=slow_invoke
        )

        workflow = (
            WorkflowBuilder("timeout_test")
            .add_phase("p1", capability="slow_cap", timeout_seconds=0.1)
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "test")

        assert results["p1"].status == PhaseStatus.FAILED

    @pytest.mark.asyncio
    async def test_fast_invoke_within_timeout(self):
        """Phase within timeout completes normally."""

        async def fast_invoke(text, ctx):
            return {"fast": True}

        registry = CapabilityRegistry()
        registry.register(
            "fast", ComponentType.SERVICE, capabilities=["fast_cap"], invoke=fast_invoke
        )

        workflow = (
            WorkflowBuilder("fast_test")
            .add_phase("p1", capability="fast_cap", timeout_seconds=5.0)
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "test")

        assert results["p1"].status == PhaseStatus.COMPLETED
        assert results["p1"].output == {"fast": True}


# ============================================================
# Optional phase handling
# ============================================================


class TestOptionalPhases:
    @pytest.mark.asyncio
    async def test_optional_phase_no_provider_skipped(self):
        """Optional phase without provider is SKIPPED."""
        registry = CapabilityRegistry()

        workflow = (
            WorkflowBuilder("opt_test")
            .add_phase("p1", capability="nonexistent_cap", optional=True)
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "test")

        assert results["p1"].status == PhaseStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_required_phase_no_provider_fails(self):
        """Required phase without provider FAILS."""
        registry = CapabilityRegistry()

        workflow = (
            WorkflowBuilder("req_test")
            .add_phase("p1", capability="nonexistent_cap", optional=False)
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "test")

        assert results["p1"].status == PhaseStatus.FAILED


# ============================================================
# Multi-phase workflow
# ============================================================


class TestMultiPhaseWorkflow:
    @pytest.mark.asyncio
    async def test_three_phase_pipeline(self):
        """Complete 3-phase pipeline with real invoke callables."""

        async def extract_invoke(text, ctx):
            return {"claims": text.split(".")}

        async def analyze_invoke(text, ctx):
            claims = ctx.get("phase_extract_output", {})
            count = len(claims.get("claims", [])) if isinstance(claims, dict) else 0
            return {"claim_count": count}

        async def synthesize_invoke(text, ctx):
            analysis = ctx.get("phase_analyze_output", {})
            return {"summary": f"Found {analysis.get('claim_count', 0)} claims"}

        registry = CapabilityRegistry()
        registry.register(
            "extractor",
            ComponentType.AGENT,
            capabilities=["extract"],
            invoke=extract_invoke,
        )
        registry.register(
            "analyzer",
            ComponentType.AGENT,
            capabilities=["analyze"],
            invoke=analyze_invoke,
        )
        registry.register(
            "synthesizer",
            ComponentType.AGENT,
            capabilities=["synthesize"],
            invoke=synthesize_invoke,
        )

        workflow = (
            WorkflowBuilder("pipeline")
            .add_phase("extract", capability="extract")
            .add_phase("analyze", capability="analyze", depends_on=["extract"])
            .add_phase("synthesize", capability="synthesize", depends_on=["analyze"])
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "Claim one. Claim two. Claim three")

        assert results["extract"].status == PhaseStatus.COMPLETED
        assert results["analyze"].status == PhaseStatus.COMPLETED
        assert results["synthesize"].status == PhaseStatus.COMPLETED
        assert results["extract"].output["claims"][0] == "Claim one"
        assert (
            results["analyze"].output["claim_count"] >= 3
        )  # 3 claims + possible empty trailing

    @pytest.mark.asyncio
    async def test_mixed_invoke_and_none(self):
        """Workflow with some invoke callables and some None."""

        async def real_invoke(text, ctx):
            return {"real": True}

        registry = CapabilityRegistry()
        registry.register(
            "real", ComponentType.AGENT, capabilities=["real_cap"], invoke=real_invoke
        )
        registry.register_agent(
            "legacy", type("L", (), {}), capabilities=["legacy_cap"]
        )

        workflow = (
            WorkflowBuilder("mixed")
            .add_phase("p1", capability="real_cap")
            .add_phase("p2", capability="legacy_cap")
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, "test")

        assert results["p1"].output == {"real": True}
        assert results["p2"].output is None
        assert results["p1"].status == PhaseStatus.COMPLETED
        assert results["p2"].status == PhaseStatus.COMPLETED


# ============================================================
# Integration: real quality evaluator
# ============================================================


class TestRealComponentIntegration:
    @pytest.mark.asyncio
    async def test_quality_evaluator_real_invoke(self):
        """Integration test: quality evaluator produces real scores."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        workflow = (
            WorkflowBuilder("quality_only")
            .add_phase("quality", capability="argument_quality")
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(
            workflow,
            "Les vaccins sont efficaces car les études scientifiques le montrent.",
        )

        assert results["quality"].status == PhaseStatus.COMPLETED
        assert results["quality"].output is not None
        assert isinstance(results["quality"].output, dict)
        assert "note_finale" in results["quality"].output

    @pytest.mark.asyncio
    async def test_counter_argument_real_invoke(self):
        """Integration test: counter-argument plugin produces real analysis."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        workflow = (
            WorkflowBuilder("counter_only")
            .add_phase("counter", capability="counter_argument_generation")
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(
            workflow, "Les vaccins sont dangereux car un ami est tombé malade."
        )

        assert results["counter"].status == PhaseStatus.COMPLETED
        assert results["counter"].output is not None
        assert "parsed_argument" in results["counter"].output
        assert "suggested_strategy" in results["counter"].output

    @pytest.mark.asyncio
    async def test_light_workflow_quality_and_counter(self):
        """Integration test: light workflow chains quality -> counter."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
            build_light_workflow,
        )

        registry = setup_registry(include_optional=False)
        workflow = build_light_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(
            workflow,
            "La peine de mort devrait être abolie car elle ne dissuade pas le crime.",
        )

        assert results["quality"].status == PhaseStatus.COMPLETED
        assert results["quality"].output is not None

        assert results["counter"].status == PhaseStatus.COMPLETED
        assert results["counter"].output is not None
        # Counter should have received quality context
        assert results["counter"].output.get("quality_context") is not None
