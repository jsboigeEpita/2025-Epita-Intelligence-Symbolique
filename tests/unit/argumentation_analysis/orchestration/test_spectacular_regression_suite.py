"""Golden regression suite for spectacular and sherlock_modern workflows (#365).

Validates workflow structure, execution order, and state population
with deterministic mock providers. Catches regressions if phases,
dependencies, or state fields change unexpectedly.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseStatus,
    WorkflowExecutor,
)
from argumentation_analysis.orchestration.workflows import (
    build_spectacular_workflow,
    reset_workflow_catalog,
    get_workflow_catalog,
)
from argumentation_analysis.orchestration.sherlock_modern_orchestrator import (
    build_sherlock_modern_workflow,
)


@pytest.fixture(autouse=True)
def _reset_catalog():
    reset_workflow_catalog()
    yield
    reset_workflow_catalog()


# Deterministic mock outputs for each capability
MOCK_OUTPUTS = {
    "fact_extraction": {
        "extracts": [
            {"id": "e1", "content": "claim_1"},
            {"id": "e2", "content": "claim_2"},
        ],
        "arguments": [{"id": "a1", "description": "arg_1"}],
    },
    "argument_quality": {
        "per_argument_scores": {"a1": {"clarity": 7.0}},
        "note_finale": 6.5,
    },
    "nl_to_logic_translation": {
        "translations": [{"formula": "P(a)", "logic_type": "fol", "is_valid": True}],
    },
    "neural_fallacy_detection": {
        "fallacies": [{"type": "ad_hominem", "confidence": 0.85}],
        "total": 1,
    },
    "hierarchical_fallacy_detection": {
        "fallacies": {"f1": {"type": "hasty_generalization"}},
        "total": 1,
    },
    "propositional_logic": {
        "formulas": ["p => q", "p"],
        "satisfiable": True,
        "model": {"p": True, "q": True},
    },
    "fol_reasoning": {
        "formulas": ["forall X: P(X) => Q(X)"],
        "consistent": True,
        "inferences": ["Q(a)"],
    },
    "modal_logic": {
        "formulas": ["[]P => P"],
        "valid": True,
        "modalities": ["necessity"],
    },
    "dung_extensions": {
        "extensions": {"grounded": ["a1"], "preferred": [["a1", "a2"]]},
    },
    "aspic_plus_reasoning": {
        "extensions": [{"args": ["a1"], "defeated": []}],
        "statistics": {"extension_count": 1},
    },
    "counter_argument_generation": {
        "counter_arguments": [{"content": "counter_1", "strategy": "reductio"}],
        "suggested_strategy": {"strategy_name": "reductio_ad_absurdum"},
    },
    "belief_maintenance": {
        "beliefs": {"b1": {"name": "claim_1", "valid": True}},
        "retraction_chain": [],
    },
    "adversarial_debate": {
        "transcript": [{"proponent": "P arg", "opponent": "O counter"}],
        "winner": "opponent",
    },
    "assumption_based_reasoning": {
        "atms_contexts": [
            {
                "hypothesis_id": "h_trust",
                "coherent": True,
                "assumptions": ["source_reliable"],
            },
            {
                "hypothesis_id": "h_skeptical",
                "coherent": False,
                "assumptions": ["source_unreliable"],
            },
        ],
        "has_contradictions": True,
    },
    "governance_simulation": {
        "method": "borda",
        "winner": "arg_1",
        "scores": {"arg_1": 5.0, "arg_2": 3.0},
    },
    "formal_synthesis": {
        "summary": "Formal analysis complete",
        "phase_results": {"fol": {"consistent": True}},
        "overall_validity": 0.85,
    },
    "narrative_synthesis": {
        "narrative": "Investigation complete with 2 hypotheses tested.",
        "paragraph_count": 3,
    },
    "atms_hypothesis_testing": {
        "atms_contexts": [
            {"hypothesis_id": "h1", "coherent": True},
            {"hypothesis_id": "h2", "coherent": False},
        ],
        "has_contradictions": True,
    },
}


def _make_mock_registry():
    """Build a mock CapabilityRegistry with providers for all capabilities."""
    registry = MagicMock()

    def find_for_capability(cap):
        output = MOCK_OUTPUTS.get(cap, {})
        provider = MagicMock()
        provider.name = f"mock_{cap}"
        provider.invoke = AsyncMock(return_value=output)
        return [provider]

    registry.find_for_capability = MagicMock(side_effect=find_for_capability)
    return registry


def _make_mock_state_writers():
    """Build state writers that populate UnifiedAnalysisState."""
    writers = {}

    def _write_quality(output, state, ctx):
        if isinstance(output, dict) and "per_argument_scores" in output:
            for arg_id, scores in output["per_argument_scores"].items():
                state.add_quality_score(arg_id, scores, output.get("note_finale", 0))

    def _write_counter(output, state, ctx):
        if isinstance(output, dict):
            for ca in output.get("counter_arguments", []):
                state.add_counter_argument(
                    "arg", ca.get("content", ""), ca.get("strategy", "general"), 0.7
                )

    def _write_jtms(output, state, ctx):
        if isinstance(output, dict):
            for bid, bdata in output.get("beliefs", {}).items():
                if isinstance(bdata, dict):
                    state.add_jtms_belief(
                        bdata.get("name", bid), bdata.get("valid"), []
                    )

    def _write_atms(output, state, ctx):
        if isinstance(output, dict):
            for ctx_data in output.get("atms_contexts", []):
                if isinstance(ctx_data, dict):
                    state.atms_contexts.append(ctx_data)

    def _write_debate(output, state, ctx):
        if isinstance(output, dict):
            state.add_debate_transcript(
                "debate", output.get("transcript", []), output.get("winner")
            )

    def _write_governance(output, state, ctx):
        if isinstance(output, dict) and "method" in output:
            state.add_governance_decision(
                output["method"], output.get("winner", ""), output.get("scores", {})
            )

    def _write_fallacy(output, state, ctx):
        if isinstance(output, dict):
            fallacies = output.get("fallacies", {})
            if isinstance(fallacies, dict):
                for fid, fdata in fallacies.items():
                    if isinstance(fdata, dict):
                        state.identified_fallacies[fid] = fdata

    def _write_extract(output, state, ctx):
        if isinstance(output, dict):
            for ext in output.get("extracts", []):
                state.add_extract(ext.get("id", ""), ext.get("content", ""))
            for arg in output.get("arguments", []):
                state.add_argument(arg.get("description", ""))

    def _write_pl(output, state, ctx):
        if isinstance(output, dict) and "formulas" in output:
            state.add_propositional_analysis_result(
                output["formulas"], output.get("satisfiable", True), output.get("model")
            )

    def _write_fol(output, state, ctx):
        if isinstance(output, dict) and "formulas" in output:
            state.add_fol_analysis_result(
                output["formulas"],
                output.get("consistent", True),
                output.get("inferences", []),
            )

    def _write_modal(output, state, ctx):
        if isinstance(output, dict) and "formulas" in output:
            state.add_modal_analysis_result(
                output["formulas"],
                output.get("valid", True),
                output.get("modalities", []),
            )

    def _write_nl_to_logic(output, state, ctx):
        if isinstance(output, dict):
            for tr in output.get("translations", []):
                state.add_nl_to_logic_translation(
                    "text",
                    tr.get("formula", ""),
                    tr.get("logic_type", "fol"),
                    tr.get("is_valid", True),
                )

    def _write_dung(output, state, ctx):
        if isinstance(output, dict) and "extensions" in output:
            state.add_dung_framework("dung", list(output["extensions"].keys()), [])

    def _write_aspic(output, state, ctx):
        if isinstance(output, dict):
            state.add_aspic_result(
                "aspic", output.get("extensions", []), output.get("statistics", {})
            )

    def _write_neural_fallacy(output, state, ctx):
        if isinstance(output, dict):
            for f in output.get("fallacies", []):
                state.add_neural_fallacy_score(
                    "segment", f.get("type", ""), f.get("confidence", 0.5)
                )

    def _write_formal_synthesis(output, state, ctx):
        if isinstance(output, dict) and "summary" in output:
            state.add_formal_synthesis_report(
                output["summary"],
                output.get("phase_results", {}),
                output.get("overall_validity", 0),
            )

    def _write_narrative_synthesis(output, state, ctx):
        if isinstance(output, dict) and "narrative" in output:
            state.narrative_synthesis = output["narrative"]

    def _write_atms_hypothesis(output, state, ctx):
        _write_atms(output, state, ctx)

    writers["argument_quality"] = _write_quality
    writers["counter_argument_generation"] = _write_counter
    writers["belief_maintenance"] = _write_jtms
    writers["assumption_based_reasoning"] = _write_atms
    writers["adversarial_debate"] = _write_debate
    writers["governance_simulation"] = _write_governance
    writers["hierarchical_fallacy_detection"] = _write_fallacy
    writers["fact_extraction"] = _write_extract
    writers["propositional_logic"] = _write_pl
    writers["fol_reasoning"] = _write_fol
    writers["modal_logic"] = _write_modal
    writers["nl_to_logic_translation"] = _write_nl_to_logic
    writers["dung_extensions"] = _write_dung
    writers["aspic_plus_reasoning"] = _write_aspic
    writers["neural_fallacy_detection"] = _write_neural_fallacy
    writers["formal_synthesis"] = _write_formal_synthesis
    writers["narrative_synthesis"] = _write_narrative_synthesis
    writers["atms_hypothesis_testing"] = _write_atms_hypothesis
    return writers


async def _execute_workflow(wf, text="Test discourse for golden regression."):
    registry = _make_mock_registry()
    executor = WorkflowExecutor(registry)
    state = UnifiedAnalysisState(text)
    writers = _make_mock_state_writers()
    results = await executor.execute(wf, text, state=state, state_writers=writers)
    return results, state


# ── Spectacular Workflow Golden Tests ───────────────────────────────────────


class TestSpectacularWorkflowGolden:
    """Golden regression tests for build_spectacular_workflow()."""

    EXPECTED_PHASES = {
        "extract",
        "quality",
        "nl_to_logic",
        "neural_detect",
        "hierarchical_fallacy",
        "pl",
        "fol",
        "modal",
        "dung_extensions",
        "aspic_analysis",
        "counter",
        "jtms",
        "debate",
        "atms",
        "governance",
        "formal_synthesis",
        "narrative_synthesis",
    }

    def test_phase_count_is_17(self):
        wf = build_spectacular_workflow()
        assert len(wf.phases) == 17

    def test_all_expected_phases_present(self):
        wf = build_spectacular_workflow()
        assert {p.name for p in wf.phases} == self.EXPECTED_PHASES

    def test_dag_validates_clean(self):
        wf = build_spectacular_workflow()
        assert wf.validate() == []

    def test_execution_order_has_6_levels(self):
        wf = build_spectacular_workflow()
        levels = wf.get_execution_order()
        assert len(levels) == 6

    def test_extract_is_sole_entry_point(self):
        wf = build_spectacular_workflow()
        levels = wf.get_execution_order()
        assert levels[0] == ["extract"]

    def test_l1_parallel_phases(self):
        wf = build_spectacular_workflow()
        levels = wf.get_execution_order()
        assert set(levels[1]) == {
            "hierarchical_fallacy",
            "neural_detect",
            "nl_to_logic",
            "quality",
        }

    def test_l2_includes_formal_logic_and_counter(self):
        wf = build_spectacular_workflow()
        levels = wf.get_execution_order()
        assert {"fol", "modal", "pl"}.issubset(set(levels[2]))
        assert "counter" in levels[2]

    def test_counter_depends_on_quality(self):
        wf = build_spectacular_workflow()
        counter = wf.get_phase("counter")
        assert "quality" in counter.depends_on

    def test_atms_depends_on_jtms(self):
        wf = build_spectacular_workflow()
        atms = wf.get_phase("atms")
        assert "jtms" in atms.depends_on

    def test_formal_synthesis_terminal(self):
        wf = build_spectacular_workflow()
        synth = wf.get_phase("formal_synthesis")
        assert "fol" in synth.depends_on
        assert "modal" in synth.depends_on
        assert "aspic_analysis" in synth.depends_on
        levels = wf.get_execution_order()
        assert "formal_synthesis" in levels[-1]

    @pytest.mark.asyncio
    async def test_all_16_phases_complete(self):
        wf = build_spectacular_workflow()
        results, state = await _execute_workflow(wf)
        completed = [r for r in results.values() if r.status == PhaseStatus.COMPLETED]
        assert len(completed) == 17

    @pytest.mark.asyncio
    async def test_no_failed_phases(self):
        wf = build_spectacular_workflow()
        results, _ = await _execute_workflow(wf)
        failed = [r for r in results.values() if r.status == PhaseStatus.FAILED]
        assert failed == []

    @pytest.mark.asyncio
    async def test_state_populated_extracts(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.extracts) >= 2

    @pytest.mark.asyncio
    async def test_state_populated_arguments(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.identified_arguments) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_fallacies(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.identified_fallacies) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_quality(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.argument_quality_scores) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_counter(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.counter_arguments) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_jtms(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.jtms_beliefs) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_atms(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.atms_contexts) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_debate(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.debate_transcripts) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_governance(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.governance_decisions) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_dung(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.dung_frameworks) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_aspic(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.aspic_results) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_formal_synthesis(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.formal_synthesis_reports) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_pl(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.propositional_analysis_results) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_fol(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.fol_analysis_results) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_modal(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.modal_analysis_results) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_nl_to_logic(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.nl_to_logic_translations) >= 1

    @pytest.mark.asyncio
    async def test_state_populated_neural_fallacy(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.neural_fallacy_scores) >= 1

    @pytest.mark.asyncio
    async def test_state_field_coverage_minimum_15(self):
        """At least 15 distinct state fields should be populated."""
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        snapshot = state.get_state_snapshot(summarize=True)
        populated = sum(
            1 for k, v in snapshot.items() if isinstance(v, (int, float)) and v > 0
        )
        assert populated >= 15

    @pytest.mark.asyncio
    async def test_workflow_results_stored_in_state(self):
        wf = build_spectacular_workflow()
        _, state = await _execute_workflow(wf)
        assert "spectacular_analysis" in state.workflow_results
        wf_data = state.workflow_results["spectacular_analysis"]
        assert wf_data["completed"] == 17
        assert wf_data["failed"] == 0


# ── Sherlock Modern Workflow Golden Tests ────────────────────────────────────


class TestSherlockModernWorkflowGolden:
    """Golden regression tests for build_sherlock_modern_workflow()."""

    EXPECTED_PHASES = {
        "extract",
        "hierarchical_fallacy",
        "quality",
        "counter",
        "jtms",
        "atms",
        "narrative_synthesis",
    }

    def test_workflow_builds(self):
        wf = build_sherlock_modern_workflow()
        assert wf is not None
        assert wf.name == "sherlock_modern"

    def test_phase_count_is_7(self):
        wf = build_sherlock_modern_workflow()
        assert len(wf.phases) == 7

    def test_all_expected_phases_present(self):
        wf = build_sherlock_modern_workflow()
        assert {p.name for p in wf.phases} == self.EXPECTED_PHASES

    def test_dag_validates_clean(self):
        wf = build_sherlock_modern_workflow()
        assert wf.validate() == []

    def test_execution_order_6_levels(self):
        wf = build_sherlock_modern_workflow()
        levels = wf.get_execution_order()
        assert len(levels) == 6
        assert levels[0] == ["extract"]
        assert set(levels[1]) == {"hierarchical_fallacy", "quality"}

    def test_dependency_chain(self):
        wf = build_sherlock_modern_workflow()
        assert wf.get_phase("extract").depends_on == []
        assert "extract" in wf.get_phase("hierarchical_fallacy").depends_on
        assert "extract" in wf.get_phase("quality").depends_on
        assert "quality" in wf.get_phase("counter").depends_on
        assert "counter" in wf.get_phase("jtms").depends_on
        assert "jtms" in wf.get_phase("atms").depends_on
        assert "atms" in wf.get_phase("narrative_synthesis").depends_on

    def test_capabilities_match_phases(self):
        wf = build_sherlock_modern_workflow()
        caps = wf.get_required_capabilities()
        assert "fact_extraction" in caps
        assert "belief_maintenance" in caps
        assert "narrative_synthesis" in caps

    @pytest.mark.asyncio
    async def test_all_7_phases_complete(self):
        wf = build_sherlock_modern_workflow()
        results, state = await _execute_workflow(wf)
        completed = [r for r in results.values() if r.status == PhaseStatus.COMPLETED]
        assert len(completed) == 7

    @pytest.mark.asyncio
    async def test_no_failed_phases(self):
        wf = build_sherlock_modern_workflow()
        results, _ = await _execute_workflow(wf)
        failed = [r for r in results.values() if r.status == PhaseStatus.FAILED]
        assert failed == []

    @pytest.mark.asyncio
    async def test_state_populated_after_execution(self):
        wf = build_sherlock_modern_workflow()
        _, state = await _execute_workflow(wf)
        assert len(state.extracts) >= 1
        assert len(state.identified_arguments) >= 1
        assert len(state.counter_arguments) >= 1
        assert len(state.jtms_beliefs) >= 1
        assert len(state.atms_contexts) >= 1

    @pytest.mark.asyncio
    async def test_workflow_results_stored(self):
        wf = build_sherlock_modern_workflow()
        _, state = await _execute_workflow(wf)
        assert "sherlock_modern" in state.workflow_results


# ── Catalog Registration Golden Tests ────────────────────────────────────────


class TestWorkflowCatalogGolden:
    """Golden tests ensuring workflows register in catalog."""

    def test_catalog_includes_spectacular(self):
        catalog = get_workflow_catalog()
        assert "spectacular" in catalog
        assert catalog["spectacular"].name == "spectacular_analysis"
        assert len(catalog["spectacular"].phases) == 17

    def test_catalog_includes_sherlock_modern(self):
        catalog = get_workflow_catalog()
        assert "sherlock_modern" in catalog
        assert catalog["sherlock_modern"].name == "sherlock_modern"
        assert len(catalog["sherlock_modern"].phases) == 7

    def test_spectacular_is_among_largest(self):
        catalog = get_workflow_catalog()
        spectacular_count = len(catalog["spectacular"].phases)
        assert spectacular_count >= 16
        largest = max(len(wf.phases) for wf in catalog.values())
        assert spectacular_count >= largest - 2

    def test_catalog_workflow_names_unique(self):
        catalog = get_workflow_catalog()
        names = [wf.name for wf in catalog.values()]
        assert len(names) == len(set(names)), f"Duplicate workflow names: {names}"
