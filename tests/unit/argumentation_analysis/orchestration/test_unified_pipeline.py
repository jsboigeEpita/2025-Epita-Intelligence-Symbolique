"""
Tests for the unified pipeline orchestration module.

Validates:
- Registry setup with all components
- Pre-built workflow definitions (light, standard, full)
- Workflow execution via WorkflowExecutor
- UnifiedAnalysisState integration
- Graceful degradation when components are missing
"""

import pytest
from unittest.mock import MagicMock, patch

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
    WorkflowExecutor,
    PhaseResult,
    PhaseStatus,
)
from argumentation_analysis.core.shared_state import (
    RhetoricalAnalysisState,
    UnifiedAnalysisState,
)

# ============================================================
# Test: UnifiedAnalysisState
# ============================================================


class TestUnifiedAnalysisState:
    """Test UnifiedAnalysisState extension of RhetoricalAnalysisState."""

    def test_inherits_from_rhetorical(self):
        """UnifiedAnalysisState is a subclass of RhetoricalAnalysisState."""
        assert issubclass(UnifiedAnalysisState, RhetoricalAnalysisState)

    def test_initialization(self):
        """All unified fields initialize to empty."""
        state = UnifiedAnalysisState("Test text")
        assert state.raw_text == "Test text"
        assert state.counter_arguments == []
        assert state.argument_quality_scores == {}
        assert state.jtms_beliefs == {}
        assert state.dung_frameworks == {}
        assert state.governance_decisions == []
        assert state.debate_transcripts == []
        assert state.transcription_segments == []
        assert state.semantic_index_refs == []
        assert state.neural_fallacy_scores == []
        assert state.workflow_results == {}

    def test_base_methods_still_work(self):
        """Base RhetoricalAnalysisState methods work on UnifiedAnalysisState."""
        state = UnifiedAnalysisState("Test text for analysis")
        task_id = state.add_task("Analyze arguments")
        assert task_id.startswith("task_")
        arg_id = state.add_argument("Premise A implies B")
        assert arg_id.startswith("arg_")
        fallacy_id = state.add_fallacy("ad_hominem", "Attacks the person")
        assert fallacy_id.startswith("fallacy_")

    def test_add_counter_argument(self):
        """Can add counter-argument results."""
        state = UnifiedAnalysisState("Test text")
        ca_id = state.add_counter_argument(
            original_arg="All birds fly",
            counter_content="Penguins are birds but cannot fly",
            strategy="analogical_counter",
            score=0.85,
        )
        assert ca_id.startswith("ca_")
        assert len(state.counter_arguments) == 1
        assert state.counter_arguments[0]["strategy"] == "analogical_counter"
        assert state.counter_arguments[0]["score"] == 0.85

    def test_add_quality_score(self):
        """Can add quality scores for arguments."""
        state = UnifiedAnalysisState("Test text")
        state.add_quality_score(
            arg_id="arg_1",
            scores={"clarity": 0.8, "relevance": 0.9},
            overall=0.85,
        )
        assert "arg_1" in state.argument_quality_scores
        assert state.argument_quality_scores["arg_1"]["overall"] == 0.85

    def test_add_jtms_belief(self):
        """Can add JTMS beliefs."""
        state = UnifiedAnalysisState("Test text")
        b_id = state.add_jtms_belief(
            name="P implies Q",
            valid=True,
            justifications=["premise_1", "rule_1"],
        )
        assert b_id.startswith("jtms_")
        assert state.jtms_beliefs[b_id]["valid"] is True

    def test_add_dung_framework(self):
        """Can add Dung argumentation frameworks."""
        state = UnifiedAnalysisState("Test text")
        df_id = state.add_dung_framework(
            name="debate_1",
            arguments=["a", "b", "c"],
            attacks=[["a", "b"], ["b", "c"]],
            extensions={"grounded": [["a", "c"]]},
        )
        assert df_id.startswith("dung_")
        assert len(state.dung_frameworks[df_id]["arguments"]) == 3

    def test_add_governance_decision(self):
        """Can add governance voting decisions."""
        state = UnifiedAnalysisState("Test text")
        gd_id = state.add_governance_decision(
            method="borda",
            winner="option_A",
            scores={"option_A": 5.0, "option_B": 3.0},
        )
        assert gd_id.startswith("gov_")
        assert state.governance_decisions[0]["method"] == "borda"

    def test_add_debate_transcript(self):
        """Can add debate transcripts."""
        state = UnifiedAnalysisState("Test text")
        dt_id = state.add_debate_transcript(
            topic="Should AI be regulated?",
            exchanges=[
                {"speaker": "advocate", "content": "AI needs oversight"},
                {"speaker": "critic", "content": "Regulation stifles innovation"},
            ],
            winner="advocate",
        )
        assert dt_id.startswith("debate_")
        assert len(state.debate_transcripts[0]["exchanges"]) == 2

    def test_set_workflow_results(self):
        """Can store workflow execution results."""
        state = UnifiedAnalysisState("Test text")
        state.set_workflow_results(
            "standard_analysis",
            {"completed": 3, "failed": 0, "skipped": 2},
        )
        assert "standard_analysis" in state.workflow_results

    def test_snapshot_summarize(self):
        """Summarized snapshot includes unified dimension counts."""
        state = UnifiedAnalysisState("Test text")
        state.add_counter_argument("arg", "counter", "socratic", 0.7)
        state.add_counter_argument("arg2", "counter2", "reductio", 0.8)
        state.add_quality_score("arg_1", {"clarity": 0.8}, 0.8)
        snapshot = state.get_state_snapshot(summarize=True)
        assert snapshot["counter_argument_count"] == 2
        assert snapshot["quality_scores_count"] == 1
        assert snapshot["jtms_belief_count"] == 0

    def test_snapshot_full(self):
        """Full snapshot includes unified dimension data."""
        state = UnifiedAnalysisState("Test text")
        state.add_jtms_belief("B1", True, ["j1"])
        snapshot = state.get_state_snapshot(summarize=False)
        assert "jtms_beliefs" in snapshot
        assert len(snapshot["jtms_beliefs"]) == 1


# ============================================================
# Test: Registry Setup
# ============================================================


class TestRegistrySetup:
    """Test setup_registry() function."""

    def test_setup_registry_creates_registry(self):
        """setup_registry returns a CapabilityRegistry."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        assert isinstance(registry, CapabilityRegistry)

    def test_setup_registry_registers_core_components(self):
        """Core components are registered."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        all_caps = registry.get_all_capabilities()
        # Counter-argument should always be available
        assert "counter_argument_generation" in all_caps

    def test_setup_registry_declares_tweety_slots(self):
        """Tweety extension slots are declared."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        slots = registry.get_all_slots()
        assert "aspic_plus_reasoning" in slots
        assert "adf_reasoning" in slots
        assert "bipolar_argumentation" in slots

    def test_setup_registry_with_optional(self):
        """Optional components are attempted when include_optional=True."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        # This should not raise even if optional deps are missing
        registry = setup_registry(include_optional=True)
        assert isinstance(registry, CapabilityRegistry)
        summary = registry.summary()
        assert summary["total_registrations"] > 0

    def test_counter_argument_capabilities(self):
        """Counter-argument agent provides expected capabilities."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        agents = registry.find_agents_for_capability("counter_argument_generation")
        assert len(agents) >= 1
        agent_reg = agents[0]
        assert "argument_parsing" in agent_reg.capabilities
        assert "vulnerability_analysis" in agent_reg.capabilities

    def test_quality_evaluator_registered(self):
        """Quality evaluator is registered."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        caps = registry.get_all_capabilities()
        assert "argument_quality" in caps

    def test_jtms_service_registered(self):
        """JTMS service is registered."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        caps = registry.get_all_capabilities()
        assert "belief_maintenance" in caps


# ============================================================
# Test: Pre-built Workflows
# ============================================================


class TestPrebuiltWorkflows:
    """Test pre-built workflow definitions."""

    def test_build_light_workflow(self):
        """Light workflow has 3 phases."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_light_workflow,
        )

        wf = build_light_workflow()
        assert wf.name == "light_analysis"
        assert len(wf.phases) == 3
        caps = wf.get_required_capabilities()
        assert "argument_quality" in caps
        assert "counter_argument_generation" in caps

    def test_build_standard_workflow(self):
        """Standard workflow has 5 phases with dependencies."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        assert wf.name == "standard_analysis"
        assert len(wf.phases) == 5
        # Counter depends on quality
        counter_phase = wf.get_phase("counter")
        assert "quality" in counter_phase.depends_on

    def test_build_full_workflow(self):
        """Full workflow traverses all major capabilities."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        assert wf.name == "full_analysis"
        assert len(wf.phases) >= 7
        caps = wf.get_required_capabilities()
        assert "argument_quality" in caps
        assert "counter_argument_generation" in caps
        assert "adversarial_debate" in caps

    def test_all_workflows_valid(self):
        """All pre-built workflows pass validation."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_light_workflow,
            build_standard_workflow,
            build_full_workflow,
        )

        for builder in [
            build_light_workflow,
            build_standard_workflow,
            build_full_workflow,
        ]:
            wf = builder()
            errors = wf.validate()
            assert errors == [], f"{wf.name} has validation errors: {errors}"

    def test_workflow_catalog(self):
        """Workflow catalog contains all 3 pre-built workflows."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )

        catalog = get_workflow_catalog()
        assert "light" in catalog
        assert "standard" in catalog
        assert "full" in catalog

    def test_execution_order_respects_dependencies(self):
        """Execution order respects phase dependencies."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        order = wf.get_execution_order()
        # Find levels
        flat_order = []
        for level in order:
            flat_order.extend(level)
        # Quality must come before counter
        assert flat_order.index("quality") < flat_order.index("counter")

    def test_optional_phases_marked(self):
        """Optional phases are properly marked."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        transcribe = wf.get_phase("transcribe")
        assert transcribe.optional is True
        quality = wf.get_phase("quality")
        assert quality.optional is False


# ============================================================
# Test: Workflow Execution
# ============================================================


class TestWorkflowExecution:
    """Test workflow execution via WorkflowExecutor."""

    def test_executor_with_registry(self):
        """WorkflowExecutor accepts a CapabilityRegistry."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        executor = WorkflowExecutor(registry)
        assert executor is not None

    @pytest.mark.asyncio
    async def test_execute_light_workflow(self):
        """Light workflow executes with registered components."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
            build_light_workflow,
        )

        registry = setup_registry(include_optional=False)
        workflow = build_light_workflow()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, input_data="Test argument text")
        assert isinstance(results, dict)
        assert "quality" in results
        assert "counter" in results
        # Quality and counter should complete (registered)
        assert results["quality"].status == PhaseStatus.COMPLETED
        assert results["counter"].status == PhaseStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_with_missing_optional(self):
        """Optional phases are skipped when provider is missing."""
        registry = CapabilityRegistry()
        # Only register quality — no counter or jtms
        registry.register_agent(
            name="quality_only",
            agent_class=type("FakeQuality", (), {}),
            capabilities=["argument_quality"],
        )
        workflow = (
            WorkflowBuilder("test_missing")
            .add_phase("quality", capability="argument_quality")
            .add_phase(
                "counter",
                capability="counter_argument_generation",
                optional=True,
            )
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, input_data="Test")
        assert results["quality"].status == PhaseStatus.COMPLETED
        assert results["counter"].status == PhaseStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_execute_required_missing_fails(self):
        """Required phases fail when no provider is available."""
        registry = CapabilityRegistry()
        workflow = (
            WorkflowBuilder("test_fail")
            .add_phase("quality", capability="nonexistent_capability")
            .build()
        )
        executor = WorkflowExecutor(registry)
        results = await executor.execute(workflow, input_data="Test")
        assert results["quality"].status == PhaseStatus.FAILED


# ============================================================
# Test: run_unified_analysis
# ============================================================


class TestRunUnifiedAnalysis:
    """Test the convenience function run_unified_analysis."""

    @pytest.mark.asyncio
    async def test_run_with_default_registry(self):
        """run_unified_analysis works with auto-created registry."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis("Test argument text", workflow_name="light")
        assert "workflow_name" in result
        assert "phases" in result
        assert "summary" in result
        assert result["workflow_name"] == "light_analysis"

    @pytest.mark.asyncio
    async def test_run_with_custom_registry(self):
        """run_unified_analysis accepts a custom registry."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        registry = CapabilityRegistry()
        registry.register_agent(
            name="fake_quality",
            agent_class=type("FQ", (), {}),
            capabilities=["argument_quality"],
        )
        custom_wf = (
            WorkflowBuilder("custom")
            .add_phase("q", capability="argument_quality")
            .build()
        )
        result = await run_unified_analysis(
            "Test", registry=registry, custom_workflow=custom_wf
        )
        assert result["summary"]["completed"] == 1

    @pytest.mark.asyncio
    async def test_run_unknown_workflow_raises(self):
        """run_unified_analysis raises ValueError for unknown workflow."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        with pytest.raises(ValueError, match="Unknown workflow"):
            await run_unified_analysis("Test", workflow_name="nonexistent")

    @pytest.mark.asyncio
    async def test_run_summary_structure(self):
        """Result summary has correct structure."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis("Test argument", workflow_name="light")
        summary = result["summary"]
        assert "completed" in summary
        assert "failed" in summary
        assert "skipped" in summary
        assert "total" in summary
        assert (
            summary["total"]
            == summary["completed"] + summary["failed"] + summary["skipped"]
        )

    @pytest.mark.asyncio
    async def test_capabilities_used_and_missing(self):
        """Result reports capabilities_used and capabilities_missing."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis("Test argument", workflow_name="light")
        assert "capabilities_used" in result
        assert "capabilities_missing" in result
        assert isinstance(result["capabilities_used"], list)
        assert isinstance(result["capabilities_missing"], list)
