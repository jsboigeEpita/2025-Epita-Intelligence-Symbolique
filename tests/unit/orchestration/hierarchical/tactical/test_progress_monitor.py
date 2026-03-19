# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.tactical.monitor
Covers ProgressMonitor: task progress updates, anomaly detection,
progress reports, critical issue detection, corrective actions, coherence eval.
"""

import pytest
from datetime import datetime, timedelta

from argumentation_analysis.orchestration.hierarchical.tactical.monitor import (
    ProgressMonitor,
)
from argumentation_analysis.orchestration.hierarchical.tactical.state import (
    TacticalState,
)


@pytest.fixture
def state():
    """Create a TacticalState with sample tasks."""
    s = TacticalState()
    s.add_assigned_objective(
        {"id": "obj-1", "description": "Analyze text", "priority": "high"}
    )
    s.add_task(
        {
            "id": "t1",
            "description": "Task 1",
            "objective_id": "obj-1",
            "estimated_duration": 60,
        },
        "pending",
    )
    s.add_task(
        {
            "id": "t2",
            "description": "Task 2",
            "objective_id": "obj-1",
            "estimated_duration": 120,
        },
        "pending",
    )
    return s


@pytest.fixture
def monitor(state):
    return ProgressMonitor(tactical_state=state)


# ============================================================
# __init__
# ============================================================


class TestProgressMonitorInit:
    def test_default_state(self):
        pm = ProgressMonitor()
        assert isinstance(pm.state, TacticalState)

    def test_custom_state(self, state):
        pm = ProgressMonitor(tactical_state=state)
        assert pm.state is state

    def test_default_thresholds(self):
        pm = ProgressMonitor()
        assert "task_delay" in pm.thresholds
        assert "progress_stagnation" in pm.thresholds
        assert "conflict_ratio" in pm.thresholds


# ============================================================
# update_task_progress
# ============================================================


class TestUpdateTaskProgress:
    def test_success(self, monitor, state):
        state.assign_task("t1", "agent-1")
        state.update_task_status("t1", "in_progress")
        result = monitor.update_task_progress("t1", 0.5)
        assert result["status"] == "success"
        assert result["current_progress"] == 0.5

    def test_task_not_found(self, monitor):
        result = monitor.update_task_progress("nonexistent", 0.5)
        assert result["status"] == "error"

    def test_previous_progress_tracked(self, monitor, state):
        state.update_task_status("t1", "in_progress")
        monitor.update_task_progress("t1", 0.3)
        result = monitor.update_task_progress("t1", 0.6)
        assert result["previous_progress"] == 0.3
        assert result["current_progress"] == 0.6

    def test_anomalies_returned(self, monitor, state):
        state.update_task_status("t1", "in_progress")
        monitor.update_task_progress("t1", 0.5)
        # Regression: progress goes backward
        result = monitor.update_task_progress("t1", 0.3)
        assert len(result["anomalies"]) > 0
        assert any(a["type"] == "regression" for a in result["anomalies"])


# ============================================================
# _check_task_anomalies
# ============================================================


class TestCheckTaskAnomalies:
    def test_stagnation_detected(self, monitor, state):
        state.update_task_status("t1", "in_progress")
        anomalies = monitor._check_task_anomalies("t1", 0.5, 0.52)
        assert any(a["type"] == "stagnation" for a in anomalies)

    def test_regression_detected(self, monitor, state):
        state.update_task_status("t1", "in_progress")
        anomalies = monitor._check_task_anomalies("t1", 0.5, 0.3)
        assert any(a["type"] == "regression" for a in anomalies)

    def test_no_anomaly_for_good_progress(self, monitor, state):
        state.update_task_status("t1", "in_progress")
        anomalies = monitor._check_task_anomalies("t1", 0.3, 0.6)
        assert not any(a["type"] == "stagnation" for a in anomalies)
        assert not any(a["type"] == "regression" for a in anomalies)

    def test_blocked_dependency(self, monitor, state):
        state.add_task(
            {
                "id": "t3",
                "description": "Task 3",
                "objective_id": "obj-1",
                "estimated_duration": 60,
            },
            "in_progress",
        )
        state.add_task_dependency("t1", "t3")
        state.update_task_status("t3", "failed")
        anomalies = monitor._check_task_anomalies("t1", 0.0, 0.1)
        assert any(a["type"] == "blocked_dependency" for a in anomalies)

    def test_nonexistent_task_returns_empty(self, monitor):
        anomalies = monitor._check_task_anomalies("fake", 0.0, 0.5)
        assert anomalies == []

    def test_near_completion_no_stagnation(self, monitor, state):
        state.update_task_status("t1", "in_progress")
        anomalies = monitor._check_task_anomalies("t1", 0.91, 0.92)
        assert not any(a["type"] == "stagnation" for a in anomalies)


# ============================================================
# generate_progress_report
# ============================================================


class TestGenerateProgressReport:
    def test_empty_state_report(self):
        pm = ProgressMonitor()
        report = pm.generate_progress_report()
        assert report["tasks_summary"]["total"] == 0
        assert report["overall_progress"] == 0.0

    def test_report_with_tasks(self, monitor, state):
        state.update_task_status("t1", "completed")
        report = monitor.generate_progress_report()
        assert report["tasks_summary"]["completed"] == 1
        assert report["tasks_summary"]["pending"] == 1
        assert report["overall_progress"] > 0.0

    def test_report_contains_issues_for_failed_tasks(self, monitor, state):
        state.update_task_status("t1", "failed")
        report = monitor.generate_progress_report()
        assert any(i["type"] == "task_failure" for i in report["issues"])

    def test_report_with_unresolved_conflicts(self, monitor, state):
        state.add_conflict(
            {
                "id": "c1",
                "description": "Conflict",
                "involved_tasks": ["t1"],
                "severity": "high",
            }
        )
        report = monitor.generate_progress_report()
        assert report["conflicts"]["total"] == 1
        assert report["conflicts"]["resolved"] == 0
        assert any(i["type"] == "conflict" for i in report["issues"])

    def test_progress_by_objective(self, monitor, state):
        state.update_task_status("t1", "completed")
        report = monitor.generate_progress_report()
        assert "obj-1" in report["progress_by_objective"]
        obj_progress = report["progress_by_objective"]["obj-1"]
        assert obj_progress["completed_tasks"] == 1
        assert obj_progress["progress"] > 0.0

    def test_in_progress_uses_actual_progress(self, monitor, state):
        state.update_task_status("t1", "in_progress")
        state.update_task_progress("t1", 0.7)
        report = monitor.generate_progress_report()
        assert report["overall_progress"] > 0.0

    def test_blocked_task_detected(self, monitor, state):
        state.add_task(
            {
                "id": "t3",
                "description": "Dep",
                "objective_id": "obj-1",
                "estimated_duration": 30,
            },
            "failed",
        )
        state.add_task_dependency("t1", "t3")
        report = monitor.generate_progress_report()
        assert any(i["type"] == "blocked_task" for i in report["issues"])


# ============================================================
# detect_critical_issues
# ============================================================


class TestDetectCriticalIssues:
    def test_no_issues_clean_state(self, monitor):
        issues = monitor.detect_critical_issues()
        assert issues == []

    def test_blocked_task(self, monitor, state):
        state.update_task_status("t1", "in_progress")
        state.add_task(
            {
                "id": "dep",
                "description": "Failed dep",
                "objective_id": "obj-1",
                "estimated_duration": 30,
            },
            "failed",
        )
        state.add_task_dependency("t1", "dep")
        issues = monitor.detect_critical_issues()
        blocked = [i for i in issues if i["type"] == "blocked_task"]
        assert len(blocked) >= 1
        assert "dep" in blocked[0]["blocked_by"]

    def test_high_failure_rate(self, monitor, state):
        # Make both tasks failed
        state.update_task_status("t1", "failed")
        state.update_task_status("t2", "failed")
        issues = monitor.detect_critical_issues()
        assert any(i["type"] == "high_failure_rate" for i in issues)

    def test_delayed_task_with_start_time(self, monitor, state):
        past = (datetime.now() - timedelta(seconds=200)).isoformat()
        state.update_task_status("t1", "in_progress")
        # Modify task to include start_time
        for task in state.tasks["in_progress"]:
            if task["id"] == "t1":
                task["start_time"] = past
                task["estimated_duration"] = 60  # 60 sec, but 200 elapsed
                break
        issues = monitor.detect_critical_issues()
        delayed = [i for i in issues if i["type"] == "delayed_task"]
        assert len(delayed) >= 1


# ============================================================
# suggest_corrective_actions
# ============================================================


class TestSuggestCorrectiveActions:
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
        assert actions[0]["action_type"] == "review_strategy"

    def test_empty_issues(self, monitor):
        actions = monitor.suggest_corrective_actions([])
        assert actions == []

    def test_multiple_issues(self, monitor):
        issues = [
            {"type": "blocked_task", "task_id": "t1", "blocked_by": ["dep1"]},
            {"type": "delayed_task", "task_id": "t2"},
            {"type": "conflict", "involved_tasks": ["t1", "t2"]},
        ]
        actions = monitor.suggest_corrective_actions(issues)
        assert len(actions) == 3


# ============================================================
# _evaluate_overall_coherence
# ============================================================


class TestEvaluateOverallCoherence:
    @pytest.fixture
    def monitor_fresh(self):
        return ProgressMonitor()

    def test_all_high_scores(self, monitor_fresh):
        result = monitor_fresh._evaluate_overall_coherence(
            {"coherence_score": 0.9},
            {"coherence_score": 0.9},
            {"coherence_score": 0.9},
            [],
        )
        assert result["overall_score"] == pytest.approx(0.9, abs=0.01)
        assert result["coherence_level"] == "Élevé"

    def test_all_low_scores(self, monitor_fresh):
        result = monitor_fresh._evaluate_overall_coherence(
            {"coherence_score": 0.1},
            {"coherence_score": 0.1},
            {"coherence_score": 0.1},
            [],
        )
        assert result["overall_score"] < 0.3
        assert result["coherence_level"] == "Très faible"

    def test_contradiction_penalty(self, monitor_fresh):
        no_contradictions = monitor_fresh._evaluate_overall_coherence(
            {"coherence_score": 0.8},
            {"coherence_score": 0.8},
            {"coherence_score": 0.8},
            [],
        )
        with_contradictions = monitor_fresh._evaluate_overall_coherence(
            {"coherence_score": 0.8},
            {"coherence_score": 0.8},
            {"coherence_score": 0.8},
            [{"severity": "critical"}, {"severity": "high"}],
        )
        assert with_contradictions["overall_score"] < no_contradictions["overall_score"]
        assert with_contradictions["contradiction_penalty"] > 0.0

    def test_penalty_capped_at_half(self, monitor_fresh):
        result = monitor_fresh._evaluate_overall_coherence(
            {"coherence_score": 1.0},
            {"coherence_score": 1.0},
            {"coherence_score": 1.0},
            [{"severity": "critical"}] * 10,  # Many contradictions
        )
        assert result["contradiction_penalty"] == 0.5

    def test_weights_sum(self, monitor_fresh):
        result = monitor_fresh._evaluate_overall_coherence(
            {"coherence_score": 1.0},
            {"coherence_score": 1.0},
            {"coherence_score": 1.0},
            [],
        )
        weights = result["weights_used"]
        assert sum(weights.values()) == pytest.approx(1.0)

    def test_missing_scores_default_zero(self, monitor_fresh):
        result = monitor_fresh._evaluate_overall_coherence({}, {}, {}, [])
        assert result["overall_score"] == 0.0

    def test_moderate_level(self, monitor_fresh):
        result = monitor_fresh._evaluate_overall_coherence(
            {"coherence_score": 0.7},
            {"coherence_score": 0.65},
            {"coherence_score": 0.7},
            [],
        )
        assert result["coherence_level"] == "Modéré"

    def test_contradictions_count(self, monitor_fresh):
        result = monitor_fresh._evaluate_overall_coherence(
            {"coherence_score": 0.5},
            {"coherence_score": 0.5},
            {"coherence_score": 0.5},
            [{"severity": "low"}, {"severity": "medium"}],
        )
        assert result["contradictions_count"] == 2


# ============================================================
# _log_action
# ============================================================


class TestLogAction:
    def test_logs_to_state(self, monitor, state):
        initial_log_count = len(state.tactical_actions_log)
        monitor._log_action("test_type", "test description")
        assert len(state.tactical_actions_log) == initial_log_count + 1
        last = state.tactical_actions_log[-1]
        assert last["type"] == "test_type"
        assert last["agent_id"] == "progress_monitor"
