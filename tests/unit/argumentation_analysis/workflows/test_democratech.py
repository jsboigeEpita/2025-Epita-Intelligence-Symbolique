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
        # BO-2 #1472: 10 phases — extract prepended so quality→governance has
        # argument material to reason over (was 9; governance never decided).
        assert len(wf.phases) == 10

    def test_required_capabilities(self):
        wf = build_democratech_workflow()
        caps = wf.get_required_capabilities()
        assert "fact_extraction" in caps
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
        assert "extract" in required_names
        assert "quality_baseline" in required_names
        assert "counter_arguments" in required_names
        assert "adversarial_debate" in required_names
        assert "democratic_vote" in required_names

    def test_execution_order_respects_dependencies(self):
        wf = build_democratech_workflow()
        order = wf.get_execution_order()
        # Flatten to a flat list
        flat = [phase for level in order for phase in level]
        # BO-2 #1472: extract feeds quality_baseline (the material to reason over)
        assert flat.index("extract") < flat.index("quality_baseline")
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
            "fact_extraction",
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

        assert results["extract"].status == PhaseStatus.COMPLETED
        assert results["quality_baseline"].status == PhaseStatus.COMPLETED
        assert results["counter_arguments"].status == PhaseStatus.COMPLETED
        assert results["adversarial_debate"].status == PhaseStatus.COMPLETED
        assert results["democratic_vote"].status == PhaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_missing_optional_capabilities(self):
        registry = _make_registry(
            "fact_extraction",
            "argument_quality",
            "counter_argument_generation",
            "adversarial_debate",
            "governance_simulation",
        )
        wf = build_democratech_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Test proposition")

        # Required phases complete (extract is required since BO-2 #1472)
        assert results["extract"].status == PhaseStatus.COMPLETED
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
            "fact_extraction",
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
            "fact_extraction",
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
        registry.register(
            "extract",
            ComponentType.AGENT,
            capabilities=["fact_extraction"],
            invoke=AsyncMock(return_value={"arguments": [{"text": "an argument"}]}),
        )
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


# --- Governance cabling tests (BO-2 #1472) ---


class TestGovernanceCabling:
    """BO-2 #1472: governance must resolve democratech's phase-name variants.

    The democratech workflow names its phases ``quality_baseline`` /
    ``adversarial_debate`` / ``counter_arguments`` / ``fallacy_detection`` /
    ``belief_tracking``, but the canonical context keys governance historically
    read were ``phase_quality_output`` / ``phase_debate_output`` / etc. Without
    the multi-key fallback, governance received an empty upstream and rendered
    a permanently-degraded verdict — the theatre #1019 forbids.
    """

    def test_resolve_phase_output_canonical_key(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _resolve_phase_output,
        )

        ctx = {"phase_quality_output": {"note_finale": 7.0}}
        assert _resolve_phase_output(ctx, "phase_quality_output") == {"note_finale": 7.0}

    def test_resolve_phase_output_democratech_fallback(self):
        """The crux: governance finds quality under the democratech phase name."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _resolve_phase_output,
        )

        ctx = {"phase_quality_baseline_output": {"per_argument_scores": {"arg_1": {}}}}
        out = _resolve_phase_output(
            ctx, "phase_quality_output", "phase_quality_baseline_output"
        )
        assert out == {"per_argument_scores": {"arg_1": {}}}

    def test_resolve_phase_output_prefers_first_non_empty(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _resolve_phase_output,
        )

        ctx = {
            "phase_quality_output": {},  # present but empty
            "phase_quality_baseline_output": {"note_finale": 8.0},
        }
        out = _resolve_phase_output(
            ctx, "phase_quality_output", "phase_quality_baseline_output"
        )
        assert out == {"note_finale": 8.0}

    def test_resolve_phase_output_empty_when_absent(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _resolve_phase_output,
        )

        assert _resolve_phase_output({}, "phase_quality_output") == {}

    def test_resolve_phase_output_ignores_non_dict(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _resolve_phase_output,
        )

        ctx = {"phase_quality_output": "not a dict"}
        assert _resolve_phase_output(ctx, "phase_quality_output") == {}


@pytest.mark.requires_api
@pytest.mark.slow
class TestDemocratechE2EGenuineFirsthand:
    """BO-2 #1472 DoD #1: the democratech workflow decides E2E firsthand with
    real LLM agents (no mock), rendering a genuine governance verdict.

    Runs the real workflow with a live LLM key on a synthetic multi-option
    proposition (privacy HARD: domain-public chess-club budget). With the
    extract phase + governance cabling fixes, governance must receive >=2
    evaluated arguments and decide firsthand (12-method formal aggregation).
    Marked requires_api+slow: skips without a key / on the fast CI gate.
    """

    @pytest.mark.asyncio
    async def test_governance_decides_firsthand_on_multi_option_proposition(self):
        from argumentation_analysis.workflows.democratech import run_deliberation

        proposition = (
            "Le club d'echecs dispose d'un budget participatif de 2000 euros. "
            "Option A : tournoi inter-villes a 2000 euros pour la visibilite et "
            "le recrutement de nouveaux membres. "
            "Option B : materiel pedagogique (echiquiers, horloges, supports) car "
            "les debutants manquent de supports. "
            "Option C : format hybride 1000 tournoi + 1000 materiel."
        )
        result = await run_deliberation(proposition, consensus_threshold=0.7)
        phases = result.get("phases", {})
        gov = phases.get("democratic_vote")
        assert gov is not None, "democratic_vote phase must run"
        assert isinstance(gov.output, dict)
        # DoD #1 crux: a genuine firsthand decision, not a degraded/empty verdict.
        assert gov.output.get("governance_decided_firsthand") is True, (
            f"governance must decide firsthand with a live LLM key on multi-option "
            f"material (got verdict={gov.output.get('governance_verdict')!r})"
        )
        # Honnête anti-théâtre: a decided verdict is NOT marked degraded.
        assert gov.output.get("degraded") is False
        assert "governance_simulation" not in result.get("capabilities_degraded", [])
