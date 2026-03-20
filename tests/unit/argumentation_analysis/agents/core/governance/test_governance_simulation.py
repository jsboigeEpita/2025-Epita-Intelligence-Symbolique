# tests/unit/argumentation_analysis/agents/core/governance/test_governance_simulation.py
"""Tests for governance simulation — Shapley values, gossip consensus, coalition formation."""

import pytest
from unittest.mock import MagicMock, patch
import math

from argumentation_analysis.agents.core.governance.simulation import (
    shapley_value,
    get_neighbors,
    distributed_gossip_consensus,
    simulate_governance,
)


def make_sim_agent(
    name, decision=None, preferences=None, personality="default", trust=None
):
    """Create a mock agent for simulation tests."""
    agent = MagicMock()
    agent.name = name
    agent.decide = MagicMock(
        return_value=decision or (preferences[0] if preferences else "A")
    )
    agent.preferences = preferences or ["A", "B"]
    agent.personality = personality
    agent.trust = trust or {}
    agent.coalition = None
    agent.update_memory = MagicMock()
    return agent


# ── shapley_value ──


class TestShapleyValue:
    def test_empty_coalition(self):
        result = shapley_value([], [], lambda s: 0)
        assert result == {}

    def test_single_agent(self):
        agent = make_sim_agent("A")
        payoff = lambda names: 1.0 if "A" in names else 0.0
        result = shapley_value([agent], [agent], payoff)
        assert abs(result["A"] - 1.0) < 1e-6

    def test_two_agents_equal(self):
        a1 = make_sim_agent("A")
        a2 = make_sim_agent("B")
        # Payoff = number of agents present
        payoff = lambda names: len(names)
        result = shapley_value([a1, a2], [a1, a2], payoff)
        assert abs(result["A"] - 1.0) < 1e-6
        assert abs(result["B"] - 1.0) < 1e-6

    def test_three_agents_additive(self):
        agents = [make_sim_agent(n) for n in ["A", "B", "C"]]
        payoff = lambda names: len(names)
        result = shapley_value(agents, agents, payoff)
        for name in ["A", "B", "C"]:
            assert abs(result[name] - 1.0) < 1e-6

    def test_values_sum_to_grand_coalition(self):
        agents = [make_sim_agent(n) for n in ["X", "Y"]]
        # Shapley values sum to v(N) - v(empty) = 3.0 - 0.0 = 3.0
        payoff = lambda names: (
            3.0 if len(names) == 2 else (1.0 if len(names) == 1 else 0.0)
        )
        result = shapley_value(agents, agents, payoff)
        total = sum(result.values())
        # v(N) - v(∅) = 3.0 - 0.0, but each agent's marginal is relative
        # X: (payoff({X})-payoff({})) + (payoff({X,Y})-payoff({Y})) / 2 each
        # = (1-0)/2 + (3-1)/2 = 0.5 + 1.0 = 1.5 each → total = 3.0
        assert abs(total - 3.0) < 1e-6


# ── get_neighbors ──


class TestGetNeighbors:
    def test_fully_connected(self):
        agents = [make_sim_agent(n) for n in ["A", "B", "C"]]
        adjacency = [[0, 1, 1], [1, 0, 1], [1, 1, 0]]
        neighbors = get_neighbors(agents[0], agents, adjacency)
        assert len(neighbors) == 2

    def test_no_connections(self):
        agents = [make_sim_agent(n) for n in ["A", "B", "C"]]
        adjacency = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
        neighbors = get_neighbors(agents[0], agents, adjacency)
        assert len(neighbors) == 0

    def test_self_not_included(self):
        agents = [make_sim_agent(n) for n in ["A", "B"]]
        adjacency = [[1, 1], [1, 1]]  # self-loop in matrix
        neighbors = get_neighbors(agents[0], agents, adjacency)
        assert all(n.name != "A" for n in neighbors)

    def test_partial_connections(self):
        agents = [make_sim_agent(n) for n in ["A", "B", "C"]]
        adjacency = [[0, 1, 0], [1, 0, 0], [0, 0, 0]]
        neighbors = get_neighbors(agents[0], agents, adjacency)
        assert len(neighbors) == 1
        assert neighbors[0].name == "B"


# ── distributed_gossip_consensus ──


class TestDistributedGossipConsensus:
    def test_all_agree(self):
        agents = [make_sim_agent(n, decision="X") for n in ["A", "B", "C"]]
        adjacency = [[0, 1, 1], [1, 0, 1], [1, 1, 0]]
        winner, votes = distributed_gossip_consensus(agents, ["X", "Y"], adjacency)
        assert winner == "X"

    def test_majority_converges(self):
        agents = [
            make_sim_agent("A", decision="X"),
            make_sim_agent("B", decision="X"),
            make_sim_agent("C", decision="Y"),
        ]
        adjacency = [[0, 1, 1], [1, 0, 1], [1, 1, 0]]
        winner, votes = distributed_gossip_consensus(
            agents, ["X", "Y"], adjacency, rounds=5
        )
        assert winner == "X"

    def test_returns_votes_dict(self):
        agents = [make_sim_agent("A", decision="X")]
        adjacency = [[0]]
        winner, votes = distributed_gossip_consensus(agents, ["X"], adjacency)
        assert "A" in votes

    def test_custom_rounds(self):
        agents = [make_sim_agent("A", decision="X")]
        adjacency = [[0]]
        winner, votes = distributed_gossip_consensus(agents, ["X"], adjacency, rounds=1)
        assert winner == "X"


# ── simulate_governance ──


class TestSimulateGovernance:
    def test_with_adjacency_networked(self):
        agents = [
            make_sim_agent("A", decision="X", preferences=["X", "Y"]),
            make_sim_agent("B", decision="X", preferences=["X", "Y"]),
        ]
        scenario = {
            "options": ["X", "Y"],
            "context": {"adjacency": [[0, 1], [1, 0]]},
        }
        result = simulate_governance(agents, scenario, "majority")
        assert result["networked"] is True
        assert result["winner"] == "X"
        assert "votes" in result
        assert "satisfaction" in result
        assert result["agent_names"] == ["A", "B"]

    def test_without_adjacency_coalition(self):
        agents = [
            make_sim_agent("A", decision="X", preferences=["X", "Y"], trust={}),
            make_sim_agent("B", decision="X", preferences=["X", "Y"], trust={}),
        ]
        scenario = {"options": ["X", "Y"], "context": {}}
        result = simulate_governance(agents, scenario, "majority")
        assert "coalitions" in result
        assert "coalition_payoffs" in result
        assert result["winner"] in ["X", "Y"]

    def test_satisfaction_values(self):
        agents = [
            make_sim_agent("A", decision="X", preferences=["X", "Y"]),
        ]
        scenario = {
            "options": ["X", "Y"],
            "context": {"adjacency": [[0]]},
        }
        result = simulate_governance(agents, scenario, "majority")
        assert all(0.0 <= s <= 1.0 for s in result["satisfaction"])

    def test_update_memory_called(self):
        agents = [make_sim_agent("A", decision="X", preferences=["X"])]
        scenario = {"options": ["X"], "context": {"adjacency": [[0]]}}
        simulate_governance(agents, scenario, "majority")
        agents[0].update_memory.assert_called_once()

    def test_coalition_formation_with_trust(self):
        a1 = make_sim_agent("A", decision="X", preferences=["X", "Y"])
        a2 = make_sim_agent("B", decision="X", preferences=["X", "Y"])
        a1.trust = {"B": 0.9}
        a2.trust = {"A": 0.9}
        scenario = {"options": ["X", "Y"], "context": {}}
        result = simulate_governance([a1, a2], scenario, "majority")
        # High trust should form coalition
        assert "coalitions" in result

    def test_conflicts_detected(self):
        agents = [
            make_sim_agent("A", decision="X", preferences=["X", "Y"], trust={}),
            make_sim_agent("B", decision="Y", preferences=["Y", "X"], trust={}),
        ]
        scenario = {"options": ["X", "Y"], "context": {}}
        result = simulate_governance(agents, scenario, "majority")
        assert "conflicts" in result
        assert "resolved_conflicts" in result

    def test_result_has_options(self):
        agents = [make_sim_agent("A", decision="X", preferences=["X"])]
        scenario = {"options": ["X", "Y"], "context": {"adjacency": [[0]]}}
        result = simulate_governance(agents, scenario, "majority")
        assert result["options"] == ["X", "Y"]
