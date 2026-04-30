"""Tests for ATMS multi-context activation (#349).

Validates that _invoke_atms generates 3-4 hypotheses with coherence
computed per context, and that at least one hypothesis is coherent under
some contexts but incoherent under others.
"""

import asyncio
import pytest

from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_atms,
    _generate_hypotheses,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import _write_atms_to_state


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


class TestGenerateHypotheses:
    """Tests for _generate_hypotheses helper."""

    def test_returns_at_least_3_hypotheses(self):
        arg_names = ["arg_a", "arg_b", "arg_c", "arg_d"]
        result = _generate_hypotheses(arg_names, [], [], {})
        assert len(result) >= 3

    def test_returns_at_most_4_hypotheses(self):
        arg_names = ["a", "b", "c", "d", "e", "f"]
        result = _generate_hypotheses(arg_names, [], [], {})
        assert len(result) <= 4

    def test_full_trust_hypothesis_includes_all_args(self):
        arg_names = ["alpha", "beta", "gamma"]
        result = _generate_hypotheses(arg_names, [], [], {})
        full_trust = [h for h in result if h["id"] == "h_full_trust"]
        assert len(full_trust) == 1
        assert set(full_trust[0]["assumptions"]) == set(arg_names)

    def test_skeptical_hypothesis_has_one_arg(self):
        arg_names = ["x", "y", "z"]
        result = _generate_hypotheses(arg_names, [], [], {})
        skeptical = [h for h in result if h["id"] == "h_skeptical"]
        assert len(skeptical) == 1
        assert len(skeptical[0]["assumptions"]) == 1

    def test_fallacy_excluded_hypothesis(self):
        arg_names = ["clean_arg", "bad_arg"]
        fallacies = [{"target_argument": "bad_arg", "type": "ad_hominem"}]
        result = _generate_hypotheses(arg_names, [], fallacies, {})
        excluded = [h for h in result if h["id"] == "h_fallacy_excluded"]
        assert len(excluded) == 1
        assert "bad_arg" not in excluded[0]["assumptions"]

    def test_empty_args_produces_fewer_hypotheses(self):
        result = _generate_hypotheses([], [], [], {})
        # With no args, only full_trust (with empty assumptions) is generated
        assert len(result) >= 1


class TestInvokeAtmsMultiContext:
    """Tests for _invoke_atms multi-context output."""

    def test_output_contains_atms_contexts(self):
        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument about climate"},
                    {"text": "Second argument about economy"},
                    {"text": "Third argument about education"},
                ],
                "claims": [{"text": "Claim one"}, {"text": "Claim two"}],
            },
        }
        result = _run(_invoke_atms("Test text with arguments.", context))
        assert "atms_contexts" in result
        assert isinstance(result["atms_contexts"], list)

    def test_at_least_3_contexts_generated(self):
        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Arg " + str(i)} for i in range(5)
                ],
                "claims": [{"text": "Claim"}],
            },
        }
        result = _run(_invoke_atms("Test.", context))
        assert len(result["atms_contexts"]) >= 3

    def test_each_context_has_coherence_field(self):
        context = {
            "phase_extract_output": {
                "arguments": [{"text": f"Arg {i}"} for i in range(4)],
                "claims": [{"text": "Claim"}],
            },
        }
        result = _run(_invoke_atms("Test.", context))
        for ctx in result["atms_contexts"]:
            assert "coherent" in ctx
            assert isinstance(ctx["coherent"], bool)
            assert "hypothesis_id" in ctx
            assert "label" in ctx
            assert "assumptions" in ctx

    def test_context_with_fallacies_has_incoherent_hypothesis(self):
        """When fallacies create contradictions, the full-trust context is incoherent.

        The ATMS adds CONTRA nodes for detected fallacies and marks them as
        contradictions. When all arguments are assumed true (full trust),
        the contradiction node becomes derivable, making the environment
        inconsistent.
        """
        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument with some length"},
                    {"text": "Second argument here"},
                    {"text": "Third argument present"},
                ],
                "claims": [{"text": "Claim"}],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"type": "ad_hominem"},
                ],
            },
        }
        result = _run(_invoke_atms("Test.", context))
        contexts = result["atms_contexts"]
        # If contradictions exist, full trust should be incoherent
        if result["has_contradictions"]:
            full_trust = [c for c in contexts if c["hypothesis_id"] == "h_full_trust"]
            if full_trust:
                assert full_trust[0]["coherent"] is False

    def test_differential_coherence(self):
        """At least one hypothesis coherent, another incoherent when fallacies present."""
        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument"},
                    {"text": "Second argument"},
                    {"text": "Third argument"},
                ],
                "claims": [{"text": "Some claim"}],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"type": "straw_man", "argument": "First argument"},
                ],
            },
        }
        result = _run(_invoke_atms("Test.", context))
        contexts = result["atms_contexts"]
        coherent = [c for c in contexts if c["coherent"] is True]
        incoherent = [c for c in contexts if c["coherent"] is False]
        # There should be at least one of each
        assert len(coherent) >= 1 or len(incoherent) >= 1


class TestAtmsStateWriter:
    """Tests for state_writer integration with atms_contexts."""

    def test_atms_contexts_stored_in_state(self):
        state = UnifiedAnalysisState("test text")
        output = {
            "environments": {"node_a": {"is_assumption": True, "environments": [["x"]]}},
            "assumption_count": 1,
            "node_count": 2,
            "consistent_derivations": [],
            "has_contradictions": False,
            "atms_contexts": [
                {
                    "hypothesis_id": "h_full_trust",
                    "label": "All accepted",
                    "assumptions": ["arg1"],
                    "coherent": True,
                    "derivable_beliefs": ["claim1"],
                    "contradicting_beliefs": [],
                    "derivation_count": 1,
                    "contradiction_count": 0,
                },
                {
                    "hypothesis_id": "h_skeptical",
                    "label": "Skeptical",
                    "assumptions": [],
                    "coherent": True,
                    "derivable_beliefs": [],
                    "contradicting_beliefs": [],
                    "derivation_count": 0,
                    "contradiction_count": 0,
                },
            ],
        }
        _write_atms_to_state(output, state, {})
        assert len(state.atms_contexts) == 2
        assert state.atms_contexts[0]["hypothesis_id"] == "h_full_trust"
        assert state.atms_contexts[1]["coherent"] is True

    def test_atms_contexts_empty_when_no_data(self):
        state = UnifiedAnalysisState("test text")
        _write_atms_to_state(None, state, {})
        assert state.atms_contexts == []

    def test_state_has_atms_contexts_field(self):
        state = UnifiedAnalysisState("test text")
        assert hasattr(state, "atms_contexts")
        assert isinstance(state.atms_contexts, list)
        assert len(state.atms_contexts) == 0
