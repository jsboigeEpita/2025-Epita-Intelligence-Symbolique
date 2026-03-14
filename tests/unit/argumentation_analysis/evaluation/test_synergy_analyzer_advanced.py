"""
Advanced tests for synergy_analyzer.py (edge cases, robustness).
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from argumentation_analysis.evaluation.synergy_analyzer import (
    WORKFLOW_PHASES,
    DIFFICULTY_LEVELS,
    FALLACY_CATEGORIES,
    WorkflowMetrics,
    SynergyRecommendation,
    SynergyAnalyzer,
)
from argumentation_analysis.evaluation.result_collector import ResultCollector
from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult


# =====================================================================
# Constants Tests
# =====================================================================


class TestSynergyConstants:
    """Tests for module constants."""

    def test_workflow_phases_defined(self):
        """Verify workflow phases are defined."""
        assert "light" in WORKFLOW_PHASES
        assert "standard" in WORKFLOW_PHASES
        assert "full" in WORKFLOW_PHASES

    def test_light_workflow_phases(self):
        """Verify light workflow has expected phases."""
        phases = WORKFLOW_PHASES["light"]
        assert "extract" in phases
        assert "quality" in phases
        assert "counter" in phases
        assert len(phases) == 3

    def test_standard_workflow_phases(self):
        """Verify standard workflow has expected phases."""
        phases = WORKFLOW_PHASES["standard"]
        assert "extract" in phases
        assert "quality" in phases
        assert "counter" in phases
        assert "jtms" in phases
        assert "governance" in phases or "debate" in phases

    def test_full_workflow_phases(self):
        """Verify full workflow has expected phases."""
        phases = WORKFLOW_PHASES["full"]
        assert "transcribe" in phases
        assert "extract" in phases
        assert "quality" in phases
        assert "index" in phases

    def test_difficulty_levels(self):
        """Verify difficulty levels are defined."""
        assert "easy" in DIFFICULTY_LEVELS
        assert "medium" in DIFFICULTY_LEVELS
        assert "hard" in DIFFICULTY_LEVELS

    def test_fallacy_categories_defined(self):
        """Verify fallacy categories are defined."""
        assert len(FALLACY_CATEGORIES) >= 10
        assert "ad_hominem" in FALLACY_CATEGORIES
        assert "straw_man" in FALLACY_CATEGORIES


# =====================================================================
# WorkflowMetrics Tests
# =====================================================================


class TestWorkflowMetrics:
    """Tests for WorkflowMetrics dataclass."""

    def test_default_values(self):
        """Verify default metric values."""
        metrics = WorkflowMetrics(workflow_name="light")
        assert metrics.workflow_name == "light"
        assert metrics.total_runs == 0
        assert metrics.success_rate == 0.0
        assert metrics.avg_duration == 0.0
        assert metrics.completion_ratio == 0.0
        assert metrics.by_difficulty == {}
        assert metrics.by_fallacy_category == {}

    def test_full_initialization(self):
        """Verify full metrics initialization."""
        metrics = WorkflowMetrics(
            workflow_name="standard",
            total_runs=10,
            success_rate=0.9,
            avg_duration=5.5,
            avg_phases_completed=5,
            avg_phases_total=6,
            completion_ratio=0.833,
            by_difficulty={"easy": {"count": 3, "success_rate": 1.0}},
        )
        assert metrics.workflow_name == "standard"
        assert metrics.total_runs == 10
        assert metrics.success_rate == 0.9


# =====================================================================
# SynergyRecommendation Tests
# =====================================================================


class TestSynergyRecommendation:
    """Tests for SynergyRecommendation dataclass."""

    def test_default_values(self):
        """Verify default recommendation values."""
        rec = SynergyRecommendation(
            use_case="quick_assessment",
            recommended_workflow="light",
            confidence=0.9,
            reasoning="Fastest workflow",
        )
        assert rec.use_case == "quick_assessment"
        assert rec.recommended_workflow == "light"
        assert rec.confidence == 0.9
        assert rec.alternative_workflows == []
        assert rec.expected_metrics == {}

    def test_with_alternatives(self):
        """Verify recommendation with alternatives."""
        rec = SynergyRecommendation(
            use_case="test",
            recommended_workflow="standard",
            confidence=0.8,
            reasoning="Test",
            alternative_workflows=["light", "full"],
            expected_metrics={"speed": 2.5},
        )
        assert len(rec.alternative_workflows) == 2
        assert rec.expected_metrics["speed"] == 2.5


# =====================================================================
# SynergyAnalyzer Advanced Tests
# =====================================================================


class TestSynergyAnalyzerAdvanced:
    """Advanced tests for SynergyAnalyzer edge cases."""

    def test_load_corpus_custom_path(self, tmp_path):
        """Verify corpus loading from custom path."""
        custom_corpus = tmp_path / "custom_corpus.json"
        corpus_data = {
            "corpus_name": "custom",
            "documents": [
                {"id": "custom_001", "text": "Test", "expected_fallacies": [], "difficulty": "easy"}
            ]
        }
        with open(custom_corpus, "w", encoding="utf-8") as f:
            json.dump(corpus_data, f)

        analyzer = SynergyAnalyzer()
        corpus = analyzer.load_corpus(corpus_path=custom_corpus)

        assert corpus["corpus_name"] == "custom"

    def test_load_corpus_caches_result(self, tmp_path):
        """Verify corpus loading is cached."""
        analyzer = SynergyAnalyzer(tmp_path)

        # First load
        corpus1 = analyzer.load_corpus()
        # Second load (should return cached)
        corpus2 = analyzer.load_corpus()

        # Should be same object reference
        assert corpus1 is corpus2

    def test_get_document_metadata_out_of_range(self):
        """Verify metadata for out-of-range index."""
        analyzer = SynergyAnalyzer()
        meta = analyzer.get_document_metadata(99999)
        assert meta["difficulty"] == "unknown"
        assert meta["expected_fallacies"] == []

    def test_analyze_workflow_performance_no_results(self, tmp_path):
        """Verify performance analysis with no results."""
        analyzer = SynergyAnalyzer(tmp_path)
        metrics = analyzer.analyze_workflow_performance()
        assert metrics == {}

    def test_analyze_workflow_performance_single_run(self, tmp_path):
        """Verify metrics for a single run."""
        collector = ResultCollector(tmp_path)
        collector.save(BenchmarkResult(
            workflow_name="light",
            model_name="test",
            document_index=0,
            document_name="doc1",
            success=True,
            duration_seconds=1.5,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
        ))

        analyzer = SynergyAnalyzer(tmp_path)
        metrics = analyzer.analyze_workflow_performance()

        assert "light" in metrics
        assert metrics["light"].total_runs == 1
        assert metrics["light"].success_rate == 1.0
        assert metrics["light"].avg_duration == 1.5

    def test_analyze_workflow_performance_all_failures(self, tmp_path):
        """Verify metrics when all runs fail."""
        collector = ResultCollector(tmp_path)
        collector.save(BenchmarkResult(
            workflow_name="light",
            model_name="test",
            document_index=0,
            document_name="doc1",
            success=False,
            duration_seconds=0.5,
            phases_completed=0,
            phases_total=3,
            phases_failed=1,
            phases_skipped=0,
            error="Failed",
        ))

        analyzer = SynergyAnalyzer(tmp_path)
        metrics = analyzer.analyze_workflow_performance()

        assert metrics["light"].success_rate == 0.0
        assert metrics["light"].avg_duration == 0.0  # No successful runs

    def test_analyze_workflow_performance_by_difficulty(self, tmp_path):
        """Verify difficulty-based metrics."""
        collector = ResultCollector(tmp_path)
        # Easy doc (corpus_001 is easy)
        collector.save(BenchmarkResult(
            workflow_name="light",
            model_name="test",
            document_index=0,  # corpus_001 = easy
            document_name="corpus_001",
            success=True,
            duration_seconds=1.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
        ))
        # Hard doc (corpus_006 is hard)
        collector.save(BenchmarkResult(
            workflow_name="light",
            model_name="test",
            document_index=5,  # corpus_006 = hard
            document_name="corpus_006",
            success=True,
            duration_seconds=3.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
        ))

        analyzer = SynergyAnalyzer(tmp_path)
        metrics = analyzer.analyze_workflow_performance()

        assert "easy" in metrics["light"].by_difficulty
        assert "hard" in metrics["light"].by_difficulty
        assert metrics["light"].by_difficulty["easy"]["success_rate"] == 1.0
        assert metrics["light"].by_difficulty["hard"]["avg_duration"] == 3.0

    def test_compare_workflows_empty(self, tmp_path):
        """Verify comparison with no workflows."""
        analyzer = SynergyAnalyzer(tmp_path)
        comparison = analyzer.compare_workflows()
        assert "error" in comparison
        assert "No metrics available" in comparison["error"]

    def test_compare_workflows_identical_performance(self, tmp_path):
        """Verify comparison when workflows have identical performance."""
        collector = ResultCollector(tmp_path)
        for workflow in ["light", "standard"]:
            collector.save(BenchmarkResult(
                workflow_name=workflow,
                model_name="test",
                document_index=0,
                document_name="doc1",
                success=True,
                duration_seconds=2.0,
                phases_completed=3,
                phases_total=3,
                phases_failed=0,
                phases_skipped=0,
            ))

        analyzer = SynergyAnalyzer(tmp_path)
        comparison = analyzer.compare_workflows()

        assert comparison["summary"]["total_workflows_analyzed"] == 2
        assert comparison["summary"]["avg_success_rate"] == 1.0

    def test_generate_recommendations_edge_cases(self, tmp_path):
        """Verify recommendations handle edge cases."""
        collector = ResultCollector(tmp_path)
        # Single workflow with zero duration (edge case)
        collector.save(BenchmarkResult(
            workflow_name="light",
            model_name="test",
            document_index=0,
            document_name="doc1",
            success=True,
            duration_seconds=0.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
        ))

        analyzer = SynergyAnalyzer(tmp_path)
        recommendations = analyzer.generate_recommendations()

        # Should still generate recommendations
        assert len(recommendations) > 0

    def test_generate_report_with_output_path(self, tmp_path):
        """Verify report generation to custom path."""
        collector = ResultCollector(tmp_path)
        collector.save(BenchmarkResult(
            workflow_name="light",
            model_name="test",
            document_index=0,
            document_name="doc1",
            success=True,
            duration_seconds=1.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
        ))

        custom_output = tmp_path / "custom_report.json"
        analyzer = SynergyAnalyzer(tmp_path)
        report_path = analyzer.generate_report(output_path=custom_output)

        assert report_path == custom_output
        assert custom_output.exists()

    def test_export_markdown_custom_output(self, tmp_path):
        """Verify markdown export to custom path."""
        collector = ResultCollector(tmp_path)
        collector.save(BenchmarkResult(
            workflow_name="light",
            model_name="test",
            document_index=0,
            document_name="doc1",
            success=True,
            duration_seconds=1.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
        ))

        custom_output = tmp_path / "custom_report.md"
        analyzer = SynergyAnalyzer(tmp_path)
        report_path = analyzer.export_markdown_report(output_path=custom_output)

        assert report_path == custom_output
        content = custom_output.read_text(encoding="utf-8")
        assert "# Synergy Analysis Report" in content

    def test_recommendations_include_all_use_cases(self, tmp_path):
        """Verify all expected use case types are generated."""
        collector = ResultCollector(tmp_path)
        # Create varied data for all use cases
        for i in range(3):
            # Easy docs
            collector.save(BenchmarkResult(
                workflow_name="light",
                model_name="test",
                document_index=i,
                document_name=f"corpus_00{i+1}",
                success=True,
                duration_seconds=1.0,
                phases_completed=3,
                phases_total=3,
                phases_failed=0,
                phases_skipped=0,
            ))
            # Hard docs
            collector.save(BenchmarkResult(
                workflow_name="full",
                model_name="test",
                document_index=i+5,
                document_name=f"corpus_00{i+6}",
                success=True,
                duration_seconds=5.0,
                phases_completed=8,
                phases_total=8,
                phases_failed=0,
                phases_skipped=0,
            ))

        analyzer = SynergyAnalyzer(tmp_path)
        recommendations = analyzer.generate_recommendations()

        use_cases = {r.use_case for r in recommendations}
        assert "quick_assessment" in use_cases
        assert "thorough_analysis" in use_cases

    def test_confidence_in_valid_range(self, tmp_path):
        """Verify all recommendation confidences are in [0, 1]."""
        collector = ResultCollector(tmp_path)
        collector.save(BenchmarkResult(
            workflow_name="light",
            model_name="test",
            document_index=0,
            document_name="doc1",
            success=True,
            duration_seconds=1.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
        ))

        analyzer = SynergyAnalyzer(tmp_path)
        recommendations = analyzer.generate_recommendations()

        for rec in recommendations:
            assert 0.0 <= rec.confidence <= 1.0, f"Invalid confidence: {rec.confidence}"
