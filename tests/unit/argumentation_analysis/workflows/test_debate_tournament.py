"""Tests for the Debate Tournament workflow."""

import pytest
from unittest.mock import AsyncMock, patch

from argumentation_analysis.workflows.debate_tournament import (
    build_debate_tournament_workflow,
    run_tournament,
    _debate_score_converged,
    DEFAULT_MAX_ROUNDS,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    LoopConfig,
    PhaseStatus,
    WorkflowExecutor,
)
from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)


# --- Build tests ---


class TestBuildDebateTournamentWorkflow:
    """Validate workflow structure."""

    def test_build_creates_valid_workflow(self):
        wf = build_debate_tournament_workflow()
        assert wf.name == "debate_tournament"
        errors = wf.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_phase_count(self):
        wf = build_debate_tournament_workflow()
        assert len(wf.phases) == 6

    def test_required_capabilities(self):
        wf = build_debate_tournament_workflow()
        caps = wf.get_required_capabilities()
        assert "argument_quality" in caps
        assert "counter_argument_generation" in caps
        assert "adversarial_debate" in caps
        assert "governance_simulation" in caps

    def test_debate_rounds_has_loop_config(self):
        wf = build_debate_tournament_workflow()
        debate = wf.get_phase("debate_rounds")
        assert debate is not None
        assert debate.loop_config is not None
        assert debate.loop_config.max_iterations == DEFAULT_MAX_ROUNDS
        assert debate.loop_config.convergence_fn is not None

    def test_custom_max_rounds(self):
        wf = build_debate_tournament_workflow(max_rounds=5)
        debate = wf.get_phase("debate_rounds")
        assert debate.loop_config.max_iterations == 5

    def test_belief_record_is_optional(self):
        wf = build_debate_tournament_workflow()
        belief = wf.get_phase("belief_record")
        assert belief is not None
        assert belief.optional is True

    def test_execution_order(self):
        wf = build_debate_tournament_workflow()
        order = wf.get_execution_order()
        flat = [phase for level in order for phase in level]
        assert flat.index("quality_prep") < flat.index("vulnerability_scan")
        assert flat.index("vulnerability_scan") < flat.index("debate_rounds")
        assert flat.index("debate_rounds") < flat.index("final_scoring")
        assert flat.index("final_scoring") < flat.index("jury_vote")

    def test_metadata(self):
        wf = build_debate_tournament_workflow()
        assert wf.metadata["domain"] == "adversarial_debate"


# --- Convergence function tests ---


class TestDebateScoreConverged:
    """Test _debate_score_converged function."""

    def test_stable_scores_converge(self):
        prev = {"logical_coherence": 0.8, "evidence_quality": 0.7,
                "relevance_score": 0.75, "persuasiveness": 0.8}
        curr = {"logical_coherence": 0.81, "evidence_quality": 0.71,
                "relevance_score": 0.76, "persuasiveness": 0.8}
        assert _debate_score_converged(prev, curr) is True

    def test_changing_scores_not_converged(self):
        prev = {"logical_coherence": 0.5, "evidence_quality": 0.4,
                "relevance_score": 0.3, "persuasiveness": 0.4}
        curr = {"logical_coherence": 0.8, "evidence_quality": 0.7,
                "relevance_score": 0.75, "persuasiveness": 0.8}
        assert _debate_score_converged(prev, curr) is False

    def test_non_dict_inputs(self):
        assert _debate_score_converged("not dict", {"score": 0.5}) is False
        assert _debate_score_converged({"score": 0.5}, None) is False

    def test_generic_score_key(self):
        prev = {"debate_score": 0.7}
        curr = {"debate_score": 0.72}
        assert _debate_score_converged(prev, curr) is True

    def test_large_change_not_converged(self):
        prev = {"debate_score": 0.3}
        curr = {"debate_score": 0.8}
        assert _debate_score_converged(prev, curr) is False


# --- Execution tests ---


def _make_registry(*capabilities):
    """Create a registry with fake invoke callables."""
    registry = CapabilityRegistry()
    for cap in capabilities:
        invoke_fn = AsyncMock(return_value={"capability": cap, "score": 0.75})
        registry.register(
            name=f"mock_{cap}",
            component_type=ComponentType.AGENT,
            capabilities=[cap],
            invoke=invoke_fn,
        )
    return registry


class TestDebateTournamentExecution:
    """Test workflow execution with mock registry."""

    @pytest.mark.asyncio
    async def test_execute_full_tournament(self):
        registry = _make_registry(
            "argument_quality",
            "counter_argument_generation",
            "adversarial_debate",
            "governance_simulation",
            "belief_maintenance",
        )
        wf = build_debate_tournament_workflow(max_rounds=2)
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Should AI be regulated?")

        assert results["quality_prep"].status == PhaseStatus.COMPLETED
        assert results["vulnerability_scan"].status == PhaseStatus.COMPLETED
        assert results["debate_rounds"].status == PhaseStatus.COMPLETED
        assert results["final_scoring"].status == PhaseStatus.COMPLETED
        assert results["jury_vote"].status == PhaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_missing_optional_belief(self):
        registry = _make_registry(
            "argument_quality",
            "counter_argument_generation",
            "adversarial_debate",
            "governance_simulation",
        )
        wf = build_debate_tournament_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Test topic")

        assert results["belief_record"].status == PhaseStatus.SKIPPED
        assert results["jury_vote"].status == PhaseStatus.COMPLETED


# --- Convenience wrapper tests ---


class TestRunTournament:
    """Test the run_tournament convenience function."""

    @pytest.mark.asyncio
    async def test_calls_run_unified_analysis(self):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value={"workflow_name": "debate_tournament", "phases": {}},
        ) as mock_run:
            result = await run_tournament("AI regulation debate")
            mock_run.assert_called_once()
            assert result["workflow_name"] == "debate_tournament"

    @pytest.mark.asyncio
    async def test_passes_max_rounds(self):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value={"workflow_name": "debate_tournament", "phases": {}},
        ) as mock_run:
            await run_tournament("Test", max_rounds=5)
            call_kwargs = mock_run.call_args[1]
            wf = call_kwargs["custom_workflow"]
            debate = wf.get_phase("debate_rounds")
            assert debate.loop_config.max_iterations == 5
