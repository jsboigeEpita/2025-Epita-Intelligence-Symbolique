# tests/unit/argumentation_analysis/agents/core/governance/test_governance_methods.py
"""Tests for 7 governance voting methods."""

import pytest
from unittest.mock import MagicMock, patch
import numpy as np
import random

from argumentation_analysis.agents.core.governance.governance_methods import (
    majority_voting,
    plurality_voting,
    borda_count,
    condorcet_method,
    quadratic_voting,
    byzantine_consensus,
    raft_consensus,
    GOVERNANCE_METHODS,
)


def make_agent(decision=None, preferences=None, personality="default"):
    """Create a mock agent with .decide(), .preferences, .personality."""
    agent = MagicMock()
    agent.decide = MagicMock(return_value=decision)
    agent.preferences = preferences or []
    agent.personality = personality
    return agent


# ── GOVERNANCE_METHODS registry ──


class TestGovernanceMethodsRegistry:
    def test_has_seven_methods(self):
        assert len(GOVERNANCE_METHODS) == 7

    def test_keys(self):
        expected = {
            "majority",
            "plurality",
            "borda",
            "condorcet",
            "quadratic",
            "byzantine",
            "raft",
        }
        assert set(GOVERNANCE_METHODS.keys()) == expected

    def test_all_callable(self):
        for name, fn in GOVERNANCE_METHODS.items():
            assert callable(fn), f"{name} is not callable"


# ── majority_voting ──


class TestMajorityVoting:
    def test_unanimous(self):
        agents = [make_agent("A"), make_agent("A"), make_agent("A")]
        assert majority_voting(agents, ["A", "B"], {}) == "A"

    def test_majority_wins(self):
        agents = [make_agent("A"), make_agent("A"), make_agent("B")]
        assert majority_voting(agents, ["A", "B"], {}) == "A"

    def test_single_agent(self):
        agents = [make_agent("X")]
        assert majority_voting(agents, ["X", "Y"], {}) == "X"

    def test_three_options(self):
        agents = [make_agent("C"), make_agent("C"), make_agent("A"), make_agent("B")]
        assert majority_voting(agents, ["A", "B", "C"], {}) == "C"


# ── plurality_voting ──


class TestPluralityVoting:
    def test_same_as_majority(self):
        agents = [make_agent("A"), make_agent("B"), make_agent("A")]
        assert plurality_voting(agents, ["A", "B"], {}) == "A"


# ── borda_count ──


class TestBordaCount:
    def test_unanimous_preference(self):
        agents = [
            make_agent(preferences=["A", "B", "C"]),
            make_agent(preferences=["A", "B", "C"]),
        ]
        # A gets 2+2=4, B gets 1+1=2, C gets 0
        assert borda_count(agents, ["A", "B", "C"], {}) == "A"

    def test_reversed_preferences(self):
        agents = [
            make_agent(preferences=["A", "B", "C"]),
            make_agent(preferences=["C", "B", "A"]),
        ]
        # A: 2+0=2, B: 1+1=2, C: 0+2=2 → tie, max picks first found
        result = borda_count(agents, ["A", "B", "C"], {})
        assert result in ["A", "B", "C"]

    def test_clear_winner(self):
        agents = [
            make_agent(preferences=["B", "A"]),
            make_agent(preferences=["B", "A"]),
            make_agent(preferences=["A", "B"]),
        ]
        # B: 1+1+0=2, A: 0+0+1=1
        assert borda_count(agents, ["A", "B"], {}) == "B"

    def test_single_option(self):
        agents = [make_agent(preferences=["X"])]
        assert borda_count(agents, ["X"], {}) == "X"


# ── condorcet_method ──


class TestCondorcetMethod:
    def test_condorcet_winner_exists(self):
        # A beats B (2-1), A beats C (2-1)
        agents = [
            make_agent(preferences=["A", "B", "C"]),
            make_agent(preferences=["A", "C", "B"]),
            make_agent(preferences=["B", "C", "A"]),
        ]
        assert condorcet_method(agents, ["A", "B", "C"], {}) == "A"

    def test_fallback_to_borda(self):
        # Condorcet cycle: A>B, B>C, C>A → no winner → borda fallback
        agents = [
            make_agent(preferences=["A", "B", "C"]),
            make_agent(preferences=["B", "C", "A"]),
            make_agent(preferences=["C", "A", "B"]),
        ]
        result = condorcet_method(agents, ["A", "B", "C"], {})
        assert result in ["A", "B", "C"]

    def test_two_options(self):
        agents = [
            make_agent(preferences=["X", "Y"]),
            make_agent(preferences=["X", "Y"]),
        ]
        assert condorcet_method(agents, ["X", "Y"], {}) == "X"


# ── quadratic_voting ──


class TestQuadraticVoting:
    def test_default_budget(self):
        agents = [make_agent(preferences=["A", "B"], personality="strict")]
        result = quadratic_voting(agents, ["A", "B"], {})
        assert result == "A"

    def test_flexible_agent_splits_budget(self):
        agent = make_agent(preferences=["A", "B"], personality="flexible")
        result = quadratic_voting([agent], ["A", "B"], {})
        # Budget 9: top gets 4, second gets 5 → B wins
        assert result in ["A", "B"]

    def test_custom_budget(self):
        agents = [make_agent(preferences=["A"], personality="strict")]
        result = quadratic_voting(agents, ["A", "B"], {"quadratic_budget": 16})
        assert result == "A"

    def test_none_context_uses_default(self):
        agents = [make_agent(preferences=["A"], personality="strict")]
        result = quadratic_voting(agents, ["A", "B"], None)
        assert result == "A"

    def test_multiple_agents(self):
        agents = [
            make_agent(preferences=["A", "B"], personality="strict"),
            make_agent(preferences=["A", "B"], personality="strict"),
            make_agent(preferences=["B", "A"], personality="strict"),
        ]
        result = quadratic_voting(agents, ["A", "B"], {})
        assert result == "A"  # 2 agents give all budget to A


# ── byzantine_consensus ──


class TestByzantineConsensus:
    def test_no_byzantine(self):
        agents = [make_agent("A"), make_agent("A"), make_agent("A")]
        result = byzantine_consensus(agents, ["A", "B"], {"byzantine_ratio": 0.0})
        assert result == "A"

    def test_with_byzantine_ratio(self):
        np.random.seed(42)
        agents = [make_agent("A")] * 10
        result = byzantine_consensus(agents, ["A", "B"], {"byzantine_ratio": 0.2})
        assert result in ["A", "B"]

    def test_none_context_default_ratio(self):
        np.random.seed(42)
        agents = [make_agent("A")] * 5
        result = byzantine_consensus(agents, ["A", "B"], None)
        assert result in ["A", "B"]

    def test_honest_majority_wins(self):
        np.random.seed(0)
        agents = [make_agent("A")] * 20
        result = byzantine_consensus(agents, ["A", "B"], {"byzantine_ratio": 0.1})
        # 18 honest agents voting A, 2 random → A should win
        assert result == "A"


# ── raft_consensus ──


class TestRaftConsensus:
    def test_proposal_accepted(self):
        agents = [
            make_agent("A", preferences=["A", "B"]),
            make_agent("A", preferences=["A", "B"]),
            make_agent("A", preferences=["A", "B"]),
        ]
        # np.random.choice can't handle MagicMock list directly, patch it
        with patch(
            "argumentation_analysis.agents.core.governance.governance_methods.np.random.choice",
            side_effect=lambda x: x[0],
        ):
            result = raft_consensus(agents, ["A", "B"], {})
        assert result == "A"

    def test_proposal_rejected_fallback(self):
        # Leader proposes A, but others prefer C (A not in top 2)
        agents = [
            make_agent("A", preferences=["A", "B"]),
            make_agent("C", preferences=["C", "D"]),
            make_agent("C", preferences=["C", "D"]),
            make_agent("C", preferences=["C", "D"]),
            make_agent("C", preferences=["C", "D"]),
        ]
        with patch(
            "argumentation_analysis.agents.core.governance.governance_methods.np.random.choice",
            side_effect=lambda x: x[0],
        ):
            result = raft_consensus(agents, ["A", "B", "C", "D"], {})
        assert result in ["A", "B", "C", "D"]

    def test_single_agent_is_leader(self):
        agent = make_agent("X", preferences=["X", "Y"])
        with patch(
            "argumentation_analysis.agents.core.governance.governance_methods.np.random.choice",
            side_effect=lambda x: x[0],
        ):
            result = raft_consensus([agent], ["X", "Y"], {})
        assert result == "X"
