# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.operational.state
Covers OperationalState: init, task management, text extracts, analysis results,
issues, metrics, action log, queries, clear, tactical task lookup.
"""

import asyncio
import pytest

from argumentation_analysis.orchestration.hierarchical.operational.state import (
    OperationalState,
)


@pytest.fixture
def state():
    return OperationalState()


def _make_task(task_id="t1", **extra):
    base = {"id": task_id, "description": f"Task {task_id}"}
    base.update(extra)
    return base


# ============================================================
# Initialization
# ============================================================

class TestInit:
    def test_creates_instance(self, state):
        assert isinstance(state, OperationalState)

    def test_assigned_tasks_empty(self, state):
        assert state.assigned_tasks == []

    def test_text_extracts_empty(self, state):
        assert state.text_extracts == {}

    def test_analysis_results_has_categories(self, state):
        assert "identified_arguments" in state.analysis_results
        assert "identified_fallacies" in state.analysis_results
        assert "formal_analyses" in state.analysis_results

    def test_encountered_issues_empty(self, state):
        assert state.encountered_issues == []

    def test_operational_metrics_structure(self, state):
        assert "processing_times" in state.operational_metrics
        assert "confidence_scores" in state.operational_metrics
        assert "coverage_metrics" in state.operational_metrics

    def test_actions_log_empty(self, state):
        assert state.operational_actions_log == []


# ============================================================
# add_task
# ============================================================

class TestAddTask:
    def test_adds_task(self, state):
        task_id = state.add_task(_make_task("t1"))
        assert task_id == "t1"
        assert len(state.assigned_tasks) == 1

    def test_sets_pending_status(self, state):
        state.add_task(_make_task("t1"))
        assert state.assigned_tasks[0]["status"] == "pending"

    def test_sets_assigned_at(self, state):
        state.add_task(_make_task("t1"))
        assert "assigned_at" in state.assigned_tasks[0]

    def test_duplicate_returns_existing_id(self, state):
        state.add_task(_make_task("t1"))
        task_id = state.add_task(_make_task("t1"))
        assert task_id == "t1"
        assert len(state.assigned_tasks) == 1

    def test_auto_generates_id(self, state):
        task_id = state.add_task({"description": "No ID"})
        assert task_id.startswith("op-")

    def test_multiple_tasks(self, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"))
        assert len(state.assigned_tasks) == 2


# ============================================================
# update_task_status
# ============================================================

class TestUpdateTaskStatus:
    def test_updates_status(self, state):
        state.add_task(_make_task("t1"))
        result = state.update_task_status("t1", "in_progress")
        assert result is True
        assert state.assigned_tasks[0]["status"] == "in_progress"

    def test_nonexistent_task_returns_false(self, state):
        result = state.update_task_status("nonexistent", "done")
        assert result is False

    def test_adds_status_history(self, state):
        state.add_task(_make_task("t1"))
        state.update_task_status("t1", "in_progress", details={"reason": "started"})
        assert "status_history" in state.assigned_tasks[0]
        assert len(state.assigned_tasks[0]["status_history"]) == 1

    def test_sets_updated_at(self, state):
        state.add_task(_make_task("t1"))
        state.update_task_status("t1", "completed")
        assert "status_updated_at" in state.assigned_tasks[0]


# ============================================================
# get_task
# ============================================================

class TestGetTask:
    def test_existing_task(self, state):
        state.add_task(_make_task("t1"))
        task = state.get_task("t1")
        assert task is not None
        assert task["id"] == "t1"

    def test_nonexistent_task(self, state):
        assert state.get_task("nonexistent") is None


# ============================================================
# Text extracts
# ============================================================

class TestTextExtracts:
    def test_add_extract(self, state):
        result = state.add_text_extract("ext1", {"text": "Hello"})
        assert result is True
        assert "ext1" in state.text_extracts

    def test_duplicate_extract_returns_false(self, state):
        state.add_text_extract("ext1", {"text": "Hello"})
        result = state.add_text_extract("ext1", {"text": "World"})
        assert result is False


# ============================================================
# Analysis results
# ============================================================

class TestAnalysisResults:
    def test_add_known_type(self, state):
        result_id = state.add_analysis_result(
            "identified_arguments", {"content": "arg1"}
        )
        assert len(state.analysis_results["identified_arguments"]) == 1
        assert state.analysis_results["identified_arguments"][0]["id"] == result_id

    def test_adds_timestamp(self, state):
        state.add_analysis_result("identified_fallacies", {"content": "f1"})
        assert "timestamp" in state.analysis_results["identified_fallacies"][0]

    def test_unknown_type_creates_category(self, state):
        state.add_analysis_result("custom_type", {"data": "val"})
        assert "custom_type" in state.analysis_results
        assert len(state.analysis_results["custom_type"]) == 1

    def test_auto_generates_result_id(self, state):
        result_id = state.add_analysis_result(
            "identified_arguments", {"content": "arg"}
        )
        assert result_id.startswith("result-")


# ============================================================
# Issues
# ============================================================

class TestIssues:
    def test_add_issue(self, state):
        issue_id = state.add_issue({"severity": "high"})
        assert len(state.encountered_issues) == 1
        assert state.encountered_issues[0]["id"] == issue_id

    def test_adds_timestamp(self, state):
        state.add_issue({"severity": "low"})
        assert "timestamp" in state.encountered_issues[0]

    def test_auto_generates_id(self, state):
        issue_id = state.add_issue({"severity": "medium"})
        assert issue_id.startswith("issue-")

    def test_preserves_existing_id(self, state):
        issue_id = state.add_issue({"id": "my-issue", "severity": "high"})
        assert issue_id == "my-issue"


# ============================================================
# Metrics
# ============================================================

class TestMetrics:
    def test_update_execution_time(self, state):
        state.update_metrics("t1", {"execution_time": 1.5})
        assert state.operational_metrics["processing_times"]["t1"] == 1.5

    def test_update_confidence(self, state):
        state.update_metrics("t1", {"confidence": 0.9})
        assert state.operational_metrics["confidence_scores"]["t1"] == 0.9

    def test_update_coverage(self, state):
        state.update_metrics("t1", {"coverage": 0.8})
        assert state.operational_metrics["coverage_metrics"]["t1"] == 0.8

    def test_custom_metric(self, state):
        state.update_metrics("t1", {"custom_key": 42})
        assert state.operational_metrics["custom_key"]["t1"] == 42

    def test_returns_true(self, state):
        assert state.update_metrics("t1", {"confidence": 0.5}) is True


# ============================================================
# Action log
# ============================================================

class TestActionLog:
    def test_log_action(self, state):
        state.log_action("started", {"task": "t1"})
        assert len(state.operational_actions_log) == 1
        assert state.operational_actions_log[0]["action"] == "started"

    def test_has_timestamp(self, state):
        state.log_action("finished", {})
        assert "timestamp" in state.operational_actions_log[0]


# ============================================================
# Query methods
# ============================================================

class TestQueries:
    def test_get_task_results(self, state):
        state.add_analysis_result(
            "identified_arguments", {"task_id": "t1", "content": "arg"}
        )
        results = state.get_task_results("t1")
        assert "identified_arguments" in results
        assert len(results["identified_arguments"]) == 1

    def test_get_task_results_empty(self, state):
        results = state.get_task_results("nonexistent")
        assert results == {}

    def test_get_task_issues(self, state):
        state.add_issue({"task_id": "t1", "severity": "high"})
        state.add_issue({"task_id": "t2", "severity": "low"})
        issues = state.get_task_issues("t1")
        assert len(issues) == 1
        assert issues[0]["task_id"] == "t1"

    def test_get_task_metrics(self, state):
        state.update_metrics("t1", {"execution_time": 1.0, "confidence": 0.9})
        metrics = state.get_task_metrics("t1")
        assert metrics["execution_time"] == 1.0
        assert metrics["confidence_scores"] == 0.9

    def test_get_pending_tasks(self, state):
        state.add_task(_make_task("t1"))
        state.add_task(_make_task("t2"))
        state.update_task_status("t1", "in_progress")
        pending = state.get_pending_tasks()
        assert len(pending) == 1
        assert pending[0]["id"] == "t2"

    def test_get_in_progress_tasks(self, state):
        state.add_task(_make_task("t1"))
        state.update_task_status("t1", "in_progress")
        in_progress = state.get_in_progress_tasks()
        assert len(in_progress) == 1

    def test_get_completed_tasks(self, state):
        state.add_task(_make_task("t1"))
        state.update_task_status("t1", "completed")
        completed = state.get_completed_tasks()
        assert len(completed) == 1

    def test_get_failed_tasks(self, state):
        state.add_task(_make_task("t1"))
        state.update_task_status("t1", "failed")
        failed = state.get_failed_tasks()
        assert len(failed) == 1


# ============================================================
# clear
# ============================================================

class TestClear:
    def test_resets_tasks(self, state):
        state.add_task(_make_task("t1"))
        state.clear()
        assert state.assigned_tasks == []

    def test_resets_extracts(self, state):
        state.add_text_extract("ext1", {"text": "hello"})
        state.clear()
        assert state.text_extracts == {}

    def test_resets_issues(self, state):
        state.add_issue({"severity": "high"})
        state.clear()
        assert state.encountered_issues == []


# ============================================================
# find_operational_task_by_tactical_id
# ============================================================

class TestFindByTacticalId:
    def test_finds_task(self, state):
        state.add_task(_make_task("op1", tactical_task_id="tac1"))
        result = state.find_operational_task_by_tactical_id("tac1")
        assert result == "op1"

    def test_returns_none_not_found(self, state):
        result = state.find_operational_task_by_tactical_id("nonexistent")
        assert result is None

    def test_returns_first_match(self, state):
        state.add_task(_make_task("op1", tactical_task_id="tac1"))
        state.add_task(_make_task("op2", tactical_task_id="tac1"))
        result = state.find_operational_task_by_tactical_id("tac1")
        assert result == "op1"


# ============================================================
# Result futures
# ============================================================

class TestResultFutures:
    def test_add_and_get_future(self, state):
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        state.add_result_future("t1", future)
        retrieved = state.get_result_future("t1")
        assert retrieved is future
        loop.close()

    def test_get_removes_future(self, state):
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        state.add_result_future("t1", future)
        state.get_result_future("t1")
        assert state.get_result_future("t1") is None
        loop.close()

    def test_get_nonexistent_returns_none(self, state):
        assert state.get_result_future("nonexistent") is None
