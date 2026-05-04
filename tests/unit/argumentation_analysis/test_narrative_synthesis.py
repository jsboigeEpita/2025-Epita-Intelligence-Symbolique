"""Tests for narrative synthesis (#351).

Validates that build_narrative produces 1-2 readable paragraphs referencing
at least 5 distinct state fields, and that the pipeline integration works.
"""

import asyncio
import pytest

from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    build_narrative,
    NarrativeSynthesisPlugin,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_narrative_synthesis_to_state,
    CAPABILITY_STATE_WRITERS,
)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _rich_state() -> UnifiedAnalysisState:
    """Create a state with data from multiple analysis phases."""
    state = UnifiedAnalysisState("Test discourse for analysis.")

    # Quality
    state.add_quality_score("arg_1", {"clarte": 4.0, "coherence": 3.5}, 3.8)
    state.add_quality_score("arg_2", {"clarte": 2.0, "pertinence": 2.5}, 2.2)

    # Fallacies
    state.add_fallacy("ad_hominem", "Attack on person", "arg_1")
    state.add_fallacy("straw_man", "Distortion", "arg_2")

    # Counter-arguments
    state.add_counter_argument("arg_1", "Counter via reductio", "reductio", 0.7)

    # JTMS
    state.add_jtms_belief("premise_A", True, justifications=[])
    state.add_jtms_belief("premise_B", False, justifications=["retracted"])
    state.jtms_retraction_chain = [
        {
            "trigger": "premise_B",
            "retracted": ["premise_B"],
            "cascaded": ["claim_X"],
            "reason": "inconsistency",
        }
    ]

    # ATMS
    state.atms_contexts = [
        {"hypothesis_id": "h_full", "coherent": False, "assumptions": ["a", "b"]},
        {"hypothesis_id": "h_skeptical", "coherent": True, "assumptions": ["a"]},
    ]

    # Dung
    state.dung_frameworks = {
        "framework_1": {
            "extensions": [["arg_1"], ["arg_2"]],
            "attacks": [["arg_1", "arg_2"]],
        }
    }

    # Formal logic
    state.fol_analysis_results = [{"query": "consistency", "result": "UNSAT"}]
    state.propositional_analysis_results = [{"satisfiable": False}]

    return state


class TestBuildNarrative:
    """Tests for build_narrative function."""

    def test_produces_non_empty_string(self):
        state = _rich_state()
        result = build_narrative(state)
        assert isinstance(result, str)
        assert len(result) > 50

    def test_references_quality(self):
        state = _rich_state()
        result = build_narrative(state)
        assert "qualite" in result.lower() or "evaluation" in result.lower()

    def test_references_fallacies(self):
        state = _rich_state()
        result = build_narrative(state)
        assert "sophisme" in result.lower()

    def test_references_jtms(self):
        state = _rich_state()
        result = build_narrative(state)
        assert "jtms" in result.lower() or "croyance" in result.lower()

    def test_references_atms(self):
        state = _rich_state()
        result = build_narrative(state)
        assert "atms" in result.lower() or "hypothese" in result.lower()

    def test_references_counter_arguments(self):
        state = _rich_state()
        result = build_narrative(state)
        assert "contre-argument" in result.lower() or "contestat" in result.lower()

    def test_at_least_5_distinct_references(self):
        state = _rich_state()
        result = build_narrative(state)
        keywords = [
            "qualite",
            "sophisme",
            "croyance",
            "hypothese",
            "contre-argument",
            "dung",
            "logique",
            "jtms",
            "atms",
            "retraction",
            "extension",
        ]
        found = sum(1 for kw in keywords if kw in result.lower())
        assert found >= 5, f"Only {found} references found in: {result[:200]}"

    def test_readable_prose_not_json(self):
        state = _rich_state()
        result = build_narrative(state)
        assert not result.startswith("{")
        assert not result.startswith("[")
        assert '{"' not in result
        assert "': " not in result

    def test_max_2_paragraphs(self):
        state = _rich_state()
        result = build_narrative(state)
        paragraphs = [p for p in result.split("\n\n") if p.strip()]
        assert len(paragraphs) <= 2

    def test_empty_state_gives_fallback(self):
        state = UnifiedAnalysisState("empty")
        result = build_narrative(state)
        assert isinstance(result, str)
        assert len(result) > 0
        assert "partielles" in result.lower()

    def test_only_quality(self):
        state = UnifiedAnalysisState("test")
        state.add_quality_score("arg_1", {"clarte": 4}, 4.0)
        result = build_narrative(state)
        assert "qualite" in result.lower() or "evaluation" in result.lower()
        assert "argument" in result.lower()


class TestNarrativeSynthesisPlugin:
    """Tests for the SK plugin wrapper."""

    def test_plugin_synthesize(self):
        plugin = NarrativeSynthesisPlugin()
        import json

        state_dict = {
            "argument_quality_scores": {"arg_1": {"overall": 3.5}},
            "identified_fallacies": {"f_1": {"type": "ad_hominem"}},
        }
        result = plugin.synthesize(json.dumps(state_dict))
        assert isinstance(result, str)
        assert len(result) > 0


class TestNarrativeStateWriter:
    """Tests for state writer integration."""

    def test_narrative_stored_in_state(self):
        state = UnifiedAnalysisState("test")
        output = {"narrative": "This is the synthesis paragraph.", "paragraph_count": 1}
        _write_narrative_synthesis_to_state(output, state, {})
        assert state.narrative_synthesis == "This is the synthesis paragraph."

    def test_empty_output_no_crash(self):
        state = UnifiedAnalysisState("test")
        _write_narrative_synthesis_to_state(None, state, {})
        assert state.narrative_synthesis == ""

    def test_capability_registered(self):
        assert "narrative_synthesis" in CAPABILITY_STATE_WRITERS
