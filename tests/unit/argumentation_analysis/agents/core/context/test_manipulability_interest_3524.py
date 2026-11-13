"""#3524 — a manipulation witness must be one its movers have a reason to make.

The Gibbard-Satterthwaite definition of a manipulation is a misreport that
leaves the misreporting player strictly better off. The pre-#3524 engine
recorded every ballot change that MOVED the Condorcet winner, whatever the
mover got: the c5 and c6 panels measured 18/18 and 30/30 coalitions whose new
winner was ranked BELOW the baseline by at least one member. These witnesses
are born red against that engine — each profile below is one the old
enumeration populated, and the corrected engine must leave empty while
counting what it removed.

The kept lists come out empty on every profile that HAS a Condorcet winner,
and that is structural, not an accident of the fixtures: to install a winner
``T`` the movers must make ``T`` beat the baseline pairwise, and a ballot can
only raise its contribution to ``T``-over-baseline by flipping that contest —
i.e. only by belonging to a player who ranked the baseline ABOVE ``T`` (not
necessarily first). Every change needs at least one mover it harms, so no
witness whose movers ALL gain can exist at any coalition size
(``TestTheKeptListsAreEmptyOnEveryProfileWithAWinner`` measures it instead of
asserting it). What carries the measurement is therefore
``dropped_against_interest`` (with the bound stated where it is rendered), and
the positive branch of the check is exercised directly: the predicate on a
ballot, and the writer on a record carrying such a witness.
"""

from __future__ import annotations

import itertools

import pytest

from argumentation_analysis.agents.core.context import strategist
from argumentation_analysis.agents.core.context.strategist import (
    _strictly_prefers,
    compute_manipulability,
)
from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    _format_strategic_block,
)

_OPTIONS = ["A", "B", "C"]

# Three players rank A first and one ranks B first: A is the Condorcet winner,
# no single player can replace it, and three pairs can install B — the old
# engine reported all three as coalitions. Every pair member ranks A first, so
# every one of them ends up with a winner they rank below the baseline.
_PAIR_MOVES_AGAINST_INTEREST = {
    "P1": ["A", "B", "C"],
    "P2": ["A", "B", "C"],
    "P3": ["A", "B", "C"],
    "P4": ["B", "A", "C"],
}

# Two players rank A first, one ranks B first and B beats C: A still wins.
# The old engine reported three single-player pivots (each A-first member
# "moving" the outcome to B), all against the mover's own ballot.
_SINGLE_MOVES_AGAINST_INTEREST = {
    "P1": ["A", "B", "C"],
    "P2": ["A", "B", "C"],
    "P3": ["B", "C", "A"],
}


class TestTheInterestCheckRemovesAntiInterestWitnesses:
    def test_a_pair_that_can_move_but_prefers_the_baseline_is_not_a_witness(
        self,
    ) -> None:
        """Born red: the old engine returned three coalitions here."""
        game = compute_manipulability(_PAIR_MOVES_AGAINST_INTEREST, _OPTIONS)

        assert game["winner"] == "A"
        # The move exists — the pair CAN install B — but no member prefers it:
        # P1's own ballot ranks A above B, so the pair would vote against
        # itself to reach B.
        assert _strictly_prefers(["A", "B", "C"], "B", "A") is False
        assert game["coalitions"] == []
        assert game["dropped_against_interest"] == 3

    def test_a_single_pivot_against_its_own_ballot_is_not_a_witness(self) -> None:
        """Born red: the old engine returned two pivots and three coalitions
        here — five witnesses, every one of them installing a winner its
        movers rank below the baseline."""
        game = compute_manipulability(_SINGLE_MOVES_AGAINST_INTEREST, _OPTIONS)

        assert game["winner"] == "A"
        assert game["single_player"] == []
        assert game["dropped_against_interest"] == 5

    def test_a_profile_with_only_anti_interest_candidates_counts_them(self) -> None:
        """The counter separates "no candidate at all" from "all removed"."""
        profile = {
            "P1": ["A", "B", "C"],
            "P2": ["A", "C", "B"],
            "P3": ["A", "B", "C"],
        }
        game = compute_manipulability(profile, _OPTIONS)

        assert game["single_player"] == []
        assert game["coalitions"] == []
        # Three pairs can move the outcome, none of them beneficially.
        assert game["dropped_against_interest"] == 3

    def test_a_profile_no_move_can_reach_counts_zero(self) -> None:
        unanimous = {
            "P1": ["A", "B", "C"],
            "P2": ["A", "B", "C"],
            "P3": ["A", "B", "C"],
            "P4": ["A", "C", "B"],
        }
        game = compute_manipulability(unanimous, _OPTIONS)

        assert game["winner"] == "A"
        assert game["single_player"] == []
        assert game["coalitions"] == []
        assert game["dropped_against_interest"] == 0

    def test_an_undecided_profile_counts_nothing(self) -> None:
        cyclic = {
            "P1": ["A", "B", "C"],
            "P2": ["B", "C", "A"],
            "P3": ["C", "A", "B"],
        }
        game = compute_manipulability(cyclic, _OPTIONS)

        assert game["status"] == "no_condorcet_winner"
        assert game["dropped_against_interest"] == 0


class TestTheKeptListsAreEmptyOnEveryProfileWithAWinner:
    """The structural claim of the engine's docstring, measured.

    A docstring that says "no witness can exist" is a claim about every
    profile; three fixtures do not carry it. The complete profiles of three
    options are few enough to enumerate, and the same sweep run once on 3
    options x 5 players and 4 options x 3 and 4 players found the same zero
    (133 776 profiles with a winner in all).
    """

    @pytest.mark.parametrize(
        "players,with_winner,dropped", [(3, 204, 1116), (4, 576, 1872)]
    )
    def test_no_complete_profile_keeps_a_witness(
        self, players: int, with_winner: int, dropped: int
    ) -> None:
        rankings = [list(order) for order in itertools.permutations(_OPTIONS)]
        seen = removed = 0
        for combo in itertools.product(rankings, repeat=players):
            profile = {f"P{index}": list(b) for index, b in enumerate(combo)}
            game = compute_manipulability(profile, _OPTIONS)
            if game["winner"] is None:
                continue
            seen += 1
            removed += game["dropped_against_interest"]
            assert game["single_player"] == [], profile
            assert game["coalitions"] == [], profile
        # The population control: the sweep did meet profiles with a winner,
        # and moves to drop — an empty loop would pass the two asserts above.
        assert (seen, removed) == (with_winner, dropped)

    def test_the_harmed_mover_need_not_rank_the_baseline_first(self) -> None:
        """The reason is "ranked the baseline ABOVE the target", not "first".

        P1 ranks C first and A second. Reporting B first makes B win, at
        P1's expense (A sits above B on P1's ballot). A check that read "the
        mover's first choice is not the baseline" would keep this as a
        manipulation; the engine drops it.
        """
        profile = {
            "P1": ["C", "A", "B"],
            "P2": ["A", "B", "C"],
            "P3": ["B", "A", "C"],
        }
        game = compute_manipulability(profile, _OPTIONS)

        assert game["winner"] == "A"
        assert profile["P1"][0] != "A"
        assert {"player": "P1", "reports": "B", "winner": "B"} not in game[
            "single_player"
        ]
        assert game["single_player"] == []
        assert game["dropped_against_interest"] > 0

    def test_a_pair_with_one_member_who_gains_is_still_not_a_witness(self) -> None:
        """BOTH members, not one: P3 ranks B above A and gains when P1 and P3
        install B, but P1 pays for it. The render says "au moins un des
        porteurs" for that reason — in a dropped pair one member may gain."""
        game = compute_manipulability(_SINGLE_MOVES_AGAINST_INTEREST, _OPTIONS)

        assert _strictly_prefers(_SINGLE_MOVES_AGAINST_INTEREST["P3"], "B", "A")
        assert not _strictly_prefers(_SINGLE_MOVES_AGAINST_INTEREST["P1"], "B", "A")
        assert game["coalitions"] == []


class TestTheCountIsTheOldEnumeration:
    @staticmethod
    def _old_enumeration(profile: dict) -> int:
        """The pre-#3524 witness count, re-derived independently in the test.

        Same ballot change, same ``winner != baseline`` test, no interest
        check — exactly what the engine recorded before #3524.
        """
        from argumentation_analysis.agents.core.governance.social_choice import (
            condorcet_winner,
        )

        def reports_first(ballot: list, target: str) -> list:
            return [target] + [name for name in ballot if name != target]

        players = list(profile)
        ballots = [list(profile[player]) for player in players]
        baseline = condorcet_winner(ballots, _OPTIONS)
        count = 0
        for index in range(len(players)):
            for target in _OPTIONS:
                if target == baseline:
                    continue
                trial = list(ballots)
                trial[index] = reports_first(ballots[index], target)
                winner = condorcet_winner(trial, _OPTIONS)
                if winner is not None and winner != baseline:
                    count += 1
        for first in range(len(players)):
            for second in range(first + 1, len(players)):
                for target in _OPTIONS:
                    if target == baseline:
                        continue
                    trial = list(ballots)
                    trial[first] = reports_first(ballots[first], target)
                    trial[second] = reports_first(ballots[second], target)
                    winner = condorcet_winner(trial, _OPTIONS)
                    if winner is not None and winner != baseline:
                        count += 1
                        break
        return count

    @pytest.mark.parametrize(
        "profile",
        [_PAIR_MOVES_AGAINST_INTEREST, _SINGLE_MOVES_AGAINST_INTEREST],
        ids=["pairs-only", "pivots-and-pairs"],
    )
    def test_the_counter_equals_what_the_old_engine_recorded(self, profile) -> None:
        """The count is COMPLETE, not merely non-zero: every witness the old
        enumeration produced is accounted for, none silently vanishes."""
        old_total = self._old_enumeration(profile)
        game = compute_manipulability(profile, _OPTIONS)

        assert old_total > 0  # the fixtures are ones the old engine populated
        assert game["dropped_against_interest"] == old_total

    def test_the_predicate_accepts_a_ballot_that_prefers_the_new_winner(
        self,
    ) -> None:
        """The positive branch, on the only object that can carry it."""
        assert _strictly_prefers(["B", "A", "C"], "B", "A") is True
        # Absent from the scored ballot: no declared preference, no witness.
        assert _strictly_prefers(["A", "B"], "C", "A") is False


class TestTheWriterNeverClaimsAnAntiInterestMove:
    def _block(self, game: dict) -> str:
        return _format_strategic_block({"players": [], "options": [], "game": game})

    def test_a_beneficial_single_witness_is_rendered_as_a_preference(self) -> None:
        game = {
            "status": "ok",
            "winner": "A",
            "single_player": [{"player": "P1", "reports": "B", "winner": "B"}],
            "coalitions": [],
            "dropped_against_interest": 0,
        }
        block = self._block(game)

        assert "que son bulletin classe devant « A »" in block
        assert "peut porter" not in block

    def test_a_beneficial_coalition_is_rendered_as_a_shared_preference(self) -> None:
        game = {
            "status": "ok",
            "winner": "A",
            "single_player": [],
            "coalitions": [{"players": ["P1", "P2"], "report": "B", "winner": "B"}],
            "dropped_against_interest": 0,
        }
        block = self._block(game)

        assert "que leurs bulletins classent devant « A »" in block
        assert "portent « B » en tête" not in block

    def test_the_empty_case_states_the_bound_and_names_no_manipulation(self) -> None:
        game = {
            "status": "ok",
            "winner": "A",
            "single_player": [],
            "coalitions": [],
            "dropped_against_interest": 0,
        }
        block = self._block(game)

        assert "profil non manipulable par un joueur seul ni par une paire" in block
        assert "ÉCARTÉS" not in block

    def test_the_removed_candidates_are_counted_in_the_render(self) -> None:
        """Never silent: a reader seeing only the empty list would think the
        profile was never tested."""
        game = {
            "status": "ok",
            "winner": "A",
            "single_player": [],
            "coalitions": [],
            "dropped_against_interest": 13,
        }
        block = self._block(game)

        assert "Déplacements ÉCARTÉS (13)" in block
        assert "DERRIÈRE le gagnant actuel" in block
        # The bound that is true of every dropped move: one mover harmed, not
        # necessarily all of them.
        assert "au moins un des porteurs de chaque déplacement" in block
        assert "profil non manipulable par un joueur seul ni par une paire" in block


class TestTheGuardIsLoadBearing:
    def test_neutralising_the_check_brings_the_witnesses_back(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The mutation control, kept as a witness.

        Remove the interest check and the first test of this file goes red:
        the three coalitions of ``_PAIR_MOVES_AGAINST_INTEREST`` come back.
        """
        monkeypatch.setattr(strategist, "_strictly_prefers", lambda *a: True)

        game = compute_manipulability(_PAIR_MOVES_AGAINST_INTEREST, _OPTIONS)

        assert len(game["coalitions"]) == 3
        assert game["dropped_against_interest"] == 0
