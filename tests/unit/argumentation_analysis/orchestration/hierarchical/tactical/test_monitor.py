# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.tactical.monitor
Covers ProgressMonitor: init, update_task_progress, anomaly detection,
progress reports, critical issues, corrective actions, coherence evaluation.
"""

import pytest
from datetime import datetime, timedelta

from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)
from argumentation_analysis.orchestration.hierarchical.tactical.monitor import (
    ProgressMonitor,
)


@pytest.fixture
def state():
    return TacticalState()


@pytest.fixture
def monitor(state):
    return ProgressMonitor(tactical_state=state)


def _make_task(task_id, obj_id="obj1", **extra):
    task = {"id": task_id, "description": f"Task {task_id}", "objective_id": obj_id}
    task.update(extra)
    return task


# ============================================================
# Initialization
# ============================================================


class TestInit:
    def test_creates_instance(self, monitor):
        assert isinstance(monitor, ProgressMonitor)

    def test_default_state(self):
        m = ProgressMonitor()
        assert isinstance(m.state, TacticalState)

    def test_custom_state(self, state, monitor):
        assert monitor.state is state

    def test_thresholds(self, monitor):
        assert "task_delay" in monitor.thresholds
        assert "progress_stagnation" in monitor.thresholds
        assert "conflict_ratio" in monitor.thresholds


# ============================================================
# update_task_progress
# ============================================================


class TestUpdateTaskProgress:
    def test_update_existing_task(self, monitor, state):
        state.add_task(_make_task("t1"))
        result = monitor.update_task_progress("t1", 0.5)
        assert result["status"] == "success"
        assert result["current_progress"] == 0.5

    def test_update_nonexistent_task(self, monitor):
        result = monitor.update_task_progress("nonexistent", 0.5)
        assert result["status"] == "error"

    def test_returns_anomalies(self, monitor, state):
        state.add_task(_make_task("t1"))
        result = monitor.update_task_progress("t1", 0.5)
        assert "anomalies" in result

    def test_previous_progress_tracked(self, monitor, state):
        state.add_task(_make_task("t1"))
        monitor.update_task_progress("t1", 0.3)
        result = monitor.update_task_progress("t1", 0.5)
        assert result["previous_progress"] == 0.3


# ============================================================
# _check_task_anomalies
# ============================================================


class TestCheckAnomalies:
    def test_stagnation_detected(self, monitor, state):
        state.add_task(_make_task("t1"))
        state.task_progress["t1"] = 0.3
        anomalies = monitor._check_task_anomalies("t1", 0.3, 0.35)
        stagnation = [a for a in anomalies if a["type"] == "stagnation"]
        assert len(stagnation) >= 1

    def test_no_stagnation_near_completion(self, monitor, state):
        state.add_task(_make_task("t1"))
        # Near completion (>0.9) should not flag stagnation
        anomalies = monitor._check_task_anomalies("t1", 0.9, 0.95)
        stagnation = [a for a in anomalies if a["type"] == "stagnation"]
        assert len(stagnation) == 0

    def test_regression_detected(self, monitor, state):
        state.add_task(_make_task("t1"))
        anomalies = monitor._check_task_anomalies("t1", 0.5, 0.3)
        regression = [a for a in anomalies if a["type"] == "regression"]
        assert len(regression) >= 1

    def test_blocked_dependency(self, monitor, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"), status="failed")
        state.add_task_dependency("t1", "t2")
        anomalies = monitor._check_task_anomalies("t1", 0.0, 0.1)
        blocked = [a for a in anomalies if a["type"] == "blocked_dependency"]
        assert len(blocked) >= 1

    def test_nonexistent_task(self, monitor):
        anomalies = monitor._check_task_anomalies("nonexistent", 0, 0.1)
        assert anomalies == []

    def test_good_progress_no_anomalies(self, monitor, state):
        state.add_task(_make_task("t1"))
        anomalies = monitor._check_task_anomalies("t1", 0.3, 0.6)
        assert len(anomalies) == 0


# ============================================================
# generate_progress_report
# ============================================================


class TestGenerateProgressReport:
    def test_empty_state(self, monitor):
        report = monitor.generate_progress_report()
        assert report["overall_progress"] == 0.0
        assert report["tasks_summary"]["total"] == 0

    def test_with_tasks(self, monitor, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"), status="completed")
        report = monitor.generate_progress_report()
        assert report["tasks_summary"]["total"] == 2
        assert report["tasks_summary"]["pending"] == 1
        assert report["tasks_summary"]["completed"] == 1

    def test_overall_progress(self, monitor, state):
        state.add_task(_make_task("t1"), status="completed")
        state.add_task(_make_task("t2"), status="completed")
        report = monitor.generate_progress_report()
        assert report["overall_progress"] == 1.0

    def test_in_progress_weighted(self, monitor, state):
        state.add_task(_make_task("t1"), status="in_progress")
        state.task_progress["t1"] = 0.5
        state.add_task(_make_task("t2"), status="completed")
        report = monitor.generate_progress_report()
        # t1: 0.5, t2: 1.0 => overall = (0.5 + 1.0) / 2 = 0.75
        assert report["overall_progress"] == 0.75

    def test_progress_by_objective(self, monitor, state):
        state.add_assigned_objective({"id": "obj1"})
        state.add_task(_make_task("t1", "obj1"), status="completed")
        state.add_task(_make_task("t2", "obj1"))
        report = monitor.generate_progress_report()
        assert "obj1" in report["progress_by_objective"]
        assert report["progress_by_objective"]["obj1"]["total_tasks"] == 2
        assert report["progress_by_objective"]["obj1"]["completed_tasks"] == 1

    def test_issues_include_conflicts(self, monitor, state):
        state.add_conflict(
            {"id": "c1", "description": "test conflict", "severity": "high"}
        )
        report = monitor.generate_progress_report()
        conflict_issues = [i for i in report["issues"] if i["type"] == "conflict"]
        assert len(conflict_issues) == 1

    def test_issues_include_failed_tasks(self, monitor, state):
        state.add_task(_make_task("t1"), status="failed")
        report = monitor.generate_progress_report()
        failure_issues = [i for i in report["issues"] if i["type"] == "task_failure"]
        assert len(failure_issues) == 1

    def test_issues_include_blocked_tasks(self, monitor, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"), status="failed")
        state.add_task_dependency("t1", "t2")
        report = monitor.generate_progress_report()
        blocked = [i for i in report["issues"] if i["type"] == "blocked_task"]
        assert len(blocked) == 1

    def test_has_timestamp(self, monitor):
        report = monitor.generate_progress_report()
        assert "timestamp" in report

    def test_has_conflicts_summary(self, monitor):
        report = monitor.generate_progress_report()
        assert "conflicts" in report
        assert "total" in report["conflicts"]
        assert "resolved" in report["conflicts"]


# ============================================================
# detect_critical_issues
# ============================================================


class TestDetectCriticalIssues:
    def test_no_issues(self, monitor):
        issues = monitor.detect_critical_issues()
        assert issues == []

    def test_blocked_task_detected(self, monitor, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("dep1"), status="failed")
        state.add_task_dependency("t1", "dep1")
        issues = monitor.detect_critical_issues()
        blocked = [i for i in issues if i["type"] == "blocked_task"]
        assert len(blocked) >= 1
        assert "dep1" in blocked[0]["blocked_by"]

    def test_high_failure_rate(self, monitor, state):
        # 3 failed out of 4 total = 75% failure rate > 20% threshold
        state.add_task(_make_task("t1"), status="failed")
        state.add_task(_make_task("t2"), status="failed")
        state.add_task(_make_task("t3"), status="failed")
        state.add_task(_make_task("t4"), status="completed")
        issues = monitor.detect_critical_issues()
        high_fail = [i for i in issues if i["type"] == "high_failure_rate"]
        assert len(high_fail) == 1

    def test_no_high_failure_rate_below_threshold(self, monitor, state):
        state.add_task(_make_task("t1"), status="failed")
        for i in range(10):
            state.add_task(_make_task(f"ok{i}"), status="completed")
        issues = monitor.detect_critical_issues()
        high_fail = [i for i in issues if i["type"] == "high_failure_rate"]
        assert len(high_fail) == 0

    def test_delayed_task_with_start_time(self, monitor, state):
        # Task started 2 hours ago with 1 hour estimated, progress at 10%
        past = (datetime.now() - timedelta(hours=2)).isoformat()
        state.add_task(
            _make_task("t1", start_time=past, estimated_duration=3600),
            status="in_progress",
        )
        state.task_progress["t1"] = 0.1
        issues = monitor.detect_critical_issues()
        delayed = [i for i in issues if i["type"] == "delayed_task"]
        assert len(delayed) >= 1


# ============================================================
# suggest_corrective_actions
# ============================================================


class TestSuggestCorrectiveActions:
    def test_no_issues(self, monitor):
        actions = monitor.suggest_corrective_actions([])
        assert actions == []

    def test_blocked_task_action(self, monitor):
        issues = [{"type": "blocked_task", "task_id": "t1", "blocked_by": ["dep1"]}]
        actions = monitor.suggest_corrective_actions(issues)
        assert len(actions) == 1
        assert actions[0]["action_type"] == "reassign_dependency"

    def test_delayed_task_action(self, monitor):
        issues = [{"type": "delayed_task", "task_id": "t1"}]
        actions = monitor.suggest_corrective_actions(issues)
        assert len(actions) == 1
        assert actions[0]["action_type"] == "allocate_resources"

    def test_conflict_action(self, monitor):
        issues = [{"type": "conflict", "involved_tasks": ["t1", "t2"]}]
        actions = monitor.suggest_corrective_actions(issues)
        assert len(actions) == 1
        assert actions[0]["action_type"] == "resolve_conflict"

    def test_high_failure_rate_action(self, monitor):
        issues = [{"type": "high_failure_rate"}]
        actions = monitor.suggest_corrective_actions(issues)
        assert len(actions) == 1
        assert actions[0]["action_type"] == "review_strategy"

    def test_multiple_issues(self, monitor):
        issues = [
            {"type": "blocked_task", "task_id": "t1", "blocked_by": ["dep1"]},
            {"type": "delayed_task", "task_id": "t2"},
            {"type": "high_failure_rate"},
        ]
        actions = monitor.suggest_corrective_actions(issues)
        assert len(actions) == 3


# ============================================================
# _evaluate_overall_coherence
# ============================================================


class TestEvaluateCoherence:
    def test_high_coherence(self, monitor):
        result = monitor._evaluate_overall_coherence(
            {"coherence_score": 0.9},
            {"coherence_score": 0.9},
            {"coherence_score": 0.9},
            [],
        )
        assert result["overall_score"] >= 0.8
        assert result["coherence_level"] == "Élevé"

    def test_moderate_coherence(self, monitor):
        result = monitor._evaluate_overall_coherence(
            {"coherence_score": 0.7},
            {"coherence_score": 0.7},
            {"coherence_score": 0.7},
            [],
        )
        assert result["coherence_level"] == "Modéré"

    def test_low_coherence(self, monitor):
        result = monitor._evaluate_overall_coherence(
            {"coherence_score": 0.4},
            {"coherence_score": 0.4},
            {"coherence_score": 0.5},
            [],
        )
        assert result["coherence_level"] == "Faible"

    def test_very_low_coherence(self, monitor):
        result = monitor._evaluate_overall_coherence(
            {"coherence_score": 0.1},
            {"coherence_score": 0.1},
            {"coherence_score": 0.1},
            [],
        )
        assert result["coherence_level"] == "Très faible"

    def test_contradiction_penalty(self, monitor):
        no_contradiction = monitor._evaluate_overall_coherence(
            {"coherence_score": 0.9},
            {"coherence_score": 0.9},
            {"coherence_score": 0.9},
            [],
        )
        with_contradiction = monitor._evaluate_overall_coherence(
            {"coherence_score": 0.9},
            {"coherence_score": 0.9},
            {"coherence_score": 0.9},
            [{"severity": "high"}],
        )
        assert with_contradiction["overall_score"] < no_contradiction["overall_score"]
        assert with_contradiction["contradiction_penalty"] > 0

    def test_max_penalty_capped(self, monitor):
        many_contradictions = [{"severity": "critical"}] * 10
        result = monitor._evaluate_overall_coherence(
            {"coherence_score": 1.0},
            {"coherence_score": 1.0},
            {"coherence_score": 1.0},
            many_contradictions,
        )
        assert result["contradiction_penalty"] == 0.5  # Capped at 0.5

    def test_result_structure(self, monitor):
        result = monitor._evaluate_overall_coherence(
            {"coherence_score": 0.5},
            {"coherence_score": 0.6},
            {"coherence_score": 0.7},
            [],
        )
        assert "overall_score" in result
        assert "coherence_level" in result
        assert "structure_contribution" in result
        assert "thematic_contribution" in result
        assert "logical_contribution" in result
        assert "weights_used" in result
        assert "component_scores" in result

    def test_weights_correct(self, monitor):
        result = monitor._evaluate_overall_coherence(
            {"coherence_score": 1.0},
            {"coherence_score": 0.0},
            {"coherence_score": 0.0},
            [],
        )
        # Only structure contributes: 1.0 * 0.3 = 0.3
        assert abs(result["overall_score"] - 0.3) < 0.01

    def test_zero_scores(self, monitor):
        result = monitor._evaluate_overall_coherence(
            {"coherence_score": 0.0},
            {"coherence_score": 0.0},
            {"coherence_score": 0.0},
            [],
        )
        assert result["overall_score"] == 0.0
