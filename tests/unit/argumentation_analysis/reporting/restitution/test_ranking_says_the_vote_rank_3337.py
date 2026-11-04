"""#3337 — the ranking line says the vote winner's rank when it is not first.

Paid pass R1131a (``doc_A``): Act II crowned the vote winner ``arg_14`` « la
réponse la mieux tenue du corpus mesuré » while the measured ranking it was
handed puts ``arg_69`` first (5.0) and ``arg_14`` second, tied with ``arg_28``
(4.5). #3159 forbade only the whole-scope superlative; #3297 licenses any
measured scope — both pass while the superlative crowns the wrong unit,
because nothing reads the rank.

The repair is the #3329 gesture: the ranking line itself — the line the
writer copies — says the fact. When the governance winner is NOT the
measured top-1, the line names the winner's rank, score, and the real leader,
and says what the vote does not say. When the winner IS the top-1 (or there
is no vote, or the "winner" is a strategy, not a unit), the line stays
byte-identical — nothing is added, nothing is banned, no rewriter.

Fixtures reproduce the doc_A shape (opaque ids, synthetic counts).
Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
    quality_ranking_line,
)


#: #3394 — production shape: ``overall`` rides with its ``scores`` map
#: (``add_quality_score`` writes the pair); six evaluated virtues here.
_N6 = {f"v{i}": 1.0 for i in range(6)}


def _doc_a_quality() -> dict:
    quality = {
        "arg_69": {"overall": 5.0, "scores": dict(_N6)},
        "arg_14": {"overall": 4.5, "scores": dict(_N6)},
        "arg_28": {"overall": 4.5, "scores": dict(_N6)},
    }
    for i in range(5):
        quality[f"arg_{100 + i}"] = {"overall": 2.0, "scores": dict(_N6)}
    return quality


def _args(n: int = 90) -> dict:
    return {f"arg_{i}": f"unité synthétique {i}" for i in range(1, n + 1)}


def _state(**fields) -> SimpleNamespace:
    base = dict(
        source_metadata={},
        stakes_and_stakeholders={
            "stakes": [],
            "stakeholders": [],
            "rhetorical_register": "",
            "discursive_arena": "",
        },
        identified_arguments=_args(),
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


class TestTheRankingSaysTheVoteRank:
    def test_the_ranking_line_names_the_rank_and_the_real_leader(self):
        """The doc_A shape: winner arg_14 second, tied — the line says so."""
        state = _state(
            argument_quality_scores=_doc_a_quality(),
            governance_decisions=_vote("arg_14"),
        )
        line = build_act2_evidence(state).quality_ranking
        assert "est 2ᵉ à égalité" in line, line
        assert "arg_69 (5,00 sur 6) est en tête" in line, line
        assert "le vote ne dit pas qu'il est le mieux tenu" in line, line

    def test_control_winner_is_the_top1_keeps_the_line_byte_identical(self):
        """DoD control: winner arg_69 first — the line is unchanged, to the byte."""
        quality = _doc_a_quality()
        state = _state(
            argument_quality_scores=quality,
            governance_decisions=_vote("arg_69"),
        )
        assert build_act2_evidence(state).quality_ranking == quality_ranking_line(
            quality, 90
        )

    def test_a_tie_at_the_top_is_the_same_fact_in_both_id_orders(self):
        """#3341: a shared maximum is ONE fact. Comparing the winner's id with
        ``scored[0][0]`` made the sentence depend on how that id sorts against
        the other holder — « 1ᵉ à égalité » for one ordering, silence for the
        other. Same fact, same sentence, whatever the ids."""
        quality_14 = {
            "arg_14": {"overall": 5.0, "scores": dict(_N6)},
            "arg_69": {"overall": 5.0, "scores": dict(_N6)},
            "arg_28": {"overall": 4.5, "scores": dict(_N6)},
        }
        quality_69 = {
            "arg_69": {"overall": 5.0, "scores": dict(_N6)},
            "arg_14": {"overall": 5.0, "scores": dict(_N6)},
            "arg_28": {"overall": 4.5, "scores": dict(_N6)},
        }
        base_14 = quality_ranking_line(quality_14, 3)
        base_69 = quality_ranking_line(quality_69, 3)
        # The ranking base is deterministic whatever the dict order; only the
        # sentence AFTER it is the fact under test.
        assert base_14 == base_69
        fact_14 = quality_ranking_line(quality_14, 3, "arg_14")[len(base_14) :]
        fact_69 = quality_ranking_line(quality_69, 3, "arg_69")[len(base_69) :]
        normalised_14 = fact_14.replace("arg_14", "<W>").replace("arg_69", "<C>")
        normalised_69 = fact_69.replace("arg_69", "<W>").replace("arg_14", "<C>")
        assert normalised_14 == normalised_69, (fact_14, fact_69)

    def test_a_tie_at_the_top_says_the_head_is_shared(self):
        """The #3329 shape: no « 1ᵉ » (not a French ordinal), no « en tête »
        for a holder at the SAME score, and no « le vote ne dit pas qu'il est
        le mieux tenu » — it shares the top, that tail would be false."""
        quality = {
            "arg_14": {"overall": 5.0, "scores": dict(_N6)},
            "arg_69": {"overall": 5.0, "scores": dict(_N6)},
            "arg_28": {"overall": 4.5, "scores": dict(_N6)},
        }
        line = quality_ranking_line(quality, 3, "arg_14")
        assert (
            "partage la tête de ce classement (5,00 sur 6) avec arg_69" in line
        ), line
        assert "1ᵉ" not in line, line
        assert "en tête" not in line, line
        assert "le vote ne dit pas" not in line, line

    def test_a_three_way_tie_names_every_holder(self):
        """A shared head is named by every co-holder, in the same id order the
        line's own listing uses — never one of them « en tête »."""
        quality = {
            "arg_14": {"overall": 5.0, "scores": dict(_N6)},
            "arg_69": {"overall": 5.0, "scores": dict(_N6)},
            "arg_3": {"overall": 5.0, "scores": dict(_N6)},
            "arg_28": {"overall": 4.5, "scores": dict(_N6)},
        }
        line = quality_ranking_line(quality, 4, "arg_69")
        assert (
            "partage la tête de ce classement (5,00 sur 6) avec arg_14 et arg_3"
            in line
        ), line
        assert "en tête" not in line, line

    def test_the_tie_fact_survives_relabeling_in_the_prompt(self):
        """#3296 holds for the new branch too: the sentence rides the per-act
        letter table, the prompt carries no raw id."""
        state = _state(
            identified_arguments=_args(90),
            argument_quality_scores={
                "arg_14": {"overall": 5.0, "scores": dict(_N6)},
                "arg_69": {"overall": 5.0, "scores": dict(_N6)},
                "arg_28": {"overall": 4.5, "scores": dict(_N6)},
            },
            governance_decisions=_vote("arg_14"),
        )
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert "partage la tête" in prompt
        assert not re.search(r"arg_\d+", prompt)

    def test_no_vote_keeps_the_line_unchanged(self):
        quality = _doc_a_quality()
        state = _state(argument_quality_scores=quality)
        assert build_act2_evidence(state).quality_ranking == quality_ranking_line(
            quality, 90
        )

    def test_a_strategy_winner_is_never_ranked(self):
        """R1078: a fallback producer writes a STRATEGY into ``winner`` — it is
        not a unit, the ranking line makes no claim about it."""
        quality = _doc_a_quality()
        state = _state(
            argument_quality_scores=quality,
            governance_decisions=_vote("compromise"),
        )
        assert build_act2_evidence(state).quality_ranking == quality_ranking_line(
            quality, 90
        )

    def test_a_unique_rank_carries_no_tie_clause(self):
        quality = {
            "arg_7": {"overall": 5.0, "scores": dict(_N6)},
            "arg_8": {"overall": 4.7, "scores": dict(_N6)},
            "arg_9": {"overall": 4.0, "scores": dict(_N6)},
        }
        state = _state(
            identified_arguments={
                **_args(9),
                **{f"arg_{i}": f"unité {i}" for i in (7, 8, 9)},
            },
            argument_quality_scores=quality,
            governance_decisions=_vote("arg_9"),
        )
        line = build_act2_evidence(state).quality_ranking
        assert "est 3ᵉ de ce classement (4,00 sur 6)" in line, line
        assert "à égalité" not in line.split("Classement qualité")[1], line

    def test_the_fact_survives_relabeling_in_the_prompt(self):
        """#3296: the fact rides the per-act letter table like every other
        id — the prompt carries the fact, never a raw id."""
        state = _state(
            argument_quality_scores=_doc_a_quality(),
            governance_decisions=_vote("arg_14"),
        )
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert "est 2ᵉ à égalité" in prompt
        assert re.search(r"[α-ω]+ \(5,00 sur 6\) est en tête", prompt), prompt
        assert not re.search(r"arg_\d+", prompt)

    def test_an_unscored_winner_says_it_is_not_in_the_ranking(self):
        """#3326 shape: the vote winner is a real unit the quality pass never
        scored — the line says the vote ranks nothing here."""
        quality = {"arg_69": {"overall": 5.0}, "arg_28": {"overall": 4.5}}
        state = _state(
            argument_quality_scores=quality,
            governance_decisions=_vote("arg_14"),
        )
        line = build_act2_evidence(state).quality_ranking
        assert "n'est pas dans ce classement mesuré" in line, line
        assert "le vote ne dit pas qu'il est le mieux tenu" in line, line

    def test_five_co_holders_count_the_last_one_in_the_singular(self):
        """#3337 residual (R1133): at exactly five co-holders the overflow
        count is 1 and the line read « et 1 autres ». The noun agrees with
        its count now; #3329's cap still names four."""
        quality = {
            "arg_14": {"overall": 5.0},
            "arg_28": {"overall": 5.0},
            "arg_3": {"overall": 5.0},
            "arg_69": {"overall": 5.0},
            "arg_7": {"overall": 5.0},
            "arg_8": {"overall": 5.0},
            "arg_9": {"overall": 4.0},
        }
        line = quality_ranking_line(quality, 7, "arg_14")
        assert " et 1 autre." in line, line
        assert "1 autres" not in line, line

    def test_control_two_remaining_co_holders_keep_the_plural(self):
        """Positive control for the residual: from six co-holders on, the
        plural branch is what main already printed — unchanged."""
        quality = {
            "arg_14": {"overall": 5.0},
            "arg_28": {"overall": 5.0},
            "arg_3": {"overall": 5.0},
            "arg_69": {"overall": 5.0},
            "arg_7": {"overall": 5.0},
            "arg_8": {"overall": 5.0},
            "arg_9": {"overall": 5.0},
        }
        line = quality_ranking_line(quality, 8, "arg_14")
        assert " et 2 autres." in line, line
