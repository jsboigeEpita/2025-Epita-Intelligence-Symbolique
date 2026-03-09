"""Tests for formal workflows: formal_debate, belief_dynamics, argument_strength."""

import pytest
from unittest.mock import AsyncMock, patch

from argumentation_analysis.workflows.formal_debate import (
    build_formal_debate_workflow,
    run_formal_debate,
)
from argumentation_analysis.workflows.belief_dynamics import (
    build_belief_dynamics_workflow,
    run_belief_dynamics,
    _needs_quality_recheck,
)
from argumentation_analysis.workflows.argument_strength import (
    build_argument_strength_workflow,
    run_argument_strength,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseStatus,
    WorkflowExecutor,
)
from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)


# =====================================================================
# Helper
# =====================================================================


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


# =====================================================================
# Formal Debate Workflow Tests
# =====================================================================


class TestBuildFormalDebateWorkflow:
    """Validate formal_debate workflow structure."""

    def test_build_creates_valid_workflow(self):
        wf = build_formal_debate_workflow()
        assert wf.name == "formal_debate"
        errors = wf.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_phase_count(self):
        wf = build_formal_debate_workflow()
        assert len(wf.phases) == 6  # 5 original + 1 optional ABA (#85)

    def test_required_capabilities(self):
        wf = build_formal_debate_workflow()
        caps = wf.get_required_capabilities()
        assert "argument_quality" in caps
        assert "aspic_plus_reasoning" in caps
        assert "dialogue_protocols" in caps
        assert "ranking_semantics" in caps
        assert "governance_simulation" in caps
        assert "aba_reasoning" in caps  # #85

    def test_execution_order(self):
        wf = build_formal_debate_workflow()
        order = wf.get_execution_order()
        flat = [phase for level in order for phase in level]
        assert flat.index("quality_baseline") < flat.index("formalization")
        assert flat.index("formalization") < flat.index("structured_dialogue")
        assert flat.index("structured_dialogue") < flat.index("strength_ranking")
        assert flat.index("strength_ranking") < flat.index("final_vote")

    def test_metadata(self):
        wf = build_formal_debate_workflow()
        assert wf.metadata["domain"] == "formal_argumentation"
        assert wf.metadata["version"] == "1.0"

    def test_optional_phases(self):
        wf = build_formal_debate_workflow()
        phases = wf.phases if isinstance(wf.phases, list) else list(wf.phases.values())
        optional_names = {p.name for p in phases if p.optional}
        assert optional_names == {"aba_formalization"}  # #85


class TestFormalDebateExecution:
    """Test formal_debate workflow execution with mock registry."""

    @pytest.mark.asyncio
    async def test_execute_full_pipeline(self):
        registry = _make_registry(
            "argument_quality",
            "aspic_plus_reasoning",
            "dialogue_protocols",
            "ranking_semantics",
            "governance_simulation",
        )
        wf = build_formal_debate_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "AI should be regulated")

        assert results["quality_baseline"].status == PhaseStatus.COMPLETED
        assert results["formalization"].status == PhaseStatus.COMPLETED
        assert results["structured_dialogue"].status == PhaseStatus.COMPLETED
        assert results["strength_ranking"].status == PhaseStatus.COMPLETED
        assert results["final_vote"].status == PhaseStatus.COMPLETED


class TestRunFormalDebate:
    """Test the run_formal_debate convenience function."""

    @pytest.mark.asyncio
    async def test_calls_run_unified_analysis(self):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value={"workflow_name": "formal_debate", "phases": {}},
        ) as mock_run:
            result = await run_formal_debate("Test proposition")
            mock_run.assert_called_once()
            assert result["workflow_name"] == "formal_debate"


# =====================================================================
# Belief Dynamics Workflow Tests
# =====================================================================


class TestBuildBeliefDynamicsWorkflow:
    """Validate belief_dynamics workflow structure."""

    def test_build_creates_valid_workflow(self):
        wf = build_belief_dynamics_workflow()
        assert wf.name == "belief_dynamics"
        errors = wf.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_phase_count(self):
        wf = build_belief_dynamics_workflow()
        assert len(wf.phases) == 5

    def test_required_capabilities(self):
        wf = build_belief_dynamics_workflow()
        caps = wf.get_required_capabilities()
        assert "adversarial_debate" in caps
        assert "belief_revision" in caps
        assert "belief_maintenance" in caps
        assert "governance_simulation" in caps

    def test_quality_recheck_is_conditional(self):
        wf = build_belief_dynamics_workflow()
        recheck = wf.get_phase("quality_recheck")
        assert recheck is not None
        assert recheck.optional is True
        assert recheck.condition is not None

    def test_execution_order(self):
        wf = build_belief_dynamics_workflow()
        order = wf.get_execution_order()
        flat = [phase for level in order for phase in level]
        assert flat.index("adversarial_test") < flat.index("belief_update")
        assert flat.index("belief_update") < flat.index("belief_tracking")
        assert flat.index("belief_tracking") < flat.index("consensus_check")

    def test_metadata(self):
        wf = build_belief_dynamics_workflow()
        assert wf.metadata["domain"] == "belief_dynamics"


class TestNeedsQualityRecheck:
    """Test _needs_quality_recheck condition function."""

    def test_low_consensus_triggers_recheck(self):
        ctx = {"phase_consensus_check_output": {"consensus": 0.4}}
        assert _needs_quality_recheck(ctx) is True

    def test_high_consensus_skips_recheck(self):
        ctx = {"phase_consensus_check_output": {"consensus": 0.9}}
        assert _needs_quality_recheck(ctx) is False

    def test_missing_output_skips(self):
        assert _needs_quality_recheck({}) is False

    def test_non_dict_output_skips(self):
        ctx = {"phase_consensus_check_output": "not a dict"}
        assert _needs_quality_recheck(ctx) is False

    def test_consensus_rate_key(self):
        ctx = {"phase_consensus_check_output": {"consensus_rate": 0.5}}
        assert _needs_quality_recheck(ctx) is True


class TestBeliefDynamicsExecution:
    """Test belief_dynamics workflow execution with mock registry."""

    @pytest.mark.asyncio
    async def test_execute_full_pipeline(self):
        registry = _make_registry(
            "adversarial_debate",
            "belief_revision",
            "belief_maintenance",
            "governance_simulation",
            "argument_quality",
        )
        wf = build_belief_dynamics_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Belief revision test")

        assert results["adversarial_test"].status == PhaseStatus.COMPLETED
        assert results["belief_update"].status == PhaseStatus.COMPLETED
        assert results["belief_tracking"].status == PhaseStatus.COMPLETED
        assert results["consensus_check"].status == PhaseStatus.COMPLETED


class TestRunBeliefDynamics:
    """Test the run_belief_dynamics convenience function."""

    @pytest.mark.asyncio
    async def test_calls_run_unified_analysis(self):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value={"workflow_name": "belief_dynamics", "phases": {}},
        ) as mock_run:
            result = await run_belief_dynamics("Test proposition")
            mock_run.assert_called_once()
            assert result["workflow_name"] == "belief_dynamics"


# =====================================================================
# Argument Strength Workflow Tests
# =====================================================================


class TestBuildArgumentStrengthWorkflow:
    """Validate argument_strength workflow structure."""

    def test_build_creates_valid_workflow(self):
        wf = build_argument_strength_workflow()
        assert wf.name == "argument_strength"
        errors = wf.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_phase_count(self):
        wf = build_argument_strength_workflow()
        assert len(wf.phases) == 5  # 4 original + 1 optional bipolar (#85)

    def test_required_capabilities(self):
        wf = build_argument_strength_workflow()
        caps = wf.get_required_capabilities()
        assert "argument_quality" in caps
        assert "ranking_semantics" in caps
        assert "counter_argument_generation" in caps
        assert "bipolar_argumentation" in caps  # #85

    def test_uncertainty_is_optional(self):
        wf = build_argument_strength_workflow()
        unc = wf.get_phase("uncertainty_analysis")
        assert unc is not None
        assert unc.optional is True

    def test_execution_order(self):
        wf = build_argument_strength_workflow()
        order = wf.get_execution_order()
        flat = [phase for level in order for phase in level]
        assert flat.index("quality_baseline") < flat.index("formal_ranking")
        assert flat.index("formal_ranking") < flat.index("vulnerability_scan")

    def test_metadata(self):
        wf = build_argument_strength_workflow()
        assert wf.metadata["domain"] == "argument_evaluation"


class TestArgumentStrengthExecution:
    """Test argument_strength workflow execution with mock registry."""

    @pytest.mark.asyncio
    async def test_execute_full_pipeline(self):
        registry = _make_registry(
            "argument_quality",
            "ranking_semantics",
            "probabilistic_argumentation",
            "counter_argument_generation",
        )
        wf = build_argument_strength_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Strong argument test")

        assert results["quality_baseline"].status == PhaseStatus.COMPLETED
        assert results["formal_ranking"].status == PhaseStatus.COMPLETED
        assert results["vulnerability_scan"].status == PhaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_missing_optional_probabilistic(self):
        registry = _make_registry(
            "argument_quality",
            "ranking_semantics",
            "counter_argument_generation",
        )
        wf = build_argument_strength_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Test without probabilistic")

        assert results["uncertainty_analysis"].status == PhaseStatus.SKIPPED
        assert results["vulnerability_scan"].status == PhaseStatus.COMPLETED


class TestRunArgumentStrength:
    """Test the run_argument_strength convenience function."""

    @pytest.mark.asyncio
    async def test_calls_run_unified_analysis(self):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value={"workflow_name": "argument_strength", "phases": {}},
        ) as mock_run:
            result = await run_argument_strength("Test argument")
            mock_run.assert_called_once()
            assert result["workflow_name"] == "argument_strength"


# =====================================================================
# State Writers Tests
# =====================================================================


class TestStateWriters:
    """Test that state writers for Track A capabilities work correctly."""

    def _make_state(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        return UnifiedAnalysisState("Test text")

    def test_write_ranking_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_ranking_to_state,
        )
        state = self._make_state()
        output = {"method": "categorizer", "arguments": ["a", "b"], "comparisons": []}
        _write_ranking_to_state(output, state, {})
        assert len(state.ranking_results) == 1
        assert state.ranking_results[0]["method"] == "categorizer"

    def test_write_aspic_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_aspic_to_state,
        )
        state = self._make_state()
        output = {"reasoner_type": "simple", "extensions": [["a"]], "statistics": {}}
        _write_aspic_to_state(output, state, {})
        assert len(state.aspic_results) == 1

    def test_write_belief_revision_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_belief_revision_to_state,
        )
        state = self._make_state()
        output = {"method": "dalal", "original": ["p"], "revised": ["!p"]}
        _write_belief_revision_to_state(output, state, {})
        assert len(state.belief_revision_results) == 1

    def test_write_dialogue_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_dialogue_to_state,
        )
        state = self._make_state()
        output = {"topic": "AI", "outcome": "accepted", "dialogue_trace": [{"round": 1}]}
        _write_dialogue_to_state(output, state, {})
        assert len(state.dialogue_results) == 1
        assert state.dialogue_results[0]["outcome"] == "accepted"

    def test_write_probabilistic_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_probabilistic_to_state,
        )
        state = self._make_state()
        output = {"arguments": ["a", "b"], "acceptance_probabilities": {"a": 0.8, "b": 0.3}}
        _write_probabilistic_to_state(output, state, {})
        assert len(state.probabilistic_results) == 1

    def test_write_bipolar_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_bipolar_to_state,
        )
        state = self._make_state()
        output = {"framework_type": "necessity", "arguments": ["a"], "supports": []}
        _write_bipolar_to_state(output, state, {})
        assert len(state.bipolar_results) == 1

    def test_state_writers_handle_none(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_ranking_to_state,
            _write_aspic_to_state,
            _write_belief_revision_to_state,
        )
        state = self._make_state()
        _write_ranking_to_state(None, state, {})
        _write_aspic_to_state(None, state, {})
        _write_belief_revision_to_state(None, state, {})
        assert len(state.ranking_results) == 0
        assert len(state.aspic_results) == 0
        assert len(state.belief_revision_results) == 0


# =====================================================================
# Catalog Registration Tests
# =====================================================================


class TestWorkflowCatalog:
    """Test that formal workflows are registered in catalog."""

    def test_formal_debate_in_catalog(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )
        catalog = get_workflow_catalog()
        assert "formal_debate" in catalog

    def test_belief_dynamics_in_catalog(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )
        catalog = get_workflow_catalog()
        assert "belief_dynamics" in catalog

    def test_argument_strength_in_catalog(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )
        catalog = get_workflow_catalog()
        assert "argument_strength" in catalog

    def test_catalog_total_count(self):
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )
        catalog = get_workflow_catalog()
        # 7 core + 3 macro (Track D) + 3 formal = 13
        assert len(catalog) >= 13
