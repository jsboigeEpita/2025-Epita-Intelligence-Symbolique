"""Tests for convergent multidimensional synthesis (#634).

Validates that compute_argument_convergence detects when several independent
methods (fallacy detection, abstract argumentation, truth maintenance, quality
scoring, counter-argumentation) flag the same argument, and that
build_convergent_synthesis surfaces named convergent verdicts and a conclusion.
"""

from argumentation_analysis.plugins.narrative_synthesis_plugin import (
    compute_argument_convergence,
    build_convergent_synthesis,
    _native_dung_rejections,
    NarrativeSynthesisPlugin,
)
from argumentation_analysis.core.shared_state import UnifiedAnalysisState


def _state_with_args(*descriptions: str) -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("Test discourse for convergence analysis.")
    for desc in descriptions:
        state.add_argument(desc)
    return state


def _virtues(overall: float, n: int = 9) -> dict:
    """#1942 honest entry shape: n per-virtue [0, 1] notes whose SUM is
    ``overall`` — readers normalize by ``len(scores)``."""
    return {f"vertu_{i}": overall / n for i in range(n)}


# A not-weak entry (0.6 of the applicable maximum) that spans the weak bar
# on a second, otherwise-silent argument — the #1942 non-vacuity gate needs
# the run's population to span before "qualite faible" means anything.
_SPANNING_OVERALL = 5.4


class TestDungRejection:
    """_native_dung_rejections handles the three extension storage shapes
    (#1912: fixtures aligned to the canonical writer shape — production
    natives are always ``verification_*``, the nameless handcrafted states
    predate that convention)."""

    def test_enriched_all_members_form(self):
        state = _state_with_args("a", "b", "c")  # arg_1, arg_2, arg_3
        state.dung_frameworks = {
            "dung_1": {
                "name": "verification_grounded",
                "semantics": "grounded",
                "arguments": ["arg_1", "arg_2", "arg_3"],
                "extensions": {"all_members": ["arg_1", "arg_2"]},
            }
        }
        rejected = _native_dung_rejections(state)
        assert rejected == {"arg_3": "grounded"}

    def test_semantics_to_list_form(self):
        state = _state_with_args("a", "b", "c")
        # This is the shape add_dung_framework stores (Dict[str, List[str]])
        state.add_dung_framework(
            name="verification_grounded",
            arguments=["arg_1", "arg_2", "arg_3"],
            attacks=[["arg_1", "arg_3"]],
            extensions={"grounded": ["arg_1", "arg_2"]},
        )
        rejected = _native_dung_rejections(state)
        assert "arg_3" in rejected

    def test_list_of_lists_form(self):
        state = _state_with_args("a", "b", "c")
        state.dung_frameworks = {
            "dung_1": {
                "name": "verification_preferred",
                "semantics": "preferred",
                "arguments": ["arg_1", "arg_2", "arg_3"],
                "extensions": [["arg_1"], ["arg_2"]],
            }
        }
        rejected = _native_dung_rejections(state)
        assert rejected == {"arg_3": "preferred"}

    def test_no_frameworks_returns_empty(self):
        state = _state_with_args("a")
        assert _native_dung_rejections(state) == {}

    def test_all_args_accepted_none_rejected(self):
        state = _state_with_args("a", "b")
        state.dung_frameworks = {
            "dung_1": {
                "name": "verification_grounded",
                "arguments": ["arg_1", "arg_2"],
                "extensions": {"all_members": ["arg_1", "arg_2"]},
            }
        }
        assert _native_dung_rejections(state) == {}


class TestComputeConvergence:
    """compute_argument_convergence counts independent weakness signals."""

    def test_single_method_scores_one(self):
        state = _state_with_args("strong argument")
        state.add_fallacy("ad_hominem", "attack on person", "arg_1")
        conv = compute_argument_convergence(state)
        assert conv["arg_1"]["score"] == 1
        methods = [m for m, _ in conv["arg_1"]["signals"]]
        assert methods == ["sophisme"]

    def test_two_methods_scores_two(self):
        state = _state_with_args("weak argument", "solid argument")
        state.add_fallacy("straw_man", "distortion", "arg_1")
        state.add_quality_score("arg_1", _virtues(2.25), 2.25)  # 0.25 fraction
        state.add_quality_score("arg_2", _virtues(_SPANNING_OVERALL), _SPANNING_OVERALL)
        conv = compute_argument_convergence(state)
        assert conv["arg_1"]["score"] == 2
        methods = {m for m, _ in conv["arg_1"]["signals"]}
        assert methods == {"sophisme", "qualite faible"}

    def test_three_methods_convergence(self):
        state = _state_with_args("doomed argument", "solid argument")
        state.add_fallacy("false_dilemma", "either/or", "arg_1")
        state.add_quality_score("arg_1", _virtues(1.8), 1.8)
        state.add_quality_score("arg_2", _virtues(_SPANNING_OVERALL), _SPANNING_OVERALL)
        state.add_counter_argument(
            "doomed argument",
            "reductio counter",
            "reductio",
            0.9,
            target_arg_id="arg_1",
        )
        conv = compute_argument_convergence(state)
        assert conv["arg_1"]["score"] == 3

    def test_dung_rejection_counts_as_signal(self):
        state = _state_with_args("a", "b")
        state.add_fallacy("ad_hominem", "attack", "arg_2")
        state.dung_frameworks = {
            "dung_1": {
                "name": "verification_grounded",
                "semantics": "grounded",
                "arguments": ["arg_1", "arg_2"],
                "extensions": {"all_members": ["arg_1"]},  # arg_2 rejected
            }
        }
        conv = compute_argument_convergence(state)
        assert conv["arg_2"]["score"] == 2
        methods = {m for m, _ in conv["arg_2"]["signals"]}
        assert methods == {"sophisme", "rejet Dung"}

    def test_jtms_invalid_belief_counts(self):
        state = _state_with_args("retracted argument", "solid argument")
        # belief name uses "arg_N:" prefix (NN wiring convention)
        state.add_jtms_belief(
            "arg_1:retracted argument", False, justifications=["undermined"]
        )
        state.add_quality_score("arg_1", _virtues(1.8), 1.8)
        state.add_quality_score("arg_2", _virtues(_SPANNING_OVERALL), _SPANNING_OVERALL)
        conv = compute_argument_convergence(state)
        assert conv["arg_1"]["score"] == 2
        methods = {m for m, _ in conv["arg_1"]["signals"]}
        assert methods == {"JTMS retracte", "qualite faible"}

    def test_high_quality_not_flagged(self):
        state = _state_with_args("good argument")
        state.add_quality_score("arg_1", {"clarte": 9.0}, 8.5)  # above threshold
        conv = compute_argument_convergence(state)
        assert "arg_1" not in conv  # no signals at all

    def test_clean_argument_absent_from_result(self):
        state = _state_with_args("clean", "flawed")
        state.add_fallacy("ad_hominem", "attack", "arg_2")
        conv = compute_argument_convergence(state)
        assert "arg_1" not in conv
        assert "arg_2" in conv

    def test_empty_state_returns_empty(self):
        state = UnifiedAnalysisState("nothing here")
        assert compute_argument_convergence(state) == {}


class TestBuildConvergentSynthesis:
    """build_convergent_synthesis produces named verdicts + conclusion."""

    def test_convergent_verdict_named(self):
        state = _state_with_args("doomed", "solid")
        state.add_fallacy("false_dilemma", "either/or", "arg_1")
        state.add_quality_score("arg_1", _virtues(1.8), 1.8)
        state.add_quality_score("arg_2", _virtues(_SPANNING_OVERALL), _SPANNING_OVERALL)
        result = build_convergent_synthesis(state)
        assert "arg_1" in result["convergent_verdicts"]
        assert any("arg_1" in ins for ins in result["emergent_insights"])
        # The named verdict cites the argument id
        assert "Verdict convergent sur arg_1" in result["narrative"]

    def test_single_signal_not_a_convergent_verdict(self):
        state = _state_with_args("mildly flawed")
        state.add_fallacy("ad_hominem", "attack", "arg_1")  # only 1 method
        result = build_convergent_synthesis(state)
        assert result["convergent_verdicts"] == {}
        assert "une seule methode" in result["conclusion"]

    def test_robust_structure_no_signals(self):
        state = _state_with_args("solid")
        state.add_quality_score("arg_1", {"clarte": 9.0}, 9.0)
        result = build_convergent_synthesis(state)
        assert result["convergent_verdicts"] == {}
        assert "robuste" in result["conclusion"]

    def test_verdicts_ordered_by_convergence_strength(self):
        state = _state_with_args("two-method", "three-method", "solid")
        # arg_1: 2 methods
        state.add_fallacy("straw_man", "distortion", "arg_1")
        state.add_quality_score("arg_1", _virtues(1.8), 1.8)
        # arg_2: 3 methods
        state.add_fallacy("false_dilemma", "either/or", "arg_2")
        state.add_quality_score("arg_2", _virtues(1.35), 1.35)
        state.add_counter_argument(
            "three-method", "counter", "reductio", 0.8, target_arg_id="arg_2"
        )
        # arg_3: silent span (0.6) — opens the #1942 non-vacuity gate
        state.add_quality_score("arg_3", _virtues(_SPANNING_OVERALL), _SPANNING_OVERALL)
        result = build_convergent_synthesis(state)
        # Strongest (arg_2, score 3) must appear before arg_1 in insights
        insights_text = "\n".join(result["emergent_insights"])
        assert insights_text.index("arg_2") < insights_text.index("arg_1")
        assert "arg_2" in result["conclusion"]  # max convergence cited

    def test_base_narrative_preserved(self):
        state = _state_with_args("arg")
        state.add_fallacy("ad_hominem", "attack", "arg_1")
        state.add_quality_score("arg_1", {"x": 1.0}, 2.0)
        result = build_convergent_synthesis(state)
        # Backward compat: base template narrative still embedded
        assert result["base_narrative"]
        assert result["base_narrative"] in result["narrative"]


class TestKernelFunctionWrapper:
    """The plugin exposes convergent_synthesize for SK invocation."""

    def test_convergent_synthesize_returns_json(self):
        import json

        plugin = NarrativeSynthesisPlugin()
        state_json = json.dumps(
            {
                "identified_arguments": {
                    "arg_1": "doomed argument",
                    "arg_2": "solid argument",
                },
                "identified_fallacies": {
                    "fallacy_1": {
                        "type": "false_dilemma",
                        "justification": "either/or",
                        "target_argument_id": "arg_1",
                    }
                },
                "argument_quality_scores": {
                    # #1942: sums over the evaluated virtues, and the
                    # population spans the weak bar via the silent arg_2.
                    "arg_1": {"scores": _virtues(1.8), "overall": 1.8},
                    "arg_2": {"scores": _virtues(5.4), "overall": 5.4},
                },
            }
        )
        out = plugin.convergent_synthesize(state_json)
        parsed = json.loads(out)
        assert "narrative" in parsed
        assert "arg_1" in parsed["convergent_verdicts"]

    def test_convergent_synthesize_handles_bad_json(self):
        plugin = NarrativeSynthesisPlugin()
        out = plugin.convergent_synthesize("not valid json{")
        import json

        parsed = json.loads(out)
        # Empty state → robust-structure conclusion, no crash
        assert "conclusion" in parsed
