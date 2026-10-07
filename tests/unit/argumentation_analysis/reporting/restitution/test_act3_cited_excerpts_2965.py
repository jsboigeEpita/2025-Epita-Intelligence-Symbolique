"""#2965 (Acte III slice) — the excerpts follow the citations.

On the measured run, Act III cited 14 units (governance winner, ranked
salience, weak-point and counter targets) and received the text of **none**
of them: its only five excerpts were the first five units in insertion
order — the opening of the document — which it cites nowhere. The writer
was told to "cite the central claim" and handed the first five units.

The repair has two halves, both measured against the falsified premise
that a writer joins an id to its unit across a long prompt (it does not —
4 of 5 samples, R1071):

1. ``claim_excerpts`` follows the citations, in salience order (winner
   first, then ranked-salience anchors, then the remaining citation
   populations of #2974's ``cited_unit_ids``), keyed by opaque id, each
   text capped at ``CITED_UNIT_TEXT_CAP`` — the same budget Act II
   allocates its cited units. The dict head fills only unused budget.
2. The governance line carries the winner's referent ITSELF (capped
   text); the id stays unprinted on that line.

Privacy: invented filler, opaque ids, no corpus sentence. Deterministic:
no JVM, no LLM.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)


def _state(**fields) -> SimpleNamespace:
    base = dict(
        identified_arguments={},
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        dung_frameworks={},
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        narrative_synthesis="",
        governance_decisions=[],
        debate_transcripts=[],
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _cited_outside_head() -> SimpleNamespace:
    """Seven units; every citation sits OUTSIDE the first five in insertion
    order — the measured shape (14 cited, 0 with text on the run).

    arg_6 carries the crown: governance winner AND a localized fallacy (a
    weak-point target). arg_7 is the ranked-salience anchor (fallacy +
    weak quality → corroborant) AND a counter target. arg_1 is measured
    mid-range so the quality population spans the weak bar (the #1942
    non-vacuity gate) without earning arg_1 any role.
    """
    return _state(
        identified_arguments={
            "arg_1": "Première unité d'ouverture, mesurée mais jamais citée.",
            "arg_2": "Deuxième unité d'ouverture sans citation.",
            "arg_3": "Troisième unité d'ouverture sans citation.",
            "arg_4": "Quatrième unité d'ouverture sans citation.",
            "arg_5": "Cinquième unité d'ouverture sans citation.",
            "arg_6": (
                "Le lauréat du vote affirme une doctrine du contrôle local "
                "et en tire la clause opératoire de sa conclusion."
            ),
            "arg_7": "Une unité contestée dont la faiblesse est corroborée par deux axes.",
        },
        identified_fallacies={
            "fl_1": {
                "target_argument_id": "arg_6",
                "family": "faux dilemme",
                "justification": "L'unité réduit trois options à deux.",
            },
            "fl_2": {
                "target_argument_id": "arg_7",
                "family": "appel à l'autorité",
                "justification": "L'unité s'appuie sur une autorité hors sujet.",
            },
        },
        argument_quality_scores={
            "arg_1": {"overall": 6.0, "scores": {"clarte": 6.0}},
            "arg_7": {"overall": 3.0, "scores": {"clarte": 3.0}},
        },
        counter_arguments=[
            {
                "target_arg_id": "arg_7",
                "counter_content": "L'autorité invoquée ne couvre pas le domaine concerné.",
            }
        ],
        governance_decisions=[
            {
                "method": "vote_borda",
                "winner": "arg_6",
                "scores": {"arg_6": 12, "arg_7": 8},
            }
        ],
    )


def _governance_line(prompt: str) -> str:
    lines = [ln for ln in prompt.splitlines() if "GOUVERNANCE :" in ln]
    assert lines, "the prompt carries no governance line"
    return lines[0]


class TestTheExcerptsFollowTheCitations:
    def test_cited_units_outside_the_head_reach_the_prompt(self) -> None:
        """The issue's witness: winner, salience anchor and targets all sit
        past the first five units — on main the prompt carried the text of
        none of them (it carried arg_1..arg_5 instead)."""
        prompt = build_act3_prompt(build_act3_evidence(_cited_outside_head()))
        assert "doctrine du contrôle local" in prompt  # arg_6, the winner
        assert "corroborée par deux axes" in prompt  # arg_7, salience + target

    def test_positive_control_citations_on_the_head_change_nothing(self) -> None:
        """A state whose citations ARE the first units keeps the same
        excerpt CONTENT as the dict head — the fix selects, it does not
        inflate. Green on main by construction (non-regression guard)."""
        state = _cited_outside_head()
        state.identified_fallacies["fl_1"]["target_argument_id"] = "arg_1"
        state.identified_fallacies["fl_2"]["target_argument_id"] = "arg_2"
        # arg_7 loses its fallacy; drop its quality too, or its 3.0/10 score
        # (≥ the strong bar on the classifier's scale) turns it into an
        # unchallenged STRENGTH anchor — a citation past the head.
        state.argument_quality_scores.pop("arg_7")
        state.counter_arguments[0]["target_arg_id"] = "arg_2"
        state.governance_decisions[0]["winner"] = "arg_1"
        ev = build_act3_evidence(state)
        ids = [unit_id for unit_id, _text in ev.claim_excerpts]
        assert set(ids) == {"arg_1", "arg_2", "arg_3", "arg_4", "arg_5"}

    def test_the_selection_order_is_salience_order(self) -> None:
        """Winner first, ranked-salience anchor next, head fill last — on
        main the order was insertion order, arg_1 first."""
        ev = build_act3_evidence(_cited_outside_head())
        ids = [unit_id for unit_id, _text in ev.claim_excerpts]
        assert ids == ["arg_6", "arg_7", "arg_1", "arg_2", "arg_3"]

    def test_the_claims_block_is_keyed_by_opaque_id(self) -> None:
        """The join with the weaknesses/counter lines (which cite the same
        ids a few lines away) is carried by the block itself — main printed
        bare texts with no key."""
        prompt = build_act3_prompt(build_act3_evidence(_cited_outside_head()))
        assert "  - arg_6 : Le lauréat du vote" in prompt

    def test_a_cited_units_operative_clause_survives_the_cap(self) -> None:
        """#1914's defect shape: a cited unit's operative clause sat past
        character 340 and no writer ever saw it. The cap for a CITED unit
        is ``CITED_UNIT_TEXT_CAP`` (2000), not the 240-char excerpt cut —
        the clause here sits at ~1000, past 240, well inside 2000."""
        head_fill = (
            "Phrase de remplissage suffisamment longue pour occuper le début. " * 15
        )
        tail_fill = (
            "Phrase de queue qui pousse le texte au-delà du plafond du budget. " * 20
        )
        state = _cited_outside_head()
        state.identified_arguments["arg_6"] = (
            head_fill + " CLAUSE-OPÉRATOIRE-À-CHAR-1000. " + tail_fill
        )
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert "CLAUSE-OPÉRATOIRE-À-CHAR-1000" in prompt
        # the cut, when it fires, stays visible (never a bare slice)
        assert " […]" in prompt

    def test_honest_absence_without_arguments(self) -> None:
        """No arguments extracted → the claims block states the absence (G1
        not passed); the citation machinery fabricates nothing."""
        prompt = build_act3_prompt(build_act3_evidence(_state()))
        assert "aucune revendication extraite" in prompt


class TestTheGovernanceLineCarriesTheReferent:
    def test_the_line_carries_the_winners_text_not_its_id(self) -> None:
        """The falsified premise, closed: the referent travels ON the line,
        the id stays unprinted there — on main the line printed « arg_6 »
        and no text, and the writer described the winner by role only."""
        prompt = build_act3_prompt(build_act3_evidence(_cited_outside_head()))
        line = _governance_line(prompt)
        assert "doctrine du contrôle local" in line
        assert "« arg_6 »" not in line

    def test_a_winner_without_joinable_text_keeps_the_role_only_line(self) -> None:
        """Honest absence: a winner that is not an extracted unit has no
        text to carry — the line keeps its role-only wording (green on
        main by construction: the absence guard)."""
        state = _cited_outside_head()
        state.governance_decisions[0]["winner"] = "opt_x"
        prompt = build_act3_prompt(build_act3_evidence(state))
        line = _governance_line(prompt)
        assert "« opt_x »" in line
        assert "DÉCRIS" in line
