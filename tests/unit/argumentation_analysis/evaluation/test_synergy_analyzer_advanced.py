"""
Advanced tests for SynergyAnalyzer.

Tests cover:
- Workflow metrics calculation
- Difficulty-based analysis
- Synergy recommendations
- Report generation (JSON and Markdown)
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from argumentation_analysis.evaluation.synergy_analyzer import (
    SynergyAnalyzer,
    WorkflowMetrics,
    SynergyRecommendation,
    WORKFLOW_PHASES,
    DIFFICULTY_LEVELS,
)


@pytest.mark.unit
class TestWorkflowMetrics:
    """Test workflow metrics calculation."""

    def test_analyze_workflow_performance_empty(self, tmp_path):
        """Test analysis with no results returns empty dict."""
        analyzer = SynergyAnalyzer(tmp_path)
        metrics = analyzer.analyze_workflow_performance()

        assert metrics == {}

    def test_analyze_single_workflow_metrics(self, tmp_path):
        """Test metrics calculation for a single workflow."""
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        collector = ResultCollector(tmp_path)

        # Add results for light workflow
        for i in range(5):
            result = BenchmarkResult(
                timestamp=datetime.now().isoformat(),
                workflow_name="light",
                model_name="gpt-4",
                document_index=i,
                document_name=f"doc{i}.txt",
                success=(i < 4),  # 4 success, 1 failure
                duration_seconds=5.0 + i,
                phases_completed=3 if i < 4 else 0,
                phases_total=3,
                phases_failed=0 if i < 4 else 3,
                phases_skipped=0,
                error=None if i < 4 else "Failed",
                state_snapshot={},
            )
            collector.save(result)

        analyzer = SynergyAnalyzer(tmp_path)
        metrics = analyzer.analyze_workflow_performance()

        assert "light" in metrics
        light_metric = metrics["light"]
        assert light_metric.workflow_name == "light"
        assert light_metric.total_runs == 5
        assert light_metric.success_rate == 0.8  # 4/5
        assert light_metric.avg_duration > 0
        assert light_metric.avg_phases_completed == 3.0
        assert light_metric.completion_ratio == 1.0  # 3/3

    def test_analyze_multiple_workflows(self, tmp_path):
        """Test metrics calculation for multiple workflows."""
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        collector = ResultCollector(tmp_path)

        # Add results for different workflows
        workflows = ["light", "standard", "full"]
        workflow_durations = {"light": 5.0, "standard": 10.0, "full": 15.0}
        for workflow in workflows:
            for i in range(3):
                result = BenchmarkResult(
                    timestamp=datetime.now().isoformat(),
                    workflow_name=workflow,
                    model_name="gpt-4",
                    document_index=i,
                    document_name=f"{workflow}_doc{i}.txt",
                    success=True,
                    duration_seconds=workflow_durations[workflow],  # Different durations per workflow
                    phases_completed=len(WORKFLOW_PHASES[workflow]),
                    phases_total=len(WORKFLOW_PHASES[workflow]),
                    phases_failed=0,
                    phases_skipped=0,
                    error=None,
                    state_snapshot={},
                )
                collector.save(result)

        analyzer = SynergyAnalyzer(tmp_path)
        metrics = analyzer.analyze_workflow_performance()

        assert len(metrics) == 3
        assert all(wf in metrics for wf in workflows)
        assert metrics["light"].avg_duration < metrics["standard"].avg_duration
        assert metrics["standard"].avg_duration < metrics["full"].avg_duration

    def test_workflow_phase_definitions(self):
        """Test that workflow phase definitions are correctly defined."""
        assert "light" in WORKFLOW_PHASES
        assert "standard" in WORKFLOW_PHASES
        assert "full" in WORKFLOW_PHASES

        assert len(WORKFLOW_PHASES["light"]) == 3
        assert len(WORKFLOW_PHASES["standard"]) == 6
        assert len(WORKFLOW_PHASES["full"]) == 9

        # Check specific phases
        assert "extract" in WORKFLOW_PHASES["light"]
        assert "quality" in WORKFLOW_PHASES["light"]
        assert "counter" in WORKFLOW_PHASES["light"]
        assert "debate" in WORKFLOW_PHASES["standard"]
        assert "index" in WORKFLOW_PHASES["full"]


@pytest.mark.unit
class TestDifficultyBasedAnalysis:
    """Test difficulty-based workflow analysis."""

    def test_get_document_metadata_with_corpus(self, tmp_path):
        """Test getting document metadata when corpus is available."""
        # Create a mock corpus
        corpus = {
            "documents": [
                {
                    "id": "doc1",
                    "difficulty": "easy",
                    "expected_fallacies": ["hasty_generalization"],
                    "expected_quality_score_range": [7, 9],
                },
                {
                    "id": "doc2",
                    "difficulty": "hard",
                    "expected_fallacies": ["straw_man", "red_herring"],
                    "expected_quality_score_range": [3, 5],
                },
            ]
        }

        corpus_path = tmp_path / "corpus" / "baseline_corpus_v1.json"
        corpus_path.parent.mkdir(parents=True, exist_ok=True)
        with open(corpus_path, "w", encoding="utf-8") as f:
            json.dump(corpus, f, ensure_ascii=False)

        analyzer = SynergyAnalyzer(tmp_path)
        analyzer.load_corpus(corpus_path)

        metadata = analyzer.get_document_metadata(0)
        assert metadata["id"] == "doc1"
        assert metadata["difficulty"] == "easy"
        assert metadata["expected_fallacies"] == ["hasty_generalization"]

        metadata = analyzer.get_document_metadata(1)
        assert metadata["id"] == "doc2"
        assert metadata["difficulty"] == "hard"

    def test_get_document_metadata_without_corpus(self, tmp_path):
        """Test getting document metadata when corpus is not available."""
        analyzer = SynergyAnalyzer(tmp_path)
        metadata = analyzer.get_document_metadata(999)

        assert metadata["difficulty"] == "unknown"
        assert metadata["expected_fallacies"] == []

    def test_analyze_by_difficulty_level(self, tmp_path):
        """Test analysis segmented by difficulty level."""
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        # Create corpus with difficulty levels
        corpus = {
            "documents": [
                {"id": "doc0", "difficulty": "easy"},
                {"id": "doc1", "difficulty": "medium"},
                {"id": "doc2", "difficulty": "hard"},
            ]
        }

        corpus_path = tmp_path / "corpus" / "baseline_corpus_v1.json"
        corpus_path.parent.mkdir(parents=True, exist_ok=True)
        with open(corpus_path, "w", encoding="utf-8") as f:
            json.dump(corpus, f, ensure_ascii=False)

        # Add results
        collector = ResultCollector(tmp_path)
        for i in range(3):
            result = BenchmarkResult(
                timestamp=datetime.now().isoformat(),
                workflow_name="light",
                model_name="gpt-4",
                document_index=i,
                document_name=f"doc{i}.txt",
                success=True,
                duration_seconds=5.0,
                phases_completed=3,
                phases_total=3,
                phases_failed=0,
                phases_skipped=0,
                error=None,
                state_snapshot={},
            )
            collector.save(result)

        analyzer = SynergyAnalyzer(tmp_path)
        analyzer.load_corpus(corpus_path)
        metrics = analyzer.analyze_workflow_performance()

        assert "light" in metrics
        light_metric = metrics["light"]
        assert "by_difficulty" in light_metric.__dict__
        assert "easy" in light_metric.by_difficulty
        assert "medium" in light_metric.by_difficulty
        assert "hard" in light_metric.by_difficulty

    def test_difficulty_levels_constant(self):
        """Test that difficulty levels are correctly defined."""
        assert isinstance(DIFFICULTY_LEVELS, list)
        assert "easy" in DIFFICULTY_LEVELS
        assert "medium" in DIFFICULTY_LEVELS
        assert "hard" in DIFFICULTY_LEVELS


@pytest.mark.unit
class TestRecommendations:
    """Test synergy recommendation generation."""

    def test_generate_recommendations_empty(self, tmp_path):
        """Test that empty results generate no recommendations."""
        analyzer = SynergyAnalyzer(tmp_path)
        recommendations = analyzer.generate_recommendations()

        assert recommendations == []

    def test_generate_quick_assessment_recommendation(self, tmp_path):
        """Test recommendation for quick assessment use case."""
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        collector = ResultCollector(tmp_path)

        # Light workflow - fast
        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="light",
            model_name="gpt-4",
            document_index=0,
            document_name="doc1.txt",
            success=True,
            duration_seconds=3.0,  # Fast
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={},
        )
        collector.save(result)

        # Standard workflow - slower
        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="standard",
            model_name="gpt-4",
            document_index=1,
            document_name="doc2.txt",
            success=True,
            duration_seconds=10.0,  # Slower
            phases_completed=6,
            phases_total=6,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={},
        )
        collector.save(result)

        analyzer = SynergyAnalyzer(tmp_path)
        recommendations = analyzer.generate_recommendations()

        # Should have at least quick_assessment recommendation
        quick_rec = next((r for r in recommendations if r.use_case == "quick_assessment"), None)
        assert quick_rec is not None
        assert quick_rec.recommended_workflow == "light"
        assert quick_rec.confidence > 0
        assert "fastest" in quick_rec.reasoning.lower()

    def test_generate_thorough_analysis_recommendation(self, tmp_path):
        """Test recommendation for thorough analysis use case."""
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        collector = ResultCollector(tmp_path)

        # Light workflow - lower completion
        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="light",
            model_name="gpt-4",
            document_index=0,
            document_name="doc1.txt",
            success=True,
            duration_seconds=5.0,
            phases_completed=2,
            phases_total=3,
            phases_failed=1,
            phases_skipped=0,
            error=None,
            state_snapshot={},
        )
        collector.save(result)

        # Standard workflow - higher completion
        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="standard",
            model_name="gpt-4",
            document_index=1,
            document_name="doc2.txt",
            success=True,
            duration_seconds=10.0,
            phases_completed=6,
            phases_total=6,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={},
        )
        collector.save(result)

        analyzer = SynergyAnalyzer(tmp_path)
        recommendations = analyzer.generate_recommendations()

        # Should have thorough_analysis recommendation
        thorough_rec = next((r for r in recommendations if r.use_case == "thorough_analysis"), None)
        assert thorough_rec is not None
        assert thorough_rec.recommended_workflow == "standard"
        assert "completion" in thorough_rec.reasoning.lower()

    def test_synergy_recommendation_dataclass(self):
        """Test SynergyRecommendation dataclass structure."""
        rec = SynergyRecommendation(
            use_case="test_use_case",
            recommended_workflow="light",
            confidence=0.85,
            reasoning="Test reasoning",
            alternative_workflows=["standard", "full"],
            expected_metrics={"success_rate": 0.9},
        )

        assert rec.use_case == "test_use_case"
        assert rec.recommended_workflow == "light"
        assert rec.confidence == 0.85
        assert rec.reasoning == "Test reasoning"
        assert len(rec.alternative_workflows) == 2
        assert rec.expected_metrics["success_rate"] == 0.9


@pytest.mark.unit
class TestReportGeneration:
    """Test report generation functionality."""

    def test_generate_json_report(self, tmp_path):
        """Test JSON report generation."""
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        collector = ResultCollector(tmp_path)

        # Add sample result
        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="light",
            model_name="gpt-4",
            document_index=0,
            document_name="doc1.txt",
            success=True,
            duration_seconds=5.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={},
        )
        collector.save(result)

        analyzer = SynergyAnalyzer(tmp_path)
        report_path = analyzer.generate_report()

        assert report_path.exists()
        assert report_path.suffix == ".json"

        # Verify JSON is valid
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        assert "generated_at" in report
        assert "comparison" in report
        assert "recommendations" in report
        assert "workflow_phases" in report

    def test_generate_markdown_report(self, tmp_path):
        """Test Markdown report generation."""
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        collector = ResultCollector(tmp_path)

        # Add sample result
        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="light",
            model_name="gpt-4",
            document_index=0,
            document_name="doc1.txt",
            success=True,
            duration_seconds=5.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={},
        )
        collector.save(result)

        analyzer = SynergyAnalyzer(tmp_path)
        report_path = analyzer.export_markdown_report()

        assert report_path.exists()
        assert report_path.suffix == ".md"

        # Verify Markdown content
        content = report_path.read_text(encoding="utf-8")
        assert "# Synergy Analysis Report" in content
        assert "## Executive Summary" in content
        assert "## Workflow Comparison" in content
        assert "## Recommendations" in content
        assert "## Workflow Phases" in content

    def test_compare_workflows(self, tmp_path):
        """Test workflow comparison functionality."""
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        collector = ResultCollector(tmp_path)

        # Add results for multiple workflows
        for workflow in ["light", "standard"]:
            for i in range(3):
                result = BenchmarkResult(
                    timestamp=datetime.now().isoformat(),
                    workflow_name=workflow,
                    model_name="gpt-4",
                    document_index=i,
                    document_name=f"{workflow}_doc{i}.txt",
                    success=True,
                    duration_seconds=5.0 if workflow == "light" else 10.0,
                    phases_completed=3 if workflow == "light" else 6,
                    phases_total=3 if workflow == "light" else 6,
                    phases_failed=0,
                    phases_skipped=0,
                    error=None,
                    state_snapshot={},
                )
                collector.save(result)

        analyzer = SynergyAnalyzer(tmp_path)
        comparison = analyzer.compare_workflows()

        assert "workflows" in comparison
        assert "best_by_success_rate" in comparison
        assert "best_by_speed" in comparison
        assert "best_by_completion" in comparison
        assert "summary" in comparison

        # Check that light is fastest
        if comparison["best_by_speed"]:
            assert comparison["best_by_speed"]["workflow"] == "light"

    def test_generate_report_custom_path(self, tmp_path):
        """Test report generation to custom path."""
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        collector = ResultCollector(tmp_path)

        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="light",
            model_name="gpt-4",
            document_index=0,
            document_name="doc1.txt",
            success=True,
            duration_seconds=5.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={},
        )
        collector.save(result)

        # Create parent directory first
        custom_dir = tmp_path / "custom_reports"
        custom_dir.mkdir(parents=True, exist_ok=True)
        custom_path = custom_dir / "synergy.json"

        analyzer = SynergyAnalyzer(tmp_path)
        report_path = analyzer.generate_report(custom_path)

        assert report_path == custom_path
        assert custom_path.exists()
