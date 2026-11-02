# -*- coding: utf-8 -*-
"""#3356 — a tied head is shared, not crowned on one holder.

The last tie slot #3341/#3347 left open in ``quality_ranking_line``: with a
TIED maximum the off-top branch's closing clause read ``scored[0]``'s id and
said « {id} (score) est en tête » — one holder crowned « en tête » by the
alphabetical accident of the sort, the same defect #3347 removed from the
listing one clause earlier. Paid pass R1134a (``doc_A``, union tree of
R1134) read it on the render.

A shared head is now named the ONE way the line names ties — #3341's
``_tie_companions``, its count/noun agreement inside: « arg_1 et arg_2 (4.5)
partagent la tête ». A sole top-1 keeps the exact pre-#3356 clause, byte
for byte (positive control; the #3337/#3341/#3347 witnesses hold the rest).

Synthetic vocabularies only — no corpus text, opaque ids only.
"""

from __future__ import annotations

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    quality_ranking_line,
)


def _quality(scores: dict) -> dict:
    return {arg_id: {"overall": score} for arg_id, score in scores.items()}


#: The dispatch's probe: a tied head at 4.5, the vote winner below it.
_PROBE = {"arg_1": 4.5, "arg_2": 4.5, "arg_3": 4.0, "arg_4": 3.0}


class TestATiedHeadIsShared:
    def test_the_probe_says_the_holders_share_the_head(self):
        """Born red on main: the clause read ``scored[0]`` and crowned
        arg_1 alone (« arg_1 (4.5) est en tête ») while arg_2 holds the
        same maximum."""
        line = quality_ranking_line(_quality(_PROBE), 4, "arg_3")
        assert "arg_1 et arg_2 (4.5) partagent la tête" in line, line
        assert "est en tête" not in line, line
        assert "Le gagnant du vote, arg_3, est 3ᵉ de ce classement (4.0)" in line, line

    def test_a_sole_top_one_keeps_the_exact_clause(self):
        """Positive control: no tie at the head — the pre-#3356 clause,
        byte-identical."""
        line = quality_ranking_line(
            _quality({"arg_1": 5.0, "arg_2": 4.7, "arg_3": 4.0}), 3, "arg_3"
        )
        assert line.endswith(
            "est 3ᵉ de ce classement (4.0) ; arg_1 (5.0) est en tête : "
            "le vote ne dit pas qu'il est le mieux tenu."
        ), line

    def test_a_wide_head_tie_is_capped_and_counted(self):
        """Five holders of the maximum: the #3329 cap and the #3337
        count/noun agreement ride through the same helper."""
        scores = {f"arg_{i}": 5.0 for i in range(1, 6)}
        scores["arg_w"] = 4.0
        line = quality_ranking_line(_quality(scores), 6, "arg_w")
        assert (
            "arg_1, arg_2, arg_3, arg_4 et 1 autre (5.0) partagent la tête" in line
        ), line
        assert "1 autres" not in line, line

    def test_a_tied_head_and_a_tied_rank_are_both_named(self):
        """Both tie clauses in one line: the winner's rank-mates AND the
        shared head each name their holders."""
        scores = {
            "arg_1": 5.0,
            "arg_2": 5.0,
            "arg_3": 4.0,
            "arg_4": 4.0,
            "arg_5": 3.0,
        }
        line = quality_ranking_line(_quality(scores), 5, "arg_4")
        # Two 5.0 holders hold ranks 1-2, so the 4.0 pair is 3rd.
        assert "est 3ᵉ à égalité de ce classement (4.0) avec arg_3" in line, line
        assert "arg_1 et arg_2 (5.0) partagent la tête" in line, line
