# tests/unit/argumentation_analysis/agents/core/governance/test_conflict_resolution.py
"""Tests for conflict detection and mediation strategies."""

import pytest

from argumentation_analysis.agents.core.governance.conflict_resolution import (
    detect_conflicts,
    resolve_conflict,
    collaborative_mediation,
    competitive_mediation,
    compromise_mediation,
)

# ── detect_conflicts ──


class TestDetectConflicts:
    def test_no_conflicts_same_positions(self):
        positions = {"A": "option1", "B": "option1", "C": "option1"}
        assert detect_conflicts(positions) == []

    def test_all_conflicts_different_positions(self):
        positions = {"A": "opt1", "B": "opt2", "C": "opt3"}
        conflicts = detect_conflicts(positions)
        assert len(conflicts) == 3  # A-B, A-C, B-C

    def test_partial_conflicts(self):
        positions = {"A": "opt1", "B": "opt1", "C": "opt2"}
        conflicts = detect_conflicts(positions)
        assert len(conflicts) == 2  # A-C, B-C

    def test_two_agents_conflict(self):
        positions = {"A": "yes", "B": "no"}
        conflicts = detect_conflicts(positions)
        assert len(conflicts) == 1
        assert set(conflicts[0]["agents"]) == {"A", "B"}
        assert conflicts[0]["conflict_level"] == 1.0

    def test_two_agents_agreement(self):
        positions = {"A": "yes", "B": "yes"}
        assert detect_conflicts(positions) == []

    def test_single_agent(self):
        positions = {"A": "opt1"}
        assert detect_conflicts(positions) == []

    def test_empty_positions(self):
        assert detect_conflicts({}) == []

    def test_conflict_agents_pair(self):
        positions = {"X": 1, "Y": 2}
        conflicts = detect_conflicts(positions)
        assert conflicts[0]["agents"] == ["X", "Y"]

    def test_four_agents_all_different(self):
        positions = {"A": 1, "B": 2, "C": 3, "D": 4}
        conflicts = detect_conflicts(positions)
        assert len(conflicts) == 6  # C(4,2) = 6

    def test_four_agents_two_groups(self):
        positions = {"A": "x", "B": "x", "C": "y", "D": "y"}
        conflicts = detect_conflicts(positions)
        # Conflicts: A-C, A-D, B-C, B-D
        assert len(conflicts) == 4


# ── resolve_conflict ──


class TestResolveConflict:
    @pytest.fixture
    def conflict(self):
        return {"agents": ["A", "B"], "conflict_level": 1.0}

    def test_collaborative_strategy(self, conflict):
        result = resolve_conflict(conflict, "collaborative")
        assert result["resolution_type"] == "collaborative"
        assert result["success_probability"] == 0.8
        assert result["agents"] == ["A", "B"]

    def test_competitive_strategy(self, conflict):
        result = resolve_conflict(conflict, "competitive")
        assert result["resolution_type"] == "competitive"
        assert result["success_probability"] == 0.5

    def test_compromise_strategy(self, conflict):
        result = resolve_conflict(conflict, "compromise")
        assert result["resolution_type"] == "compromise"
        assert result["success_probability"] == 0.7

    def test_default_strategy(self, conflict):
        result = resolve_conflict(conflict)
        assert result["resolution_type"] == "collaborative"

    def test_unknown_strategy_falls_back(self, conflict):
        result = resolve_conflict(conflict, "unknown_strategy")
        assert result["resolution_type"] == "collaborative"

    def test_agents_preserved(self, conflict):
        for strategy in ["collaborative", "competitive", "compromise"]:
            result = resolve_conflict(conflict, strategy)
            assert result["agents"] == ["A", "B"]


# ── Individual mediation functions ──


class TestMediationStrategies:
    @pytest.fixture
    def conflict(self):
        return {"agents": ["X", "Y"], "conflict_level": 1.0}

    def test_collaborative_mediation(self, conflict):
        result = collaborative_mediation(conflict)
        assert result["resolution_type"] == "collaborative"
        assert result["success_probability"] == 0.8
        assert "common ground" in result["details"]

    def test_competitive_mediation(self, conflict):
        result = competitive_mediation(conflict)
        assert result["resolution_type"] == "competitive"
        assert result["success_probability"] == 0.5
        assert "compete" in result["details"]

    def test_compromise_mediation(self, conflict):
        result = compromise_mediation(conflict)
        assert result["resolution_type"] == "compromise"
        assert result["success_probability"] == 0.7
        assert "middle ground" in result["details"]

    def test_all_results_have_agents(self, conflict):
        for fn in [
            collaborative_mediation,
            competitive_mediation,
            compromise_mediation,
        ]:
            result = fn(conflict)
            assert result["agents"] == ["X", "Y"]

    def test_all_results_have_details(self, conflict):
        for fn in [
            collaborative_mediation,
            competitive_mediation,
            compromise_mediation,
        ]:
            result = fn(conflict)
            assert isinstance(result["details"], str)
            assert len(result["details"]) > 0

    def test_success_probability_ordering(self, conflict):
        collab = collaborative_mediation(conflict)["success_probability"]
        comp = competitive_mediation(conflict)["success_probability"]
        compr = compromise_mediation(conflict)["success_probability"]
        assert collab > compr > comp


# ── Integration ──


class TestConflictResolutionIntegration:
    def test_detect_then_resolve(self):
        positions = {"Alice": "A", "Bob": "B"}
        conflicts = detect_conflicts(positions)
        assert len(conflicts) == 1
        resolution = resolve_conflict(conflicts[0])
        assert resolution["agents"] == ["Alice", "Bob"]
        assert resolution["resolution_type"] == "collaborative"

    def test_detect_and_resolve_all(self):
        positions = {"A": 1, "B": 2, "C": 3}
        conflicts = detect_conflicts(positions)
        resolutions = [resolve_conflict(c, "compromise") for c in conflicts]
        assert len(resolutions) == 3
        assert all(r["resolution_type"] == "compromise" for r in resolutions)

    def test_no_conflicts_no_resolution(self):
        positions = {"A": "same", "B": "same"}
        conflicts = detect_conflicts(positions)
        assert conflicts == []
