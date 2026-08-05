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
        # #1593: ``isinstance(result, list)`` passed even with detect_conflicts_fn
        # stubbed to report a fake conflict — it never checked emptiness. The name
        # promises NO conflicts, i.e. an empty list.
        assert result == [], f"expected no conflicts, got {result}"

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
        # #1593: a single agent cannot conflict with itself; the name promises
        # an empty list, not just a list. Stubbed to a fake conflict, the old
        # ``isinstance`` assertion still passed.
        assert result == [], f"expected no conflict for a single agent, got {result}"

    def test_three_agents_mixed(self, plugin):
        positions = {"a": "pour", "b": "contre", "c": "pour"}
        result = json.loads(plugin.detect_conflicts_fn(json.dumps(positions)))
        # #1593: ``isinstance(result, list)`` passed even with detect_conflicts_fn
        # stubbed to ``[]`` (no detection). The name "mixed" promises conflicts
        # ARE detected — mirrors test_opposing_positions.
        assert (
            len(result) >= 1
        ), f"expected conflicts among mixed positions, got {result}"


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
        # #1593: ``isinstance(result, dict)`` passed with resolve_conflict_fn
        # stubbed to a dict with no resolution fields. The name promises the
        # collaborative STRATEGY is honored — measured: resolution_type == collaborative.
        assert result.get("resolution_type") == "collaborative", result

    def test_competitive(self, plugin):
        conflict = {
            "agents": ["a", "b"],
            "positions": {"a": "pour", "b": "contre"},
            "conflict_level": "medium",
        }
        result = json.loads(
            plugin.resolve_conflict_fn(json.dumps(conflict), strategy="competitive")
        )
        # #1593: vacuous ``isinstance(result, dict)``. Name promises the
        # competitive strategy — measured: resolution_type == competitive.
        assert result.get("resolution_type") == "competitive", result

    def test_arbitration(self, plugin):
        conflict = {
            "agents": ["a", "b"],
            "positions": {"a": "pour", "b": "contre"},
            "conflict_level": "low",
        }
        result = json.loads(
            plugin.resolve_conflict_fn(json.dumps(conflict), strategy="arbitration")
        )
        # #1593: vacuous ``isinstance(result, dict)``. NOTE: arbitration currently
        # maps to the collaborative resolution in production (resolution_type ==
        # "collaborative"), so we assert the real invariant the name still implies
        # — the conflict's agents are carried through — rather than a strategy
        # value the code does not produce. Flagged in PR #1593; prod untouched.
        assert result.get("agents") == ["a", "b"], result

    def test_default_strategy(self, plugin):
        conflict = {
            "agents": ["a", "b"],
            "positions": {"a": "x", "b": "y"},
            "conflict_level": "low",
        }
        result = json.loads(plugin.resolve_conflict_fn(json.dumps(conflict)))
        # #1593: vacuous ``isinstance(result, dict)``. The default strategy still
        # resolves the conflict — the real invariant is the conflict's agents
        # are preserved in the resolution (stubbed to a keyless dict, this fails).
        assert result.get("agents") == ["a", "b"], result


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
