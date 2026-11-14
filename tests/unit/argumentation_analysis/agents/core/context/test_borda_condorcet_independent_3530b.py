"""#3530 suite (R1167 dispatch, item 2b) — the points block renders whatever
the Condorcet status.

The measured cause on the c8 panel: the engine computes ``borda`` on EVERY
usable profile (cycled ones included), but the render printed it only inside
the Condorcet-winner branch — 5 ``no_condorcet_winner`` documents, 12 points
witnesses on 4 of them (the fifth's points enumeration found no winner
either) that never reached the prompt. The restructure:

* the points block is hoisted out of the status branch and always rendered
  when the block exists (``_borda_lines``);
* the non-concluding line scopes its absence to Condorcet — it no longer
  forbids presenting ANY winner, which would contradict the points head
  printed right below it;
* the « aucun pivot » line is scoped to its rule, so a points witness that
  follows it does not read as contradicted;
* when Condorcet did not conclude, the points head says the points rule is
  the only one that names a winner.

Profiles through the REAL engine (``compute_manipulability``), render
through the REAL seam (``_format_strategic_block``). Synthetic players and
options only.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.context.strategist import (
    compute_manipulability,
)
from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    _format_strategic_block,
)

# A Condorcet cycle broken by a fourth ballot: A ties C pairwise (2–2) so no
# Condorcet winner exists, while the points give A 5, B 4, C 3 — the points
# rule names a winner the Condorcet contest cannot.
_CYCLED_WITH_POINTS_WINNER = {
    "P1": ["A", "B", "C"],
    "P2": ["B", "C", "A"],
    "P3": ["C", "A", "B"],
    "P4": ["A", "B", "C"],
}

_OPTIONS = ["A", "B", "C"]


def _block(game: dict) -> str:
    return _format_strategic_block({"players": [], "options": [], "game": game})


class TestThePointsBlockSurvivesACycle:
    def test_a_cycled_profile_still_renders_its_points_winner(self):
        game = compute_manipulability(_CYCLED_WITH_POINTS_WINNER, _OPTIONS)
        # the engine's own verdicts, measured here so the fixture cannot rot:
        # no Condorcet winner, a points winner, and the two disagree on the
        # very existence of one.
        assert game["status"] == "no_condorcet_winner"
        assert game["winner"] is None
        assert game["borda"]["winner"] == "A"

        block = _block(game)
        assert (
            "Si l'issue se réglait aux points (Borda) — gagnant CALCULÉ : « A »"
            in block
        )
        # the head says what the cycle means: points is the only rule that
        # names a winner here.
        assert "les points sont ici la seule règle qui désigne" in block
        # the non-concluding line is scoped, and the old blanket prohibition
        # (which would contradict the head printed below it) is gone.
        assert "aucun gagnant sous cette règle" in block
        assert "ne présente AUCUN gagnant" not in block

    def test_the_condorcet_line_precedes_the_points_head(self):
        game = compute_manipulability(_CYCLED_WITH_POINTS_WINNER, _OPTIONS)
        block = _block(game)
        assert block.index("Calcul (Condorcet) : non concluant") < block.index(
            "Si l'issue se réglait aux points"
        )

    def test_a_points_witness_on_a_cycled_profile_reaches_the_block(self):
        """The 12 lost witnesses of the c8 measure were pivots and
        coalitions, not just heads: a cycled profile with a points WITNESS
        renders the witness line too. The fixture is engine-measured: the
        pairwise contest ties A–C (no Condorcet winner), the points give A,
        and P3 + P4 together install C, which both rank above A."""
        profile = {
            "P1": ["A", "B", "C", "D"],
            "P2": ["A", "B", "C", "D"],
            "P3": ["B", "C", "A", "D"],
            "P4": ["C", "A", "B", "D"],
        }
        game = compute_manipulability(profile, ["A", "B", "C", "D"])
        assert game["status"] == "no_condorcet_winner"
        assert game["borda"]["winner"] == "A"
        assert game["borda"]["coalitions"], "fixture must carry a witness"
        assert game["borda"]["coalitions"][0]["players"] == ["P3", "P4"]

        block = _block(game)
        assert "Coalition aux points (Borda) : P3 + P4" in block


class TestTheAucunPivotLineIsRuleScoped:
    def test_the_no_pivot_line_does_not_silence_a_points_witness(self):
        """The order fix: « aucun pivot sous Condorcet » may precede a points
        witness — the line must say its bound is its OWN rule, or the reader
        takes the points witness as contradicted."""
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
        block = _block(game)
        assert "SOUS CETTE RÈGLE" in block
        assert block.index(
            "Aucun pivot CALCULÉ sous la règle de Condorcet"
        ) < block.index("Pivot aux points (Borda) : P3")


class TestTheOtherBranchesStayHonest:
    def test_an_insufficient_profile_names_no_points_winner(self):
        game = compute_manipulability({"P1": ["A"]}, _OPTIONS)
        assert game["status"] == "insufficient_profile"
        assert "borda" not in game
        block = _block(game)
        assert "aux points (Borda)" not in block
        assert "aucun gagnant sous cette règle" in block

    def test_a_winning_condorcet_game_keeps_its_order(self):
        """Non-regression: the ok branch still prints its winner first and
        the points head last — the restructure must be byte-order-neutral
        there."""
        game = compute_manipulability(
            {
                "P1": ["A", "B", "C"],
                "P2": ["A", "B", "C"],
                "P3": ["B", "A", "C"],
            },
            _OPTIONS,
        )
        assert game["status"] == "ok"
        block = _block(game)
        assert block.index("Gagnant CALCULÉ (Condorcet)") < block.index(
            "Si l'issue se réglait aux points"
        )
