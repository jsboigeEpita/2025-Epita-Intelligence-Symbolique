# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.operational.state
Covers OperationalState: task management, text extracts, analysis results,
issues, metrics, action log, filtering, serialization.
"""

import pytest
import asyncio

from argumentation_analysis.orchestration.hierarchical.operational.state import (
    OperationalState,
)


@pytest.fixture
def state():
    return OperationalState()


# ============================================================
# __init__
# ============================================================

class TestInit:
    def test_default_values(self, state):
        assert state.assigned_tasks == []
        assert state.text_extracts == {}
        assert state.encountered_issues == []
        assert state.operational_actions_log == []

    def test_analysis_results_structure(self, state):
        expected_keys = {
            "identified_arguments", "identified_fallacies", "formal_analyses",
            "extracted_data", "visualizations", "complex_fallacy_analyses",
            "contextual_fallacy_analyses", "fallacy_severity_evaluations",
            "argument_structure_visualizations", "argument_coherence_evaluations",
            "semantic_argument_analyses", "contextual_fallacy_detections",
        }
        assert expected_keys == set(state.analysis_results.keys())

    def test_metrics_structure(self, state):
        assert "processing_times" in state.operational_metrics
        assert "confidence_scores" in state.operational_metrics
        assert "coverage_metrics" in state.operational_metrics


# ============================================================
# add_task
# ============================================================

class TestAddTask:
    def test_add_with_id(self, state):
        task_id = state.add_task({"id": "t1", "description": "Test task"})
        assert task_id == "t1"
        assert len(state.assigned_tasks) == 1
        assert state.assigned_tasks[0]["status"] == "pending"

    def test_auto_generates_id(self, state):
        task_id = state.add_task({"description": "No ID task"})
        assert task_id.startswith("op-")

    def test_duplicate_task_not_added(self, state):
        state.add_task({"id": "t1", "description": "First"})
        state.add_task({"id": "t1", "description": "Duplicate"})
        assert len(state.assigned_tasks) == 1

    def test_assigned_at_set(self, state):
        state.add_task({"id": "t1"})
        assert "assigned_at" in state.assigned_tasks[0]


# ============================================================
# update_task_status
# ============================================================

class TestUpdateTaskStatus:
    def test_update_success(self, state):
        state.add_task({"id": "t1"})
        result = state.update_task_status("t1", "in_progress")
        assert result is True
        assert state.assigned_tasks[0]["status"] == "in_progress"

    def test_update_nonexistent(self, state):
        result = state.update_task_status("fake", "completed")
        assert result is False

    def test_with_details_creates_history(self, state):
        state.add_task({"id": "t1"})
        state.update_task_status("t1", "in_progress", details={"reason": "started"})
        assert "status_history" in state.assigned_tasks[0]
        assert len(state.assigned_tasks[0]["status_history"]) == 1

    def test_status_updated_at_set(self, state):
        state.add_task({"id": "t1"})
        state.update_task_status("t1", "completed")
        assert "status_updated_at" in state.assigned_tasks[0]


# ============================================================
# get_task
# ============================================================

class TestGetTask:
    def test_found(self, state):
        state.add_task({"id": "t1", "description": "Test"})
        task = state.get_task("t1")
        assert task is not None
        assert task["description"] == "Test"

    def test_not_found(self, state):
        assert state.get_task("nonexistent") is None


# ============================================================
# add_text_extract
# ============================================================

class TestAddTextExtract:
    def test_add_success(self, state):
        result = state.add_text_extract("e1", {"text": "Hello", "source": "test"})
        assert result is True
        assert "e1" in state.text_extracts

    def test_duplicate_rejected(self, state):
        state.add_text_extract("e1", {"text": "First"})
        result = state.add_text_extract("e1", {"text": "Second"})
        assert result is False
        assert state.text_extracts["e1"]["text"] == "First"


# ============================================================
# add_analysis_result
# ============================================================

class TestAddAnalysisResult:
    def test_known_type(self, state):
        result_id = state.add_analysis_result("identified_fallacies", {"type": "ad_hominem"})
        assert len(state.analysis_results["identified_fallacies"]) == 1
        assert state.analysis_results["identified_fallacies"][0]["type"] == "ad_hominem"

    def test_auto_id(self, state):
        result_id = state.add_analysis_result("identified_arguments", {"content": "test"})
        assert result_id.startswith("result-")

    def test_custom_id(self, state):
        result_id = state.add_analysis_result("identified_arguments", {"id": "r1", "content": "test"})
        assert result_id == "r1"

    def test_unknown_type_creates_category(self, state):
        state.add_analysis_result("new_category", {"data": 42})
        assert "new_category" in state.analysis_results
        assert len(state.analysis_results["new_category"]) == 1

    def test_timestamp_added(self, state):
        state.add_analysis_result("identified_fallacies", {"type": "test"})
        assert "timestamp" in state.analysis_results["identified_fallacies"][0]


# ============================================================
# add_issue
# ============================================================

class TestAddIssue:
    def test_add_with_id(self, state):
        issue_id = state.add_issue({"id": "i1", "description": "Problem"})
        assert issue_id == "i1"
        assert len(state.encountered_issues) == 1

    def test_auto_id(self, state):
        issue_id = state.add_issue({"description": "No ID"})
        assert issue_id.startswith("issue-")

    def test_timestamp_added(self, state):
        state.add_issue({"description": "Test"})
        assert "timestamp" in state.encountered_issues[0]


# ============================================================
# update_metrics
# ============================================================

class TestUpdateMetrics:
    def test_execution_time(self, state):
        state.update_metrics("t1", {"execution_time": 1.5})
        assert state.operational_metrics["processing_times"]["t1"] == 1.5

    def test_confidence(self, state):
        state.update_metrics("t1", {"confidence": 0.9})
        assert state.operational_metrics["confidence_scores"]["t1"] == 0.9

    def test_coverage(self, state):
        state.update_metrics("t1", {"coverage": 0.8})
        assert state.operational_metrics["coverage_metrics"]["t1"] == 0.8

    def test_custom_metric(self, state):
        state.update_metrics("t1", {"custom_metric": 42})
        assert state.operational_metrics["custom_metric"]["t1"] == 42

    def test_returns_true(self, state):
        assert state.update_metrics("t1", {}) is True


# ============================================================
# log_action
# ============================================================

class TestLogAction:
    def test_logs_entry(self, state):
        state.log_action("analyze", {"text": "sample"})
        assert len(state.operational_actions_log) == 1
        assert state.operational_actions_log[0]["action"] == "analyze"
        assert "timestamp" in state.operational_actions_log[0]


# ============================================================
# get_task_results / get_task_issues / get_task_metrics
# ============================================================

class TestGetTaskData:
    def test_get_task_results(self, state):
        state.add_analysis_result("identified_fallacies", {"task_id": "t1", "type": "ad_hominem"})
        state.add_analysis_result("identified_fallacies", {"task_id": "t2", "type": "straw_man"})
        results = state.get_task_results("t1")
        assert "identified_fallacies" in results
        assert len(results["identified_fallacies"]) == 1

    def test_get_task_results_empty(self, state):
        results = state.get_task_results("nonexistent")
        assert results == {}

    def test_get_task_issues(self, state):
        state.add_issue({"task_id": "t1", "description": "Error"})
        state.add_issue({"task_id": "t2", "description": "Other"})
        issues = state.get_task_issues("t1")
        assert len(issues) == 1

    def test_get_task_metrics(self, state):
        state.update_metrics("t1", {"execution_time": 2.0, "confidence": 0.95})
        metrics = state.get_task_metrics("t1")
        assert metrics["execution_time"] == 2.0
        assert metrics["confidence_scores"] == 0.95


# ============================================================
# Filtering methods
# ============================================================

class TestFilteringMethods:
    def test_get_pending_tasks(self, state):
        state.add_task({"id": "t1"})
        state.add_task({"id": "t2"})
        state.update_task_status("t2", "in_progress")
        pending = state.get_pending_tasks()
        assert len(pending) == 1
        assert pending[0]["id"] == "t1"

    def test_get_in_progress_tasks(self, state):
        state.add_task({"id": "t1"})
        state.update_task_status("t1", "in_progress")
        ip = state.get_in_progress_tasks()
        assert len(ip) == 1

    def test_get_completed_tasks(self, state):
        state.add_task({"id": "t1"})
        state.update_task_status("t1", "completed")
        completed = state.get_completed_tasks()
        assert len(completed) == 1

    def test_get_failed_tasks(self, state):
        state.add_task({"id": "t1"})
        state.update_task_status("t1", "failed")
        failed = state.get_failed_tasks()
        assert len(failed) == 1


# ============================================================
# clear
# ============================================================

class TestClear:
    def test_resets_state(self, state):
        state.add_task({"id": "t1"})
        state.add_text_extract("e1", {"text": "x"})
        state.add_issue({"description": "issue"})
        state.clear()
        assert state.assigned_tasks == []
        assert state.text_extracts == {}
        assert state.encountered_issues == []


# ============================================================
# find_operational_task_by_tactical_id
# ============================================================

class TestFindByTacticalId:
    def test_found(self, state):
        state.add_task({"id": "op1", "tactical_task_id": "tac1"})
        result = state.find_operational_task_by_tactical_id("tac1")
        assert result == "op1"

    def test_not_found(self, state):
        result = state.find_operational_task_by_tactical_id("nonexistent")
        assert result is None


# ============================================================
# add_result_future / get_result_future
# ============================================================

class TestResultFutures:
    def test_add_and_get(self, state):
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

    def test_get_nonexistent(self, state):
        assert state.get_result_future("fake") is None
