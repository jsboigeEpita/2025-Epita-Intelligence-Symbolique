"""Tests for the Democratech deliberation workflow."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.workflows.democratech import (
    build_democratech_workflow,
    run_deliberation,
    _needs_refinement,
    DEFAULT_CONSENSUS_THRESHOLD,
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


class TestBuildDemocratechWorkflow:
    """Validate workflow structure and metadata."""

    def test_build_creates_valid_workflow(self):
        wf = build_democratech_workflow()
        assert wf.name == "democratech"
        errors = wf.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_phase_count(self):
        wf = build_democratech_workflow()
        assert len(wf.phases) == 9

    def test_required_capabilities(self):
        wf = build_democratech_workflow()
        caps = wf.get_required_capabilities()
        assert "argument_quality" in caps
        assert "counter_argument_generation" in caps
        assert "adversarial_debate" in caps
        assert "governance_simulation" in caps

    def test_optional_phases(self):
        wf = build_democratech_workflow()
        optional_names = {p.name for p in wf.phases if p.optional}
        assert "transcription" in optional_names
        assert "fallacy_detection" in optional_names
        assert "belief_tracking" in optional_names
        assert "indexing" in optional_names
        assert "quality_recheck" in optional_names

    def test_required_phases(self):
        wf = build_democratech_workflow()
        required_names = {p.name for p in wf.phases if not p.optional}
        assert "quality_baseline" in required_names
        assert "counter_arguments" in required_names
        assert "adversarial_debate" in required_names
        assert "democratic_vote" in required_names

    def test_execution_order_respects_dependencies(self):
        wf = build_democratech_workflow()
        order = wf.get_execution_order()
        # Flatten to a flat list
        flat = [phase for level in order for phase in level]
        assert flat.index("quality_baseline") < flat.index("counter_arguments")
        assert flat.index("counter_arguments") < flat.index("adversarial_debate")
        assert flat.index("adversarial_debate") < flat.index("democratic_vote")
        assert flat.index("democratic_vote") < flat.index("quality_recheck")

    def test_quality_recheck_has_condition(self):
        wf = build_democratech_workflow()
        recheck = wf.get_phase("quality_recheck")
        assert recheck is not None
        assert recheck.condition is not None

    def test_custom_consensus_threshold(self):
        wf = build_democratech_workflow(consensus_threshold=0.5)
        recheck = wf.get_phase("quality_recheck")
        # Verify condition uses the custom threshold
        ctx_low = {"phase_democratic_vote_output": {"consensus": 0.4}}
        ctx_high = {"phase_democratic_vote_output": {"consensus": 0.6}}
        assert recheck.condition(ctx_low) is True
        assert recheck.condition(ctx_high) is False

    def test_metadata(self):
        wf = build_democratech_workflow()
        assert wf.metadata["domain"] == "democratic_decision_making"
        assert wf.metadata["version"] == "1.0"


# --- Condition function tests ---


class TestNeedsRefinement:
    """Test the _needs_refinement condition function."""

    def test_low_consensus_triggers_refinement(self):
        ctx = {"phase_democratic_vote_output": {"consensus": 0.4}}
        assert _needs_refinement(ctx, 0.7) is True

    def test_high_consensus_skips_refinement(self):
        ctx = {"phase_democratic_vote_output": {"consensus": 0.9}}
        assert _needs_refinement(ctx, 0.7) is False

    def test_exact_threshold_skips_refinement(self):
        ctx = {"phase_democratic_vote_output": {"consensus": 0.7}}
        assert _needs_refinement(ctx, 0.7) is False

    def test_missing_vote_output(self):
        assert _needs_refinement({}, 0.7) is False

    def test_non_dict_vote_output(self):
        ctx = {"phase_democratic_vote_output": "not a dict"}
        assert _needs_refinement(ctx, 0.7) is False

    def test_consensus_rate_key(self):
        ctx = {"phase_democratic_vote_output": {"consensus_rate": 0.3}}
        assert _needs_refinement(ctx, 0.7) is True


# --- Execution tests ---


def _make_registry(*capabilities):
    """Create a registry with fake invoke callables for given capabilities."""
    registry = CapabilityRegistry()
    for cap in capabilities:
        invoke_fn = AsyncMock(return_value={"capability": cap, "score": 0.8})
        registry.register(
            name=f"mock_{cap}",
            component_type=ComponentType.AGENT,
            capabilities=[cap],
            invoke=invoke_fn,
        )
    return registry


class TestDemocratechExecution:
    """Test workflow execution with mock registry."""

    @pytest.mark.asyncio
    async def test_execute_full_pipeline(self):
        registry = _make_registry(
            "speech_transcription",
            "argument_quality",
            "neural_fallacy_detection",
            "counter_argument_generation",
            "adversarial_debate",
            "belief_maintenance",
            "governance_simulation",
            "semantic_indexing",
        )
        wf = build_democratech_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Test proposition")

        assert results["quality_baseline"].status == PhaseStatus.COMPLETED
        assert results["counter_arguments"].status == PhaseStatus.COMPLETED
        assert results["adversarial_debate"].status == PhaseStatus.COMPLETED
        assert results["democratic_vote"].status == PhaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_missing_optional_capabilities(self):
        registry = _make_registry(
            "argument_quality",
            "counter_argument_generation",
            "adversarial_debate",
            "governance_simulation",
        )
        wf = build_democratech_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Test proposition")

        # Required phases complete
        assert results["quality_baseline"].status == PhaseStatus.COMPLETED
        assert results["democratic_vote"].status == PhaseStatus.COMPLETED
        # Optional phases skipped
        assert results["transcription"].status == PhaseStatus.SKIPPED
        assert results["fallacy_detection"].status == PhaseStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_conditional_recheck_triggered(self):
        """Low consensus triggers quality recheck."""
        low_consensus = AsyncMock(return_value={"consensus": 0.3, "method": "majority"})
        registry = _make_registry(
            "counter_argument_generation",
            "adversarial_debate",
        )
        # Register governance with low consensus output
        registry.register(
            name="mock_governance",
            component_type=ComponentType.AGENT,
            capabilities=["governance_simulation"],
            invoke=low_consensus,
        )
        # Register quality (used for baseline AND recheck)
        quality_invoke = AsyncMock(return_value={"note_finale": 7.0})
        registry.register(
            name="mock_quality",
            component_type=ComponentType.AGENT,
            capabilities=["argument_quality"],
            invoke=quality_invoke,
        )

        wf = build_democratech_workflow(consensus_threshold=0.7)
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Controversial proposition")

        assert results["quality_recheck"].status == PhaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_conditional_recheck_skipped_high_consensus(self):
        """High consensus skips quality recheck."""
        high_consensus = AsyncMock(
            return_value={"consensus": 0.95, "method": "condorcet"}
        )
        registry = _make_registry(
            "counter_argument_generation",
            "adversarial_debate",
        )
        registry.register(
            name="mock_governance",
            component_type=ComponentType.AGENT,
            capabilities=["governance_simulation"],
            invoke=high_consensus,
        )
        quality_invoke = AsyncMock(return_value={"note_finale": 8.0})
        registry.register(
            name="mock_quality",
            component_type=ComponentType.AGENT,
            capabilities=["argument_quality"],
            invoke=quality_invoke,
        )

        wf = build_democratech_workflow(consensus_threshold=0.7)
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Uncontroversial proposition")

        assert results["quality_recheck"].status == PhaseStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_context_flows_between_phases(self):
        """Downstream phases receive upstream outputs in context."""
        captured_contexts = []

        async def capturing_invoke(text, ctx):
            captured_contexts.append(dict(ctx))
            return {"captured": True}

        registry = CapabilityRegistry()
        quality_invoke = AsyncMock(return_value={"note_finale": 7.5})
        registry.register(
            "quality",
            ComponentType.AGENT,
            capabilities=["argument_quality"],
            invoke=quality_invoke,
        )
        registry.register(
            "counter",
            ComponentType.AGENT,
            capabilities=["counter_argument_generation"],
            invoke=capturing_invoke,
        )
        registry.register(
            "debate",
            ComponentType.AGENT,
            capabilities=["adversarial_debate"],
            invoke=AsyncMock(return_value={"debate": True}),
        )
        registry.register(
            "governance",
            ComponentType.AGENT,
            capabilities=["governance_simulation"],
            invoke=AsyncMock(return_value={"consensus": 0.9}),
        )

        wf = build_democratech_workflow()
        executor = WorkflowExecutor(registry)
        await executor.execute(wf, "Test input")

        # counter_arguments phase should see quality_baseline output
        assert len(captured_contexts) >= 1
        counter_ctx = captured_contexts[0]
        assert "phase_quality_baseline_output" in counter_ctx


# --- Convenience wrapper tests ---


class TestRunDeliberation:
    """Test the run_deliberation convenience function."""

    @pytest.mark.asyncio
    async def test_calls_run_unified_analysis(self):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value={"workflow_name": "democratech", "phases": {}},
        ) as mock_run:
            result = await run_deliberation("Test proposition")
            mock_run.assert_called_once()
            assert result["workflow_name"] == "democratech"

    @pytest.mark.asyncio
    async def test_passes_custom_threshold(self):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value={"workflow_name": "democratech", "phases": {}},
        ) as mock_run:
            await run_deliberation("Test", consensus_threshold=0.5)
            call_kwargs = mock_run.call_args[1]
            wf = call_kwargs["custom_workflow"]
            recheck = wf.get_phase("quality_recheck")
            # Verify threshold is 0.5
            ctx = {"phase_democratic_vote_output": {"consensus": 0.4}}
            assert recheck.condition(ctx) is True
