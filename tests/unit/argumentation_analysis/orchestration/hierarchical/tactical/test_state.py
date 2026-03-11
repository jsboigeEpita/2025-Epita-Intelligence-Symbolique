# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.tactical.state
Covers TacticalState: init, task lifecycle, assignments, dependencies,
progress, conflicts, rhetorical results, serialization, queries.
"""

import json
import pytest

from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)


@pytest.fixture
def state():
    return TacticalState()


def _make_task(task_id, objective_id="obj1"):
    return {"id": task_id, "description": f"Task {task_id}", "objective_id": objective_id}


# ============================================================
# Initialization
# ============================================================

class TestInit:
    def test_creates_instance(self, state):
        assert isinstance(state, TacticalState)

    def test_empty_objectives(self, state):
        assert state.assigned_objectives == []

    def test_task_statuses(self, state):
        assert set(state.tasks.keys()) == {"pending", "in_progress", "completed", "failed"}
        for v in state.tasks.values():
            assert v == []

    def test_empty_assignments(self, state):
        assert state.task_assignments == {}

    def test_empty_dependencies(self, state):
        assert state.task_dependencies == {}

    def test_empty_progress(self, state):
        assert state.task_progress == {}

    def test_empty_intermediate_results(self, state):
        assert state.intermediate_results == {}

    def test_rhetorical_analysis_results_keys(self, state):
        expected = {
            "complex_fallacy_analyses", "contextual_fallacy_analyses",
            "fallacy_severity_evaluations", "argument_structure_visualizations",
            "argument_coherence_evaluations", "semantic_argument_analyses",
            "contextual_fallacy_detections",
        }
        assert set(state.rhetorical_analysis_results.keys()) == expected

    def test_empty_conflicts(self, state):
        assert state.identified_conflicts == []

    def test_initial_metrics(self, state):
        assert state.tactical_metrics["task_completion_rate"] == 0.0
        assert state.tactical_metrics["agent_utilization"] == {}
        assert state.tactical_metrics["conflict_resolution_rate"] == 0.0

    def test_empty_actions_log(self, state):
        assert state.tactical_actions_log == []


# ============================================================
# add_assigned_objective
# ============================================================

class TestAddObjective:
    def test_add_one(self, state):
        state.add_assigned_objective({"id": "o1", "description": "test", "priority": "high"})
        assert len(state.assigned_objectives) == 1

    def test_add_multiple(self, state):
        for i in range(3):
            state.add_assigned_objective({"id": f"o{i}"})
        assert len(state.assigned_objectives) == 3


# ============================================================
# add_task / update_task_status
# ============================================================

class TestTaskLifecycle:
    def test_add_pending(self, state):
        state.add_task(_make_task("t1"))
        assert len(state.tasks["pending"]) == 1

    def test_add_in_progress(self, state):
        state.add_task(_make_task("t1"), status="in_progress")
        assert len(state.tasks["in_progress"]) == 1

    def test_add_invalid_status_ignored(self, state):
        state.add_task(_make_task("t1"), status="nonexistent")
        assert all(len(v) == 0 for v in state.tasks.values())

    def test_update_pending_to_in_progress(self, state):
        state.add_task(_make_task("t1"))
        result = state.update_task_status("t1", "in_progress")
        assert result is True
        assert len(state.tasks["pending"]) == 0
        assert len(state.tasks["in_progress"]) == 1

    def test_update_to_completed(self, state):
        state.add_task(_make_task("t1"), status="in_progress")
        assert state.update_task_status("t1", "completed") is True
        assert len(state.tasks["completed"]) == 1

    def test_update_nonexistent_task(self, state):
        assert state.update_task_status("nonexistent", "completed") is False

    def test_update_invalid_status(self, state):
        state.add_task(_make_task("t1"))
        assert state.update_task_status("t1", "bogus") is False


# ============================================================
# assign_task
# ============================================================

class TestAssignTask:
    def test_assign_existing_task(self, state):
        state.add_task(_make_task("t1"))
        assert state.assign_task("t1", "agent1") is True
        assert state.task_assignments["t1"] == "agent1"

    def test_assign_nonexistent_task(self, state):
        assert state.assign_task("nonexistent", "agent1") is False

    def test_reassign_task(self, state):
        state.add_task(_make_task("t1"))
        state.assign_task("t1", "agent1")
        state.assign_task("t1", "agent2")
        assert state.task_assignments["t1"] == "agent2"


# ============================================================
# add_task_dependency
# ============================================================

class TestTaskDependency:
    def test_add_dependency(self, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"))
        assert state.add_task_dependency("t1", "t2") is True
        assert "t2" in state.task_dependencies["t1"]

    def test_dependency_nonexistent_task(self, state):
        state.add_task(_make_task("t1"))
        assert state.add_task_dependency("t1", "nonexistent") is False

    def test_dependency_nonexistent_parent(self, state):
        state.add_task(_make_task("t1"))
        assert state.add_task_dependency("nonexistent", "t1") is False

    def test_no_duplicate_dependency(self, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"))
        state.add_task_dependency("t1", "t2")
        state.add_task_dependency("t1", "t2")
        assert state.task_dependencies["t1"].count("t2") == 1

    def test_get_task_dependencies(self, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"))
        state.add_task_dependency("t1", "t2")
        assert state.get_task_dependencies("t1") == ["t2"]

    def test_get_empty_dependencies(self, state):
        assert state.get_task_dependencies("nonexistent") == []


# ============================================================
# update_task_progress
# ============================================================

class TestTaskProgress:
    def test_update_progress(self, state):
        state.add_task(_make_task("t1"))
        assert state.update_task_progress("t1", 0.5) is True
        assert state.task_progress["t1"] == 0.5

    def test_clamp_above_one(self, state):
        state.add_task(_make_task("t1"))
        state.update_task_progress("t1", 1.5)
        assert state.task_progress["t1"] == 1.0

    def test_clamp_below_zero(self, state):
        state.add_task(_make_task("t1"))
        state.update_task_progress("t1", -0.5)
        assert state.task_progress["t1"] == 0.0

    def test_nonexistent_task(self, state):
        assert state.update_task_progress("nonexistent", 0.5) is False

    def test_auto_complete_on_full_progress(self, state):
        state.add_task(_make_task("t1"), status="in_progress")
        state.assign_task("t1", "agent1")
        state.update_task_progress("t1", 1.0)
        assert len(state.tasks["completed"]) == 1

    def test_completion_rate_updated(self, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"))
        state.update_task_status("t1", "completed")
        # Manually trigger rate update
        state._update_task_completion_rate()
        assert state.tactical_metrics["task_completion_rate"] == 0.5


# ============================================================
# Intermediate Results
# ============================================================

class TestIntermediateResults:
    def test_add_result(self, state):
        state.add_task(_make_task("t1"))
        assert state.add_intermediate_result("t1", {"score": 0.9}) is True
        assert state.intermediate_results["t1"]["score"] == 0.9

    def test_add_result_nonexistent_task(self, state):
        assert state.add_intermediate_result("nonexistent", "data") is False


# ============================================================
# Rhetorical Analysis Results
# ============================================================

class TestRhetoricalResults:
    def test_add_valid_type(self, state):
        state.add_task(_make_task("t1"))
        result = state.add_rhetorical_analysis_result("t1", "complex_fallacy_analyses", {"data": 1})
        assert result is True

    def test_add_invalid_type(self, state):
        state.add_task(_make_task("t1"))
        assert state.add_rhetorical_analysis_result("t1", "nonexistent_type", {}) is False

    def test_add_nonexistent_task(self, state):
        assert state.add_rhetorical_analysis_result("nonexistent", "complex_fallacy_analyses", {}) is False

    def test_get_result_by_type_and_task(self, state):
        state.add_task(_make_task("t1"))
        state.add_rhetorical_analysis_result("t1", "complex_fallacy_analyses", {"v": 42})
        result = state.get_rhetorical_analysis_result("complex_fallacy_analyses", "t1")
        assert result == {"v": 42}

    def test_get_all_results_for_type(self, state):
        state.add_task(_make_task("t1"))
        state.add_rhetorical_analysis_result("t1", "complex_fallacy_analyses", {"v": 1})
        results = state.get_rhetorical_analysis_result("complex_fallacy_analyses")
        assert isinstance(results, dict)
        assert "t1" in results

    def test_get_nonexistent_type(self, state):
        assert state.get_rhetorical_analysis_result("bogus_type") is None


# ============================================================
# Conflicts
# ============================================================

class TestConflicts:
    def test_add_conflict(self, state):
        state.add_conflict({"id": "c1", "description": "test", "severity": "high"})
        assert len(state.identified_conflicts) == 1

    def test_resolve_conflict(self, state):
        state.add_conflict({"id": "c1", "description": "test"})
        result = state.resolve_conflict("c1", {"method": "majority"})
        assert result is True
        assert state.identified_conflicts[0]["resolved"] is True

    def test_resolve_nonexistent_conflict(self, state):
        assert state.resolve_conflict("nonexistent", {}) is False

    def test_conflict_resolution_rate(self, state):
        state.add_conflict({"id": "c1"})
        state.add_conflict({"id": "c2"})
        state.resolve_conflict("c1", {"method": "vote"})
        assert state.tactical_metrics["conflict_resolution_rate"] == 0.5

    def test_no_conflicts_rate_is_one(self, state):
        state._update_conflict_resolution_rate()
        assert state.tactical_metrics["conflict_resolution_rate"] == 1.0


# ============================================================
# Agent utilization & action log
# ============================================================

class TestAgentUtilization:
    def test_set_utilization(self, state):
        state.update_agent_utilization("a1", 0.75)
        assert state.tactical_metrics["agent_utilization"]["a1"] == 0.75

    def test_clamp_utilization(self, state):
        state.update_agent_utilization("a1", 1.5)
        assert state.tactical_metrics["agent_utilization"]["a1"] == 1.0

    def test_log_action(self, state):
        state.log_tactical_action({"type": "test", "description": "hello"})
        assert len(state.tactical_actions_log) == 1


# ============================================================
# Queries
# ============================================================

class TestQueries:
    def test_get_pending_tasks(self, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"), status="in_progress")
        pending = state.get_pending_tasks()
        assert len(pending) == 1
        assert pending[0]["id"] == "t1"

    def test_get_tasks_for_agent(self, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"))
        state.assign_task("t1", "agent1")
        state.assign_task("t2", "agent2")
        tasks = state.get_tasks_for_agent("agent1")
        assert len(tasks) == 1
        assert tasks[0]["id"] == "t1"

    def test_get_tasks_for_agent_includes_status(self, state):
        state.add_task(_make_task("t1"))
        state.assign_task("t1", "agent1")
        tasks = state.get_tasks_for_agent("agent1")
        assert tasks[0]["status"] == "pending"

    def test_get_objective_for_task(self, state):
        state.add_task(_make_task("t1", objective_id="obj42"))
        assert state.get_objective_for_task("t1") == "obj42"

    def test_get_objective_for_nonexistent_task(self, state):
        assert state.get_objective_for_task("nonexistent") is None

    def test_are_all_tasks_done_true(self, state):
        state.add_task(_make_task("t1", "obj1"), status="completed")
        state.add_task(_make_task("t2", "obj1"), status="failed")
        assert state.are_all_tasks_for_objective_done("obj1") is True

    def test_are_all_tasks_done_false(self, state):
        state.add_task(_make_task("t1", "obj1"), status="completed")
        state.add_task(_make_task("t2", "obj1"), status="pending")
        assert state.are_all_tasks_for_objective_done("obj1") is False

    def test_are_all_tasks_done_no_tasks(self, state):
        assert state.are_all_tasks_for_objective_done("nonexistent") is False


# ============================================================
# Snapshots and summaries
# ============================================================

class TestSnapshots:
    def test_get_snapshot_structure(self, state):
        snap = state.get_snapshot()
        assert "objectives_count" in snap
        assert "tasks" in snap
        assert "conflicts" in snap
        assert "metrics" in snap

    def test_get_snapshot_task_counts(self, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"), status="completed")
        snap = state.get_snapshot()
        assert snap["tasks"]["pending"] == 1
        assert snap["tasks"]["completed"] == 1

    def test_get_status_summary(self, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"), status="failed")
        summary = state.get_status_summary()
        assert summary["total_tasks"] == 2
        assert summary["pending"] == 1
        assert summary["failed"] == 1

    def test_get_objective_results(self, state):
        state.add_task(_make_task("t1", "obj1"))
        state.add_intermediate_result("t1", {"score": 0.8})
        results = state.get_objective_results("obj1")
        assert "results" in results
        assert len(results["results"]) == 1
        assert results["results"][0]["result"]["score"] == 0.8

    def test_get_objective_results_empty(self, state):
        results = state.get_objective_results("nonexistent")
        assert results == {}


# ============================================================
# JSON serialization
# ============================================================

class TestSerialization:
    def test_to_json_is_valid(self, state):
        state.add_task(_make_task("t1"))
        state.add_assigned_objective({"id": "o1"})
        json_str = state.to_json()
        parsed = json.loads(json_str)
        assert "tasks" in parsed
        assert "assigned_objectives" in parsed

    def test_from_json_roundtrip(self, state):
        state.add_task(_make_task("t1"))
        state.add_assigned_objective({"id": "o1"})
        state.assign_task("t1", "agent1")
        state.update_task_progress("t1", 0.7)
        state.add_conflict({"id": "c1"})

        json_str = state.to_json()
        restored = TacticalState.from_json(json_str)

        assert len(restored.assigned_objectives) == 1
        assert restored.task_assignments["t1"] == "agent1"
        assert restored.task_progress["t1"] == 0.7
        assert len(restored.identified_conflicts) == 1

    def test_from_json_partial(self):
        partial = json.dumps({"tasks": {"pending": [{"id": "t1"}], "in_progress": [], "completed": [], "failed": []}})
        restored = TacticalState.from_json(partial)
        assert len(restored.tasks["pending"]) == 1

    def test_to_json_non_serializable_results(self, state):
        state.add_task(_make_task("t1"))
        state.add_intermediate_result("t1", object())  # Non-JSON-serializable
        json_str = state.to_json()
        parsed = json.loads(json_str)
        # Should be converted to string
        assert isinstance(parsed["intermediate_results"]["t1"], str)


# ============================================================
# Completion rate edge cases
# ============================================================

class TestCompletionRate:
    def test_zero_tasks(self, state):
        state._update_task_completion_rate()
        assert state.tactical_metrics["task_completion_rate"] == 0.0

    def test_all_completed(self, state):
        state.add_task(_make_task("t1"), status="completed")
        state.add_task(_make_task("t2"), status="completed")
        state._update_task_completion_rate()
        assert state.tactical_metrics["task_completion_rate"] == 1.0

    def test_mixed_statuses(self, state):
        state.add_task(_make_task("t1"), status="pending")
        state.add_task(_make_task("t2"), status="in_progress")
        state.add_task(_make_task("t3"), status="completed")
        state.add_task(_make_task("t4"), status="failed")
        state._update_task_completion_rate()
        assert state.tactical_metrics["task_completion_rate"] == 0.25
