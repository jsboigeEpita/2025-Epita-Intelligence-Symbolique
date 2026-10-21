"""#3107 — a FOL inconsistency states its cause, and the acts read it.

The render was handed one fact — ``consistent: False`` — and no cause. On a
two-speaker document, two speakers' opposite claims written into ONE theory
read as "Speaker_A's reasoning is invalidated", and the synthesis pinned the
failure on "quantifier scope" while the contradiction sat between two GROUND
literals (the issue's entry 1 held 28 formulas, exactly one of them
quantified).

The repair is a fact, not a prompt: the writer computes the cause from the
formulas and from what each formula came from (its source unit, and the
speaker when an extractor recorded one), stores it on the entry, and the
renderers phrase THAT. The vocabulary has no quantifier cause, and a ground
contradiction explicitly says the scope plays no part.

Witnessed here:

* two voices ⇒ ``between_voices``, and the phrase names them;
* one voice contradicting itself ⇒ ``self_contradiction`` — a real finding,
  kept (anti-pendulum: never suppress an inconsistent verdict);
* a ground pair next to a quantified formula ⇒ the cause is the ground pair,
  the quantified count is disclosed, and no renderer attributes it to the
  scope.

Real ``UnifiedAnalysisState`` objects, the production writer and readers,
opaque predicates — no network, no LLM, zero spend.
"""

from __future__ import annotations

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.fol_cause import (
    cause_phrase,
    classify_inconsistency,
    ground_contradiction_pairs,
    ground_literal,
)
from argumentation_analysis.orchestration.state_writers import _write_fol_to_state
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    _collect_formal_findings,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    _collect_weak_points,
    _fol_stated_causes,
    build_act3_prompt,
    Act3Evidence,
)
from argumentation_analysis.reporting.restitution.appendix import _fol_axis_status


def _two_voice_state():
    """Real state, two arguments, two recorded speakers (Speaker_A / Speaker_B)."""
    state = UnifiedAnalysisState("texte")
    a = state.add_argument("P(a)", producer="llm_extract")
    b = state.add_argument("not P(a)", producer="llm_extract")
    state.argument_provenance[a]["speaker"] = "Speaker_A"
    state.argument_provenance[b]["speaker"] = "Speaker_B"
    return state, a, b


def _fol_output(formulas, cause, sources, consistent=False):
    return {
        "formulas": formulas,
        "consistent": consistent,
        "inferences": [],
        "confidence": 0.4,
        "message": "FOL consistency check (EProver)",
        "fol_status": "decided",
        "consistency_cause": cause,
        "formula_sources": sources,
    }


class TestGroundLiteralParse:
    def test_ground_literal_reads_polarity_and_normalises_spacing(self):
        assert ground_literal("P(a)") == ("P(a)", True)
        assert ground_literal("!P(a, b)") == ("P(a,b)", False)
        assert ground_literal("¬P( a , b )") == ("P(a,b)", False)

    def test_non_ground_forms_are_not_ground(self):
        for formula in (
            "P(X)",  # variable
            "forall X: (P(X) => Q(X))",
            "exists X: P(X)",
            "P(f(a))",  # function symbol
            "P(a) && Q(b)",  # connective: not one literal
            "P()",
            "",
            None,
        ):
            assert ground_literal(formula) is None, formula

    def test_contradiction_pairs_are_found_by_atom(self):
        pairs = ground_contradiction_pairs(["P(a)", "Q(b)", "!P(a )"])
        assert [(p["positive_index"], p["negative_index"]) for p in pairs] == [(0, 2)]


class TestCauseClassification:
    def test_two_voices_make_a_contradiction_between_voices(self):
        cause = classify_inconsistency(
            ["P(a)", "!P(a)"],
            [["arg_1"], ["arg_2"]],
            {"arg_1": "Speaker_A", "arg_2": "Speaker_B"},
        )
        assert cause["cause"] == "between_voices"
        assert cause["ground"] is True
        phrase = cause_phrase(cause)
        assert "contradiction entre voix" in phrase
        assert "Speaker_A" in phrase and "Speaker_B" in phrase
        assert "portée des quantificateurs n'y joue aucun rôle" in phrase

    def test_one_voice_contradicting_itself_stays_a_finding(self):
        cause = classify_inconsistency(
            ["P(a)", "!P(a)"],
            [["arg_1"], ["arg_1"]],
            {"arg_1": "Speaker_A"},
        )
        assert cause["cause"] == "self_contradiction"
        assert "auto-contradiction" in cause_phrase(cause)
        assert "Speaker_A" in cause_phrase(cause)

    def test_two_units_without_speakers_are_named_as_sources_not_voices(self):
        cause = classify_inconsistency(["P(a)", "!P(a)"], [["arg_1"], ["arg_2"]], {})
        assert cause["cause"] == "between_sources"
        phrase = cause_phrase(cause)
        assert "unités sources" in phrase
        assert "voix" not in phrase, "an unknown speaker must not be invented"

    def test_one_batch_is_named_as_coarse_attribution(self):
        cause = classify_inconsistency(
            ["P(a)", "!P(a)"], [["arg_1", "arg_2"], ["arg_1", "arg_2"]], {}
        )
        assert cause["cause"] == "batch_attribution"
        assert "lot de traduction" in cause_phrase(cause)

    def test_ground_pair_next_to_a_quantified_formula_discloses_both(self):
        formulas = ["P(a)", "forall X: (Q(X) => R(X))", "!P(a)"]
        cause = classify_inconsistency(formulas, [["arg_1"], ["arg_2"], ["arg_1"]], {})
        assert cause["ground"] is True
        assert cause["quantified_formulas"] == 1
        phrase = cause_phrase(cause)
        assert "littéraux ground" in phrase
        assert "portée des quantificateurs n'y joue aucun rôle" in phrase

    def test_no_ground_pair_is_undetermined_never_quantifier_scope(self):
        cause = classify_inconsistency(
            ["forall X: (P(X) => Q(X))", "forall X: (P(X) => !Q(X))"],
            [["arg_1"], ["arg_2"]],
            {"arg_1": "Speaker_A", "arg_2": "Speaker_B"},
        )
        assert cause["cause"] == "undetermined"
        phrase = cause_phrase(cause)
        assert "cause non établie" in phrase
        assert (
            "portée des quantificateurs" not in phrase
        ), "an absence is not a cause: the phrase must not name the scope"


class TestWriterAndRender:
    def test_two_voices_reach_the_state_and_the_appendix(self):
        state, a, b = _two_voice_state()
        formulas = ["P(a)", "!P(a)"]
        cause = classify_inconsistency(
            formulas, [[a], [b]], {a: "Speaker_A", b: "Speaker_B"}
        )
        _write_fol_to_state(_fol_output(formulas, cause, [[a], [b]]), state, {})

        entry = state.fol_analysis_results[0]
        assert entry["consistent"] is False
        assert entry["consistency_cause"]["cause"] == "between_voices"
        assert entry["formula_sources"] == [[a], [b]]

        status = _fol_axis_status(state.fol_analysis_results)
        assert status["inconsistantes"] == 1
        assert any(
            "contradiction entre voix" in c for c in status.get("causes", [])
        ), status

    def test_act2_finding_carries_the_cause_and_never_invalidates_a_voice(self):
        state, a, b = _two_voice_state()
        formulas = ["P(a)", "!P(a)"]
        cause = classify_inconsistency(
            formulas, [[a], [b]], {a: "Speaker_A", b: "Speaker_B"}
        )
        _write_fol_to_state(_fol_output(formulas, cause, [[a], [b]]), state, {})

        findings = _collect_formal_findings(state)
        fol = [f for f in findings if f.kind == "fol"]
        assert len(fol) == 1
        assert "contradiction entre voix" in fol[0].detail
        assert "invalid" not in fol[0].detail.lower()
        # The scope is named ONLY to rule it out — the ground pair is the cause.
        assert "portée des quantificateurs n'y joue aucun rôle" in fol[0].detail

    def test_act3_weak_point_and_prompt_read_the_cause(self):
        state, a, b = _two_voice_state()
        formulas = ["P(a)", "!P(a)"]
        cause = classify_inconsistency(
            formulas, [[a], [b]], {a: "Speaker_A", b: "Speaker_B"}
        )
        _write_fol_to_state(_fol_output(formulas, cause, [[a], [b]]), state, {})

        assert any("contradiction entre voix" in c for c in _fol_stated_causes(state))
        weak = _collect_weak_points({}, {}, 0, 1, _fol_stated_causes(state))
        assert "contradiction entre voix" in weak[0].label

        prompt = build_act3_prompt(Act3Evidence())
        assert (
            "invalide ce raisonnement" not in prompt
        ), "the template that produced the misattribution is removed"
        assert "DIS LA CAUSE" in prompt
        assert "portée des quantificateurs" in prompt

    def test_a_consistent_theory_states_no_cause(self):
        state = UnifiedAnalysisState("texte")
        _write_fol_to_state(
            {
                "formulas": ["P(a)", "Q(b)"],
                "consistent": True,
                "inferences": [],
                "confidence": 0.8,
                "message": "FOL consistency check (EProver)",
                "fol_status": "decided",
            },
            state,
            {},
        )
        entry = state.fol_analysis_results[0]
        assert "consistency_cause" not in entry
        assert "formula_sources" not in entry
