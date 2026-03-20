# tests/unit/argumentation_analysis/agents/core/governance/test_governance_metrics.py
"""Tests for governance simulation metrics — consensus, fairness, efficiency, etc."""

import pytest
import numpy as np

from argumentation_analysis.agents.core.governance.metrics import (
    consensus_rate,
    gini,
    fairness_index,
    efficiency,
    satisfaction,
    stability,
    per_agent_satisfaction,
    summarize_results,
    validate_scenario,
)

# ── consensus_rate ──


class TestConsensusRate:
    def test_unanimous(self):
        assert consensus_rate({"votes": ["A", "A", "A"], "winner": "A"}) == 1.0

    def test_majority(self):
        r = consensus_rate({"votes": ["A", "A", "B"], "winner": "A"})
        assert r == pytest.approx(2 / 3)

    def test_no_winner(self):
        assert consensus_rate({"votes": ["A", "B"], "winner": None}) == 0.0

    def test_empty_votes(self):
        assert consensus_rate({"votes": [], "winner": "A"}) == 0.0

    def test_missing_keys(self):
        assert consensus_rate({}) == 0.0
        assert consensus_rate(None) == 0.0

    def test_winner_not_in_votes(self):
        assert consensus_rate({"votes": ["A", "B"], "winner": "C"}) == 0.0


# ── gini ──


class TestGini:
    def test_perfect_equality(self):
        g = gini([1, 1, 1, 1])
        assert g == pytest.approx(0.0, abs=0.01)

    def test_perfect_inequality(self):
        g = gini([0, 0, 0, 100])
        assert g > 0.5

    def test_empty(self):
        assert gini([]) == 0.0

    def test_single_element(self):
        g = gini([5])
        assert g == pytest.approx(0.0, abs=0.01)

    def test_negative_values(self):
        """Negative values are shifted to be non-negative."""
        g = gini([-2, -1, 0, 1, 2])
        assert 0 <= g <= 1

    def test_returns_float(self):
        assert isinstance(gini([1, 2, 3]), float)


# ── fairness_index ──


class TestFairnessIndex:
    def test_equal_satisfaction(self):
        r = {"satisfaction": [0.8, 0.8, 0.8]}
        f = fairness_index(r)
        assert f == pytest.approx(1.0, abs=0.01)

    def test_unequal_satisfaction(self):
        r = {"satisfaction": [0.0, 0.0, 0.0, 1.0]}
        f = fairness_index(r)
        assert f < 1.0

    def test_missing_key(self):
        assert fairness_index({}) == 0.0

    def test_none_input(self):
        assert fairness_index(None) == 0.0


# ── efficiency ──


class TestEfficiency:
    def test_one_round(self):
        assert efficiency({"rounds": 1}) == 1.0

    def test_max_rounds(self):
        assert efficiency({"rounds": 3}, max_rounds=3) == 0.0

    def test_two_of_three(self):
        e = efficiency({"rounds": 2}, max_rounds=3)
        assert e == pytest.approx(0.5)

    def test_none_input(self):
        assert efficiency(None) == 0

    def test_max_rounds_one(self):
        assert efficiency({"rounds": 1}, max_rounds=1) == 1.0

    def test_clamped_to_range(self):
        e = efficiency({"rounds": 10}, max_rounds=3)
        assert 0.0 <= e <= 1.0


# ── satisfaction ──


class TestSatisfaction:
    def test_mean(self):
        r = {"satisfaction": [0.5, 0.7, 0.9]}
        s = satisfaction(r)
        assert s == pytest.approx(0.7)

    def test_missing_key(self):
        assert satisfaction({}) == 0.0

    def test_none(self):
        assert satisfaction(None) == 0.0


# ── stability ──


class TestStability:
    def test_all_same_winner(self):
        results = [{"winner": "A"}, {"winner": "A"}, {"winner": "A"}]
        assert stability(results) == 1.0

    def test_different_winners(self):
        results = [{"winner": "A"}, {"winner": "B"}]
        assert stability(results) == 0.0

    def test_empty(self):
        assert stability([]) == 0.0

    def test_single_run(self):
        assert stability([{"winner": "A"}]) == 1.0


# ── per_agent_satisfaction ──


class TestPerAgentSatisfaction:
    def test_normal(self):
        r = {
            "agent_names": ["Alice", "Bob"],
            "satisfaction": [0.8, 0.6],
        }
        result = per_agent_satisfaction(r)
        assert result == {"Alice": 0.8, "Bob": 0.6}

    def test_missing_keys(self):
        assert per_agent_satisfaction({}) == {}
        assert per_agent_satisfaction(None) == {}


# ── summarize_results ──


class TestSummarizeResults:
    def test_single_run(self):
        r = {
            "votes": ["A", "A", "B"],
            "winner": "A",
            "satisfaction": [0.8, 0.7, 0.6],
            "rounds": 1,
        }
        summary = summarize_results(r)
        assert "consensus_rate" in summary
        assert "fairness" in summary
        assert "efficiency" in summary
        assert "satisfaction" in summary
        assert "stability" not in summary  # single run

    def test_batch_runs(self):
        runs = [
            {
                "votes": ["A", "A"],
                "winner": "A",
                "satisfaction": [0.9, 0.9],
                "rounds": 1,
            },
            {
                "votes": ["A", "B"],
                "winner": "A",
                "satisfaction": [0.8, 0.6],
                "rounds": 2,
            },
        ]
        summary = summarize_results(runs)
        assert "stability" in summary
        assert summary["consensus_rate"] > 0
        assert isinstance(summary["fairness"], float)


# ── validate_scenario ──


class TestValidateScenario:
    def test_valid(self):
        scenario = {
            "agents": [
                {"name": "A", "preferences": ["opt1", "opt2"]},
                {"name": "B", "preferences": ["opt2", "opt1"]},
            ],
            "options": ["opt1", "opt2"],
        }
        valid, msg = validate_scenario(scenario)
        assert valid is True
        assert msg == ""

    def test_missing_agents(self):
        valid, msg = validate_scenario({"options": ["a"]})
        assert valid is False
        assert "Missing" in msg

    def test_missing_options(self):
        valid, msg = validate_scenario({"agents": [{"name": "A", "preferences": []}]})
        assert valid is False

    def test_none_scenario(self):
        valid, msg = validate_scenario(None)
        assert valid is False

    def test_duplicate_agent_name(self):
        scenario = {
            "agents": [
                {"name": "A", "preferences": ["opt1"]},
                {"name": "A", "preferences": ["opt1"]},
            ],
            "options": ["opt1"],
        }
        valid, msg = validate_scenario(scenario)
        assert valid is False
        assert "Duplicate" in msg

    def test_invalid_preference(self):
        scenario = {
            "agents": [{"name": "A", "preferences": ["nonexistent"]}],
            "options": ["opt1"],
        }
        valid, msg = validate_scenario(scenario)
        assert valid is False
        assert "invalid preference" in msg

    def test_agent_missing_name(self):
        scenario = {
            "agents": [{"preferences": ["opt1"]}],
            "options": ["opt1"],
        }
        valid, msg = validate_scenario(scenario)
        assert valid is False
        assert "required fields" in msg

    def test_valid_adjacency_matrix(self):
        scenario = {
            "agents": [
                {"name": "A", "preferences": ["opt1"]},
                {"name": "B", "preferences": ["opt1"]},
            ],
            "options": ["opt1"],
            "context": {
                "adjacency": [[0, 1], [1, 0]],
            },
        }
        valid, msg = validate_scenario(scenario)
        assert valid is True

    def test_invalid_adjacency_matrix(self):
        scenario = {
            "agents": [
                {"name": "A", "preferences": ["opt1"]},
                {"name": "B", "preferences": ["opt1"]},
            ],
            "options": ["opt1"],
            "context": {
                "adjacency": [[0, 1]],  # only 1 row for 2 agents
            },
        }
        valid, msg = validate_scenario(scenario)
        assert valid is False
        assert "Adjacency" in msg
