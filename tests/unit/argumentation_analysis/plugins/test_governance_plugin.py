# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.plugins.governance_plugin
Covers GovernancePlugin: detect_conflicts_fn, resolve_conflict_fn,
compute_consensus_metrics, list_governance_methods.
"""

import pytest
import json

from argumentation_analysis.plugins.governance_plugin import GovernancePlugin


@pytest.fixture
def plugin():
    return GovernancePlugin()


# ============================================================
# detect_conflicts_fn
# ============================================================


class TestDetectConflicts:
    def test_no_conflicts(self, plugin):
        positions = {"agent_a": "agree", "agent_b": "agree"}
        result = json.loads(plugin.detect_conflicts_fn(json.dumps(positions)))
        assert isinstance(result, list)

    def test_opposing_positions(self, plugin):
        positions = {"agent_a": "pour", "agent_b": "contre"}
        result = json.loads(plugin.detect_conflicts_fn(json.dumps(positions)))
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_empty_positions(self, plugin):
        result = json.loads(plugin.detect_conflicts_fn("{}"))
        assert isinstance(result, list)
        assert len(result) == 0

    def test_single_agent(self, plugin):
        positions = {"agent_a": "pour"}
        result = json.loads(plugin.detect_conflicts_fn(json.dumps(positions)))
        assert isinstance(result, list)

    def test_three_agents_mixed(self, plugin):
        positions = {"a": "pour", "b": "contre", "c": "pour"}
        result = json.loads(plugin.detect_conflicts_fn(json.dumps(positions)))
        assert isinstance(result, list)


# ============================================================
# resolve_conflict_fn
# ============================================================


class TestResolveConflict:
    def test_collaborative(self, plugin):
        conflict = {
            "agents": ["a", "b"],
            "positions": {"a": "pour", "b": "contre"},
            "conflict_level": "high",
        }
        result = json.loads(
            plugin.resolve_conflict_fn(json.dumps(conflict), strategy="collaborative")
        )
        assert isinstance(result, dict)

    def test_competitive(self, plugin):
        conflict = {
            "agents": ["a", "b"],
            "positions": {"a": "pour", "b": "contre"},
            "conflict_level": "medium",
        }
        result = json.loads(
            plugin.resolve_conflict_fn(json.dumps(conflict), strategy="competitive")
        )
        assert isinstance(result, dict)

    def test_arbitration(self, plugin):
        conflict = {
            "agents": ["a", "b"],
            "positions": {"a": "pour", "b": "contre"},
            "conflict_level": "low",
        }
        result = json.loads(
            plugin.resolve_conflict_fn(json.dumps(conflict), strategy="arbitration")
        )
        assert isinstance(result, dict)

    def test_default_strategy(self, plugin):
        conflict = {
            "agents": ["a", "b"],
            "positions": {"a": "x", "b": "y"},
            "conflict_level": "low",
        }
        result = json.loads(plugin.resolve_conflict_fn(json.dumps(conflict)))
        assert isinstance(result, dict)


# ============================================================
# compute_consensus_metrics
# ============================================================


class TestComputeConsensusMetrics:
    def test_unanimous(self, plugin):
        results = {"votes": ["X", "X", "X"], "winner": "X"}
        metrics = json.loads(plugin.compute_consensus_metrics(json.dumps(results)))
        assert "consensus_rate" in metrics
        assert metrics["consensus_rate"] == 1.0

    def test_split_vote(self, plugin):
        results = {"votes": ["X", "Y"], "winner": "X"}
        metrics = json.loads(plugin.compute_consensus_metrics(json.dumps(results)))
        assert "consensus_rate" in metrics
        assert metrics["consensus_rate"] == 0.5

    def test_has_fairness_key(self, plugin):
        results = {"votes": ["X", "X"], "winner": "X"}
        metrics = json.loads(plugin.compute_consensus_metrics(json.dumps(results)))
        assert "fairness_index" in metrics

    def test_has_satisfaction_key(self, plugin):
        results = {"votes": ["X", "X"], "winner": "X"}
        metrics = json.loads(plugin.compute_consensus_metrics(json.dumps(results)))
        assert "satisfaction" in metrics


# ============================================================
# list_governance_methods
# ============================================================


class TestListGovernanceMethods:
    def test_returns_list(self, plugin):
        result = json.loads(plugin.list_governance_methods())
        assert isinstance(result, dict)
        assert "agent_based" in result
        assert isinstance(result["agent_based"], list)

    def test_contains_majority(self, plugin):
        result = json.loads(plugin.list_governance_methods())
        # At least majority should be present
        assert len(result["agent_based"]) >= 1
