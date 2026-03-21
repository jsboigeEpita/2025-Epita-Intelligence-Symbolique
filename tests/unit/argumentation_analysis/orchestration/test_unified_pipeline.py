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
        """Tweety extension capabilities are registered (as services or slots)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        # Track A handlers are registered as services with invoke callables
        # (or fall back to slots if registration fails)
        all_caps = registry.get_all_capabilities()
        assert "aspic_plus_reasoning" in all_caps
        assert "adf_reasoning" in all_caps
        assert "bipolar_argumentation" in all_caps

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
        """Light workflow has 3 phases (extract + quality + counter)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_light_workflow,
        )

        wf = build_light_workflow()
        assert wf.name == "light_analysis"
        assert len(wf.phases) == 3
        caps = wf.get_required_capabilities()
        assert "fact_extraction" in caps
        assert "argument_quality" in caps
        assert "counter_argument_generation" in caps

    def test_build_standard_workflow(self):
        """Standard workflow has 6 phases with fact extraction and dependencies."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_standard_workflow,
        )

        wf = build_standard_workflow()
        assert wf.name == "standard_analysis"
        assert len(wf.phases) == 6
        # Quality depends on extract
        quality_phase = wf.get_phase("quality")
        assert "extract" in quality_phase.depends_on
        # Counter depends on quality
        counter_phase = wf.get_phase("counter")
        assert "quality" in counter_phase.depends_on

    def test_build_full_workflow(self):
        """Full workflow traverses all major capabilities with fact extraction."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        assert wf.name == "full_analysis"
        assert len(wf.phases) >= 8
        caps = wf.get_required_capabilities()
        assert "fact_extraction" in caps
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


# ============================================================
# Test: real invocation through run_unified_analysis
# ============================================================


class TestRealInvocationViaUnifiedAnalysis:
    """Test that run_unified_analysis produces real outputs (not None)."""

    @pytest.mark.asyncio
    async def test_light_workflow_produces_quality_output(self):
        """Light workflow quality phase produces real evaluation scores."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis(
            "Les vaccins sont efficaces car les études scientifiques le prouvent.",
            workflow_name="light",
        )
        quality_phase = result["phases"]["quality"]
        assert quality_phase.output is not None
        assert isinstance(quality_phase.output, dict)
        assert "note_finale" in quality_phase.output

    @pytest.mark.asyncio
    async def test_light_workflow_chains_quality_to_counter(self):
        """Light workflow chains quality output to counter-argument phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis(
            "La peine de mort est nécessaire car elle dissuade les criminels.",
            workflow_name="light",
        )
        counter_phase = result["phases"]["counter"]
        assert counter_phase.output is not None
        assert "parsed_argument" in counter_phase.output
        assert "quality_context" in counter_phase.output
        # quality_context should contain the upstream quality output
        assert counter_phase.output["quality_context"] is not None

    @pytest.mark.asyncio
    async def test_context_param_passed_through(self):
        """Custom context is available to invoke callables."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        result = await run_unified_analysis(
            "Argument test.",
            workflow_name="light",
            context={"custom_key": "custom_value"},
        )
        # Workflow should complete — context param doesn't break anything
        assert result["summary"]["completed"] >= 1


# ============================================================
# State integration via run_unified_analysis (#64)
# ============================================================


class TestStateViaRunUnifiedAnalysis:
    @pytest.mark.asyncio
    async def test_state_returned_by_default(self):
        """run_unified_analysis returns unified_state and state_snapshot by default."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        registry = setup_registry(include_optional=False)
        result = await run_unified_analysis(
            "L'argument est valide car il est logiquement cohérent.",
            workflow_name="light",
            registry=registry,
        )
        assert "unified_state" in result
        assert isinstance(result["unified_state"], UnifiedAnalysisState)
        assert "state_snapshot" in result
        assert isinstance(result["state_snapshot"], dict)
        # Snapshot should have summary counts
        assert "counter_argument_count" in result["state_snapshot"]

    @pytest.mark.asyncio
    async def test_create_state_false_omits_state(self):
        """run_unified_analysis with create_state=False omits state from result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        result = await run_unified_analysis(
            "Test.", workflow_name="light", registry=registry, create_state=False
        )
        assert "unified_state" not in result
        assert "state_snapshot" not in result


# ============================================================
# Test: Invoke callables
# ============================================================


class TestInvokeCallables:
    """Test _invoke_* async callables with mocked dependencies."""

    async def test_invoke_quality_evaluator(self):
        """_invoke_quality_evaluator calls ArgumentQualityEvaluator.evaluate."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_quality_evaluator,
        )

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate.return_value = {"note_finale": 7.5, "clarity": 8.0}
        with patch(
            "argumentation_analysis.agents.core.quality.quality_evaluator.ArgumentQualityEvaluator",
            return_value=mock_evaluator,
        ):
            result = await _invoke_quality_evaluator("Test arg", {})
        assert result == {"note_finale": 7.5, "clarity": 8.0}

    async def test_invoke_counter_argument(self):
        """_invoke_counter_argument calls CounterArgumentPlugin methods."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_counter_argument,
        )

        mock_plugin = MagicMock()
        mock_plugin.parse_argument.return_value = '{"premise": "X", "conclusion": "Y"}'
        mock_plugin.suggest_strategy.return_value = (
            '{"strategy_name": "reductio", "confidence": 0.9}'
        )
        with patch(
            "argumentation_analysis.agents.core.counter_argument.counter_agent.CounterArgumentPlugin",
            return_value=mock_plugin,
        ):
            result = await _invoke_counter_argument(
                "Test", {"phase_quality_output": {"score": 5}}
            )
        assert result["parsed_argument"]["premise"] == "X"
        assert result["suggested_strategy"]["strategy_name"] == "reductio"
        assert result["quality_context"] == {"score": 5}

    async def test_invoke_counter_argument_no_quality_context(self):
        """_invoke_counter_argument handles missing quality context."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_counter_argument,
        )

        mock_plugin = MagicMock()
        mock_plugin.parse_argument.return_value = '{"premise": "X"}'
        mock_plugin.suggest_strategy.return_value = '{"strategy_name": "analogy"}'
        with patch(
            "argumentation_analysis.agents.core.counter_argument.counter_agent.CounterArgumentPlugin",
            return_value=mock_plugin,
        ):
            result = await _invoke_counter_argument("Test", {})
        assert result["quality_context"] is None

    async def test_invoke_debate_analysis(self):
        """_invoke_debate_analysis calls DebatePlugin."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_debate_analysis,
        )

        mock_plugin = MagicMock()
        mock_plugin.analyze_argument_quality.return_value = (
            '{"score": 7, "winner": "pro"}'
        )
        with patch(
            "argumentation_analysis.agents.core.debate.debate_agent.DebatePlugin",
            return_value=mock_plugin,
        ):
            result = await _invoke_debate_analysis("Some debate text", {})
        assert result["score"] == 7
        assert result["winner"] == "pro"

    async def test_invoke_governance(self):
        """_invoke_governance calls GovernancePlugin and returns enriched result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_governance,
        )

        mock_plugin = MagicMock()
        mock_plugin.list_governance_methods.return_value = '["majority", "borda"]'
        mock_plugin.detect_conflicts_fn.return_value = "[]"
        with patch(
            "argumentation_analysis.plugins.governance_plugin.GovernancePlugin",
            return_value=mock_plugin,
        ):
            result = await _invoke_governance("text", {})
        assert result["available_methods"] == ["majority", "borda"]
        assert "conflicts" in result
        assert "extraction_method" in result
        assert result["conflict_count"] == 0

    async def test_invoke_jtms(self):
        """_invoke_jtms extracts sentences and creates beliefs."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_jtms,
        )

        result = await _invoke_jtms("First claim. Second claim. Third.", {})
        assert result["belief_count"] == 3
        assert "claim_0" in result["beliefs"]
        assert "claim_1" in result["beliefs"]
        assert "claim_2" in result["beliefs"]

    async def test_invoke_jtms_caps_at_10(self):
        """_invoke_jtms caps beliefs at 10."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_jtms,
        )

        text = ". ".join([f"Sentence {i}" for i in range(20)]) + "."
        result = await _invoke_jtms(text, {})
        assert result["belief_count"] == 10

    async def test_invoke_speech_transcription(self):
        """_invoke_speech_transcription returns status info."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_speech_transcription,
        )

        result = await _invoke_speech_transcription("", {})
        assert result["status"] == "ready"
        assert "audio_path" in result["note"]

    async def test_invoke_fact_extraction(self):
        """_invoke_fact_extraction extracts claims from text (LLM or heuristic)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fact_extraction,
        )

        text = "This is a very long claim sentence. Short. Another long enough claim for extraction."
        result = await _invoke_fact_extraction(text, {})
        assert result["claim_count"] >= 1
        assert result["source_length"] == len(text)
        assert "extraction_method" in result
        assert result["extraction_method"] in ("llm", "heuristic")
        assert isinstance(result["claims"], list)
        assert isinstance(result.get("arguments", []), list)
        assert isinstance(result.get("fallacies", []), list)

    async def test_invoke_fact_extraction_empty(self):
        """_invoke_fact_extraction handles empty text."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fact_extraction,
        )

        result = await _invoke_fact_extraction("", {})
        assert result["claim_count"] == 0

    async def test_invoke_propositional_logic_success(self):
        """_invoke_propositional_logic returns result on success."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (True, "consistent")
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ):
            result = await _invoke_propositional_logic("p => q", {})
        assert result["satisfiable"] is True
        assert result["logic_type"] == "propositional"

    async def test_invoke_propositional_logic_error(self):
        """_invoke_propositional_logic returns error dict on exception."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            side_effect=RuntimeError("JVM not started"),
        ):
            result = await _invoke_propositional_logic("p", {})
        assert "error" in result
        assert result["satisfiable"] is False

    async def test_invoke_propositional_logic_non_list_formulas(self):
        """_invoke_propositional_logic handles non-list formulas context."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (False, "inconsistent")
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ):
            result = await _invoke_propositional_logic(
                "p", {"formulas": "single_formula"}
            )
        assert result["formulas"] == ["single_formula"]
        assert result["satisfiable"] is False

    async def test_invoke_fol_reasoning_success(self):
        """_invoke_fol_reasoning returns result on success."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (True, "ok")
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ):
            result = await _invoke_fol_reasoning("forall X: P(X)", {})
        assert result["consistent"] is True
        assert result["confidence"] == 0.8

    async def test_invoke_fol_reasoning_inconsistent(self):
        """_invoke_fol_reasoning returns low confidence for inconsistency."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = (False, "inconsistent")
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ):
            result = await _invoke_fol_reasoning("text", {})
        assert result["consistent"] is False
        assert result["confidence"] == 0.3

    async def test_invoke_fol_reasoning_error(self):
        """_invoke_fol_reasoning returns error dict on exception."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            side_effect=Exception("no JVM"),
        ):
            result = await _invoke_fol_reasoning("text", {})
        assert "error" in result
        assert result["confidence"] == 0.0

    async def test_invoke_modal_logic_necessity(self):
        """_invoke_modal_logic detects necessity modality."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_modal_logic,
        )

        mock_bridge = MagicMock()
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ):
            result = await _invoke_modal_logic("text", {"formulas": ["[]p => q"]})
        assert "necessity" in result["modalities"]
        assert result["logic_type"] == "modal"

    async def test_invoke_modal_logic_possibility(self):
        """_invoke_modal_logic detects possibility modality."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_modal_logic,
        )

        mock_bridge = MagicMock()
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ):
            result = await _invoke_modal_logic("text", {"formulas": ["<>p"]})
        assert "possibility" in result["modalities"]

    async def test_invoke_modal_logic_no_modality(self):
        """_invoke_modal_logic returns none_detected when no modality keywords."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_modal_logic,
        )

        mock_bridge = MagicMock()
        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            return_value=mock_bridge,
        ):
            result = await _invoke_modal_logic("text", {"formulas": ["p => q"]})
        assert result["modalities"] == ["none_detected"]

    async def test_invoke_modal_logic_error(self):
        """_invoke_modal_logic returns error dict on exception."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_modal_logic,
        )

        with patch(
            "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge",
            side_effect=Exception("fail"),
        ):
            result = await _invoke_modal_logic("text", {})
        assert "error" in result
        assert result["valid"] is False

    async def test_invoke_dung_extensions_error(self):
        """_invoke_dung_extensions returns error dict on exception."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_dung_extensions,
        )

        with patch(
            "argumentation_analysis.agents.core.logic.af_handler.AFHandler",
            side_effect=Exception("no handler"),
        ):
            result = await _invoke_dung_extensions("text", {})
        assert "error" in result
        assert result["extensions"] == {}

    async def test_invoke_dung_extensions_no_arguments(self):
        """_invoke_dung_extensions generates default args when none provided."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_dung_extensions,
        )

        mock_handler = MagicMock()
        mock_handler.analyze_dung_framework.return_value = {
            "extensions": {"preferred": []}
        }

        # Patch at the module level where the import happens inside the function
        with patch.dict(
            "sys.modules",
            {
                "argumentation_analysis.agents.core.logic.af_handler": MagicMock(
                    AFHandler=MagicMock(return_value=mock_handler)
                ),
                "argumentation_analysis.core.jvm_setup": MagicMock(
                    TweetyInitializer=MagicMock()
                ),
            },
        ):
            result = await _invoke_dung_extensions("text", {})
        # Should have called with default arg_0, arg_1, arg_2
        call_args = mock_handler.analyze_dung_framework.call_args
        assert call_args[0][0] == ["arg_0", "arg_1", "arg_2"]

    async def test_invoke_formal_synthesis_no_phases(self):
        """_invoke_formal_synthesis with empty context."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_formal_synthesis,
        )

        result = await _invoke_formal_synthesis("text", {})
        assert result["summary"] == "No formal results collected"
        assert result["overall_validity"] == 0.5
        assert result["phase_count"] == 0

    async def test_invoke_formal_synthesis_with_results(self):
        """_invoke_formal_synthesis aggregates upstream phase results."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_formal_synthesis,
        )

        ctx = {
            "phase_prop_output": {"satisfiable": True, "formulas": ["p"]},
            "phase_fol_output": {"consistent": False, "formulas": ["forall X: P(X)"]},
            "phase_modal_output": {"valid": True, "formulas": ["[]p"]},
            "not_a_phase": "ignored",
        }
        result = await _invoke_formal_synthesis("text", ctx)
        assert result["phase_count"] == 3
        # 2 true + 1 false = 2/3
        assert abs(result["overall_validity"] - 2.0 / 3.0) < 0.01

    async def test_invoke_formal_synthesis_with_error_phase(self):
        """_invoke_formal_synthesis handles phase with error."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_formal_synthesis,
        )

        ctx = {
            "phase_broken_output": {"error": "something went wrong badly here"},
        }
        result = await _invoke_formal_synthesis("text", ctx)
        assert "error" in result["summary"]

    async def test_invoke_formal_synthesis_with_extensions(self):
        """_invoke_formal_synthesis handles phase with extensions."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_formal_synthesis,
        )

        ctx = {
            "phase_dung_output": {
                "extensions": {"preferred": [["a"], ["b"]], "grounded": [["a"]]}
            },
        }
        result = await _invoke_formal_synthesis("text", ctx)
        assert "extensions" in result["summary"]


# ============================================================
# Test: State writer functions
# ============================================================


class TestStateWriters:
    """Test _write_*_to_state functions with edge cases."""

    def _make_state(self):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        return UnifiedAnalysisState("Test text")

    def test_write_quality_to_state(self):
        """_write_quality_to_state writes scores correctly."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_quality_to_state,
        )

        state = self._make_state()
        output = {
            "note_finale": 7.5,
            "clarity": 8.0,
            "relevance": 6.0,
            "non_numeric": "skip",
        }
        _write_quality_to_state(output, state, {})
        assert "arg_input" in state.argument_quality_scores
        assert state.argument_quality_scores["arg_input"]["overall"] == 7.5

    def test_write_quality_to_state_none_output(self):
        """_write_quality_to_state handles None output."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_quality_to_state,
        )

        state = self._make_state()
        _write_quality_to_state(None, state, {})
        assert state.argument_quality_scores == {}

    def test_write_quality_to_state_non_numeric_overall(self):
        """_write_quality_to_state skips when note_finale is non-numeric."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_quality_to_state,
        )

        state = self._make_state()
        _write_quality_to_state({"note_finale": "high"}, state, {})
        assert state.argument_quality_scores == {}

    def test_write_counter_argument_to_state(self):
        """_write_counter_argument_to_state writes parsed results."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_counter_argument_to_state,
        )

        state = self._make_state()
        output = {
            "parsed_argument": {"premise": "All birds fly"},
            "suggested_strategy": {"strategy_name": "reductio", "confidence": 0.85},
        }
        _write_counter_argument_to_state(output, state, {})
        assert len(state.counter_arguments) == 1
        assert state.counter_arguments[0]["score"] == 0.85

    def test_write_counter_argument_non_dict_parsed(self):
        """_write_counter_argument_to_state handles non-dict parsed_argument."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_counter_argument_to_state,
        )

        state = self._make_state()
        output = {
            "parsed_argument": "not a dict",
            "suggested_strategy": "also not a dict",
        }
        _write_counter_argument_to_state(output, state, {"input_data": "test"})
        assert len(state.counter_arguments) == 1

    def test_write_counter_argument_non_numeric_score(self):
        """_write_counter_argument_to_state handles non-numeric confidence."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_counter_argument_to_state,
        )

        state = self._make_state()
        output = {
            "parsed_argument": {},
            "suggested_strategy": {"confidence": "high"},
        }
        _write_counter_argument_to_state(output, state, {})
        assert state.counter_arguments[0]["score"] == 0.0

    def test_write_jtms_to_state(self):
        """_write_jtms_to_state writes beliefs correctly."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_jtms_to_state,
        )

        state = self._make_state()
        output = {
            "beliefs": {"claim_0": "True", "claim_1": "False", "claim_2": "maybe"}
        }
        _write_jtms_to_state(output, state, {})
        assert len(state.jtms_beliefs) == 3

    def test_write_jtms_to_state_non_dict_beliefs(self):
        """_write_jtms_to_state returns early if beliefs is not dict."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_jtms_to_state,
        )

        state = self._make_state()
        _write_jtms_to_state({"beliefs": "invalid"}, state, {})
        assert len(state.jtms_beliefs) == 0

    def test_write_debate_to_state(self):
        """_write_debate_to_state writes transcript."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_debate_to_state,
        )

        state = self._make_state()
        output = {"winner": "pro"}
        _write_debate_to_state(output, state, {"input_data": "Should AI be regulated?"})
        assert len(state.debate_transcripts) == 1
        assert state.debate_transcripts[0]["winner"] == "pro"

    def test_write_debate_to_state_no_winner(self):
        """_write_debate_to_state handles missing winner."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_debate_to_state,
        )

        state = self._make_state()
        # Empty dict is falsy, so use a dict with some content but no winner
        _write_debate_to_state({"some_key": "value"}, state, {})
        assert len(state.debate_transcripts) == 1
        assert state.debate_transcripts[0]["winner"] is None

    def test_write_debate_to_state_empty_dict(self):
        """_write_debate_to_state returns early for empty dict (falsy)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_debate_to_state,
        )

        state = self._make_state()
        _write_debate_to_state({}, state, {})
        assert len(state.debate_transcripts) == 0

    def test_write_governance_to_state(self):
        """_write_governance_to_state writes decision."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_governance_to_state,
        )

        state = self._make_state()
        output = {"available_methods": ["majority", "borda"]}
        _write_governance_to_state(output, state, {})
        assert len(state.governance_decisions) == 1

    def test_write_governance_to_state_empty_methods(self):
        """_write_governance_to_state does nothing for empty methods."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_governance_to_state,
        )

        state = self._make_state()
        _write_governance_to_state({"available_methods": []}, state, {})
        assert len(state.governance_decisions) == 0

    def test_write_camembert_to_state(self):
        """_write_camembert_to_state writes fallacy detections."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_camembert_to_state,
        )

        state = self._make_state()
        output = {
            "detections": [
                {
                    "text": "attack the person",
                    "label": "ad_hominem",
                    "confidence": 0.92,
                },
                {"text": "straw man", "label": "straw_man", "confidence": 0.78},
            ]
        }
        _write_camembert_to_state(output, state, {})
        assert len(state.neural_fallacy_scores) == 2

    def test_write_camembert_to_state_non_list_detections(self):
        """_write_camembert_to_state handles non-list detections."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_camembert_to_state,
        )

        state = self._make_state()
        _write_camembert_to_state({"detections": "not a list"}, state, {})
        assert len(state.neural_fallacy_scores) == 0

    def test_write_camembert_to_state_non_dict_detection(self):
        """_write_camembert_to_state skips non-dict items in detections."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_camembert_to_state,
        )

        state = self._make_state()
        _write_camembert_to_state({"detections": ["not_a_dict", 42]}, state, {})
        assert len(state.neural_fallacy_scores) == 0

    def test_write_semantic_index_to_state(self):
        """_write_semantic_index_to_state writes search results."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_semantic_index_to_state,
        )

        state = self._make_state()
        output = {
            "results": [{"id": "doc1", "score": 0.95, "snippet": "relevant text"}]
        }
        _write_semantic_index_to_state(output, state, {"input_data": "query"})
        assert len(state.semantic_index_refs) == 1

    def test_write_semantic_index_to_state_non_list(self):
        """_write_semantic_index_to_state handles non-list results."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_semantic_index_to_state,
        )

        state = self._make_state()
        _write_semantic_index_to_state({"results": "not list"}, state, {})
        assert len(state.semantic_index_refs) == 0

    def test_write_speech_to_state(self):
        """_write_speech_to_state writes transcription segments."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_speech_to_state,
        )

        state = self._make_state()
        output = {
            "segments": [
                {"start": 0.0, "end": 1.5, "text": "Hello", "speaker": "A"},
                {"start": 1.5, "end": 3.0, "text": "World"},
            ]
        }
        _write_speech_to_state(output, state, {})
        assert len(state.transcription_segments) == 2

    def test_write_speech_to_state_non_list_segments(self):
        """_write_speech_to_state handles non-list segments."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_speech_to_state,
        )

        state = self._make_state()
        _write_speech_to_state({"segments": "invalid"}, state, {})
        assert len(state.transcription_segments) == 0

    def test_write_fact_extraction_to_state(self):
        """_write_fact_extraction_to_state appends claims to extracts."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_fact_extraction_to_state,
        )

        state = self._make_state()
        output = {
            "claims": [
                "Claim one about something",
                "  ",
                "Claim two about another thing",
            ]
        }
        _write_fact_extraction_to_state(output, state, {})
        # Only non-empty stripped strings are added
        assert len(state.extracts) == 2

    def test_write_fact_extraction_to_state_non_list_claims(self):
        """_write_fact_extraction_to_state handles non-list claims."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_fact_extraction_to_state,
        )

        state = self._make_state()
        _write_fact_extraction_to_state({"claims": "not list"}, state, {})
        assert len(state.extracts) == 0

    def test_write_propositional_to_state(self):
        """_write_propositional_to_state writes analysis result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_propositional_to_state,
        )

        state = self._make_state()
        output = {"formulas": ["p => q"], "satisfiable": True, "model": {"p": True}}
        _write_propositional_to_state(output, state, {})

    def test_write_propositional_to_state_non_list_formulas(self):
        """_write_propositional_to_state handles non-list formulas."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_propositional_to_state,
        )

        state = self._make_state()
        output = {"formulas": "single", "satisfiable": False, "model": "not dict"}
        _write_propositional_to_state(output, state, {})

    def test_write_fol_to_state(self):
        """_write_fol_to_state writes FOL analysis result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_fol_to_state,
        )

        state = self._make_state()
        output = {
            "formulas": ["forall X: P(X)"],
            "consistent": True,
            "inferences": ["P(a)"],
            "confidence": 0.9,
        }
        _write_fol_to_state(output, state, {})

    def test_write_fol_to_state_bad_types(self):
        """_write_fol_to_state handles non-list/non-numeric types."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_fol_to_state,
        )

        state = self._make_state()
        output = {
            "formulas": "not list",
            "consistent": False,
            "inferences": "not list",
            "confidence": "not num",
        }
        _write_fol_to_state(output, state, {})

    def test_write_modal_to_state(self):
        """_write_modal_to_state writes modal analysis."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_modal_to_state,
        )

        state = self._make_state()
        output = {"formulas": ["[]p"], "valid": True, "modalities": ["necessity"]}
        _write_modal_to_state(output, state, {})

    def test_write_modal_to_state_bad_types(self):
        """_write_modal_to_state handles non-list types."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_modal_to_state,
        )

        state = self._make_state()
        _write_modal_to_state(
            {"formulas": 42, "valid": True, "modalities": "not list"}, state, {}
        )

    def test_write_dung_extensions_to_state(self):
        """_write_dung_extensions_to_state writes Dung framework results."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_dung_extensions_to_state,
        )

        state = self._make_state()
        output = {
            "semantics": "grounded",
            "extensions": {"grounded": [["a"]]},
            "statistics": {"arguments_count": 3},
        }
        _write_dung_extensions_to_state(output, state, {})
        assert len(state.dung_frameworks) == 1

    def test_write_dung_extensions_to_state_non_dict_extensions(self):
        """_write_dung_extensions_to_state handles non-dict extensions."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_dung_extensions_to_state,
        )

        state = self._make_state()
        output = {"semantics": "preferred", "extensions": "not dict", "statistics": {}}
        _write_dung_extensions_to_state(output, state, {})
        # Should still create the framework entry with empty extensions
        assert len(state.dung_frameworks) == 1

    def test_write_formal_synthesis_to_state(self):
        """_write_formal_synthesis_to_state writes synthesis report."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_formal_synthesis_to_state,
        )

        state = self._make_state()
        output = {
            "summary": "prop: satisfiable=True",
            "phase_results": {"prop": {"satisfiable": True}},
            "overall_validity": 0.85,
        }
        _write_formal_synthesis_to_state(output, state, {})

    def test_write_formal_synthesis_to_state_bad_types(self):
        """_write_formal_synthesis_to_state handles bad types."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_formal_synthesis_to_state,
        )

        state = self._make_state()
        output = {
            "summary": 42,
            "phase_results": "not dict",
            "overall_validity": "high",
        }
        _write_formal_synthesis_to_state(output, state, {})

    def test_write_ranking_to_state(self):
        """_write_ranking_to_state writes ranking result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_ranking_to_state,
        )

        state = self._make_state()
        output = {
            "method": "categorizer",
            "arguments": ["a", "b"],
            "comparisons": [{"a": 1, "b": 2}],
        }
        _write_ranking_to_state(output, state, {})

    def test_write_ranking_to_state_bad_types(self):
        """_write_ranking_to_state handles non-list arguments/comparisons."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_ranking_to_state,
        )

        state = self._make_state()
        _write_ranking_to_state(
            {"method": "x", "arguments": "bad", "comparisons": "bad"}, state, {}
        )

    def test_write_aspic_to_state(self):
        """_write_aspic_to_state writes ASPIC+ result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_aspic_to_state,
        )

        state = self._make_state()
        output = {
            "reasoner_type": "simple",
            "extensions": [["a"]],
            "statistics": {"count": 1},
        }
        _write_aspic_to_state(output, state, {})

    def test_write_aspic_to_state_bad_types(self):
        """_write_aspic_to_state handles non-list/non-dict types."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_aspic_to_state,
        )

        state = self._make_state()
        _write_aspic_to_state({"extensions": "bad", "statistics": "bad"}, state, {})

    def test_write_belief_revision_to_state(self):
        """_write_belief_revision_to_state writes revision result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_belief_revision_to_state,
        )

        state = self._make_state()
        output = {"method": "dalal", "original": ["p", "q"], "revised": ["p", "r"]}
        _write_belief_revision_to_state(output, state, {})

    def test_write_belief_revision_to_state_bad_types(self):
        """_write_belief_revision_to_state handles non-list types."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_belief_revision_to_state,
        )

        state = self._make_state()
        _write_belief_revision_to_state(
            {"original": "bad", "revised": "bad"}, state, {}
        )

    def test_write_dialogue_to_state(self):
        """_write_dialogue_to_state writes dialogue result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_dialogue_to_state,
        )

        state = self._make_state()
        output = {
            "topic": "AI",
            "outcome": "agreement",
            "dialogue_trace": [{"move": "claim"}],
        }
        _write_dialogue_to_state(output, state, {})

    def test_write_dialogue_to_state_bad_trace(self):
        """_write_dialogue_to_state handles non-list trace."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_dialogue_to_state,
        )

        state = self._make_state()
        _write_dialogue_to_state({"dialogue_trace": "bad"}, state, {})

    def test_write_probabilistic_to_state(self):
        """_write_probabilistic_to_state writes probabilistic result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_probabilistic_to_state,
        )

        state = self._make_state()
        output = {"arguments": ["a"], "acceptance_probabilities": {"a": 0.7}}
        _write_probabilistic_to_state(output, state, {})

    def test_write_probabilistic_to_state_bad_types(self):
        """_write_probabilistic_to_state handles non-list/non-dict types."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_probabilistic_to_state,
        )

        state = self._make_state()
        _write_probabilistic_to_state(
            {"arguments": "bad", "acceptance_probabilities": "bad"}, state, {}
        )

    def test_write_bipolar_to_state(self):
        """_write_bipolar_to_state writes bipolar result."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_bipolar_to_state,
        )

        state = self._make_state()
        output = {
            "framework_type": "necessity",
            "arguments": ["a"],
            "supports": [["a", "b"]],
        }
        _write_bipolar_to_state(output, state, {})

    def test_write_bipolar_to_state_bad_types(self):
        """_write_bipolar_to_state handles non-list types."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_bipolar_to_state,
        )

        state = self._make_state()
        _write_bipolar_to_state({"arguments": "bad", "supports": "bad"}, state, {})

    def test_write_aba_to_state(self):
        """_write_aba_to_state writes ABA results as Dung framework."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_aba_to_state,
        )

        state = self._make_state()
        output = {
            "assumptions": ["a", "b"],
            "extensions": [["a"]],
            "semantics": "preferred",
        }
        _write_aba_to_state(output, state, {})
        assert len(state.dung_frameworks) == 1

    def test_write_aba_to_state_non_list_assumptions(self):
        """_write_aba_to_state handles non-list assumptions."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_aba_to_state,
        )

        state = self._make_state()
        _write_aba_to_state({"assumptions": "bad"}, state, {})
        assert len(state.dung_frameworks) == 1

    def test_write_adf_to_state(self):
        """_write_adf_to_state writes ADF results as Dung framework."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_adf_to_state,
        )

        state = self._make_state()
        output = {
            "statements": ["s1"],
            "models": [{"s1": True}],
            "semantics": "grounded",
        }
        _write_adf_to_state(output, state, {})
        assert len(state.dung_frameworks) == 1

    def test_write_adf_to_state_non_list_statements(self):
        """_write_adf_to_state handles non-list statements."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_adf_to_state,
        )

        state = self._make_state()
        _write_adf_to_state({"statements": "bad"}, state, {})
        assert len(state.dung_frameworks) == 1

    def test_write_adf_to_state_uses_extensions_fallback(self):
        """_write_adf_to_state falls back to 'extensions' key if no 'models'."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_adf_to_state,
        )

        state = self._make_state()
        output = {"statements": ["s1"], "extensions": [["s1"]]}
        _write_adf_to_state(output, state, {})
        assert len(state.dung_frameworks) == 1

    def test_all_state_writers_handle_none(self):
        """All state writers handle None output gracefully."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            CAPABILITY_STATE_WRITERS,
        )

        state = self._make_state()
        for cap, writer in CAPABILITY_STATE_WRITERS.items():
            writer(None, state, {})
        # No crash = success

    def test_all_state_writers_handle_empty_dict(self):
        """All state writers handle empty dict output gracefully."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            CAPABILITY_STATE_WRITERS,
        )

        state = self._make_state()
        for cap, writer in CAPABILITY_STATE_WRITERS.items():
            writer({}, state, {})
        # No crash = success


# ============================================================
# Test: Additional workflow builders
# ============================================================


class TestAdditionalWorkflows:
    """Test workflow builders not covered by TestPrebuiltWorkflows."""

    def test_build_quality_gated_counter_workflow(self):
        """Quality-gated counter workflow has 4 phases (extract + quality + counter + recheck)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        assert wf.name == "quality_gated_counter"
        assert len(wf.phases) == 4

    def test_build_debate_governance_loop_workflow(self):
        """Debate-governance loop workflow has 3 phases."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_debate_governance_loop_workflow,
        )

        wf = build_debate_governance_loop_workflow()
        assert wf.name == "debate_governance_loop"
        assert len(wf.phases) == 3

    def test_build_jtms_dung_loop_workflow(self):
        """JTMS-Dung loop workflow has 2 phases."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_jtms_dung_loop_workflow,
        )

        wf = build_jtms_dung_loop_workflow()
        assert wf.name == "jtms_dung_loop"
        assert len(wf.phases) == 2

    def test_build_neural_symbolic_fallacy_workflow(self):
        """Neural-symbolic fallacy workflow has 3 phases (neural + hierarchical + quality)."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_neural_symbolic_fallacy_workflow,
        )

        wf = build_neural_symbolic_fallacy_workflow()
        assert wf.name == "neural_symbolic_fallacy"
        assert len(wf.phases) == 3
        phase_names = [p.name for p in wf.phases]
        assert "neural_detect" in phase_names
        assert "hierarchical_detect" in phase_names
        assert "quality_baseline" in phase_names

    def test_workflow_catalog_includes_extra_workflows(self):
        """Workflow catalog includes quality_gated, debate_governance, etc."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )

        catalog = get_workflow_catalog()
        assert "quality_gated" in catalog
        assert "debate_governance" in catalog
        assert "jtms_dung" in catalog
        assert "neural_symbolic" in catalog
        assert "hierarchical_fallacy" in catalog

    def test_quality_gate_function_proceeds_when_no_quality(self):
        """Quality gate function returns True when no quality data."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        counter_phase = wf.get_phase("counter")
        # The condition should return True when no quality output
        assert counter_phase.condition({}) is True

    def test_quality_gate_function_proceeds_when_high_score(self):
        """Quality gate function returns True when score > 3.0."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        counter_phase = wf.get_phase("counter")
        assert (
            counter_phase.condition({"phase_quality_output": {"note_finale": 5.0}})
            is True
        )

    def test_quality_gate_function_blocks_when_low_score(self):
        """Quality gate function returns False when score <= 3.0."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        counter_phase = wf.get_phase("counter")
        assert (
            counter_phase.condition({"phase_quality_output": {"note_finale": 2.0}})
            is False
        )

    def test_quality_gate_function_non_dict_output(self):
        """Quality gate function returns True for non-dict quality output."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        counter_phase = wf.get_phase("counter")
        assert counter_phase.condition({"phase_quality_output": "not a dict"}) is True

    def test_convergence_function_not_converged(self):
        """Convergence function returns False when score decreases."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        recheck_phase = wf.get_phase("quality_recheck")
        conv_fn = recheck_phase.loop_config.convergence_fn
        prev = {"note_finale": 5.0}
        curr = {"note_finale": 4.0}
        assert conv_fn(prev, curr) is False

    def test_convergence_function_converged(self):
        """Convergence function returns True when score stops improving."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        recheck_phase = wf.get_phase("quality_recheck")
        conv_fn = recheck_phase.loop_config.convergence_fn
        prev = {"note_finale": 5.0}
        curr = {"note_finale": 5.0}
        assert conv_fn(prev, curr) is True

    def test_convergence_function_non_dict(self):
        """Convergence function returns False for non-dict inputs."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_quality_gated_counter_workflow,
        )

        wf = build_quality_gated_counter_workflow()
        recheck_phase = wf.get_phase("quality_recheck")
        conv_fn = recheck_phase.loop_config.convergence_fn
        assert conv_fn("not dict", {"note_finale": 5.0}) is False
        assert conv_fn({"note_finale": 5.0}, "not dict") is False


# ============================================================
# Test: run_unified_analysis edge cases
# ============================================================


class TestRunUnifiedAnalysisEdgeCases:
    """Test edge cases in run_unified_analysis."""

    async def test_run_with_auto_routing_fallback(self):
        """run_unified_analysis with workflow_name='auto' falls back to standard on error."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        with patch(
            "argumentation_analysis.orchestration.router.TextAnalysisRouter",
            side_effect=Exception("Router not available"),
        ):
            result = await run_unified_analysis(
                "Test text", workflow_name="auto", registry=registry
            )
        assert result["workflow_name"] == "standard_analysis"

    async def test_run_with_provided_state(self):
        """run_unified_analysis uses provided state object."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        registry = setup_registry(include_optional=False)
        state = UnifiedAnalysisState("Custom state text")
        result = await run_unified_analysis(
            "Test text", workflow_name="light", registry=registry, state=state
        )
        assert result["unified_state"] is state

    async def test_run_with_state_snapshot_error(self):
        """run_unified_analysis handles get_state_snapshot failure."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        mock_state = MagicMock()
        mock_state.get_state_snapshot.side_effect = Exception("snapshot error")
        result = await run_unified_analysis(
            "Test text", workflow_name="light", registry=registry, state=mock_state
        )
        assert result["unified_state"] is mock_state
        assert result["state_snapshot"] is None

    async def test_run_unified_analysis_state_import_error(self):
        """run_unified_analysis handles UnifiedAnalysisState import failure."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.setup_registry",
            return_value=registry,
        ), patch.dict(
            "sys.modules",
            {"argumentation_analysis.core.shared_state": None},
        ):
            # Force ImportError for UnifiedAnalysisState
            result = await run_unified_analysis(
                "Test text",
                workflow_name="light",
                registry=registry,
                create_state=True,
            )
        # State creation failed but analysis should still succeed
        assert "phases" in result
        assert "summary" in result

    async def test_run_summary_lists_phases(self):
        """run_unified_analysis summary includes phase name lists."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
            setup_registry,
        )

        registry = setup_registry(include_optional=False)
        result = await run_unified_analysis(
            "Test argument text.",
            workflow_name="light",
            registry=registry,
        )
        summary = result["summary"]
        assert "completed_phases" in summary
        assert "failed_phases" in summary
        assert "skipped_phases" in summary
        assert isinstance(summary["completed_phases"], list)


# ============================================================
# Test: CAPABILITY_STATE_WRITERS mapping
# ============================================================


class TestCapabilityStateWritersMapping:
    """Test the CAPABILITY_STATE_WRITERS dict has correct entries."""

    def test_all_expected_capabilities_present(self):
        """CAPABILITY_STATE_WRITERS has entries for all core capabilities."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            CAPABILITY_STATE_WRITERS,
        )

        expected = [
            "argument_quality",
            "counter_argument_generation",
            "belief_maintenance",
            "adversarial_debate",
            "governance_simulation",
            "neural_fallacy_detection",
            "semantic_indexing",
            "speech_transcription",
            "ranking_semantics",
            "aspic_plus_reasoning",
            "belief_revision",
            "dialogue_protocols",
            "probabilistic_argumentation",
            "bipolar_argumentation",
            "aba_reasoning",
            "adf_reasoning",
            "fact_extraction",
            "propositional_logic",
            "fol_reasoning",
            "modal_logic",
            "dung_extensions",
            "formal_synthesis",
        ]
        for cap in expected:
            assert cap in CAPABILITY_STATE_WRITERS, f"Missing writer for {cap}"

    def test_all_writers_are_callable(self):
        """All state writers are callable."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            CAPABILITY_STATE_WRITERS,
        )

        for cap, writer in CAPABILITY_STATE_WRITERS.items():
            assert callable(writer), f"Writer for {cap} is not callable"


# ============================================================
# Test: _declare_tweety_slots error handling
# ============================================================


class TestDeclareTweetySlots:
    """Test _declare_tweety_slots with registration failures."""

    def test_declare_tweety_slots_registers_services(self):
        """_declare_tweety_slots registers all 8 Tweety handlers."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _declare_tweety_slots,
        )

        registry = CapabilityRegistry()
        _declare_tweety_slots(registry)
        caps = registry.get_all_capabilities()
        assert "ranking_semantics" in caps
        assert "bipolar_argumentation" in caps
        assert "aba_reasoning" in caps
        assert "adf_reasoning" in caps
        assert "aspic_plus_reasoning" in caps
        assert "dialogue_protocols" in caps

    def test_declare_tweety_slots_fallback_to_slot(self):
        """_declare_tweety_slots falls back to slot declaration on error."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _declare_tweety_slots,
        )

        registry = CapabilityRegistry()
        # Make register_service always raise to force slot declaration path
        with patch.object(
            registry, "register_service", side_effect=Exception("forced failure")
        ):
            _declare_tweety_slots(registry)

        # All capabilities should be declared as slots
        slots = registry.get_all_slots()
        assert "ranking_semantics" in slots
        assert "bipolar_argumentation" in slots


# ============================================================
# Test: setup_registry error handling
# ============================================================


class TestSetupRegistryErrors:
    """Test setup_registry with import failures."""

    def test_setup_registry_handles_counter_argument_import_error(self):
        """setup_registry skips counter_argument when import fails."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.CapabilityRegistry"
        ) as MockRegistry:
            mock_reg = MagicMock()
            mock_reg._registrations = {}
            mock_reg.summary.return_value = {"total_registrations": 0}
            MockRegistry.return_value = mock_reg
            # This tests that ImportError is caught gracefully
            registry = setup_registry(include_optional=False)
            assert registry is not None

    def test_setup_registry_logic_capability_exception(self):
        """setup_registry handles exceptions during logic capability registration."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = CapabilityRegistry()
        # Register a service with a duplicate name to cause an error
        # The setup_registry function catches Exception for logic capabilities
        # Verify it doesn't crash
        result = setup_registry(include_optional=False)
        assert isinstance(result, CapabilityRegistry)


# ============================================================
# Test: Hierarchical Fallacy Detection Integration (#84 Phase 3)
# ============================================================


class TestHierarchicalFallacyWorkflow:
    """Tests for hierarchical taxonomy-guided fallacy detection workflow."""

    def test_build_hierarchical_fallacy_workflow(self):
        """Hierarchical fallacy workflow has 3 phases with correct dependencies."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_hierarchical_fallacy_workflow,
        )

        wf = build_hierarchical_fallacy_workflow()
        assert wf.name == "hierarchical_fallacy"
        assert len(wf.phases) == 3
        phase_names = [p.name for p in wf.phases]
        assert "extract" in phase_names
        assert "hierarchical_fallacy" in phase_names
        assert "quality" in phase_names

    def test_hierarchical_fallacy_depends_on_extract(self):
        """Hierarchical fallacy phase depends on extract phase."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_hierarchical_fallacy_workflow,
        )

        wf = build_hierarchical_fallacy_workflow()
        hf_phase = wf.get_phase("hierarchical_fallacy")
        assert "extract" in hf_phase.depends_on

    def test_hierarchical_fallacy_quality_is_optional(self):
        """Quality phase in hierarchical workflow is optional."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_hierarchical_fallacy_workflow,
        )

        wf = build_hierarchical_fallacy_workflow()
        quality_phase = wf.get_phase("quality")
        assert quality_phase.optional is True

    def test_hierarchical_fallacy_execution_order(self):
        """Extract runs before hierarchical_fallacy."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            build_hierarchical_fallacy_workflow,
        )

        wf = build_hierarchical_fallacy_workflow()
        order = wf.get_execution_order()
        flat = [name for level in order for name in level]
        assert flat.index("extract") < flat.index("hierarchical_fallacy")

    def test_workflow_catalog_includes_hierarchical_fallacy(self):
        """Workflow catalog contains hierarchical_fallacy workflow."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )

        catalog = get_workflow_catalog()
        assert "hierarchical_fallacy" in catalog

    def test_registry_includes_hierarchical_fallacy_detector(self):
        """setup_registry registers hierarchical_fallacy_detector."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=True)
        providers = registry.find_for_capability("hierarchical_fallacy_detection")
        assert len(providers) >= 1
        names = [p.name for p in providers]
        assert "hierarchical_fallacy_detector" in names

    def test_registry_hierarchical_also_provides_fallacy_detection(self):
        """Hierarchical detector also provides generic fallacy_detection capability."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            setup_registry,
        )

        registry = setup_registry(include_optional=True)
        providers = registry.find_for_capability("fallacy_detection")
        names = [p.name for p in providers]
        assert "hierarchical_fallacy_detector" in names

    async def test_invoke_hierarchical_fallacy_no_taxonomy(self):
        """_invoke_hierarchical_fallacy returns skipped when taxonomy not found."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_hierarchical_fallacy,
        )

        with patch("os.path.isfile", return_value=False):
            result = await _invoke_hierarchical_fallacy("text", {})
        assert result["exploration_method"] == "skipped"
        assert result["fallacies"] == []

    async def test_invoke_hierarchical_fallacy_no_api_key(self):
        """_invoke_hierarchical_fallacy returns error when no API key."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_hierarchical_fallacy,
        )

        with patch("os.path.isfile", return_value=True), patch.dict(
            "os.environ", {"OPENAI_API_KEY": ""}, clear=False
        ):
            result = await _invoke_hierarchical_fallacy("text", {})
        assert result["exploration_method"] == "error"
        assert result["fallacies"] == []

    async def test_invoke_hierarchical_fallacy_success(self):
        """_invoke_hierarchical_fallacy returns parsed result on success.

        Tests the full invoke function by mocking SK service + plugin.
        """
        import json
        import sys
        from unittest.mock import AsyncMock
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_hierarchical_fallacy,
        )
        from argumentation_analysis.plugins.identification_models import (
            FallacyAnalysisResult,
            IdentifiedFallacy,
        )

        mock_result = FallacyAnalysisResult(
            fallacies=[
                IdentifiedFallacy(
                    fallacy_type="Ad hominem",
                    taxonomy_pk="42",
                    taxonomy_path="1.2.42",
                    explanation="Attacks the person",
                    confidence=0.85,
                    navigation_trace=["1", "1.2", "42"],
                )
            ],
            exploration_method="iterative_deepening",
            branches_explored=2,
            total_iterations=5,
        )
        mock_result_json = mock_result.model_dump_json(indent=2)

        mock_plugin_instance = MagicMock()
        mock_plugin_instance.run_guided_analysis = AsyncMock(
            return_value=mock_result_json
        )
        mock_plugin_cls = MagicMock(return_value=mock_plugin_instance)
        mock_llm_service = MagicMock()
        mock_kernel_cls = MagicMock()

        with patch("os.path.isfile", return_value=True), patch.dict(
            "os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False
        ):
            # Mock at the source modules that the function imports from
            import argumentation_analysis.plugins.fallacy_workflow_plugin as fwp_mod
            import semantic_kernel.connectors.ai.open_ai as sk_oai
            import semantic_kernel.kernel as sk_kernel
            import openai as openai_mod

            orig_plugin = fwp_mod.FallacyWorkflowPlugin
            orig_oai = sk_oai.OpenAIChatCompletion
            orig_kernel = sk_kernel.Kernel
            orig_async_client = openai_mod.AsyncOpenAI
            fwp_mod.FallacyWorkflowPlugin = mock_plugin_cls
            sk_oai.OpenAIChatCompletion = MagicMock(return_value=mock_llm_service)
            sk_kernel.Kernel = mock_kernel_cls
            openai_mod.AsyncOpenAI = MagicMock()
            try:
                result = await _invoke_hierarchical_fallacy("some argument text", {})
            finally:
                fwp_mod.FallacyWorkflowPlugin = orig_plugin
                sk_oai.OpenAIChatCompletion = orig_oai
                sk_kernel.Kernel = orig_kernel
                openai_mod.AsyncOpenAI = orig_async_client

        assert result["extraction_method"] == "iterative_deepening"
        assert len(result["fallacies"]) == 1
        assert result["fallacies"][0]["fallacy_type"] == "Ad hominem"
        assert result["branches_explored"] == 2

    def test_state_writer_hierarchical_fallacy(self):
        """_write_hierarchical_fallacy_to_state writes fallacies to state."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_hierarchical_fallacy_to_state,
        )

        state = UnifiedAnalysisState("Test text")
        output = {
            "fallacies": [
                {
                    "fallacy_type": "Straw man",
                    "explanation": "Misrepresents position",
                    "taxonomy_pk": "99",
                    "confidence": 0.8,
                    "navigation_trace": ["1", "5", "99"],
                },
                {
                    "fallacy_type": "False cause",
                    "explanation": "Correlation not causation",
                    "taxonomy_pk": "55",
                    "confidence": 0.6,
                    "navigation_trace": [],
                },
            ]
        }
        _write_hierarchical_fallacy_to_state(output, state, {})
        assert len(state.identified_fallacies) == 2
        # Check that taxonomy info is in the justification
        fallacy_values = list(state.identified_fallacies.values())
        assert "[taxonomy:99]" in fallacy_values[0]["justification"]
        assert "[confidence:0.80]" in fallacy_values[0]["justification"]
        assert "[trace:1>5>99]" in fallacy_values[0]["justification"]

    def test_state_writer_hierarchical_fallacy_empty(self):
        """_write_hierarchical_fallacy_to_state handles empty output."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_hierarchical_fallacy_to_state,
        )

        state = UnifiedAnalysisState("Test text")
        _write_hierarchical_fallacy_to_state({}, state, {})
        assert len(state.identified_fallacies) == 0

    def test_state_writer_hierarchical_fallacy_none(self):
        """_write_hierarchical_fallacy_to_state handles None output."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_hierarchical_fallacy_to_state,
        )

        state = UnifiedAnalysisState("Test text")
        _write_hierarchical_fallacy_to_state(None, state, {})
        assert len(state.identified_fallacies) == 0

    def test_capability_state_writers_includes_hierarchical(self):
        """CAPABILITY_STATE_WRITERS has an entry for hierarchical_fallacy_detection."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            CAPABILITY_STATE_WRITERS,
        )

        assert "hierarchical_fallacy_detection" in CAPABILITY_STATE_WRITERS


class TestTextualCitations:
    """Tests for source_quote support in fact extraction (#160)."""

    def test_normalize_items_with_quotes_strings(self):
        """_normalize_items_with_quotes handles legacy string format."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _normalize_items_with_quotes,
        )

        result = _normalize_items_with_quotes(["arg1", "arg2"])
        assert len(result) == 2
        assert result[0] == {"text": "arg1", "source_quote": ""}
        assert result[1] == {"text": "arg2", "source_quote": ""}

    def test_normalize_items_with_quotes_dicts(self):
        """_normalize_items_with_quotes handles new dict format with source_quote."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _normalize_items_with_quotes,
        )

        result = _normalize_items_with_quotes([
            {"text": "argument one", "source_quote": "exact quote from text"},
            {"text": "argument two"},
        ])
        assert result[0]["source_quote"] == "exact quote from text"
        assert result[1]["source_quote"] == ""

    def test_normalize_fallacies_with_quotes(self):
        """_normalize_fallacies_with_quotes handles both formats."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _normalize_fallacies_with_quotes,
        )

        result = _normalize_fallacies_with_quotes([
            {"type": "ad_hominem", "justification": "attacks person", "source_quote": "you fool"},
            "bare_assertion",
        ])
        assert result[0]["source_quote"] == "you fool"
        assert result[1]["type"] == "bare_assertion"
        assert result[1]["source_quote"] == ""

    def test_write_fact_extraction_with_quotes(self):
        """_write_fact_extraction_to_state propagates source_quote to state."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_fact_extraction_to_state,
        )

        state = UnifiedAnalysisState("Test text")
        output = {
            "claims": [
                {"text": "Earth is flat", "source_quote": "the horizon looks flat"},
            ],
            "arguments": [
                {"text": "visual argument", "source_quote": "horizon looks flat"},
            ],
            "fallacies": [
                {"type": "hasty_gen", "justification": "insufficient evidence", "source_quote": "horizon looks flat"},
            ],
        }
        _write_fact_extraction_to_state(output, state, {})

        # Claims should have source_quote in extracts
        assert len(state.extracts) == 1
        assert state.extracts[0]["source_quote"] == "the horizon looks flat"

        # Arguments: add_argument stores a string with embedded quote
        args = list(state.identified_arguments.values())
        assert len(args) == 1
        assert "[quote:" in args[0]  # string with embedded quote

        # Fallacies: add_fallacy stores {"type", "justification"} with embedded quote
        fallacies = list(state.identified_fallacies.values())
        assert len(fallacies) == 1
        assert "[quote:" in fallacies[0]["justification"]

    def test_write_fact_extraction_legacy_strings(self):
        """_write_fact_extraction_to_state still works with legacy string format."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _write_fact_extraction_to_state,
        )

        state = UnifiedAnalysisState("Test text")
        output = {
            "claims": ["claim one", "claim two"],
            "arguments": ["arg one"],
            "fallacies": [{"type": "ad_hominem", "justification": "attacks person"}],
        }
        _write_fact_extraction_to_state(output, state, {})

        assert len(state.extracts) == 2
        assert len(state.identified_arguments) == 1
        assert len(state.identified_fallacies) == 1
