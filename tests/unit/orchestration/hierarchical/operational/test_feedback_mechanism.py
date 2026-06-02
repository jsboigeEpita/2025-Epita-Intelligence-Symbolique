# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.orchestration.hierarchical.operational.feedback_mechanism
Covers RhetoricalToolsFeedback and FeedbackManager: init, add/get feedback,
stats, parameter adjustment, report generation, collect/apply feedback.
"""

import pytest
import json

from argumentation_analysis.orchestration.hierarchical.operational.feedback_mechanism import (
    RhetoricalToolsFeedback,
    FeedbackManager,
)

# ============================================================
# RhetoricalToolsFeedback
# ============================================================


class TestRhetoricalToolsFeedbackInit:
    def test_default_storage_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        fb = RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "feedback"))
        assert fb.feedback_storage_path.exists()

    def test_custom_storage_path(self, tmp_path):
        path = tmp_path / "custom_feedback"
        fb = RhetoricalToolsFeedback(feedback_storage_path=str(path))
        assert fb.feedback_storage_path == path
        assert path.exists()

    def test_empty_history(self, tmp_path):
        fb = RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "fb"))
        assert fb.feedback_history == []

    def test_stats_structure(self, tmp_path):
        fb = RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "fb"))
        expected_tools = {
            "complex_fallacy_analysis",
            "contextual_fallacy_analysis",
            "fallacy_severity_evaluation",
            "argument_structure_visualization",
            "argument_coherence_evaluation",
            "semantic_argument_analysis",
            "contextual_fallacy_detection",
        }
        assert set(fb.feedback_stats.keys()) == expected_tools
        for tool, counts in fb.feedback_stats.items():
            assert counts == {"positive": 0, "negative": 0, "neutral": 0}


class TestAddFeedback:
    @pytest.fixture
    def fb(self, tmp_path):
        return RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "fb"))

    def test_add_positive(self, fb):
        result = fb.add_feedback(
            "complex_fallacy_analysis", "r1", "positive", {"comment": "Good"}
        )
        assert result is True
        assert len(fb.feedback_history) == 1
        assert fb.feedback_stats["complex_fallacy_analysis"]["positive"] == 1

    def test_add_negative(self, fb):
        fb.add_feedback(
            "complex_fallacy_analysis", "r1", "negative", {"comment": "Bad"}
        )
        assert fb.feedback_stats["complex_fallacy_analysis"]["negative"] == 1

    def test_add_neutral(self, fb):
        fb.add_feedback("complex_fallacy_analysis", "r1", "neutral", {})
        assert fb.feedback_stats["complex_fallacy_analysis"]["neutral"] == 1

    def test_unknown_tool_rejected(self, fb):
        result = fb.add_feedback("unknown_tool", "r1", "positive", {})
        assert result is False

    def test_invalid_type_rejected(self, fb):
        result = fb.add_feedback("complex_fallacy_analysis", "r1", "bad_type", {})
        assert result is False

    def test_entry_has_timestamp(self, fb):
        fb.add_feedback("complex_fallacy_analysis", "r1", "positive", {})
        assert "timestamp" in fb.feedback_history[0]

    def test_entry_has_id(self, fb):
        fb.add_feedback("complex_fallacy_analysis", "r1", "positive", {})
        assert fb.feedback_history[0]["id"] == "feedback-1"

    def test_custom_source(self, fb):
        fb.add_feedback(
            "complex_fallacy_analysis", "r1", "positive", {}, source="system"
        )
        assert fb.feedback_history[0]["source"] == "system"

    def test_multiple_feedbacks(self, fb):
        fb.add_feedback("complex_fallacy_analysis", "r1", "positive", {})
        fb.add_feedback("complex_fallacy_analysis", "r2", "negative", {})
        fb.add_feedback("contextual_fallacy_analysis", "r3", "neutral", {})
        assert len(fb.feedback_history) == 3


class TestGetFeedback:
    @pytest.fixture
    def fb(self, tmp_path):
        f = RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "fb"))
        f.add_feedback("complex_fallacy_analysis", "r1", "positive", {})
        f.add_feedback("complex_fallacy_analysis", "r2", "negative", {})
        f.add_feedback("contextual_fallacy_analysis", "r1", "neutral", {})
        return f

    def test_get_for_result(self, fb):
        results = fb.get_feedback_for_result("r1")
        assert len(results) == 2  # r1 appears in two tools

    def test_get_for_result_not_found(self, fb):
        results = fb.get_feedback_for_result("nonexistent")
        assert results == []

    def test_get_for_tool(self, fb):
        results = fb.get_feedback_for_tool("complex_fallacy_analysis")
        assert len(results) == 2

    def test_get_for_tool_not_found(self, fb):
        results = fb.get_feedback_for_tool("semantic_argument_analysis")
        assert results == []


class TestGetFeedbackStats:
    @pytest.fixture
    def fb(self, tmp_path):
        f = RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "fb"))
        f.add_feedback("complex_fallacy_analysis", "r1", "positive", {})
        f.add_feedback("complex_fallacy_analysis", "r2", "positive", {})
        f.add_feedback("complex_fallacy_analysis", "r3", "negative", {})
        return f

    def test_stats_for_tool(self, fb):
        stats = fb.get_feedback_stats("complex_fallacy_analysis")
        assert stats["complex_fallacy_analysis"]["positive"] == 2
        assert stats["complex_fallacy_analysis"]["negative"] == 1

    def test_stats_for_unknown_tool(self, fb):
        stats = fb.get_feedback_stats("unknown")
        assert stats == {}

    def test_stats_all(self, fb):
        stats = fb.get_feedback_stats()
        assert len(stats) == 7  # All tool types


class TestApplyFeedback:
    @pytest.fixture
    def fb(self, tmp_path):
        f = RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "fb"))
        return f

    def test_no_feedbacks_unchanged(self, fb):
        params = {"confidence_threshold": 0.8}
        result = fb.apply_feedback_to_tool_parameters(
            "complex_fallacy_analysis", params
        )
        assert result == params

    def test_positive_feedback_adjusts_threshold(self, fb):
        # Add mostly positive feedback
        for i in range(8):
            fb.add_feedback("complex_fallacy_analysis", f"r{i}", "positive", {})
        fb.add_feedback("complex_fallacy_analysis", "rn", "negative", {})
        params = {"confidence_threshold": 0.8}
        result = fb.apply_feedback_to_tool_parameters(
            "complex_fallacy_analysis", params
        )
        # Positive feedback should decrease threshold slightly
        assert result["confidence_threshold"] < 0.8

    def test_negative_feedback_increases_threshold(self, fb):
        for i in range(8):
            fb.add_feedback("complex_fallacy_analysis", f"r{i}", "negative", {})
        fb.add_feedback("complex_fallacy_analysis", "rp", "positive", {})
        params = {"confidence_threshold": 0.7}
        result = fb.apply_feedback_to_tool_parameters(
            "complex_fallacy_analysis", params
        )
        assert result["confidence_threshold"] > 0.7

    def test_threshold_clamped_min(self, fb):
        for i in range(100):
            fb.add_feedback("complex_fallacy_analysis", f"r{i}", "positive", {})
        params = {"confidence_threshold": 0.51}
        result = fb.apply_feedback_to_tool_parameters(
            "complex_fallacy_analysis", params
        )
        assert result["confidence_threshold"] >= 0.5

    def test_threshold_clamped_max(self, fb):
        for i in range(100):
            fb.add_feedback("complex_fallacy_analysis", f"r{i}", "negative", {})
        params = {"confidence_threshold": 0.94}
        result = fb.apply_feedback_to_tool_parameters(
            "complex_fallacy_analysis", params
        )
        assert result["confidence_threshold"] <= 0.95

    def test_no_threshold_param_unchanged(self, fb):
        fb.add_feedback("complex_fallacy_analysis", "r1", "positive", {})
        params = {"other_param": 42}
        result = fb.apply_feedback_to_tool_parameters(
            "complex_fallacy_analysis", params
        )
        assert result["other_param"] == 42


class TestGenerateReport:
    def test_empty_report(self, tmp_path):
        fb = RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "fb"))
        report = fb.generate_feedback_report()
        assert report["total_feedbacks"] == 0
        assert report["overall_satisfaction_rate"] == 0

    def test_report_with_data(self, tmp_path):
        fb = RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "fb"))
        fb.add_feedback("complex_fallacy_analysis", "r1", "positive", {})
        fb.add_feedback("complex_fallacy_analysis", "r2", "negative", {})
        report = fb.generate_feedback_report()
        assert report["total_feedbacks"] == 2
        assert report["feedback_distribution"]["positive"] == 1
        assert report["feedback_distribution"]["negative"] == 1
        assert report["overall_satisfaction_rate"] == 0.5

    def test_report_tool_stats(self, tmp_path):
        fb = RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "fb"))
        fb.add_feedback("complex_fallacy_analysis", "r1", "positive", {})
        report = fb.generate_feedback_report()
        assert "complex_fallacy_analysis" in report["tool_statistics"]
        assert (
            report["tool_statistics"]["complex_fallacy_analysis"]["satisfaction_rate"]
            == 1.0
        )

    def test_report_recent_feedbacks(self, tmp_path):
        fb = RhetoricalToolsFeedback(feedback_storage_path=str(tmp_path / "fb"))
        for i in range(15):
            fb.add_feedback("complex_fallacy_analysis", f"r{i}", "positive", {})
        report = fb.generate_feedback_report()
        assert len(report["recent_feedbacks"]) == 10  # Limited to last 10


class TestPersistence:
    def test_save_and_load(self, tmp_path):
        path = str(tmp_path / "fb")
        fb1 = RhetoricalToolsFeedback(feedback_storage_path=path)
        fb1.add_feedback("complex_fallacy_analysis", "r1", "positive", {"note": "good"})

        # Create new instance from same path
        fb2 = RhetoricalToolsFeedback(feedback_storage_path=path)
        assert len(fb2.feedback_history) == 1
        assert fb2.feedback_history[0]["result_id"] == "r1"
        assert fb2.feedback_stats["complex_fallacy_analysis"]["positive"] == 1


# ============================================================
# FeedbackManager
# ============================================================


class TestFeedbackManagerInit:
    def test_default_state(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        fm = FeedbackManager()
        assert fm.operational_state is not None
        assert fm.rhetorical_tools_feedback is not None


class TestCollectFeedback:
    @pytest.fixture
    def fm(self, tmp_path):
        from argumentation_analysis.orchestration.hierarchical.operational.state import (
            OperationalState,
        )

        os_state = OperationalState()
        fm = FeedbackManager(operational_state=os_state)
        fm.rhetorical_tools_feedback = RhetoricalToolsFeedback(
            feedback_storage_path=str(tmp_path / "fb")
        )
        return fm

    def test_operational_level(self, fm):
        result = fm.collect_feedback(
            "operational", "complex_fallacy_analysis", "r1", "positive", {}
        )
        assert result is True

    def test_unsupported_level(self, fm):
        result = fm.collect_feedback(
            "strategic", "complex_fallacy_analysis", "r1", "positive", {}
        )
        assert result is False

    def test_unsupported_tool(self, fm):
        result = fm.collect_feedback(
            "operational", "unknown_tool", "r1", "positive", {}
        )
        assert result is False


class TestApplyFeedbackManager:
    @pytest.fixture
    def fm(self, tmp_path):
        from argumentation_analysis.orchestration.hierarchical.operational.state import (
            OperationalState,
        )

        fm = FeedbackManager(operational_state=OperationalState())
        fm.rhetorical_tools_feedback = RhetoricalToolsFeedback(
            feedback_storage_path=str(tmp_path / "fb")
        )
        return fm

    def test_apply_operational(self, fm):
        params = {"confidence_threshold": 0.8}
        result = fm.apply_feedback("operational", "complex_fallacy_analysis", params)
        assert result == params  # No feedbacks yet, unchanged

    def test_apply_unsupported_level(self, fm):
        params = {"x": 1}
        result = fm.apply_feedback("strategic", "complex_fallacy_analysis", params)
        assert result == params


class TestGenerateReportManager:
    @pytest.fixture
    def fm(self, tmp_path):
        from argumentation_analysis.orchestration.hierarchical.operational.state import (
            OperationalState,
        )

        fm = FeedbackManager(operational_state=OperationalState())
        fm.rhetorical_tools_feedback = RhetoricalToolsFeedback(
            feedback_storage_path=str(tmp_path / "fb")
        )
        return fm

    def test_operational_report(self, fm):
        report = fm.generate_feedback_report(level="operational")
        assert "total_feedbacks" in report

    def test_default_report(self, fm):
        report = fm.generate_feedback_report()
        assert "total_feedbacks" in report

    def test_unsupported_level(self, fm):
        report = fm.generate_feedback_report(level="strategic")
        assert "error" in report
