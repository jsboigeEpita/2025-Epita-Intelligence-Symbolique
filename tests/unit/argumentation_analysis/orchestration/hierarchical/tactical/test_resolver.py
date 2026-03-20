# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.tactical.resolver
Covers ConflictResolver: init, detect_conflicts, resolve_conflict,
contradiction/overlap/fallacy/formal checking, escalation.
"""

import pytest

from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)
from argumentation_analysis.orchestration.hierarchical.tactical.resolver import (
    ConflictResolver,
)


@pytest.fixture
def state():
    return TacticalState()


@pytest.fixture
def resolver(state):
    return ConflictResolver(tactical_state=state)


def _make_task(task_id, obj_id="obj1"):
    return {"id": task_id, "description": f"Task {task_id}", "objective_id": obj_id}


# ============================================================
# Initialization
# ============================================================


class TestInit:
    def test_creates_instance(self, resolver):
        assert isinstance(resolver, ConflictResolver)

    def test_default_state(self):
        r = ConflictResolver()
        assert isinstance(r.state, TacticalState)

    def test_custom_state(self, state, resolver):
        assert resolver.state is state

    def test_has_resolution_strategies(self, resolver):
        assert "contradiction" in resolver.resolution_strategies
        assert "overlap" in resolver.resolution_strategies
        assert "inconsistency" in resolver.resolution_strategies
        assert "ambiguity" in resolver.resolution_strategies


# ============================================================
# _are_arguments_contradictory
# ============================================================


class TestAreArgumentsContradictory:
    def test_contradictory_est_nest_pas(self, resolver):
        arg1 = {"conclusion": "La terre est ronde"}
        arg2 = {"conclusion": "La terre n'est pas ronde"}
        assert resolver._are_arguments_contradictory(arg1, arg2) is True

    def test_contradictory_vrai_faux(self, resolver):
        arg1 = {"conclusion": "c'est vrai"}
        arg2 = {"conclusion": "c'est faux"}
        assert resolver._are_arguments_contradictory(arg1, arg2) is True

    def test_contradictory_toujours_jamais(self, resolver):
        arg1 = {"conclusion": "il faut toujours vérifier"}
        arg2 = {"conclusion": "il ne faut jamais vérifier"}
        assert resolver._are_arguments_contradictory(arg1, arg2) is True

    def test_not_contradictory(self, resolver):
        arg1 = {"conclusion": "La terre est ronde"}
        arg2 = {"conclusion": "La terre est bleue"}
        assert resolver._are_arguments_contradictory(arg1, arg2) is False

    def test_no_conclusion_field(self, resolver):
        assert (
            resolver._are_arguments_contradictory({"text": "a"}, {"text": "b"}) is False
        )


# ============================================================
# _are_arguments_overlapping
# ============================================================


class TestAreArgumentsOverlapping:
    def test_same_subject(self, resolver):
        arg1 = {"subject": "climat"}
        arg2 = {"subject": "climat"}
        assert resolver._are_arguments_overlapping(arg1, arg2) is True

    def test_subject_contained(self, resolver):
        arg1 = {"subject": "changement climatique"}
        arg2 = {"subject": "climat"}
        assert resolver._are_arguments_overlapping(arg1, arg2) is True

    def test_different_subjects(self, resolver):
        arg1 = {"subject": "économie"}
        arg2 = {"subject": "politique"}
        assert resolver._are_arguments_overlapping(arg1, arg2) is False

    def test_no_subject_field(self, resolver):
        assert resolver._are_arguments_overlapping({}, {}) is False


# ============================================================
# _are_fallacies_contradictory
# ============================================================


class TestAreFallaciesContradictory:
    def test_same_segment_different_type(self, resolver):
        f1 = {"segment": "les experts disent", "type": "appel_autorité"}
        f2 = {"segment": "les experts disent", "type": "appel_popularité"}
        assert resolver._are_fallacies_contradictory(f1, f2) is True

    def test_same_segment_same_type(self, resolver):
        f1 = {"segment": "les experts disent", "type": "appel_autorité"}
        f2 = {"segment": "les experts disent", "type": "appel_autorité"}
        assert resolver._are_fallacies_contradictory(f1, f2) is False

    def test_different_segment(self, resolver):
        f1 = {"segment": "segment A", "type": "type1"}
        f2 = {"segment": "segment B", "type": "type2"}
        assert resolver._are_fallacies_contradictory(f1, f2) is False

    def test_missing_fields(self, resolver):
        assert resolver._are_fallacies_contradictory({}, {}) is False


# ============================================================
# _are_formal_analyses_contradictory
# ============================================================


class TestAreFormalAnalysesContradictory:
    def test_same_arg_opposite_validity(self, resolver):
        a1 = {"argument_id": "arg1", "is_valid": True}
        a2 = {"argument_id": "arg1", "is_valid": False}
        assert resolver._are_formal_analyses_contradictory(a1, a2) is True

    def test_same_arg_same_validity(self, resolver):
        a1 = {"argument_id": "arg1", "is_valid": True}
        a2 = {"argument_id": "arg1", "is_valid": True}
        assert resolver._are_formal_analyses_contradictory(a1, a2) is False

    def test_different_args(self, resolver):
        a1 = {"argument_id": "arg1", "is_valid": True}
        a2 = {"argument_id": "arg2", "is_valid": False}
        assert resolver._are_formal_analyses_contradictory(a1, a2) is False

    def test_missing_fields(self, resolver):
        assert resolver._are_formal_analyses_contradictory({}, {}) is False


# ============================================================
# detect_conflicts
# ============================================================


class TestDetectConflicts:
    def test_no_existing_results(self, resolver):
        conflicts = resolver.detect_conflicts(
            {"identified_arguments": [{"conclusion": "A"}]}
        )
        assert isinstance(conflicts, list)
        assert len(conflicts) == 0  # No existing results to compare against

    def test_detects_argument_contradiction(self, resolver, state):
        # Set up existing results
        state.add_task(_make_task("t1", "obj1"))
        state.add_intermediate_result(
            "t1", {"identified_arguments": [{"conclusion": "La terre est ronde"}]}
        )
        # Detect conflicts with contradictory argument
        conflicts = resolver.detect_conflicts(
            {"identified_arguments": [{"conclusion": "La terre n'est pas ronde"}]}
        )
        assert len(conflicts) >= 1
        assert conflicts[0]["type"] == "contradiction"

    def test_detects_argument_overlap(self, resolver, state):
        state.add_task(_make_task("t1", "obj1"))
        state.add_intermediate_result(
            "t1", {"identified_arguments": [{"subject": "climat"}]}
        )
        conflicts = resolver.detect_conflicts(
            {"identified_arguments": [{"subject": "climat"}]}
        )
        assert len(conflicts) >= 1
        assert conflicts[0]["type"] == "overlap"

    def test_detects_fallacy_contradiction(self, resolver, state):
        state.add_task(_make_task("t1", "obj1"))
        state.add_intermediate_result(
            "t1", {"identified_fallacies": [{"segment": "test", "type": "type_a"}]}
        )
        conflicts = resolver.detect_conflicts(
            {"identified_fallacies": [{"segment": "test", "type": "type_b"}]}
        )
        assert len(conflicts) >= 1

    def test_detects_formal_contradiction(self, resolver, state):
        state.add_task(_make_task("t1", "obj1"))
        state.add_intermediate_result(
            "t1", {"formal_analyses": [{"argument_id": "arg1", "is_valid": True}]}
        )
        conflicts = resolver.detect_conflicts(
            {"formal_analyses": [{"argument_id": "arg1", "is_valid": False}]}
        )
        assert len(conflicts) >= 1

    def test_conflicts_added_to_state(self, resolver, state):
        state.add_task(_make_task("t1", "obj1"))
        state.add_intermediate_result(
            "t1", {"identified_arguments": [{"conclusion": "c'est vrai"}]}
        )
        resolver.detect_conflicts(
            {"identified_arguments": [{"conclusion": "c'est faux"}]}
        )
        assert len(state.identified_conflicts) >= 1

    def test_empty_results(self, resolver):
        conflicts = resolver.detect_conflicts({})
        assert conflicts == []

    def test_logs_action(self, resolver):
        resolver.detect_conflicts({})
        assert len(resolver.state.tactical_actions_log) >= 1


# ============================================================
# resolve_conflict
# ============================================================


class TestResolveConflict:
    def test_nonexistent_conflict(self, resolver):
        result = resolver.resolve_conflict("nonexistent")
        assert result["status"] == "error"

    def test_already_resolved(self, resolver, state):
        state.add_conflict(
            {
                "id": "c1",
                "type": "contradiction",
                "resolved": True,
                "resolution": {"method": "test"},
            }
        )
        result = resolver.resolve_conflict("c1")
        assert result["status"] == "already_resolved"

    def test_resolve_contradiction_with_args(self, resolver, state):
        state.add_conflict(
            {
                "id": "c1",
                "type": "contradiction",
                "severity": "medium",
                "details": {
                    "argument1": {"conclusion": "A", "confidence": 0.8},
                    "argument2": {"conclusion": "B", "confidence": 0.3},
                },
            }
        )
        result = resolver.resolve_conflict("c1")
        assert result["status"] == "success"
        assert result["resolution"]["method"] == "confidence_based"

    def test_resolve_contradiction_with_fallacies(self, resolver, state):
        state.add_conflict(
            {
                "id": "c1",
                "type": "contradiction",
                "details": {
                    "fallacy1": {"type": "a", "confidence": 0.9},
                    "fallacy2": {"type": "b", "confidence": 0.4},
                },
            }
        )
        result = resolver.resolve_conflict("c1")
        assert result["status"] == "success"
        assert result["resolution"]["method"] == "confidence_based"

    def test_resolve_contradiction_with_analyses(self, resolver, state):
        state.add_conflict(
            {
                "id": "c1",
                "type": "contradiction",
                "details": {
                    "analysis1": {
                        "argument_id": "a1",
                        "is_valid": True,
                        "confidence": 0.7,
                    },
                    "analysis2": {
                        "argument_id": "a1",
                        "is_valid": False,
                        "confidence": 0.6,
                    },
                },
            }
        )
        result = resolver.resolve_conflict("c1")
        assert result["status"] == "success"

    def test_resolve_contradiction_default(self, resolver, state):
        state.add_conflict({"id": "c1", "type": "contradiction", "details": {}})
        result = resolver.resolve_conflict("c1")
        assert result["status"] == "success"
        assert result["resolution"]["method"] == "default"

    def test_resolve_overlap(self, resolver, state):
        state.add_conflict(
            {
                "id": "c1",
                "type": "overlap",
                "details": {
                    "argument1": {
                        "id": "a1",
                        "subject": "X",
                        "premises": ["p1"],
                        "conclusion": "C",
                        "confidence": 0.8,
                    },
                    "argument2": {
                        "id": "a2",
                        "subject": "X",
                        "premises": ["p2"],
                        "conclusion": "D",
                        "confidence": 0.6,
                    },
                },
            }
        )
        result = resolver.resolve_conflict("c1")
        assert result["status"] == "success"
        assert result["resolution"]["method"] == "merge"

    def test_resolve_overlap_default(self, resolver, state):
        state.add_conflict({"id": "c1", "type": "overlap", "details": {}})
        result = resolver.resolve_conflict("c1")
        assert result["resolution"]["method"] == "default"

    def test_resolve_inconsistency(self, resolver, state):
        state.add_conflict({"id": "c1", "type": "inconsistency", "details": {}})
        result = resolver.resolve_conflict("c1")
        assert result["resolution"]["method"] == "recency"

    def test_resolve_ambiguity(self, resolver, state):
        state.add_conflict({"id": "c1", "type": "ambiguity", "details": {}})
        result = resolver.resolve_conflict("c1")
        assert result["resolution"]["method"] == "preserve_both"


# ============================================================
# escalate_unresolved_conflicts
# ============================================================


class TestEscalateUnresolved:
    def test_no_conflicts(self, resolver):
        result = resolver.escalate_unresolved_conflicts()
        assert result == []

    def test_unresolved_escalated(self, resolver, state):
        state.add_conflict({"id": "c1", "type": "contradiction", "severity": "high"})
        result = resolver.escalate_unresolved_conflicts()
        assert len(result) == 1
        assert result[0]["conflict_id"] == "c1"
        assert result[0]["resolution_attempt"] is None

    def test_resolved_not_escalated(self, resolver, state):
        state.add_conflict(
            {
                "id": "c1",
                "type": "contradiction",
                "resolved": True,
                "resolution": {"method": "confidence_based"},
            }
        )
        result = resolver.escalate_unresolved_conflicts()
        assert len(result) == 0

    def test_default_resolution_escalated(self, resolver, state):
        state.add_conflict(
            {
                "id": "c1",
                "type": "contradiction",
                "resolved": True,
                "resolution": {"method": "default"},
            }
        )
        result = resolver.escalate_unresolved_conflicts()
        assert len(result) == 1

    def test_mixed_conflicts(self, resolver, state):
        state.add_conflict(
            {"id": "c1", "resolved": True, "resolution": {"method": "confidence_based"}}
        )
        state.add_conflict({"id": "c2", "type": "overlap"})
        state.add_conflict(
            {"id": "c3", "resolved": True, "resolution": {"method": "default"}}
        )
        result = resolver.escalate_unresolved_conflicts()
        # c2 (unresolved) and c3 (default resolution) should be escalated
        assert len(result) == 2
