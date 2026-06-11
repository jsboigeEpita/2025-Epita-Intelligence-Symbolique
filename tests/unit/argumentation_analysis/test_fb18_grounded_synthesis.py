"""Unit tests for FB-18 Mode A grounded transversal synthesis (#1039).

Covers the four pillars of the FB18_DEEP_SYNTHESIS_SPEC contract:
- VG-2 state-empty guard: _invoke_deep_synthesis fails explicitly when
  fewer than 3 artifact fields are populated (no boilerplate on empty state)
- Artifact briefing: every line carries a verbatim [artifact:...] citation
  key, and the raw discourse text never leaks into the briefing
- Value-gates VG-1/VG-3/VG-4 validation on synthetic synthesis strings
- Result shape: the invoke callable exposes grounded_synthesis_status and
  value_gates honestly (no template output dressed up as grounded)
"""

import asyncio

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)


def _make_fixture_state() -> UnifiedAnalysisState:
    """State with 4 populated artifact fields (arguments, fallacies, dung,
    counter-arguments) — above the VG-2 threshold of 3."""
    state = UnifiedAnalysisState(
        "The speaker argues that national sovereignty requires immediate action. "
        "They claim that foreign powers threaten our independence. "
        "However, the evidence shows cooperation yields better outcomes."
    )
    state.add_argument("National sovereignty requires immediate action")
    state.add_argument("Foreign powers threaten our independence")
    state.add_argument("Cooperation yields better outcomes")
    state.add_fallacy(
        "ad hominem", "Attacks foreign powers instead of argument", "arg_1"
    )
    state.add_fallacy(
        "slippery slope", "Suggests sovereignty loss without evidence", "arg_2"
    )
    state.add_dung_framework(
        name="main_framework",
        arguments=["arg_1", "arg_2", "arg_3"],
        attacks=[["arg_3", "arg_1"], ["arg_3", "arg_2"]],
        extensions={
            "grounded": ["arg_3"],
            "preferred": [["arg_3"]],
            "stable": [["arg_3"]],
        },
    )
    state.add_counter_argument(
        original_arg="Foreign powers threaten our independence",
        counter_content="Historical data shows alliances strengthen sovereignty",
        strategy="counter-example",
        score=8.5,
    )
    return state


# =========================================================================
# VG-2 — state-empty guard (fail-explicit, #1019 fail-loud)
# =========================================================================


class TestVG2StateGuard:

    def test_count_populated_fields_empty_state(self):
        state = UnifiedAnalysisState("some text")
        assert DeepSynthesisAgent.count_populated_artifact_fields(state) == 0

    def test_count_populated_fields_counts_fields_not_entries(self):
        state = UnifiedAnalysisState("some text")
        for i in range(50):
            state.add_argument(f"argument number {i}")
        # 50 arguments still = 1 populated FIELD
        assert DeepSynthesisAgent.count_populated_artifact_fields(state) == 1

    def test_count_populated_fields_fixture(self):
        state = _make_fixture_state()
        assert DeepSynthesisAgent.count_populated_artifact_fields(state) == 4

    def test_invoke_fails_explicit_on_empty_state(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_deep_synthesis,
        )

        state = UnifiedAnalysisState("a short text with no analysis artifacts")
        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", {"_state_object": state})
        )
        assert result.get("fail_explicit") is True
        assert "error" in result
        assert result["populated_artifact_fields"] == 0
        # Crucially: NO markdown boilerplate is produced
        assert "markdown" not in result

    def test_invoke_fails_explicit_below_threshold(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_deep_synthesis,
        )

        state = UnifiedAnalysisState("text")
        state.add_argument("a single argument")
        state.add_fallacy("ad hominem", "justification", "arg_1")
        # 2 populated fields < 3 → fail explicit
        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", {"_state_object": state})
        )
        assert result.get("fail_explicit") is True
        assert result["populated_artifact_fields"] == 2

    def test_invoke_passes_guard_at_threshold(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_deep_synthesis,
        )

        state = _make_fixture_state()
        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", {"_state_object": state})
        )
        assert "error" not in result
        assert result["populated_artifact_fields"] == 4


# =========================================================================
# Artifact briefing — citation keys + no raw-text leakage
# =========================================================================


class TestArtifactBriefing:

    def test_briefing_contains_citation_keys(self):
        state = _make_fixture_state()
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        assert "[artifact:identified_arguments.arg_1]" in briefing
        assert "[artifact:identified_fallacies." in briefing
        assert "[artifact:dung_frameworks." in briefing
        assert "[artifact:counter_arguments." in briefing

    def test_briefing_never_contains_raw_text(self):
        """Privacy + grounding: the LLM sees verified artifacts, not the
        discourse itself."""
        state = _make_fixture_state()
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        assert state.raw_text not in briefing

    def test_briefing_caps_items_per_field(self):
        state = UnifiedAnalysisState("text")
        for i in range(40):
            state.add_argument(f"argument number {i}")
        briefing = DeepSynthesisAgent.build_artifact_briefing(
            state, max_items_per_field=15
        )
        n_arg_lines = briefing.count("[artifact:identified_arguments.")
        assert n_arg_lines == 15

    def test_briefing_keys_match_citation_regex(self):
        """Every key emitted by the briefing must be parseable by the same
        regex the value-gates use — otherwise citations can never validate."""
        state = _make_fixture_state()
        briefing = DeepSynthesisAgent.build_artifact_briefing(state)
        artifact_lines = [
            line for line in briefing.splitlines() if line.startswith("[artifact:")
        ]
        assert artifact_lines, "briefing produced no artifact lines"
        for line in artifact_lines:
            assert DeepSynthesisAgent.CITATION_RE.match(line), line


# =========================================================================
# Value-gates VG-1 / VG-3 / VG-4 on synthetic synthesis strings
# =========================================================================


_GOOD_SYNTHESIS = """## Transversal Patterns

The relevance-family attack [artifact:identified_fallacies.fallacy_1] targets
the same argument that falls outside the grounded extension
[artifact:dung_frameworks.dung_1], a convergence of informal and formal
diagnostics.

## Rhetorical Strategy Assessment

The discourse leans on threat framing [artifact:identified_arguments.arg_2],
which the strongest counter-argument [artifact:counter_arguments.ca_1]
directly undercuts with historical evidence.

## Structural Vulnerabilities

Argument arg_1 is attacked and excluded from the grounded extension
[artifact:dung_frameworks.dung_1]; its supporting fallacy
[artifact:identified_fallacies.fallacy_1] makes it doubly fragile.

## Interpretive Synthesis

Under multi-method scrutiny the sovereignty case rests on contested premises
[artifact:identified_arguments.arg_1] and does not survive dialectical
verification [artifact:dung_frameworks.dung_1].
"""


class TestValueGates:

    def test_good_synthesis_passes_all_gates(self):
        vg = DeepSynthesisAgent.validate_value_gates(
            _GOOD_SYNTHESIS, populated_artifact_fields=4
        )
        assert vg["vg1_citation_density"]["pass"] is True
        assert vg["vg2_state_guard"]["pass"] is True
        assert vg["vg3_no_boilerplate"]["pass"] is True
        assert vg["vg4_transversal_insight"]["pass"] is True
        assert vg["all_pass"] is True

    def test_distinct_fields_cited_reported(self):
        vg = DeepSynthesisAgent.validate_value_gates(
            _GOOD_SYNTHESIS, populated_artifact_fields=4
        )
        distinct = vg["vg1_citation_density"]["distinct_fields_cited"]
        assert "identified_fallacies" in distinct
        assert "dung_frameworks" in distinct
        assert "counter_arguments" in distinct
        assert "identified_arguments" in distinct

    def test_empty_synthesis_fails_content_gates(self):
        vg = DeepSynthesisAgent.validate_value_gates("", populated_artifact_fields=4)
        assert vg["vg1_citation_density"]["pass"] is False
        assert vg["vg2_state_guard"]["pass"] is True  # state itself was fine
        assert vg["vg3_no_boilerplate"]["pass"] is False
        assert vg["vg4_transversal_insight"]["pass"] is False
        assert vg["all_pass"] is False

    def test_vg2_fails_below_threshold(self):
        vg = DeepSynthesisAgent.validate_value_gates(
            _GOOD_SYNTHESIS, populated_artifact_fields=2
        )
        assert vg["vg2_state_guard"]["pass"] is False
        assert vg["all_pass"] is False

    def test_vg3_fails_on_template_without_citations(self):
        template = (
            "## Transversal Patterns\n\nGeneric prose.\n\n"
            "## Rhetorical Strategy Assessment\n\nGeneric prose.\n\n"
            "## Structural Vulnerabilities\n\nGeneric prose.\n\n"
            "## Interpretive Synthesis\n\nGeneric prose without any citation.\n"
        )
        vg = DeepSynthesisAgent.validate_value_gates(
            template, populated_artifact_fields=4
        )
        assert vg["vg3_no_boilerplate"]["pass"] is False

    def test_vg3_fails_on_missing_sections(self):
        partial = (
            "## Transversal Patterns\n\n"
            "Cited insight [artifact:identified_arguments.arg_1].\n"
        )
        vg = DeepSynthesisAgent.validate_value_gates(
            partial, populated_artifact_fields=4
        )
        assert vg["vg3_no_boilerplate"]["pass"] is False

    def test_vg1_fails_on_low_citation_density(self):
        # ~600 words, 1 citation → requires >= 3 citations
        long_text = " ".join(["word"] * 600) + " [artifact:identified_arguments.arg_1]"
        vg = DeepSynthesisAgent.validate_value_gates(
            long_text, populated_artifact_fields=4
        )
        assert vg["vg1_citation_density"]["required_citations"] >= 3
        assert vg["vg1_citation_density"]["pass"] is False

    def test_vg4_fails_when_no_paragraph_spans_two_fields(self):
        single_field = (
            "## Transversal Patterns\n\n"
            "Insight one [artifact:identified_arguments.arg_1].\n\n"
            "## Rhetorical Strategy Assessment\n\n"
            "Insight two [artifact:identified_arguments.arg_2].\n\n"
            "## Structural Vulnerabilities\n\n"
            "Insight three [artifact:identified_arguments.arg_3].\n\n"
            "## Interpretive Synthesis\n\n"
            "Closing [artifact:identified_arguments.arg_1].\n"
        )
        vg = DeepSynthesisAgent.validate_value_gates(
            single_field, populated_artifact_fields=4
        )
        assert vg["vg4_transversal_insight"]["pass"] is False
        assert vg["all_pass"] is False


# =========================================================================
# Result shape — honest grounded_synthesis_status, gates attached
# =========================================================================


class TestInvokeResultShape:

    def test_result_exposes_grounded_fields(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_deep_synthesis,
        )

        state = _make_fixture_state()
        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", {"_state_object": state})
        )
        assert "error" not in result
        assert result["grounded_synthesis_status"] in (
            "llm",
            "unavailable",
            "failed",
        )
        assert "value_gates" in result
        assert result["value_gates"]["vg2_state_guard"]["pass"] is True
        # Without a real LLM key in unit tests the synthesis is empty —
        # the status must say so rather than shipping template output.
        if result["grounded_synthesis_status"] != "llm":
            assert result["grounded_synthesis"] == ""

    def test_report_dict_carries_value_gates(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_deep_synthesis,
        )

        state = _make_fixture_state()
        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", {"_state_object": state})
        )
        report = result["report"]
        assert "grounded_synthesis" in report
        assert "grounded_synthesis_status" in report
        assert "value_gates" in report
        assert report["populated_artifact_fields"] == 4

    def test_markdown_renders_grounded_section_explicitly(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_deep_synthesis,
        )

        state = _make_fixture_state()
        result = asyncio.get_event_loop().run_until_complete(
            _invoke_deep_synthesis("", {"_state_object": state})
        )
        markdown = result["markdown"]
        assert "## Grounded Transversal Synthesis (FB-18)" in markdown
        # Either the grounded synthesis itself, or an explicit unavailability
        # notice — never silent absence.
        if result["grounded_synthesis_status"] != "llm":
            assert "Grounded transversal synthesis" in markdown
