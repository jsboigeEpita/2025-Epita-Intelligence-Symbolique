"""
Tests for multi_model_benchmark.py — multi-model × multi-workflow benchmark runner.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from argumentation_analysis.evaluation.multi_model_benchmark import (
    ModelWorkflowScore,
    ComparisonReport,
    compute_scores,
    rank_models,
    rank_workflows,
    find_best,
    generate_markdown_report,
    run_multi_model_benchmark,
    list_available_workflows,
)
from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult
from argumentation_analysis.evaluation.model_registry import ModelRegistry, ModelConfig


@pytest.mark.unit
class TestModelWorkflowScore:
    """Tests for the ModelWorkflowScore dataclass."""

    def test_success_rate_with_runs(self):
        s = ModelWorkflowScore(
            model_name="m1", workflow_name="light", total_runs=10, successes=8
        )
        assert s.success_rate == 0.8

    def test_success_rate_zero_runs(self):
        s = ModelWorkflowScore(model_name="m1", workflow_name="light")
        assert s.success_rate == 0.0

    def test_default_values(self):
        s = ModelWorkflowScore(model_name="m1", workflow_name="wf")
        assert s.total_runs == 0
        assert s.failures == 0
        assert s.avg_duration == 0.0
        assert s.avg_completion_ratio == 0.0


def _make_result(
    workflow="light",
    model="default",
    doc_idx=0,
    success=True,
    duration=5.0,
    phases_completed=3,
    phases_total=3,
):
    return BenchmarkResult(
        workflow_name=workflow,
        model_name=model,
        document_index=doc_idx,
        document_name=f"doc_{doc_idx}",
        success=success,
        duration_seconds=duration,
        phases_completed=phases_completed,
        phases_total=phases_total,
        phases_failed=0 if success else 1,
        phases_skipped=0,
        error=None if success else "test error",
    )


@pytest.mark.unit
class TestComputeScores:
    """Tests for compute_scores aggregation."""

    def test_single_result(self):
        results = [_make_result()]
        scores = compute_scores(results)
        assert len(scores) == 1
        assert scores[0].model_name == "default"
        assert scores[0].workflow_name == "light"
        assert scores[0].total_runs == 1
        assert scores[0].successes == 1
        assert scores[0].avg_duration == 5.0

    def test_multiple_models(self):
        results = [
            _make_result(model="gpt5", duration=3.0),
            _make_result(model="gpt5", doc_idx=1, duration=4.0),
            _make_result(model="claude", duration=6.0),
            _make_result(model="claude", doc_idx=1, duration=7.0),
        ]
        scores = compute_scores(results)
        assert len(scores) == 2
        by_model = {s.model_name: s for s in scores}
        assert by_model["gpt5"].avg_duration == 3.5
        assert by_model["claude"].avg_duration == 6.5

    def test_mixed_success_failure(self):
        results = [
            _make_result(success=True, duration=5.0),
            _make_result(doc_idx=1, success=False, duration=2.0),
            _make_result(doc_idx=2, success=True, duration=8.0),
        ]
        scores = compute_scores(results)
        assert len(scores) == 1
        s = scores[0]
        assert s.total_runs == 3
        assert s.successes == 2
        assert s.failures == 1
        # avg_duration only counts successes
        assert s.avg_duration == 6.5

    def test_empty_results(self):
        assert compute_scores([]) == []

    def test_multiple_workflows(self):
        results = [
            _make_result(workflow="light"),
            _make_result(workflow="standard"),
        ]
        scores = compute_scores(results)
        assert len(scores) == 2
        wf_names = {s.workflow_name for s in scores}
        assert wf_names == {"light", "standard"}

    def test_completion_ratio(self):
        results = [
            _make_result(phases_completed=2, phases_total=4),
            _make_result(doc_idx=1, phases_completed=3, phases_total=4),
        ]
        scores = compute_scores(results)
        assert len(scores) == 1
        assert scores[0].avg_completion_ratio == pytest.approx(0.625)


@pytest.mark.unit
class TestRankModels:
    """Tests for rank_models."""

    def test_ranking_by_success_rate(self):
        scores = [
            ModelWorkflowScore(
                model_name="fast",
                workflow_name="light",
                total_runs=10,
                successes=7,
                avg_duration=2.0,
                avg_completion_ratio=0.9,
            ),
            ModelWorkflowScore(
                model_name="accurate",
                workflow_name="light",
                total_runs=10,
                successes=9,
                avg_duration=5.0,
                avg_completion_ratio=0.95,
            ),
        ]
        rankings = rank_models(scores)
        assert "light" in rankings
        assert rankings["light"][0]["model"] == "accurate"
        assert rankings["light"][0]["rank"] == 1

    def test_multiple_workflows(self):
        scores = [
            ModelWorkflowScore(
                model_name="m1",
                workflow_name="light",
                total_runs=5,
                successes=5,
                avg_duration=1.0,
                avg_completion_ratio=1.0,
            ),
            ModelWorkflowScore(
                model_name="m1",
                workflow_name="standard",
                total_runs=5,
                successes=3,
                avg_duration=3.0,
                avg_completion_ratio=0.8,
            ),
        ]
        rankings = rank_models(scores)
        assert len(rankings) == 2
        assert "light" in rankings
        assert "standard" in rankings


@pytest.mark.unit
class TestRankWorkflows:
    """Tests for rank_workflows."""

    def test_ranking_by_success_rate(self):
        scores = [
            ModelWorkflowScore(
                model_name="default",
                workflow_name="light",
                total_runs=10,
                successes=10,
                avg_duration=2.0,
                avg_completion_ratio=1.0,
            ),
            ModelWorkflowScore(
                model_name="default",
                workflow_name="full",
                total_runs=10,
                successes=6,
                avg_duration=10.0,
                avg_completion_ratio=0.7,
            ),
        ]
        rankings = rank_workflows(scores)
        assert "default" in rankings
        assert rankings["default"][0]["workflow"] == "light"


@pytest.mark.unit
class TestFindBest:
    """Tests for find_best."""

    def test_finds_best_combos(self):
        scores = [
            ModelWorkflowScore(
                model_name="fast",
                workflow_name="light",
                total_runs=5,
                successes=4,
                avg_duration=1.0,
                avg_completion_ratio=0.9,
            ),
            ModelWorkflowScore(
                model_name="accurate",
                workflow_name="standard",
                total_runs=5,
                successes=5,
                avg_duration=8.0,
                avg_completion_ratio=1.0,
            ),
        ]
        best = find_best(scores)
        assert "best_by_success" in best
        assert best["best_by_success"]["model"] == "accurate"
        assert "best_by_speed" in best
        assert best["best_by_speed"]["model"] == "fast"
        assert "best_overall" in best

    def test_empty_scores(self):
        assert find_best([]) == {}

    def test_no_successes(self):
        scores = [
            ModelWorkflowScore(
                model_name="bad",
                workflow_name="light",
                total_runs=5,
                successes=0,
            ),
        ]
        best = find_best(scores)
        assert "note" in best


@pytest.mark.unit
class TestGenerateMarkdownReport:
    """Tests for markdown report generation."""

    def test_basic_report(self):
        report = ComparisonReport(
            models=["m1", "m2"],
            workflows=["light"],
            num_documents=5,
            total_cells=10,
            total_duration_seconds=60.0,
            scores=[
                ModelWorkflowScore(
                    model_name="m1",
                    workflow_name="light",
                    total_runs=5,
                    successes=4,
                    avg_duration=3.0,
                    avg_completion_ratio=0.9,
                ),
                ModelWorkflowScore(
                    model_name="m2",
                    workflow_name="light",
                    total_runs=5,
                    successes=5,
                    avg_duration=5.0,
                    avg_completion_ratio=1.0,
                ),
            ],
        )
        md = generate_markdown_report(report)
        assert "# Multi-Model Benchmark Report" in md
        assert "m1" in md
        assert "m2" in md
        assert "light" in md

    def test_empty_report(self):
        report = ComparisonReport()
        md = generate_markdown_report(report)
        assert "# Multi-Model Benchmark Report" in md


@pytest.mark.unit
class TestListAvailableWorkflows:
    """Tests for workflow listing."""

    def test_returns_list(self):
        workflows = list_available_workflows()
        assert isinstance(workflows, list)
        assert len(workflows) > 0
        # At minimum light/standard should be present
        assert "light" in workflows or len(workflows) >= 3

    def test_contains_known_workflows(self):
        workflows = list_available_workflows()
        # These are defined in the catalog
        known = {"light", "standard", "full"}
        assert known.issubset(set(workflows))


@pytest.mark.unit
class TestRunMultiModelBenchmarkMocked:
    """Tests for run_multi_model_benchmark with full mocking."""

    @pytest.mark.asyncio
    async def test_basic_execution(self, tmp_path):
        """Test basic benchmark execution with mocked pipeline."""
        # Create test corpus
        corpus = {
            "documents": [
                {
                    "id": "test_001",
                    "text": "All cats are animals. Kitty is a cat. Therefore Kitty is an animal.",
                    "expected_fallacies": [],
                    "difficulty": "easy",
                }
            ]
        }
        corpus_file = tmp_path / "test_corpus.json"
        corpus_file.write_text(json.dumps(corpus), encoding="utf-8")

        output_dir = tmp_path / "results"

        # Mock the pipeline
        mock_result = {
            "workflow_name": "light",
            "phases": {
                "extract": MagicMock(
                    status=MagicMock(value="COMPLETED"),
                    capability="fact_extraction",
                    output={"facts": ["test"]},
                ),
            },
            "summary": {"completed": 1, "total": 1, "failed": 0, "skipped": 0},
            "unified_state": None,
        }

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "argumentation_analysis.evaluation.multi_model_benchmark.ModelRegistry.from_env"
        ) as mock_registry_cls:
            registry = ModelRegistry()
            registry.register(
                "test_model",
                ModelConfig(
                    model_id="test",
                    base_url="http://test:8080/v1",
                    api_key="test-key",
                ),
            )
            mock_registry_cls.return_value = registry

            report = await run_multi_model_benchmark(
                corpus_path=str(corpus_file),
                output_dir=str(output_dir),
                workflows=["light"],
                models=["test_model"],
                max_docs=1,
                timeout=30.0,
            )

        assert report.total_cells == 1
        assert report.num_documents == 1
        assert len(report.scores) == 1
        assert report.scores[0].model_name == "test_model"

        # Check files were created
        assert (output_dir / "comparison_report.json").exists()
        assert (output_dir / "comparison_report.md").exists()

    @pytest.mark.asyncio
    async def test_multiple_models_and_workflows(self, tmp_path):
        """Test matrix with 2 models × 2 workflows × 1 doc."""
        corpus = {"documents": [{"id": "t1", "text": "Test argument."}]}
        corpus_file = tmp_path / "corpus.json"
        corpus_file.write_text(json.dumps(corpus), encoding="utf-8")

        mock_result = {
            "workflow_name": "light",
            "phases": {},
            "summary": {"completed": 1, "total": 1, "failed": 0, "skipped": 0},
            "unified_state": None,
        }

        with patch(
            "argumentation_analysis.orchestration.unified_pipeline.run_unified_analysis",
            new_callable=AsyncMock,
            return_value=mock_result,
        ), patch(
            "argumentation_analysis.evaluation.multi_model_benchmark.ModelRegistry.from_env"
        ) as mock_reg:
            registry = ModelRegistry()
            registry.register(
                "model_a",
                ModelConfig(model_id="a", base_url="http://a/v1", api_key="k1"),
            )
            registry.register(
                "model_b",
                ModelConfig(model_id="b", base_url="http://b/v1", api_key="k2"),
            )
            mock_reg.return_value = registry

            report = await run_multi_model_benchmark(
                corpus_path=str(corpus_file),
                output_dir=str(tmp_path / "out"),
                workflows=["light", "standard"],
                models=["model_a", "model_b"],
                max_docs=1,
            )

        assert report.total_cells == 4  # 2 models × 2 workflows × 1 doc
        assert len(report.models) == 2
        assert len(report.workflows) == 2
        assert len(report.scores) == 4
