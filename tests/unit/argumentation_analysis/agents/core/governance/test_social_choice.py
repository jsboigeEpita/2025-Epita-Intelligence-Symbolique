"""Tests for formal social choice theory methods.

Validates:
- Approval voting
- STV (Single Transferable Vote / Instant Runoff)
- Copeland's method
- Kemeny-Young optimal ranking
- Schulze (Beatpath) method
- Condorcet winner detection
- Pairwise matrix construction
- GovernancePlugin social choice integration
"""
import json
import pytest

from argumentation_analysis.agents.core.governance.social_choice import (
    approval_voting,
    stv,
    copeland,
    kemeny_young,
    schulze,
    condorcet_winner,
    pairwise_matrix,
    SOCIAL_CHOICE_METHODS,
)


# ──── Test Data ────

OPTIONS = ["A", "B", "C"]

# 5 voters: A>B>C, A>B>C, B>C>A, C>A>B, C>B>A
BALLOTS = [
    ["A", "B", "C"],
    ["A", "B", "C"],
    ["B", "C", "A"],
    ["C", "A", "B"],
    ["C", "B", "A"],
]

# Clear Condorcet winner: A wins pairwise against B and C
CONDORCET_BALLOTS = [
    ["A", "B", "C"],
    ["A", "C", "B"],
    ["A", "B", "C"],
    ["B", "A", "C"],
    ["C", "A", "B"],
]


# ──── Approval Voting Tests ────


class TestApprovalVoting:
    def test_basic_approval(self):
        winner, counts = approval_voting(BALLOTS, OPTIONS, approval_threshold=1)
        # First preferences: A=2, B=1, C=2
        assert counts["A"] == 2
        assert counts["B"] == 1
        assert counts["C"] == 2
        assert winner in ("A", "C")  # Tied

    def test_approval_threshold_2(self):
        winner, counts = approval_voting(BALLOTS, OPTIONS, approval_threshold=2)
        # Top-2: A gets approved by ballots 0,1,3 = 3; B by 0,1,2,4 = 4; C by 2,3,4 = 3
        assert counts["B"] == 4
        assert winner == "B"

    def test_unanimous(self):
        ballots = [["X", "Y"], ["X", "Y"], ["X", "Y"]]
        winner, counts = approval_voting(ballots, ["X", "Y"], approval_threshold=1)
        assert winner == "X"
        assert counts["X"] == 3

    def test_single_voter(self):
        winner, counts = approval_voting([["A", "B"]], ["A", "B"], approval_threshold=1)
        assert winner == "A"

    def test_empty_ballots(self):
        winner, counts = approval_voting([], ["A", "B"], approval_threshold=1)
        assert counts["A"] == 0
        assert counts["B"] == 0


# ──── STV Tests ────


class TestSTV:
    def test_irv_basic(self):
        winners, rounds = stv(BALLOTS, OPTIONS, seats=1)
        assert len(winners) == 1
        assert winners[0] in OPTIONS
        assert len(rounds) >= 1

    def test_irv_clear_majority(self):
        ballots = [["A", "B", "C"]] * 5 + [["B", "C", "A"]] * 2
        winners, rounds = stv(ballots, OPTIONS, seats=1)
        assert winners[0] == "A"  # A has majority in first round

    def test_irv_transfer(self):
        # B eliminated first, transfers to C
        ballots = [
            ["A", "B", "C"],
            ["A", "B", "C"],
            ["C", "B", "A"],
            ["C", "B", "A"],
            ["B", "C", "A"],  # B eliminated, vote goes to C
        ]
        winners, rounds = stv(ballots, OPTIONS, seats=1)
        # After B eliminated: A=2, C=3 → C wins
        assert winners[0] == "C"

    def test_multi_seat(self):
        ballots = [["A", "B", "C"]] * 3 + [["B", "C", "A"]] * 3 + [["C", "A", "B"]] * 3
        winners, rounds = stv(ballots, OPTIONS, seats=2)
        assert len(winners) == 2

    def test_single_candidate(self):
        winners, rounds = stv([["A"]], ["A"], seats=1)
        assert winners == ["A"]


# ──── Copeland Tests ────


class TestCopeland:
    def test_basic_copeland(self):
        winner, scores = copeland(BALLOTS, OPTIONS)
        assert winner in OPTIONS
        assert set(scores.keys()) == set(OPTIONS)

    def test_condorcet_winner_copeland(self):
        winner, scores = copeland(CONDORCET_BALLOTS, OPTIONS)
        assert winner == "A"
        # A beats B and C pairwise → score = 2
        assert scores["A"] == 2

    def test_two_candidates(self):
        ballots = [["A", "B"], ["A", "B"], ["B", "A"]]
        winner, scores = copeland(ballots, ["A", "B"])
        assert winner == "A"
        assert scores["A"] == 1
        assert scores["B"] == -1

    def test_complete_tie(self):
        # Condorcet cycle: A>B, B>C, C>A
        ballots = [
            ["A", "B", "C"],
            ["B", "C", "A"],
            ["C", "A", "B"],
        ]
        winner, scores = copeland(ballots, OPTIONS)
        # All have same score (each wins 1, loses 1)
        assert scores["A"] == scores["B"] == scores["C"]


# ──── Kemeny-Young Tests ────


class TestKemenyYoung:
    def test_basic_kemeny(self):
        ranking, score = kemeny_young(BALLOTS, OPTIONS)
        assert len(ranking) == 3
        assert set(ranking) == set(OPTIONS)
        assert score > 0

    def test_unanimous_ranking(self):
        ballots = [["A", "B", "C"]] * 5
        ranking, score = kemeny_young(ballots, OPTIONS)
        assert ranking == ["A", "B", "C"]

    def test_too_many_candidates_raises(self):
        big_options = [f"C{i}" for i in range(9)]
        with pytest.raises(ValueError, match="impractical"):
            kemeny_young([], big_options)

    def test_two_candidates(self):
        ballots = [["X", "Y"], ["X", "Y"], ["Y", "X"]]
        ranking, score = kemeny_young(ballots, ["X", "Y"])
        assert ranking == ["X", "Y"]


# ──── Schulze Tests ────


class TestSchulze:
    def test_basic_schulze(self):
        winner, paths = schulze(BALLOTS, OPTIONS)
        assert winner in OPTIONS
        assert set(paths.keys()) == set(OPTIONS)

    def test_condorcet_winner_schulze(self):
        winner, paths = schulze(CONDORCET_BALLOTS, OPTIONS)
        assert winner == "A"

    def test_two_candidates(self):
        ballots = [["A", "B"], ["A", "B"], ["B", "A"]]
        winner, paths = schulze(ballots, ["A", "B"])
        assert winner == "A"

    def test_paths_structure(self):
        _, paths = schulze(BALLOTS, OPTIONS)
        for a in OPTIONS:
            assert a in paths
            for b in OPTIONS:
                if a != b:
                    assert b in paths[a]
                    assert isinstance(paths[a][b], int)


# ──── Condorcet Winner Tests ────


class TestCondorcetWinner:
    def test_has_condorcet_winner(self):
        winner = condorcet_winner(CONDORCET_BALLOTS, OPTIONS)
        assert winner == "A"

    def test_no_condorcet_winner(self):
        # Condorcet cycle
        ballots = [
            ["A", "B", "C"],
            ["B", "C", "A"],
            ["C", "A", "B"],
        ]
        winner = condorcet_winner(ballots, OPTIONS)
        assert winner is None

    def test_single_candidate(self):
        winner = condorcet_winner([["A"]], ["A"])
        assert winner == "A"


# ──── Pairwise Matrix Tests ────


class TestPairwiseMatrix:
    def test_basic_matrix(self):
        matrix = pairwise_matrix(CONDORCET_BALLOTS, OPTIONS)
        assert set(matrix.keys()) == set(OPTIONS)
        # A should beat B: 4 out of 5 voters prefer A to B
        assert matrix["A"]["B"] >= 3

    def test_symmetric_ballots(self):
        ballots = [["A", "B"], ["B", "A"]]
        matrix = pairwise_matrix(ballots, ["A", "B"])
        assert matrix["A"]["B"] == 1
        assert matrix["B"]["A"] == 1


# ──── Registry Tests ────


class TestSocialChoiceRegistry:
    def test_all_methods_registered(self):
        assert "approval" in SOCIAL_CHOICE_METHODS
        assert "stv" in SOCIAL_CHOICE_METHODS
        assert "copeland" in SOCIAL_CHOICE_METHODS
        assert "kemeny_young" in SOCIAL_CHOICE_METHODS
        assert "schulze" in SOCIAL_CHOICE_METHODS
        assert len(SOCIAL_CHOICE_METHODS) == 5

    def test_methods_are_callable(self):
        for name, method in SOCIAL_CHOICE_METHODS.items():
            assert callable(method)


# ──── GovernancePlugin Integration Tests ────


class TestGovernancePluginSocialChoice:
    @pytest.fixture
    def plugin(self):
        from argumentation_analysis.plugins.governance_plugin import GovernancePlugin
        return GovernancePlugin()

    def test_list_methods_includes_social_choice(self, plugin):
        result = json.loads(plugin.list_governance_methods())
        assert "social_choice" in result
        assert "approval" in result["social_choice"]
        assert "schulze" in result["social_choice"]

    def test_social_choice_vote_copeland(self, plugin):
        input_data = {
            "method": "copeland",
            "ballots": CONDORCET_BALLOTS,
            "options": OPTIONS,
        }
        result = json.loads(plugin.social_choice_vote(json.dumps(input_data)))
        assert result["winner"] == "A"
        assert "copeland_scores" in result

    def test_social_choice_vote_approval(self, plugin):
        input_data = {
            "method": "approval",
            "ballots": BALLOTS,
            "options": OPTIONS,
            "approval_threshold": 2,
        }
        result = json.loads(plugin.social_choice_vote(json.dumps(input_data)))
        assert "winner" in result
        assert "approval_counts" in result

    def test_social_choice_vote_stv(self, plugin):
        input_data = {
            "method": "stv",
            "ballots": BALLOTS,
            "options": OPTIONS,
        }
        result = json.loads(plugin.social_choice_vote(json.dumps(input_data)))
        assert "winners" in result
        assert "rounds" in result

    def test_social_choice_vote_schulze(self, plugin):
        input_data = {
            "method": "schulze",
            "ballots": CONDORCET_BALLOTS,
            "options": OPTIONS,
        }
        result = json.loads(plugin.social_choice_vote(json.dumps(input_data)))
        assert result["winner"] == "A"

    def test_social_choice_unknown_method(self, plugin):
        input_data = {
            "method": "nonexistent",
            "ballots": BALLOTS,
            "options": OPTIONS,
        }
        result = json.loads(plugin.social_choice_vote(json.dumps(input_data)))
        assert "error" in result

    def test_find_condorcet_winner_plugin(self, plugin):
        input_data = {
            "ballots": CONDORCET_BALLOTS,
            "options": OPTIONS,
        }
        result = json.loads(plugin.find_condorcet_winner(json.dumps(input_data)))
        assert result["condorcet_winner"] == "A"
        assert "pairwise_matrix" in result

    def test_find_condorcet_no_winner(self, plugin):
        cycle_ballots = [
            ["A", "B", "C"],
            ["B", "C", "A"],
            ["C", "A", "B"],
        ]
        input_data = {
            "ballots": cycle_ballots,
            "options": OPTIONS,
        }
        result = json.loads(plugin.find_condorcet_winner(json.dumps(input_data)))
        assert result["condorcet_winner"] is None
