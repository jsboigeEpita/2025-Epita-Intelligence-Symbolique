"""Tests for Track RR — Lift corpus C convergence depth (grounded >=3).

Root cause: _dung_rejected_args returned {text_string: semantics} while
compute_argument_convergence looks up by canonical arg_id ("arg_1" etc).
Signal 5 (Dung rejection) was a dead letter for all corpora — same pattern
as Track LL (JTMS beliefs named by raw text, never matched by arg_id check).

Fix: _resolve_dung_arg_id maps free-text Dung argument labels back to
canonical arg_ids via direct-ID and text-based matching.
"""

import types
import pytest

from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    _dung_rejected_args,
    _resolve_dung_arg_id,
    compute_argument_convergence,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(
    identified_arguments=None,
    dung_frameworks=None,
    identified_fallacies=None,
    argument_quality_scores=None,
    counter_arguments=None,
    jtms_beliefs=None,
):
    """Build a minimal namespace that looks like UnifiedAnalysisState."""
    ns = types.SimpleNamespace()
    ns.identified_arguments = identified_arguments or {}
    ns.dung_frameworks = dung_frameworks or {}
    ns.identified_fallacies = identified_fallacies or {}
    ns.argument_quality_scores = argument_quality_scores or {}
    ns.counter_arguments = counter_arguments or []
    ns.jtms_beliefs = jtms_beliefs or {}
    return ns


def _framework(arguments, rejected_args, semantics="grounded"):
    """Build a minimal Dung framework dict where rejected_args are absent from extension."""
    accepted = [a for a in arguments if a not in rejected_args]
    return {
        "arguments": arguments,
        "semantics": semantics,
        "extensions": {"all_members": accepted},
    }


# ---------------------------------------------------------------------------
# _resolve_dung_arg_id unit tests
# ---------------------------------------------------------------------------


class TestResolveDungArgId:
    """_resolve_dung_arg_id — text → canonical arg_id mapping."""

    def test_direct_canonical_id_passthrough(self):
        """If arg is already a canonical ID, return it unchanged."""
        identified = {"arg_1": "Some argument text", "arg_2": "Another argument"}
        assert _resolve_dung_arg_id("arg_1", identified) == "arg_1"
        assert _resolve_dung_arg_id("arg_2", identified) == "arg_2"

    def test_exact_text_match(self):
        """Full description match resolves to canonical ID."""
        identified = {"arg_1": "The policy increases unemployment rates."}
        assert (
            _resolve_dung_arg_id("The policy increases unemployment rates.", identified)
            == "arg_1"
        )

    def test_prefix_match(self):
        """When text[:60] == desc[:60], resolves to canonical ID."""
        long_desc = "A" * 80
        identified = {"arg_3": long_desc}
        # Both share the same first-60 chars
        assert _resolve_dung_arg_id("A" * 80, identified) == "arg_3"

    def test_substring_match_text_in_desc(self):
        """text contained within desc resolves to canonical ID."""
        identified = {
            "arg_2": "The government should invest in renewable energy sources now."
        }
        assert _resolve_dung_arg_id("government should invest", identified) == "arg_2"

    def test_substring_match_desc_in_text(self):
        """desc prefix contained within text resolves to canonical ID."""
        identified = {"arg_1": "Solar power is viable"}
        # text is longer but contains the desc as substring
        assert (
            _resolve_dung_arg_id(
                "Solar power is viable and should be adopted.", identified
            )
            == "arg_1"
        )

    def test_unresolved_returns_as_is(self):
        """Unmatched text returns as-is (no match → won't fire signal 5, not an error)."""
        identified = {"arg_1": "Something completely different"}
        result = _resolve_dung_arg_id("Totally unrelated claim.", identified)
        assert result == "Totally unrelated claim."

    def test_empty_identified_args(self):
        """Empty identified_arguments: always returns text as-is."""
        assert _resolve_dung_arg_id("any text", {}) == "any text"

    def test_none_identified_args_type(self):
        """Non-dict identified_arguments: graceful passthrough."""
        assert _resolve_dung_arg_id("text", None) == "text"  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _dung_rejected_args unit tests
# ---------------------------------------------------------------------------


class TestDungRejectedArgs:
    """_dung_rejected_args — resolves text labels to canonical arg_ids."""

    def test_canonical_id_framework_unchanged(self):
        """When Dung uses canonical IDs, rejection still works (no regression)."""
        state = _state(
            identified_arguments={"arg_1": "desc1", "arg_2": "desc2"},
            dung_frameworks={
                "fw1": _framework(["arg_1", "arg_2"], rejected_args=["arg_2"])
            },
        )
        rejected = _dung_rejected_args(state)
        assert "arg_2" in rejected
        assert "arg_1" not in rejected

    def test_text_label_framework_resolves(self):
        """Dung framework with text labels: rejected arg resolved to canonical ID."""
        text_a1 = "The policy increases unemployment and harms workers"
        text_a2 = "Renewable energy is the future of power generation"
        state = _state(
            identified_arguments={"arg_1": text_a1, "arg_2": text_a2},
            dung_frameworks={
                "fw1": _framework([text_a1, text_a2], rejected_args=[text_a2])
            },
        )
        rejected = _dung_rejected_args(state)
        # text_a2 → "arg_2" after resolution
        assert "arg_2" in rejected
        assert "arg_1" not in rejected

    def test_text_label_all_rejected(self):
        """Multiple text-label rejections all map to canonical IDs."""
        descs = {
            "arg_1": "Alpha argument about climate policy",
            "arg_2": "Beta argument about economic growth",
            "arg_3": "Gamma argument about social equity",
        }
        texts = list(descs.values())
        state = _state(
            identified_arguments=descs,
            dung_frameworks={
                "fw1": _framework(texts, rejected_args=[texts[1], texts[2]])
            },
        )
        rejected = _dung_rejected_args(state)
        assert "arg_2" in rejected
        assert "arg_3" in rejected
        assert "arg_1" not in rejected

    def test_no_frameworks(self):
        """Empty dung_frameworks → empty result."""
        state = _state(identified_arguments={"arg_1": "desc"}, dung_frameworks={})
        assert _dung_rejected_args(state) == {}

    def test_all_accepted_no_rejections(self):
        """All args in extension → empty rejections."""
        state = _state(
            identified_arguments={"arg_1": "desc1"},
            dung_frameworks={"fw1": _framework(["arg_1"], rejected_args=[])},
        )
        assert _dung_rejected_args(state) == {}

    def test_prior_rejection_not_overwritten(self):
        """First framework's semantics is preserved when multiple frameworks reject same arg."""
        state = _state(
            identified_arguments={"arg_1": "some argument"},
            dung_frameworks={
                "fw1": {
                    "arguments": ["arg_1"],
                    "semantics": "grounded",
                    "extensions": {"all_members": []},
                },
                "fw2": {
                    "arguments": ["arg_1"],
                    "semantics": "preferred",
                    "extensions": {"all_members": []},
                },
            },
        )
        rejected = _dung_rejected_args(state)
        assert rejected.get("arg_1") == "grounded"  # first framework wins


# ---------------------------------------------------------------------------
# compute_argument_convergence integration tests (signal 5)
# ---------------------------------------------------------------------------


class TestDungSignalInConvergence:
    """Signal 5 (Dung rejection) now fires after _resolve_dung_arg_id fix."""

    def test_dung_signal_fires_for_text_label_framework(self):
        """Convergence score includes Dung signal when framework uses text labels."""
        desc = (
            "The government should prioritize economic growth over environmental policy"
        )
        state = _state(
            identified_arguments={"arg_1": desc},
            dung_frameworks={"fw1": _framework([desc], rejected_args=[desc])},
        )
        result = compute_argument_convergence(state)
        assert "arg_1" in result
        signals = [s[0] for s in result["arg_1"]["signals"]]
        assert "rejet Dung" in signals

    def test_dung_signal_fires_for_canonical_id_framework(self):
        """Canonical ID framework: signal 5 still fires (no regression)."""
        state = _state(
            identified_arguments={"arg_1": "desc"},
            dung_frameworks={"fw1": _framework(["arg_1"], rejected_args=["arg_1"])},
        )
        result = compute_argument_convergence(state)
        assert "arg_1" in result
        signals = [s[0] for s in result["arg_1"]["signals"]]
        assert "rejet Dung" in signals

    def test_dung_accepted_arg_no_signal(self):
        """Accepted arg: no Dung signal."""
        state = _state(
            identified_arguments={"arg_1": "accepted arg text"},
            dung_frameworks={"fw1": _framework(["arg_1"], rejected_args=[])},
        )
        result = compute_argument_convergence(state)
        # No signals at all → arg_1 not in result
        assert "arg_1" not in result

    def test_dung_signal_contributes_to_depth_3(self):
        """With fallacy + quality + Dung, depth reaches 3 (corpus-C scenario)."""
        desc = "Renewable energy cannot replace fossil fuels economically"
        state = _state(
            identified_arguments={"arg_1": desc},
            identified_fallacies={
                "f1": {"type": "causal", "target_argument_id": "arg_1"}
            },
            argument_quality_scores={"arg_1": {"overall": 3.5}},
            dung_frameworks={"fw1": _framework([desc], rejected_args=[desc])},
        )
        result = compute_argument_convergence(state)
        assert "arg_1" in result
        assert result["arg_1"]["score"] == 3
        methods = [s[0] for s in result["arg_1"]["signals"]]
        assert "sophisme" in methods
        assert "qualite faible" in methods
        assert "rejet Dung" in methods

    def test_dung_signal_contributes_to_depth_4(self):
        """With fallacy + quality + JTMS + Dung, depth reaches 4."""
        desc = "The market will self-regulate without government intervention"
        state = _state(
            identified_arguments={"arg_1": desc},
            identified_fallacies={
                "f1": {"type": "relevance", "target_argument_id": "arg_1"}
            },
            argument_quality_scores={"arg_1": {"overall": 2.1}},
            jtms_beliefs={
                "b1": {"name": "arg_1:The market will self-regulate", "valid": False}
            },
            dung_frameworks={"fw1": _framework([desc], rejected_args=[desc])},
        )
        result = compute_argument_convergence(state)
        assert "arg_1" in result
        assert result["arg_1"]["score"] == 4
        methods = [s[0] for s in result["arg_1"]["signals"]]
        assert "sophisme" in methods
        assert "qualite faible" in methods
        assert "JTMS retracte" in methods
        assert "rejet Dung" in methods

    def test_previously_dead_signal_now_live(self):
        """Before fix: text-label Dung rejection was invisible. After fix: counted."""
        long_text = "X" * 70  # longer than 60-char prefix window
        state = _state(
            identified_arguments={"arg_1": long_text},
            dung_frameworks={"fw1": _framework([long_text], rejected_args=[long_text])},
        )
        result = compute_argument_convergence(state)
        # After fix: arg_1 appears in result with Dung signal
        assert "arg_1" in result
        assert any(s[0] == "rejet Dung" for s in result["arg_1"]["signals"])
