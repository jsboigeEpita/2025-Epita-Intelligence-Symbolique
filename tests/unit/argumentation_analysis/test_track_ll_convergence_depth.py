"""Tests for Track LL — JTMS convergence depth wiring fix (#656).

Root-cause investigation summary:
- compute_argument_convergence signal 4 (JTMS) checked ``arg_id in belief_name``
  where belief_name was a raw text excerpt.  ``arg_id`` strings ("arg_1" etc.)
  almost never appear in argument text, so the JTMS signal was a dead letter for
  every corpus.
- Fix: _invoke_jtms now names arg beliefs "arg_N:<text_excerpt[:66]>" so
  compute_argument_convergence's startswith check ``name.startswith("arg_N:")``
  fires correctly when a belief is retracted.

Tests cover:
1. JTMS signal fires when a belief prefixed with "arg_N:" is retracted
2. No false positives from defeat beliefs or ATMS entries
3. Fallback-sentence arg beliefs also carry the prefix
4. _invoke_jtms output keys carry the prefix (integration with state writers)
5. Convergence depth ≥3 achievable: fallacy + quality + JTMS for the same arg
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock

from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    compute_argument_convergence,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_JTMS_WEAK_THRESHOLD = 5.0  # from QUALITY_WEAK_THRESHOLD in plugin


def _state_with_jtms_retracted(arg_id: str, belief_text: str) -> SimpleNamespace:
    """Minimal state: one arg, one retracted JTMS belief using the new naming."""
    return SimpleNamespace(
        identified_arguments={arg_id: "Some argument description"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={
            "jtms_0001": {
                "name": f"{arg_id}:{belief_text[:66]}",
                "valid": False,
                "justifications": [],
            }
        },
        dung_frameworks={},
    )


def _state_with_jtms_valid(arg_id: str, belief_text: str) -> SimpleNamespace:
    """State: JTMS belief present but still valid (should NOT trigger signal)."""
    return SimpleNamespace(
        identified_arguments={arg_id: "Some argument"},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        jtms_beliefs={
            "jtms_0001": {
                "name": f"{arg_id}:{belief_text[:66]}",
                "valid": True,
                "justifications": [],
            }
        },
        dung_frameworks={},
    )


# ---------------------------------------------------------------------------
# JTMS signal tests
# ---------------------------------------------------------------------------


class TestJTMSConvergenceSignal:
    """compute_argument_convergence — JTMS signal (signal 4)."""

    def test_jtms_signal_fires_for_retracted_prefixed_belief(self):
        """Belief 'arg_1:...' with valid=False → JTMS signal fires."""
        state = _state_with_jtms_retracted("arg_1", "The policy increases inequality")
        result = compute_argument_convergence(state)
        assert "arg_1" in result
        methods = [m for m, _ in result["arg_1"]["signals"]]
        assert "JTMS retracte" in methods

    def test_jtms_signal_absent_when_valid(self):
        """Belief valid=True → JTMS signal should NOT fire."""
        state = _state_with_jtms_valid("arg_1", "The policy increases inequality")
        result = compute_argument_convergence(state)
        if "arg_1" in result:
            methods = [m for m, _ in result["arg_1"]["signals"]]
            assert "JTMS retracte" not in methods

    def test_jtms_no_false_positive_defeat_belief(self):
        """Defeat belief 'defeat:fallacy→arg_1:...' should NOT match arg_1 signal."""
        state = SimpleNamespace(
            identified_arguments={"arg_1": "Some argument"},
            identified_fallacies={},
            argument_quality_scores={},
            counter_arguments=[],
            jtms_beliefs={
                "jtms_d1": {
                    # Defeat belief: name starts with "defeat:", not "arg_1:"
                    "name": "defeat:ad_hominem→arg_1:The policy inc",
                    "valid": False,
                    "justifications": [],
                }
            },
            dung_frameworks={},
        )
        result = compute_argument_convergence(state)
        # No JTMS signal because the defeat belief does NOT start with "arg_1:"
        if "arg_1" in result:
            methods = [m for m, _ in result["arg_1"]["signals"]]
            assert "JTMS retracte" not in methods

    def test_jtms_no_false_positive_other_arg_in_text(self):
        """Belief 'arg_2:... mentions arg_1 ...' should NOT match arg_1."""
        state = SimpleNamespace(
            identified_arguments={"arg_1": "A", "arg_2": "B"},
            identified_fallacies={},
            argument_quality_scores={},
            counter_arguments=[],
            jtms_beliefs={
                "jtms_0001": {
                    # arg_2's belief text happens to mention "arg_1"
                    "name": "arg_2:The argument against arg_1 positio",
                    "valid": False,
                    "justifications": [],
                }
            },
            dung_frameworks={},
        )
        result = compute_argument_convergence(state)
        # arg_1 should NOT get a JTMS signal (belief starts with "arg_2:")
        if "arg_1" in result:
            methods = [m for m, _ in result["arg_1"]["signals"]]
            assert "JTMS retracte" not in methods
        # arg_2 SHOULD get the JTMS signal
        assert "arg_2" in result
        assert "JTMS retracte" in [m for m, _ in result["arg_2"]["signals"]]

    def test_jtms_no_false_positive_atms_belief(self):
        """ATMS:name beliefs should not match any arg_id."""
        state = SimpleNamespace(
            identified_arguments={"arg_1": "A"},
            identified_fallacies={},
            argument_quality_scores={},
            counter_arguments=[],
            jtms_beliefs={
                "jtms_a1": {
                    "name": "ATMS:node_0",
                    "valid": False,
                    "justifications": [],
                },
                "jtms_a2": {
                    "name": "ATMS:summary",
                    "valid": True,
                    "justifications": [],
                },
            },
            dung_frameworks={},
        )
        result = compute_argument_convergence(state)
        if "arg_1" in result:
            methods = [m for m, _ in result["arg_1"]["signals"]]
            assert "JTMS retracte" not in methods


# ---------------------------------------------------------------------------
# Convergence depth ≥3 with JTMS fix
# ---------------------------------------------------------------------------


class TestConvergenceDepthImprovement:
    """After fix: fallacy + quality + JTMS = convergence ≥3 for same arg."""

    def test_three_signals_achievable_with_jtms(self):
        """Combining fallacy + quality + JTMS produces score ≥3 for arg_1."""
        state = UnifiedAnalysisState("Test discourse.")
        state.add_argument("A rhetorically weak argument with low quality.")

        # Signal 1: fallacy targeting arg_1
        state.add_fallacy("ad_hominem", "Attacks the person, not the idea.", "arg_1")

        # Signal 2: low quality score
        state.add_quality_score("arg_1", {"clarte": 1.5, "coherence": 2.0}, 1.8)

        # Signal 4: JTMS belief retracted — using the new "arg_N:..." naming
        state.add_jtms_belief(
            "arg_1:A rhetorically weak argument with low",
            valid=False,
            justifications=["FALLACY:ad_hominem retracted it"],
        )

        result = compute_argument_convergence(state)
        assert "arg_1" in result
        score = result["arg_1"]["score"]
        assert score >= 3, f"Expected convergence ≥3, got {score}"
        methods = [m for m, _ in result["arg_1"]["signals"]]
        assert "sophisme" in methods
        assert "qualite faible" in methods
        assert "JTMS retracte" in methods

    def test_four_signals_achievable_with_jtms_and_dung(self):
        """fallacy + quality + JTMS + Dung = convergence ≥4."""
        state = UnifiedAnalysisState("Multi-signal test discourse.")
        state.add_argument("A weak argument.")

        state.add_fallacy("straw_man", "Distorts the position.", "arg_1")
        state.add_quality_score("arg_1", {"clarte": 2.0}, 2.0)
        state.add_jtms_belief(
            "arg_1:A weak argument.",
            valid=False,
            justifications=["retracted by fallacy"],
        )
        state.add_dung_framework(
            "test_af",
            arguments=["fallacy_straw_man", "arg_1"],
            attacks=[["fallacy_straw_man", "arg_1"]],
            extensions={"grounded": ["fallacy_straw_man"]},
        )

        result = compute_argument_convergence(state)
        assert "arg_1" in result
        assert result["arg_1"]["score"] >= 4


# ---------------------------------------------------------------------------
# _invoke_jtms output key naming
# ---------------------------------------------------------------------------


class TestInvokeJTMSBeliefNaming:
    """Verify _invoke_jtms output uses "arg_N:..." keys for arg beliefs."""

    async def test_arg_beliefs_carry_prefix(self):
        """Arg beliefs in output dict start with 'arg_N:' prefix."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument text"},
                    {"text": "Second argument text"},
                ],
                "claims": [],
            }
        }
        result = await _invoke_jtms("input", context)

        assert "arg_1:First argument text" in result["beliefs"]
        assert "arg_2:Second argument text" in result["beliefs"]

    async def test_retracted_belief_carries_prefix(self):
        """Retracted arg belief key starts with 'arg_N:' after fallacy retraction."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "A biased argument"}],
                "claims": [],
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [{"fallacy_type": "bias", "explanation": "biased"}]
            },
        }
        result = await _invoke_jtms("input", context)

        # The arg belief must use the new prefixed naming
        belief_key = "arg_1:A biased argument"
        assert belief_key in result["beliefs"]
        assert result["beliefs"][belief_key]["valid"] is False

    async def test_claim_beliefs_unchanged(self):
        """Claim beliefs do NOT get the arg_N prefix — only arg beliefs do."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [{"text": "Premise one"}],
                "claims": [{"text": "Conclusion statement"}],
            }
        }
        result = await _invoke_jtms("input", context)

        # Claims are not prefixed
        assert "Conclusion statement" in result["beliefs"]
        # Arg IS prefixed
        assert "arg_1:Premise one" in result["beliefs"]

    async def test_sentence_fallback_beliefs_carry_prefix(self):
        """When no args from upstream, sentence-split beliefs are also prefixed."""
        from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms

        context = {"phase_extract_output": {"arguments": [], "claims": []}}
        text = "First sentence here. Second sentence here."
        result = await _invoke_jtms(text, context)

        # At least one belief should carry the arg_N: prefix
        prefixed = [k for k in result["beliefs"] if k.startswith("arg_")]
        assert len(prefixed) >= 1
