"""Tests for the formal verification workflow (#71).

Covers:
- Workflow structure validation (10 phases, capabilities, dependencies, metadata)
- Condition function (_has_inconsistency)
- State writer functions for 6 new capabilities
- Execution with mock registry
- Convenience wrapper
- State field additions
- Catalog registration
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from argumentation_analysis.workflows.formal_verification import (
    build_formal_verification_workflow,
    run_formal_verification,
    _has_inconsistency,
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
# Workflow Structure Tests
# =====================================================================


class TestBuildFormalVerificationWorkflow:
    """Validate formal_verification workflow structure."""

    def test_build_creates_valid_workflow(self):
        wf = build_formal_verification_workflow()
        assert wf.name == "formal_verification"
        errors = wf.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_phase_count(self):
        wf = build_formal_verification_workflow()
        assert len(wf.phases) == 17  # 10 original + 7 new optional (#85/#86/#87/#89/#90)

    def test_required_capabilities(self):
        wf = build_formal_verification_workflow()
        caps = wf.get_required_capabilities()
        expected = {
            "fact_extraction",
            "propositional_logic",
            "fol_reasoning",
            "modal_logic",
            "dung_extensions",
            "aspic_plus_reasoning",
            "ranking_semantics",
            "belief_maintenance",
            "belief_revision",
            "formal_synthesis",
            # New optional capabilities (#85/#86/#87/#89/#90)
            "adf_reasoning",
            "bipolar_argumentation",
            "setaf_reasoning",
            "description_logic",
            "conditional_logic",
            "defeasible_logic",
            "qbf_reasoning",
        }
        assert expected == set(caps)

    def test_execution_order_extraction_first(self):
        wf = build_formal_verification_workflow()
        order = wf.get_execution_order()
        flat = [phase for level in order for phase in level]
        assert flat[0] == "extraction"

    def test_pl_and_fol_after_extraction(self):
        wf = build_formal_verification_workflow()
        order = wf.get_execution_order()
        flat = [phase for level in order for phase in level]
        assert flat.index("extraction") < flat.index("pl_analysis")
        assert flat.index("extraction") < flat.index("fol_analysis")

    def test_synthesis_is_last(self):
        wf = build_formal_verification_workflow()
        order = wf.get_execution_order()
        flat = [phase for level in order for phase in level]
        assert flat[-1] == "formal_synthesis"

    def test_modal_is_optional(self):
        wf = build_formal_verification_workflow()
        phases = wf.phases if isinstance(wf.phases, list) else list(wf.phases.values())
        modal_phase = [p for p in phases if p.name == "modal_analysis"][0]
        assert modal_phase.optional is True

    def test_belief_revision_is_conditional(self):
        wf = build_formal_verification_workflow()
        phases = wf.phases if isinstance(wf.phases, list) else list(wf.phases.values())
        br_phase = [p for p in phases if p.name == "belief_revision"][0]
        assert br_phase.condition is not None

    def test_metadata(self):
        wf = build_formal_verification_workflow()
        assert wf.metadata["domain"] == "formal_verification"
        assert wf.metadata["version"] == "1.0"
        assert wf.metadata["issue"] == "#71"

    def test_dung_depends_on_pl(self):
        wf = build_formal_verification_workflow()
        phases = wf.phases if isinstance(wf.phases, list) else list(wf.phases.values())
        dung_phase = [p for p in phases if p.name == "dung_analysis"][0]
        assert "pl_analysis" in dung_phase.depends_on

    def test_aspic_and_ranking_depend_on_dung(self):
        wf = build_formal_verification_workflow()
        phases = wf.phases if isinstance(wf.phases, list) else list(wf.phases.values())
        aspic_phase = [p for p in phases if p.name == "aspic_analysis"][0]
        ranking_phase = [p for p in phases if p.name == "ranking"][0]
        assert "dung_analysis" in aspic_phase.depends_on
        assert "dung_analysis" in ranking_phase.depends_on


# =====================================================================
# Condition Function Tests
# =====================================================================


class TestHasInconsistency:
    """Test the _has_inconsistency condition function."""

    def test_no_data_returns_false(self):
        assert _has_inconsistency({}) is False

    def test_consistent_fol_returns_false(self):
        ctx = {"phase_fol_analysis_output": {"consistent": True}}
        assert _has_inconsistency(ctx) is False

    def test_inconsistent_fol_returns_true(self):
        ctx = {"phase_fol_analysis_output": {"consistent": False}}
        assert _has_inconsistency(ctx) is True

    def test_satisfiable_pl_returns_false(self):
        ctx = {"phase_pl_analysis_output": {"satisfiable": True}}
        assert _has_inconsistency(ctx) is False

    def test_unsatisfiable_pl_returns_true(self):
        ctx = {"phase_pl_analysis_output": {"satisfiable": False}}
        assert _has_inconsistency(ctx) is True

    def test_jtms_retracted_beliefs_returns_true(self):
        ctx = {"phase_jtms_tracking_output": {"beliefs": {"b1": "True", "b2": "False"}}}
        assert _has_inconsistency(ctx) is True

    def test_jtms_all_valid_returns_false(self):
        ctx = {"phase_jtms_tracking_output": {"beliefs": {"b1": "True", "b2": "True"}}}
        assert _has_inconsistency(ctx) is False

    def test_non_dict_output_ignored(self):
        ctx = {"phase_fol_analysis_output": "not a dict"}
        assert _has_inconsistency(ctx) is False


# =====================================================================
# Execution Tests
# =====================================================================


class TestFormalVerificationExecution:
    """Test formal_verification execution with mock registry."""

    @pytest.mark.asyncio
    async def test_execute_full_pipeline(self):
        wf = build_formal_verification_workflow()
        caps = wf.get_required_capabilities()
        registry = _make_registry(*caps)
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Test argument for verification.")
        assert results is not None
        completed = [name for name, r in results.items() if r.status == PhaseStatus.COMPLETED]
        # At least extraction + synthesis should complete
        assert len(completed) >= 2

    @pytest.mark.asyncio
    async def test_execute_without_optional_modal(self):
        wf = build_formal_verification_workflow()
        caps = wf.get_required_capabilities()
        # Exclude modal_logic (optional)
        caps_without_modal = [c for c in caps if c != "modal_logic"]
        registry = _make_registry(*caps_without_modal)
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "Test text.")
        completed_names = [name for name, r in results.items() if r.status == PhaseStatus.COMPLETED]
        skipped_names = [name for name, r in results.items() if r.status == PhaseStatus.SKIPPED]
        assert "modal_analysis" in skipped_names
        assert "extraction" in completed_names


# =====================================================================
# Convenience Wrapper Tests
# =====================================================================


class TestRunFormalVerification:
    """Test the run_formal_verification convenience wrapper."""

    @pytest.mark.asyncio
    async def test_delegates_to_run_unified_analysis(self):
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value={"status": "ok"},
        ) as mock_run:
            # Re-import to pick up the patch (lazy import in function body)
            from argumentation_analysis.workflows.formal_verification import run_formal_verification as rfv
            result = await rfv("Test text")
            mock_run.assert_called_once()
            assert mock_run.call_args[1]["workflow_name"] == "formal_verification"
            assert result == {"status": "ok"}


# =====================================================================
# Invoke Callable Tests
# =====================================================================


class TestInvokeCallables:
    """Test the 6 new invoke callables for logic agent capabilities."""

    @pytest.mark.asyncio
    async def test_invoke_fact_extraction(self):
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_fact_extraction
        result = await _invoke_fact_extraction(
            "This is a long claim about logic. Another important assertion here. A third point.",
            {},
        )
        assert "claims" in result
        assert "claim_count" in result
        assert result["claim_count"] >= 1

    @pytest.mark.asyncio
    async def test_invoke_fact_extraction_short_text(self):
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_fact_extraction
        result = await _invoke_fact_extraction("Hi.", {})
        assert result["claim_count"] == 0  # Too short

    @pytest.mark.asyncio
    async def test_invoke_propositional_logic_error_fallback(self):
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_propositional_logic
        # Without JVM, should return error dict
        result = await _invoke_propositional_logic("a && b", {})
        assert "logic_type" in result
        assert result["logic_type"] == "propositional"

    @pytest.mark.asyncio
    async def test_invoke_fol_reasoning_error_fallback(self):
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_fol_reasoning
        result = await _invoke_fol_reasoning("forall x: P(x)", {})
        assert result["logic_type"] == "first_order"

    @pytest.mark.asyncio
    async def test_invoke_modal_logic_error_fallback(self):
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_modal_logic
        result = await _invoke_modal_logic("[]p => p", {})
        # Should either succeed or return error dict
        assert "logic_type" in result or "formulas" in result

    @pytest.mark.asyncio
    async def test_invoke_dung_extensions_error_fallback(self):
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_dung_extensions
        result = await _invoke_dung_extensions("test", {"arguments": ["a", "b"]})
        assert "semantics" in result or "error" in result

    @pytest.mark.asyncio
    async def test_invoke_formal_synthesis_aggregates(self):
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_formal_synthesis
        ctx = {
            "phase_fol_analysis_output": {"consistent": True},
            "phase_pl_analysis_output": {"satisfiable": False},
            "phase_dung_analysis_output": {"extensions": {"preferred": [["a"]]}},
        }
        result = await _invoke_formal_synthesis("test", ctx)
        assert "summary" in result
        assert "overall_validity" in result
        assert "phase_count" in result
        assert result["phase_count"] == 3

    @pytest.mark.asyncio
    async def test_invoke_formal_synthesis_empty_context(self):
        from argumentation_analysis.orchestration.unified_pipeline import _invoke_formal_synthesis
        result = await _invoke_formal_synthesis("test", {})
        assert result["overall_validity"] == 0.5
        assert result["phase_count"] == 0


# =====================================================================
# State Writer Tests
# =====================================================================


class TestStateWriters:
    """Test the 6 new state writers for logic capabilities."""

    def _make_state(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        return UnifiedAnalysisState("test text")

    def test_write_fact_extraction_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import _write_fact_extraction_to_state
        state = self._make_state()
        output = {"claims": ["Claim one here", "Claim two here"]}
        _write_fact_extraction_to_state(output, state, {})
        assert len(state.extracts) == 2

    def test_write_fact_extraction_none(self):
        from argumentation_analysis.orchestration.unified_pipeline import _write_fact_extraction_to_state
        state = self._make_state()
        _write_fact_extraction_to_state(None, state, {})
        assert len(state.extracts) == 0

    def test_write_propositional_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import _write_propositional_to_state
        state = self._make_state()
        output = {"formulas": ["a && b"], "satisfiable": True, "model": {"a": True}}
        _write_propositional_to_state(output, state, {})
        assert len(state.propositional_analysis_results) == 1
        assert state.propositional_analysis_results[0]["satisfiable"] is True

    def test_write_fol_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import _write_fol_to_state
        state = self._make_state()
        output = {"formulas": ["forall x: P(x)"], "consistent": True, "inferences": ["P(a)"], "confidence": 0.9}
        _write_fol_to_state(output, state, {})
        assert len(state.fol_analysis_results) == 1
        assert state.fol_analysis_results[0]["consistent"] is True
        assert state.fol_analysis_results[0]["confidence"] == 0.9

    def test_write_modal_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import _write_modal_to_state
        state = self._make_state()
        output = {"formulas": ["[]p"], "valid": True, "modalities": ["necessity"]}
        _write_modal_to_state(output, state, {})
        assert len(state.modal_analysis_results) == 1
        assert state.modal_analysis_results[0]["valid"] is True

    def test_write_dung_extensions_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import _write_dung_extensions_to_state
        state = self._make_state()
        output = {
            "semantics": "preferred",
            "extensions": {"preferred": [["a", "c"]]},
            "statistics": {"arguments_count": 3, "attacks_count": 2},
        }
        _write_dung_extensions_to_state(output, state, {})
        assert len(state.dung_frameworks) == 1
        fw = list(state.dung_frameworks.values())[0]
        assert fw["name"] == "verification_preferred"

    def test_write_formal_synthesis_to_state(self):
        from argumentation_analysis.orchestration.unified_pipeline import _write_formal_synthesis_to_state
        state = self._make_state()
        output = {
            "summary": "All consistent",
            "phase_results": {"fol": {"consistent": True}},
            "overall_validity": 0.85,
        }
        _write_formal_synthesis_to_state(output, state, {})
        assert len(state.formal_synthesis_reports) == 1
        assert state.formal_synthesis_reports[0]["overall_validity"] == 0.85

    def test_write_formal_synthesis_none(self):
        from argumentation_analysis.orchestration.unified_pipeline import _write_formal_synthesis_to_state
        state = self._make_state()
        _write_formal_synthesis_to_state(None, state, {})
        assert len(state.formal_synthesis_reports) == 0


# =====================================================================
# State Field Tests
# =====================================================================


class TestUnifiedAnalysisStateNewFields:
    """Test the 4 new state fields added for #71."""

    def test_fol_analysis_field_exists(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        state = UnifiedAnalysisState("test")
        assert hasattr(state, "fol_analysis_results")
        assert state.fol_analysis_results == []

    def test_propositional_analysis_field_exists(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        state = UnifiedAnalysisState("test")
        assert hasattr(state, "propositional_analysis_results")
        assert state.propositional_analysis_results == []

    def test_modal_analysis_field_exists(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        state = UnifiedAnalysisState("test")
        assert hasattr(state, "modal_analysis_results")
        assert state.modal_analysis_results == []

    def test_formal_synthesis_field_exists(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        state = UnifiedAnalysisState("test")
        assert hasattr(state, "formal_synthesis_reports")
        assert state.formal_synthesis_reports == []

    def test_add_fol_analysis_result(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        state = UnifiedAnalysisState("test")
        fol_id = state.add_fol_analysis_result(
            formulas=["forall x: P(x)"], consistent=True, inferences=["P(a)"], confidence=0.9
        )
        assert fol_id.startswith("fol_")
        assert len(state.fol_analysis_results) == 1

    def test_add_propositional_analysis_result(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        state = UnifiedAnalysisState("test")
        pl_id = state.add_propositional_analysis_result(
            formulas=["a && b"], satisfiable=True, model={"a": True, "b": True}
        )
        assert pl_id.startswith("pl_")
        assert len(state.propositional_analysis_results) == 1

    def test_add_modal_analysis_result(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        state = UnifiedAnalysisState("test")
        ml_id = state.add_modal_analysis_result(
            formulas=["[]p"], valid=True, modalities=["necessity"]
        )
        assert ml_id.startswith("modal_")
        assert len(state.modal_analysis_results) == 1

    def test_add_formal_synthesis_report(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        state = UnifiedAnalysisState("test")
        fs_id = state.add_formal_synthesis_report(
            summary="All consistent", phase_results={"fol": {}}, overall_validity=0.9
        )
        assert fs_id.startswith("fsyn_")
        assert len(state.formal_synthesis_reports) == 1

    def test_snapshot_summarize_includes_new_fields(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        state = UnifiedAnalysisState("test")
        state.add_fol_analysis_result(["f"], True, [], 0.8)
        state.add_propositional_analysis_result(["a"], True)
        snapshot = state.get_state_snapshot(summarize=True)
        assert snapshot["fol_analysis_count"] == 1
        assert snapshot["propositional_analysis_count"] == 1
        assert snapshot["modal_analysis_count"] == 0
        assert snapshot["formal_synthesis_count"] == 0

    def test_snapshot_full_includes_new_fields(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        state = UnifiedAnalysisState("test")
        state.add_modal_analysis_result(["[]p"], True, ["necessity"])
        snapshot = state.get_state_snapshot(summarize=False)
        assert "modal_analysis_results" in snapshot
        assert len(snapshot["modal_analysis_results"]) == 1


# =====================================================================
# Catalog Registration Tests
# =====================================================================


class TestCatalogRegistration:
    """Test that formal_verification workflow is in the catalog."""

    def test_formal_verification_in_catalog(self):
        from argumentation_analysis.orchestration.unified_pipeline import get_workflow_catalog
        catalog = get_workflow_catalog()
        assert "formal_verification" in catalog

    def test_catalog_total_count(self):
        from argumentation_analysis.orchestration.unified_pipeline import get_workflow_catalog
        catalog = get_workflow_catalog()
        # 7 built-in + 3 macro + 3 formal + 1 formal_verification = 14
        assert len(catalog) >= 14

    def test_formal_verification_phase_count_in_catalog(self):
        from argumentation_analysis.orchestration.unified_pipeline import get_workflow_catalog
        catalog = get_workflow_catalog()
        wf = catalog["formal_verification"]
        assert len(wf.phases) == 17  # 10 original + 7 new optional (#85/#86/#87/#89/#90)


# =====================================================================
# Registry Capability Tests
# =====================================================================


class TestLogicCapabilityRegistration:
    """Test that setup_registry() registers the 6 logic capabilities."""

    def test_logic_capabilities_registered(self):
        from argumentation_analysis.orchestration.unified_pipeline import setup_registry
        registry = setup_registry()
        all_caps = registry.get_all_capabilities()
        for cap in [
            "fact_extraction",
            "propositional_logic",
            "fol_reasoning",
            "modal_logic",
            "dung_extensions",
            "formal_synthesis",
            "sat_solving",  # #86
        ]:
            assert cap in all_caps, f"{cap} not registered"

    def test_logic_services_have_invoke(self):
        from argumentation_analysis.orchestration.unified_pipeline import setup_registry
        registry = setup_registry()
        for name in [
            "fact_extraction_service",
            "propositional_logic_service",
            "fol_reasoning_service",
            "modal_logic_service",
            "dung_extensions_service",
            "formal_synthesis_service",
            "sat_handler",  # #86
        ]:
            reg = registry._registrations.get(name)
            assert reg is not None, f"{name} not found in registrations"
            assert reg.invoke is not None, f"{name} has no invoke callable"
