"""#3530 — the points (Borda) block: where a BENEFICIAL misreport really exists.

The decision of 13/11 (option b, restricted to Borda) keeps the Condorcet
winner as the outcome and adds a second rule on top, because #3524 left the
manipulability field structurally inert: every Condorcet witness installed a
winner one of its movers ranks below the baseline, so the kept lists came out
empty on every profile — and the engine never even ran without a Condorcet
winner. Borda is single-voter manipulable where Condorcet is not (the
coordinator measured 6 of 18 recorded profiles against 0 of 12).

What this file witnesses, in the order the DoD asks for it:

- the enumeration's population, pinned: on the complete profiles of 3 options
  × 3 players, 186 have a Borda winner and **none** is manipulable by one
  player; on 3 options × 4 players, 216 profiles are pair-manipulable and none
  single-manipulable. The interest check is load-bearing: neutralised, 162 of
  the 186 3×3 profiles grow a single-player witness;
- one kept fixture per shape (a single pivot on 4 options × 3 players, a pair
  on 3 options × 4 players where NEITHER member can do it alone);
- the bounds: a tie at the top is no winner, and a seven-option profile states
  that its enumeration was cut instead of reporting silence as "not
  manipulable";
- the render names the rule (« si l'issue se réglait aux points (Borda) ») and
  says when the points and Condorcet winners differ.
"""

from __future__ import annotations

import itertools

import pytest

from argumentation_analysis.agents.core.context import strategist
from argumentation_analysis.agents.core.context.strategist import (
    BORDA_PERMUTATION_CAP,
    _borda_scores,
    borda_winner,
    compute_manipulability,
)
from argumentation_analysis.agents.core.governance.coalition_play import coalition_note
from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    _format_strategic_block,
)

_OPTIONS_3 = ["A", "B", "C"]

# 4 options × 3 players: P3 alone installs B by reporting B > C > D > A, and
# P3's own ballot ranks B above the honest Borda winner A. Measured, not
# hand-trusted: the honest scores are A 8, B 7, C 3, D 0.
_SINGLE_PROFILE = {
    "P1": ["A", "B", "C", "D"],
    "P2": ["A", "B", "C", "D"],
    "P3": ["B", "A", "C", "D"],
}

# 3 options × 4 players: B wins honestly; NEITHER P1 nor P2 can move the
# outcome alone (the 3-option population has no single-player witness at all),
# but together they install A, which both rank above B.
_PAIR_PROFILE = {
    "P1": ["A", "B", "C"],
    "P2": ["A", "B", "C"],
    "P3": ["B", "A", "C"],
    "P4": ["B", "C", "A"],
}

# The #3524 fixture, kept here as the Condorcet control: three pairs can move
# the Condorcet outcome and every one of them installs a winner its movers rank
# below A, so the Condorcet counter reads 5 and its lists stay empty.
_CONDORCET_DROPPED = {
    "P1": ["A", "B", "C"],
    "P2": ["A", "B", "C"],
    "P3": ["B", "C", "A"],
}

_RANKINGS_3 = [list(order) for order in itertools.permutations(_OPTIONS_3)]


def _sweep(players: int) -> tuple[int, int, int]:
    """(profiles with a Borda winner, single-manipulable, pair-only)."""
    with_winner = single = pair_only = 0
    for combo in itertools.product(_RANKINGS_3, repeat=players):
        profile = {f"P{index + 1}": list(ballot) for index, ballot in enumerate(combo)}
        borda = compute_manipulability(profile, _OPTIONS_3)["borda"]
        if borda["winner"] is None:
            continue
        with_winner += 1
        if borda["single_player"]:
            single += 1
        elif borda["coalitions"]:
            pair_only += 1
    return with_winner, single, pair_only


class TestThePopulationIsPinned:
    def test_no_3_option_profile_is_single_manipulable(self) -> None:
        """The exhaustive 3×3 population, measured instead of asserted.

        186 of the 216 complete profiles have a unique Borda winner; none lets
        one player install a winner they rank higher than the honest one. The
        two zeros are the point: a fixture chosen by hand could not carry them.
        """
        assert _sweep(3) == (186, 0, 0)

    def test_pairs_appear_at_four_players_and_never_alone_at_three_options(
        self,
    ) -> None:
        """216 of the 1 296 complete 3×4 profiles are pair-manipulable, and
        still none is single-manipulable — the pair branch is not decoration."""
        assert _sweep(4) == (1044, 0, 216)


class TestTheEngineKeepsBeneficialWitnesses:
    def test_a_single_player_witness_carries_the_ballot_it_reports(self) -> None:
        game = compute_manipulability(_SINGLE_PROFILE, ["A", "B", "C", "D"])

        assert game["borda"]["winner"] == "A"
        assert game["borda"]["status"] == "ok"
        # One witness per (player, winner): the first ballot in permutation
        # order that installs B and passes the interest check.
        assert game["borda"]["single_player"] == [
            {"player": "P3", "ballot": ["B", "C", "D", "A"], "winner": "B"}
        ]
        assert game["borda"]["coalitions"] == []
        assert game["borda"]["exhaustive"] is True

    def test_a_pair_is_kept_only_where_neither_member_can_do_it_alone(self) -> None:
        game = compute_manipulability(_PAIR_PROFILE, _OPTIONS_3)

        borda = game["borda"]
        assert borda["winner"] == "B"
        # Neither member alone: the single-player block is empty (measured on
        # the whole 3-option population above), so the pair is the finding.
        assert borda["single_player"] == []
        assert len(borda["coalitions"]) == 1
        kept = borda["coalitions"][0]
        assert kept["players"] == ["P1", "P2"]
        assert kept["winner"] == "A"
        # Both ballots install A; both honest ballots rank A above B.
        assert kept["ballots"] == [["A", "C", "B"], ["A", "C", "B"]]

    def test_the_interest_check_is_load_bearing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The mutation control: with the check neutralised, 162 of the 186
        3×3 profiles grow a witness — the zero above is the check's work, not
        an empty enumeration."""
        monkeypatch.setattr(strategist, "_strictly_prefers", lambda *args: True)

        with_winner, single, _pair_only = _sweep(3)

        assert with_winner == 186
        assert single == 162


class TestTheBoundsAreStated:
    def test_a_tie_at_the_top_is_no_borda_winner(self) -> None:
        profile = {"P1": ["A", "B", "C"], "P2": ["B", "A", "C"]}
        game = compute_manipulability(profile, _OPTIONS_3)

        # Honest Borda scores tie at 3: the rule names no winner, and an
        # invented tie-break would be a choice the profile does not make.
        assert _borda_scores([profile["P1"], profile["P2"]], _OPTIONS_3) == {
            "A": 3,
            "B": 3,
            "C": 0,
        }
        assert borda_winner([profile["P1"], profile["P2"]], _OPTIONS_3) is None
        assert game["borda"]["winner"] is None
        assert game["borda"]["status"] == "no_borda_winner"
        assert game["borda"]["single_player"] == []
        assert game["borda"]["coalitions"] == []

    def test_a_seven_option_profile_states_its_cut(self) -> None:
        options = list("ABCDEFG")  # 7! = 5 040 > the 720 permutation cap
        profile = {f"P{index}": list(options) for index in range(3)}
        borda = compute_manipulability(profile, options)["borda"]

        assert borda["winner"] == "A"
        assert borda["status"] == "capped"
        assert borda["exhaustive"] is False
        assert borda["permutations_per_player"] == 5040
        assert borda["permutations_per_player"] > BORDA_PERMUTATION_CAP
        assert borda["ballots_examined"] == 0
        assert borda["ballots_required"] == 5040 * 3
        # A cut enumeration says nothing about what it did not score.
        assert borda["single_player"] == []

    def test_the_engine_is_deterministic(self) -> None:
        assert compute_manipulability(
            _PAIR_PROFILE, _OPTIONS_3
        ) == compute_manipulability(_PAIR_PROFILE, _OPTIONS_3)


class TestTheCondorcetBlockIsUntouched:
    def test_its_own_counter_and_lists_are_the_pre_3530_ones(self) -> None:
        game = compute_manipulability(_CONDORCET_DROPPED, _OPTIONS_3)

        # The #3524 measurement, unchanged by this PR: the Condorcet engine
        # keeps no witness and counts the 5 moves it removed.
        assert game["winner"] == "A"
        assert game["single_player"] == []
        assert game["coalitions"] == []
        assert game["dropped_against_interest"] == 5
        # The Borda block sits BESIDE it with its own counters — a ballot and
        # a promote-first move are not the same unit. On this fixture the two
        # rules do not even agree on the EXISTENCE of a winner: A wins every
        # pairwise contest, while the points tie A and B at 4.
        assert game["borda"]["winner"] is None
        assert game["borda"]["status"] == "no_borda_winner"
        assert game["borda"]["moved_not_kept"] == 0


class TestTheRenderNamesTheRule:
    def _block(self, game: dict) -> str:
        return _format_strategic_block({"players": [], "options": [], "game": game})

    def test_the_points_line_is_conditional_and_states_a_different_winner(
        self,
    ) -> None:
        game = {
            "status": "ok",
            "winner": "A",
            "single_player": [],
            "coalitions": [],
            "dropped_against_interest": 0,
            "borda": {
                "winner": "B",
                "status": "ok",
                "single_player": [
                    {"player": "P3", "ballot": ["C", "B", "A"], "winner": "C"}
                ],
                "coalitions": [],
            },
        }
        block = self._block(game)

        assert "Si l'issue se réglait aux points (Borda)" in block
        assert "Pivot aux points (Borda) : P3 pourrait reporter « C > B > A »" in block
        assert "le gagnant de Condorcet est « A »" in block
        # Never the players' stance: the line is a hypothesis (pourrait).
        assert "pourrait reporter" in block

    def test_no_borda_line_without_a_borda_block(self) -> None:
        game = {
            "status": "ok",
            "winner": "A",
            "single_player": [],
            "coalitions": [],
            "dropped_against_interest": 0,
        }
        assert "aux points (Borda)" not in self._block(game)

    def test_a_cut_enumeration_says_so_in_the_render(self) -> None:
        game = {
            "status": "ok",
            "winner": "A",
            "single_player": [],
            "coalitions": [],
            "dropped_against_interest": 0,
            "borda": {
                "winner": "A",
                "status": "capped",
                "permutations_per_player": 5040,
                "single_player": [],
                "coalitions": [],
            },
        }
        block = self._block(game)

        assert "Énumération aux points (Borda) BORNÉE" in block
        assert "ne conclus pas à la non-manipulabilité aux points" in block

    def test_the_note_states_the_rule_and_the_disagreement(self) -> None:
        note = coalition_note(
            {
                "manipulability": {
                    "kind": "single_player",
                    "rule": "borda",
                    "players": ["elector_vertu_a"],
                    "report": "arg_3 > arg_1 > arg_2",
                    "winner": "arg_3",
                    "baseline": "arg_2",
                    "condorcet_winner": "arg_1",
                }
            }
        )

        assert "si l'issue se réglait aux points (Borda)" in note
        assert "portant « arg_3 > arg_1 > arg_2 » en tête" in note
        assert (
            "Le gagnant de Condorcet, « arg_1 », diffère du gagnant aux points, "
            "« arg_2 »." in note
        )

    def test_a_legacy_record_keeps_the_neutral_heading(self) -> None:
        note = coalition_note(
            {
                "manipulability": {
                    "kind": "coalition",
                    "players": ["P1", "P2"],
                    "report": "arg_3",
                    "winner": "arg_3",
                    "baseline": "arg_2",
                }
            }
        )

        assert "moteur de #3385" in note
        assert "aux points (Borda)" not in note
