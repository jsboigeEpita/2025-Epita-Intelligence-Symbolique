"""Tests for DeepSynthesisAgent — 9-section template-driven synthesis.

Tests use a fixture UnifiedAnalysisState with data covering all 9 sections.
No real LLM calls — pure template logic verification.

Agent instantiation is NOT tested directly (requires real SK kernel).
Section builders are tested via static method calls on the class.
"""

import asyncio
import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)
from argumentation_analysis.agents.core.synthesis.deep_synthesis_models import (
    DeepSynthesisReport,
    SourceOverview,
    ArgumentMapEntry,
    FallacyDiagnosis,
    FormalFinding,
    DungStructure,
    BeliefRetraction,
    CounterArgumentEntry,
    CrossTextParallel,
)


def _make_fixture_state() -> UnifiedAnalysisState:
    """Build a fixture state with data in every analysis dimension."""
    state = UnifiedAnalysisState(
        "The speaker argues that national sovereignty requires immediate action. "
        "They claim that foreign powers threaten our independence. "
        "However, the evidence shows cooperation yields better outcomes. "
        "We must defend our borders against external interference."
    )

    # Arguments (Section 2)
    state.add_argument("National sovereignty requires immediate action")
    state.add_argument("Foreign powers threaten our independence")
    state.add_argument("Cooperation yields better outcomes")
    state.add_argument("We must defend our borders against external interference")

    # Fallacies (Section 3)
    state.add_fallacy(
        "ad hominem",
        "Attacks foreign powers instead of addressing the argument",
        "arg_1",
    )
    state.add_fallacy(
        "slippery slope",
        "Suggests sovereignty loss without evidence of causal chain",
        "arg_2",
    )

    # Belief sets + query log (Section 4)
    state.add_belief_set("propositional", "p => q\np")
    state.query_log.append({
        "log_id": "log_1",
        "belief_set_id": "bs_1",
        "query": "q",
        "raw_result": "ENTAILMENT: q is entailed",
    })

    # Propositional analysis (Section 4)
    state.propositional_analysis_results.append({
        "axioms": ["p => q", "p"],
        "queries": ["q"],
        "results": ["q is entailed"],
        "inconsistency_measures": {"drastic": 0},
        "linked_args": ["arg_1"],
    })

    # Dung framework (Section 5)
    state.add_dung_framework(
        name="main_framework",
        arguments=["arg_1", "arg_2", "arg_3", "arg_4"],
        attacks=[["arg_3", "arg_1"], ["arg_3", "arg_2"]],
        extensions={
            "grounded": ["arg_3", "arg_4"],
            "preferred": [["arg_3", "arg_4"]],
            "stable": [["arg_3", "arg_4"]],
        },
    )

    # JTMS beliefs + retractions (Section 6)
    state.add_jtms_belief("sovereignty_threatened", True, ["arg_1 supports"])
    state.jtms_retraction_chain.append({
        "belief_name": "sovereignty_threatened",
        "was_valid": True,
        "trigger": "Contradicted by cooperation evidence (arg_3)",
    })

    # Counter-arguments (Section 7)
    state.add_counter_argument(
        original_arg="Foreign powers threaten our independence",
        counter_content="Historical data shows alliances strengthen sovereignty",
        strategy="counter-example",
        score=8.5,
    )

    # Quality scores (for weakest-arg detection in Section 7)
    state.add_quality_score("arg_1", {"clarity": 6.0, "relevance": 4.0}, 5.0)
    state.add_quality_score("arg_2", {"clarity": 3.0, "relevance": 2.0}, 2.5)

    return state


def _build_report_from_state(state, meta=None):
    """Build a full report using static method calls (no agent instantiation)."""
    Cls = DeepSynthesisAgent
    meta = meta or {}
    report = DeepSynthesisReport(
        source_overview=Cls._build_source_overview(state, meta),
        argument_map=Cls._build_argument_map(state),
        fallacy_diagnoses=Cls._build_fallacy_diagnoses(state),
        formal_findings=Cls._build_formal_findings(state),
        dung_structure=Cls._build_dung_structure(state),
        belief_retractions=Cls._build_belief_retractions(state),
        counter_arguments=Cls._build_counter_arguments(state),
        cross_text_parallels=Cls._build_cross_text_parallels(state),
    )
    report.final_synthesis = asyncio.get_event_loop().run_until_complete(
        Cls._build_final_synthesis(state, report, [])
    )
    report.total_state_fields = Cls._count_state_fields(state)
    report.sections_populated = Cls._count_populated_sections(report)
    return report


# =========================================================================
# Test: Helpers
# =========================================================================

class TestHelpers:

    def test_infer_stance_pro(self):
        assert DeepSynthesisAgent._infer_stance("I support this proposal") == "pro"

    def test_infer_stance_con(self):
        assert DeepSynthesisAgent._infer_stance("We must oppose this") == "con"

    def test_infer_stance_neutral(self):
        assert DeepSynthesisAgent._infer_stance("The data shows X") == "neutral"

    def test_fallacy_family(self):
        assert DeepSynthesisAgent._fallacy_family("ad hominem attack") == "relevance"
        assert DeepSynthesisAgent._fallacy_family("hasty generalization") == "inductive"
        assert DeepSynthesisAgent._fallacy_family("slippery slope") == "causal"
        assert DeepSynthesisAgent._fallacy_family("straw man") == "presumption"
        assert DeepSynthesisAgent._fallacy_family("unknown thing") == "other"

    def test_count_populated_sections_empty(self):
        report = DeepSynthesisReport()
        assert DeepSynthesisAgent._count_populated_sections(report) == 0

    def test_count_populated_sections_partial(self):
        report = DeepSynthesisReport()
        report.source_overview = SourceOverview(length_chars=100)
        report.argument_map = [ArgumentMapEntry(arg_id="a1", stance="pro", description="test")]
        assert DeepSynthesisAgent._count_populated_sections(report) == 2

    def test_count_state_fields(self):
        state = _make_fixture_state()
        count = DeepSynthesisAgent._count_state_fields(state)
        assert count > 0  # at least args + fallacies + beliefs


# =========================================================================
# Test: Section builders (1–9)
# =========================================================================

class TestSectionBuilders:

    @pytest.fixture
    def state(self):
        return _make_fixture_state()

    def test_s1_source_overview(self, state):
        meta = {
            "opaque_id": "corpus_dense_A",
            "era": "2020-2025",
            "language": "en",
            "discourse_type": "populist",
        }
        so = DeepSynthesisAgent._build_source_overview(state, meta)
        assert so.opaque_id == "corpus_dense_A"
        assert so.language == "en"
        assert so.discourse_type == "populist"
        assert so.length_chars > 0
        assert so.length_words > 0
        assert "corpus_dense_A" in so.contextual_frame

    def test_s2_argument_map(self, state):
        amap = DeepSynthesisAgent._build_argument_map(state)
        assert len(amap) == 4
        for entry in amap:
            assert entry.arg_id.startswith("arg_")
            assert entry.stance in ("pro", "con", "neutral")

    def test_s3_fallacy_diagnoses(self, state):
        diags = DeepSynthesisAgent._build_fallacy_diagnoses(state)
        assert len(diags) == 2
        for d in diags:
            assert d.taxonomy_path.startswith("fallacy/")
            assert len(d.impacted_args) > 0

    def test_s4_formal_findings(self, state):
        findings = DeepSynthesisAgent._build_formal_findings(state)
        assert len(findings) >= 1
        pl_findings = [f for f in findings if f.logic_type == "PL"]
        assert len(pl_findings) >= 1
        assert len(pl_findings[0].axioms) > 0

    def test_s5_dung_structure(self, state):
        dung = DeepSynthesisAgent._build_dung_structure(state)
        assert len(dung.arguments) == 4
        assert len(dung.attacks) == 2
        assert len(dung.grounded_extension) == 2
        assert "arg_3" in dung.grounded_extension
        assert len(dung.interpretation) > 0

    def test_s6_belief_retractions(self, state):
        retractions = DeepSynthesisAgent._build_belief_retractions(state)
        assert len(retractions) == 1
        assert retractions[0].belief_name == "sovereignty_threatened"

    def test_s7_counter_arguments(self, state):
        cas = DeepSynthesisAgent._build_counter_arguments(state)
        assert len(cas) == 1
        assert cas[0].score == 8.5
        assert cas[0].strategy == "counter-example"

    def test_s8_cross_text_parallels_empty(self, state):
        parallels = DeepSynthesisAgent._build_cross_text_parallels(state)
        assert parallels == []

    def test_s9_final_synthesis(self, state):
        report = _build_report_from_state(state)
        assert len(report.final_synthesis) > 100
        assert "argument" in report.final_synthesis.lower()


# =========================================================================
# Test: Markdown rendering
# =========================================================================

class TestMarkdownRendering:

    def test_render_full_report(self):
        state = _make_fixture_state()
        meta = {"opaque_id": "test_corpus", "era": "2020s", "language": "en", "discourse_type": "populist"}
        report = _build_report_from_state(state, meta)

        md = DeepSynthesisAgent.render_markdown(report)

        assert "## 1. Source Overview" in md
        assert "## 2. Argument Map" in md
        assert "## 3. Fallacy Diagnosis" in md
        assert "## 4. Formal-Method Findings" in md
        assert "## 5. Dialectical Structure" in md
        assert "## 6. Belief Revision Trace" in md
        assert "## 7. Counter-Arguments" in md
        assert "## 8. Cross-Text Rhetorical Parallels" in md

    def test_render_minimum_length(self):
        state = _make_fixture_state()
        meta = {"opaque_id": "test_corpus", "era": "2020s", "language": "en", "discourse_type": "populist"}
        report = _build_report_from_state(state, meta)
        md = DeepSynthesisAgent.render_markdown(report)
        assert len(md) >= 1500

    def test_render_empty_state(self):
        state = UnifiedAnalysisState("Short text.")
        report = DeepSynthesisReport(
            source_overview=DeepSynthesisAgent._build_source_overview(state, {}),
        )
        md = DeepSynthesisAgent.render_markdown(report)
        assert "No arguments identified" in md
        assert "No fallacies detected" in md


# =========================================================================
# Test: Invoke callable
# =========================================================================

class TestInvokeCallable:

    def test_invoke_no_state(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_deep_synthesis,
        )
        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", {})
        )
        assert "error" in result

    def test_invoke_with_state(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_deep_synthesis,
        )
        state = _make_fixture_state()
        context = {
            "_state_object": state,
            "source_metadata": {"opaque_id": "test", "era": "2020s", "language": "en", "discourse_type": "populist"},
        }
        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", context)
        )
        assert "report" in result
        assert "markdown" in result
        assert result["sections_populated"] >= 4
        assert "## 1. Source Overview" in result["markdown"]
