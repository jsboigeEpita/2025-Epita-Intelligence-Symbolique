# -*- coding: utf-8 -*-
"""#3347 — the ranking line completes the tie it used to cut into.

Paid pass R1133a (``doc 8fa89437_ext1``, main ``30ec9a3cb``): Act II wrote
that the vote winner « partage la deuxième place avec le passage [arg_22] »
while the measured ranking ties it at 4.0 with TWO units, ``arg_22`` and
``arg_28``, behind ``arg_69`` (4.5). One co-holder named out of two — the
reader takes a three-way tie for a two-way one.

Two halves, both in ``quality_ranking_line`` (the line the writer copies,
#3159):

- ``scored[:3]`` cut INSIDE the 4.0 tie: ``arg_28`` dropped, ``arg_22``
  kept — the cut follows alphabetical id order, not scores. The listing now
  carries every holder of the boundary score (bounded at six shown; beyond,
  the left-outs are counted, never silently dropped).
- the off-top branch said « est 2ᵉ à égalité » and never named the
  co-holders — the #3341 branch names the ones it shares the HEAD with, this
  branch said nothing. The writer filled the gap from the truncated
  listing. The mates are now named the #3341/#3329 way (four, then a count),
  through the same helper as the head branch.

Controls: no tie at the cut, an untied off-top winner and a sole top-1
winner keep the exact pre-#3347 line, byte for byte (the existing #3159 /
#3337 / #3341 witnesses hold the rest).

Synthetic vocabularies only — no corpus text, opaque ids only.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
    quality_ranking_line,
)

#: The recorded R1133a shape: 8 scored units of 90, one 4.5 then three 4.0.
_RECORDED = {
    "arg_69": 4.5,
    "arg_14": 4.0,
    "arg_22": 4.0,
    "arg_28": 4.0,
    "arg_3": 3.5,
    "arg_41": 3.0,
    "arg_7": 2.5,
    "arg_55": 2.0,
}


def _quality(scores: dict) -> dict:
    return {arg_id: {"overall": score} for arg_id, score in scores.items()}


def _state(**fields) -> SimpleNamespace:
    base = dict(
        source_metadata={},
        stakes_and_stakeholders={
            "stakes": [],
            "stakeholders": [],
            "rhetorical_register": "",
            "discursive_arena": "",
        },
        identified_arguments={
            f"arg_{i}": f"unité synthétique {i}" for i in range(1, 91)
        },
    )
    base.update(fields)
    return SimpleNamespace(**base)


def _vote(winner: str) -> list:
    return [
        {
            "method": "social_choice",
            "winner": winner,
            "winners": [winner],
            "scores": {winner: 12.0},
            "winner_provenance": "vote_aggregate",
        }
    ]


class TestTheListingNeverCutsInsideATie:
    def test_the_recorded_shape_lists_every_4_0_holder(self):
        """Born red on main: ``scored[:3]`` dropped arg_28 while keeping
        arg_22 — same score, alphabetical accident."""
        line = quality_ranking_line(_quality(_RECORDED), 90, "arg_14")
        assert "arg_69 (4.5), arg_14 (4.0), arg_22 (4.0), arg_28 (4.0)" in line, line

    def test_without_a_vote_the_cut_still_completes_the_tie(self):
        """The truncation defect is in the listing, not in the vote branch:
        no winner passed, arg_28 still rides the line."""
        line = quality_ranking_line(_quality(_RECORDED), 90)
        assert "arg_28 (4.0)" in line, line

    def test_a_wide_boundary_tie_counts_its_left_outs(self):
        """Six holders at the boundary score: the listing stays bounded and
        SAYS how many it leaves out — the cut is never silent again."""
        scores = {"arg_1": 5.0, "arg_2": 4.0}
        for i in range(3, 9):
            scores[f"arg_{i}"] = 3.0
        line = quality_ranking_line(_quality(scores), 8)
        assert "arg_3 (3.0) et 5 autres à 3.0" in line, line

    def test_no_tie_at_the_cut_keeps_today_three_names(self):
        """Positive control: a cut between two different scores is not a
        defect — the #3159 listing stands, byte-identical."""
        scores = {
            "arg_1": 5.0,
            "arg_2": 4.0,
            "arg_3": 3.0,
            "arg_4": 2.0,
            "arg_5": 1.0,
        }
        line = quality_ranking_line(_quality(scores), 5)
        assert line.startswith(
            "Classement qualité (base : 5 unités évaluées sur 5) : "
            "arg_1 (5.0), arg_2 (4.0), arg_3 (3.0)."
        ), line
        assert "autres" not in line, line


class TestTheOffTopBranchNamesItsCoHolders:
    def test_the_recorded_shape_names_both_mates(self):
        """Born red on main: the branch computed ``tie`` and said « à
        égalité » — the mates stayed nameless and the writer invented a
        two-way tie from the truncated listing."""
        line = quality_ranking_line(_quality(_RECORDED), 90, "arg_14")
        assert (
            "est 2ᵉ à égalité de ce classement (4.0) avec arg_22 et arg_28" in line
        ), line
        assert "arg_69 (4.5) est en tête" in line, line
        assert "le vote ne dit pas qu'il est le mieux tenu" in line, line

    def test_many_mates_are_capped_and_counted(self):
        """The #3329 cap rides here too: four named, the rest counted."""
        scores = {"arg_1": 5.0, "arg_w": 4.0}
        for i in range(2, 8):
            scores[f"arg_{i}"] = 4.0
        line = quality_ranking_line(_quality(scores), 7, "arg_w")
        assert "avec arg_2, arg_3, arg_4, arg_5 et 2 autres" in line, line

    def test_an_untied_off_top_winner_stays_byte_identical(self):
        """No tie → no « avec » clause: the pre-#3347 sentence, exactly."""
        line = quality_ranking_line(
            _quality({"arg_1": 5.0, "arg_2": 4.7, "arg_9": 4.0}), 3, "arg_9"
        )
        assert line.endswith(
            "est 3ᵉ de ce classement (4.0) ; arg_1 (5.0) est en tête : "
            "le vote ne dit pas qu'il est le mieux tenu."
        ), line

    def test_the_completed_listing_and_the_mates_ride_the_letter_table(self):
        """#3296: the new ids (arg_28 in the listing, the mates in the
        clause) reach the prompt as letters, never raw ids."""
        state = _state(
            argument_quality_scores=_quality(_RECORDED),
            governance_decisions=_vote("arg_14"),
        )
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert "est 2ᵉ à égalité" in prompt, prompt
        assert re.search(r"à égalité de ce classement \(4\.0\) avec ", prompt), prompt
        assert not re.search(r"arg_\d+", prompt), prompt
