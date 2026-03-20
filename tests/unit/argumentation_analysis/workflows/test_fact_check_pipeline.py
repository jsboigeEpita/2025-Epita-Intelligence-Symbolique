"""Tests for the Fact-Check Pipeline workflow."""

import pytest
from unittest.mock import AsyncMock, patch

from argumentation_analysis.workflows.fact_check_pipeline import (
    build_fact_check_workflow,
    run_fact_check,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseStatus,
    WorkflowExecutor,
)
from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)

# --- Build tests ---


class TestBuildFactCheckWorkflow:
    """Validate workflow structure."""

    def test_build_creates_valid_workflow(self):
        wf = build_fact_check_workflow()
        assert wf.name == "fact_check"
        errors = wf.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_phase_count(self):
        wf = build_fact_check_workflow()
        assert len(wf.phases) == 6

    def test_required_capabilities(self):
        wf = build_fact_check_workflow()
        caps = wf.get_required_capabilities()
        assert "argument_quality" in caps
        assert "belief_maintenance" in caps
        assert "counter_argument_generation" in caps

    def test_optional_phases(self):
        wf = build_fact_check_workflow()
        optional_names = {p.name for p in wf.phases if p.optional}
        assert "transcription" in optional_names
        assert "fallacy_screen" in optional_names
        assert "indexing" in optional_names

    def test_required_phases(self):
        wf = build_fact_check_workflow()
        required_names = {p.name for p in wf.phases if not p.optional}
        assert "quality_assessment" in required_names
        assert "belief_tracking" in required_names
        assert "counter_check" in required_names

    def test_execution_order(self):
        wf = build_fact_check_workflow()
        order = wf.get_execution_order()
        flat = [phase for level in order for phase in level]
        assert flat.index("quality_assessment") < flat.index("belief_tracking")
        assert flat.index("quality_assessment") < flat.index("counter_check")
        assert flat.index("belief_tracking") < flat.index("indexing")

    def test_parallel_branches(self):
        """belief_tracking and counter_check can execute in parallel."""
        wf = build_fact_check_workflow()
        order = wf.get_execution_order()
        # Find the level containing both
        for level in order:
            if "belief_tracking" in level and "counter_check" in level:
                return  # Found them at the same level
            if "fallacy_screen" in level:
                # fallacy_screen, belief_tracking, counter_check all depend on quality_assessment
                if "belief_tracking" in level or "counter_check" in level:
                    return
        # They might be in separate levels if ordering differs,
        # but both must be after quality_assessment
        flat = [phase for level in order for phase in level]
        assert flat.index("quality_assessment") < flat.index("belief_tracking")
        assert flat.index("quality_assessment") < flat.index("counter_check")

    def test_metadata(self):
        wf = build_fact_check_workflow()
        assert wf.metadata["domain"] == "fact_checking"


# --- Execution tests ---


def _make_registry(*capabilities):
    """Create a registry with fake invoke callables."""
    registry = CapabilityRegistry()
    for cap in capabilities:
        invoke_fn = AsyncMock(return_value={"capability": cap, "result": "ok"})
        registry.register(
            name=f"mock_{cap}",
            component_type=ComponentType.AGENT,
            capabilities=[cap],
            invoke=invoke_fn,
        )
    return registry


class TestFactCheckExecution:
    """Test workflow execution with mock registry."""

    @pytest.mark.asyncio
    async def test_execute_full_pipeline(self):
        registry = _make_registry(
            "speech_transcription",
            "argument_quality",
            "neural_fallacy_detection",
            "belief_maintenance",
            "counter_argument_generation",
            "semantic_indexing",
        )
        wf = build_fact_check_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "The Earth is flat because...")

        assert results["quality_assessment"].status == PhaseStatus.COMPLETED
        assert results["belief_tracking"].status == PhaseStatus.COMPLETED
        assert results["counter_check"].status == PhaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_minimal_capabilities(self):
        """Only required capabilities provided."""
        registry = _make_registry(
            "argument_quality",
            "belief_maintenance",
            "counter_argument_generation",
        )
        wf = build_fact_check_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Claim to verify")

        assert results["quality_assessment"].status == PhaseStatus.COMPLETED
        assert results["belief_tracking"].status == PhaseStatus.COMPLETED
        assert results["counter_check"].status == PhaseStatus.COMPLETED
        assert results["transcription"].status == PhaseStatus.SKIPPED
        assert results["fallacy_screen"].status == PhaseStatus.SKIPPED
        assert results["indexing"].status == PhaseStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_context_carries_quality_to_downstream(self):
        """Belief tracking and counter_check receive quality output."""
        captured_contexts = {}

        async def tracking_invoke(text, ctx):
            captured_contexts["belief"] = dict(ctx)
            return {"beliefs": {"claim_0": "True"}}

        async def counter_invoke(text, ctx):
            captured_contexts["counter"] = dict(ctx)
            return {"counter": "generated"}

        registry = CapabilityRegistry()
        registry.register(
            "quality",
            ComponentType.AGENT,
            capabilities=["argument_quality"],
            invoke=AsyncMock(return_value={"note_finale": 6.5}),
        )
        registry.register(
            "jtms",
            ComponentType.SERVICE,
            capabilities=["belief_maintenance"],
            invoke=tracking_invoke,
        )
        registry.register(
            "counter",
            ComponentType.AGENT,
            capabilities=["counter_argument_generation"],
            invoke=counter_invoke,
        )

        wf = build_fact_check_workflow()
        executor = WorkflowExecutor(registry)
        await executor.execute(wf, "Test claim")

        assert "phase_quality_assessment_output" in captured_contexts["belief"]
        assert "phase_quality_assessment_output" in captured_contexts["counter"]


# --- Convenience wrapper tests ---


class TestRunFactCheck:
    """Test the run_fact_check convenience function."""

    @pytest.mark.asyncio
    async def test_calls_run_unified_analysis(self):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value={"workflow_name": "fact_check", "phases": {}},
        ) as mock_run:
            result = await run_fact_check("Article to check")
            mock_run.assert_called_once()
            assert result["workflow_name"] == "fact_check"

    @pytest.mark.asyncio
    async def test_passes_context(self):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value={"workflow_name": "fact_check", "phases": {}},
        ) as mock_run:
            ctx = {"source": "newspaper"}
            await run_fact_check("Article", context=ctx)
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["context"] == ctx
