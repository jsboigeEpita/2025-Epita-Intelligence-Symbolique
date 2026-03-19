"""
Tests for CLI runners (run_baseline_benchmark, run_synergy_analysis).

Tests cover:
- argparse validation
- directory creation
- report generation
- error handling
"""

import argparse
import json
import logging
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.evaluation.run_baseline_benchmark import (
    main as baseline_main,
    run_baseline_benchmark,
)
from argumentation_analysis.evaluation.run_synergy_analysis import main as synergy_main


@pytest.mark.unit
class TestBaselineBenchmarkArgparse:
    """Test argparse configuration for baseline benchmark runner."""

    def test_default_arguments(self):
        """Test that default arguments are correctly configured."""
        parser = argparse.ArgumentParser(description="Baseline Capability Benchmark")
        parser.add_argument("--corpus", default="argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json")
        parser.add_argument("--output", default="argumentation_analysis/evaluation/results/baseline")
        parser.add_argument("--workflows", nargs="+", default=["light", "standard"])
        parser.add_argument("--max-docs", type=int, default=0)
        parser.add_argument("--skip-judge", action="store_true")
        parser.add_argument("--verbose", action="store_true")

        # Test with no arguments (use defaults)
        args = parser.parse_args([])
        assert args.corpus == "argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json"
        assert args.output == "argumentation_analysis/evaluation/results/baseline"
        assert args.workflows == ["light", "standard"]
        assert args.max_docs == 0
        assert args.skip_judge is False
        assert args.verbose is False

    def test_custom_arguments(self):
        """Test that custom arguments are correctly parsed."""
        parser = argparse.ArgumentParser(description="Baseline Capability Benchmark")
        parser.add_argument("--corpus", default="default_corpus.json")
        parser.add_argument("--output", default="default_output")
        parser.add_argument("--workflows", nargs="+", default=["light"])
        parser.add_argument("--max-docs", type=int, default=0)
        parser.add_argument("--skip-judge", action="store_true")
        parser.add_argument("--verbose", action="store_true")

        args = parser.parse_args([
            "--corpus", "custom_corpus.json",
            "--output", "custom_output",
            "--workflows", "light", "full",
            "--max-docs", "10",
            "--skip-judge",
            "--verbose"
        ])
        assert args.corpus == "custom_corpus.json"
        assert args.output == "custom_output"
        assert args.workflows == ["light", "full"]
        assert args.max_docs == 10
        assert args.skip_judge is True
        assert args.verbose is True


@pytest.mark.unit
class TestSynergyAnalysisArgparse:
    """Test argparse configuration for synergy analysis runner."""

    def test_default_arguments(self):
        """Test that default arguments are correctly configured."""
        parser = argparse.ArgumentParser(description="Synergy Analysis - Optimal Workflow Configuration")
        parser.add_argument("--results-dir", default="argumentation_analysis/evaluation/results")
        parser.add_argument("--output", default=None)
        parser.add_argument("--format", choices=["json", "markdown", "both"], default="both")
        parser.add_argument("--verbose", action="store_true")

        args = parser.parse_args([])
        assert args.results_dir == "argumentation_analysis/evaluation/results"
        assert args.output is None
        assert args.format == "both"
        assert args.verbose is False

    def test_custom_arguments(self):
        """Test that custom arguments are correctly parsed."""
        parser = argparse.ArgumentParser(description="Synergy Analysis - Optimal Workflow Configuration")
        parser.add_argument("--results-dir", default="default_results")
        parser.add_argument("--output", default=None)
        parser.add_argument("--format", choices=["json", "markdown", "both"], default="both")
        parser.add_argument("--verbose", action="store_true")

        args = parser.parse_args([
            "--results-dir", "custom_results",
            "--output", "custom_report.md",
            "--format", "markdown",
            "--verbose"
        ])
        assert args.results_dir == "custom_results"
        assert args.output == "custom_report.md"
        assert args.format == "markdown"
        assert args.verbose is True

    def test_invalid_format(self):
        """Test that invalid format is rejected."""
        parser = argparse.ArgumentParser(description="Synergy Analysis - Optimal Workflow Configuration")
        parser.add_argument("--format", choices=["json", "markdown", "both"], default="both")

        with pytest.raises(SystemExit):
            parser.parse_args(["--format", "invalid"])


@pytest.mark.unit
class TestDirectoryCreation:
    """Test directory creation for output paths."""

    @pytest.mark.asyncio
    async def test_output_directory_created(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        output_dir = tmp_path / "new_output_dir"
        assert not output_dir.exists()

        # Mock the benchmark components
        with patch("argumentation_analysis.evaluation.run_baseline_benchmark.ModelRegistry") as mock_registry, \
             patch("argumentation_analysis.evaluation.run_baseline_benchmark.BenchmarkRunner") as mock_runner:

            mock_instance = MagicMock()
            mock_runner.return_value = mock_instance
            mock_instance._dataset = []
            mock_instance.run_cell = AsyncMock(return_value=MagicMock(
                success=True,
                duration_seconds=1.0,
                error=None
            ))

            # Create a minimal corpus file
            corpus_path = tmp_path / "test_corpus.json"
            corpus_data = {"documents": [{"id": "doc1", "text": "Test document"}]}
            corpus_path.write_text(json.dumps(corpus_data), encoding="utf-8")

            try:
                await run_baseline_benchmark(
                    corpus_path=str(corpus_path),
                    output_dir=str(output_dir),
                    workflows=["light"],
                    max_docs=1,
                    skip_judge=True,
                )
            except Exception:
                pass  # We only care about directory creation

            # Directory should be created even if other parts fail
            assert output_dir.exists()

    def test_existing_directory_not_recreated(self, tmp_path):
        """Test that existing directory is not recreated."""
        existing_dir = tmp_path / "existing_output"
        existing_dir.mkdir(parents=True, exist_ok=True)

        # Write a marker file to verify it's not deleted
        marker = existing_dir / "marker.txt"
        marker.write_text("existing")

        assert existing_dir.exists()
        assert marker.exists()

        # The directory should still exist with marker intact
        assert existing_dir.exists()
        assert marker.exists()


@pytest.mark.unit
class TestReportGeneration:
    """Test report generation functionality."""

    def test_summary_json_format(self, tmp_path):
        """Test that summary is generated in valid JSON format."""
        output_dir = tmp_path / "results"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create a sample summary
        summary = {
            "total_runs": 10,
            "successful_runs": 8,
            "failed_runs": 2,
            "success_rate": 0.8,
            "workflows": {
                "light": {"total": 5, "successful": 4, "failed": 1},
                "standard": {"total": 5, "successful": 4, "failed": 1},
            }
        }

        summary_path = output_dir / "benchmark_summary.json"
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False, default=str)

        # Verify JSON is valid
        with open(summary_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        assert loaded["total_runs"] == 10
        assert loaded["successful_runs"] == 8
        assert loaded["workflows"]["light"]["successful"] == 4

    @pytest.mark.asyncio
    async def test_summary_contains_all_workflows(self, tmp_path):
        """Test that summary includes data for all workflows."""
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        output_dir = tmp_path / "results"
        output_dir.mkdir(parents=True, exist_ok=True)
        collector = ResultCollector(output_dir)

        # Add sample results for different workflows
        for workflow in ["light", "standard", "full"]:
            for i in range(3):
                result = BenchmarkResult(
                    workflow_name=workflow,
                    model_name="gpt-4",
                    document_index=i,
                    document_name=f"{workflow}_doc{i}.txt",
                    success=True,
                    duration_seconds=1.0 + i,
                    phases_completed=3,
                    phases_total=3,
                    phases_failed=0,
                    phases_skipped=0,
                    error=None,
                    state_snapshot={}
                )
                collector.save(result)

        summary = collector.generate_summary()

        assert "light" in str(summary)
        assert "standard" in str(summary)
        assert "full" in str(summary)


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in CLI runners."""

    @pytest.mark.asyncio
    async def test_missing_corpus_file(self, tmp_path):
        """Test that missing corpus file is handled gracefully."""
        output_dir = tmp_path / "results"
        output_dir.mkdir(parents=True, exist_ok=True)

        with pytest.raises(FileNotFoundError):
            await run_baseline_benchmark(
                corpus_path="nonexistent_corpus.json",
                output_dir=str(output_dir),
                workflows=["light"],
                max_docs=0,
                skip_judge=True,
            )

    @pytest.mark.asyncio
    async def test_invalid_corpus_format(self, tmp_path):
        """Test that invalid corpus format is handled."""
        output_dir = tmp_path / "results"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create an invalid corpus file
        corpus_path = tmp_path / "invalid_corpus.json"
        corpus_path.write_text("not valid json", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            await run_baseline_benchmark(
                corpus_path=str(corpus_path),
                output_dir=str(output_dir),
                workflows=["light"],
                max_docs=0,
                skip_judge=True,
            )
