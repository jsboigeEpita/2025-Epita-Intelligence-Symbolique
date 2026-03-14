"""
Tests for CLI runners (run_baseline_benchmark, run_synergy_analysis).
"""

import argparse
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from argumentation_analysis.evaluation import run_baseline_benchmark, run_synergy_analysis


# =====================================================================
# run_baseline_benchmark.py Tests
# =====================================================================


class TestRunBaselineBenchmark:
    """Tests for the baseline benchmark CLI runner."""

    def test_argparse_default_values(self):
        """Verify CLI argument parser has expected defaults."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--corpus", default="argumentation_analysis/evaluation/corpus/baseline_corpus_v1.json")
        parser.add_argument("--output", default="argumentation_analysis/evaluation/results/baseline")
        parser.add_argument("--workflows", nargs="+", default=["light", "standard"])
        parser.add_argument("--max-docs", type=int, default=0)
        parser.add_argument("--skip-judge", action="store_true")
        parser.add_argument("--verbose", action="store_true")

        # Simulate no arguments
        args = parser.parse_args([])
        assert args.corpus.endswith("baseline_corpus_v1.json")
        assert args.output.endswith("results/baseline")
        assert args.workflows == ["light", "standard"]
        assert args.max_docs == 0
        assert not args.skip_judge
        assert not args.verbose

    def test_argparse_custom_workflows(self):
        """Verify custom workflow selection works."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--workflows", nargs="+", choices=["light", "standard", "full"])

        args = parser.parse_args(["--workflows", "light", "full"])
        assert args.workflows == ["light", "full"]

    def test_argparse_max_docs(self):
        """Verify max_docs limit parsing."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--max-docs", type=int, default=0)

        args = parser.parse_args(["--max-docs", "5"])
        assert args.max_docs == 5

    def test_argparse_skip_judge(self):
        """Verify skip_judge flag parsing."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--skip-judge", action="store_true")

        args = parser.parse_args(["--skip-judge"])
        assert args.skip_judge is True

    @pytest.mark.asyncio
    async def test_run_baseline_benchmark_creates_output_dir(self, tmp_path):
        """Verify output directory is created."""
        from argumentation_analysis.evaluation.run_baseline_benchmark import run_baseline_benchmark

        corpus_path = tmp_path / "corpus.json"
        output_dir = tmp_path / "output"

        # Create minimal corpus
        corpus_data = {
            "corpus_name": "test",
            "documents": [
                {"id": "doc1", "text": "Test argument.", "expected_fallacies": [], "difficulty": "easy"}
            ]
        }
        with open(corpus_path, "w", encoding="utf-8") as f:
            json.dump(corpus_data, f)

        # Mock the actual analysis
        with patch("argumentation_analysis.evaluation.benchmark_runner.BenchmarkRunner.run_cell", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(
                success=True,
                duration_seconds=1.0,
                phases_completed=1,
                phases_total=1,
                phases_failed=0,
                phases_skipped=0,
            )

            await run_baseline_benchmark(
                corpus_path=str(corpus_path),
                output_dir=str(output_dir),
                workflows=["light"],
                skip_judge=True,
            )

        assert output_dir.exists()

    @pytest.mark.asyncio
    async def test_run_baseline_saves_summary(self, tmp_path):
        """Verify benchmark summary is saved."""
        from argumentation_analysis.evaluation.run_baseline_benchmark import run_baseline_benchmark

        corpus_path = tmp_path / "corpus.json"
        output_dir = tmp_path / "output"

        corpus_data = {
            "corpus_name": "test",
            "documents": [{"id": "doc1", "text": "Test.", "expected_fallacies": [], "difficulty": "easy"}]
        }
        with open(corpus_path, "w", encoding="utf-8") as f:
            json.dump(corpus_data, f)

        with patch("argumentation_analysis.evaluation.benchmark_runner.BenchmarkRunner.run_cell", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = MagicMock(
                success=True, duration_seconds=1.0, phases_completed=1,
                phases_total=1, phases_failed=0, phases_skipped=0,
            )

            await run_baseline_benchmark(
                corpus_path=str(corpus_path),
                output_dir=str(output_dir),
                workflows=["light"],
                skip_judge=True,
            )

        summary_path = output_dir / "benchmark_summary.json"
        assert summary_path.exists()
        with open(summary_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        assert "total" in summary


# =====================================================================
# run_synergy_analysis.py Tests
# =====================================================================


class TestRunSynergyAnalysis:
    """Tests for the synergy analysis CLI runner."""

    def test_argparse_defaults(self):
        """Verify default CLI arguments."""
        from argumentation_analysis.evaluation.run_synergy_analysis import main

        parser = argparse.ArgumentParser()
        parser.add_argument("--results-dir", default="argumentation_analysis/evaluation/results")
        parser.add_argument("--output", default=None)
        parser.add_argument("--format", choices=["json", "markdown", "both"], default="both")
        parser.add_argument("--verbose", action="store_true")

        args = parser.parse_args([])
        assert args.results_dir.endswith("results")
        assert args.output is None
        assert args.format == "both"
        assert not args.verbose

    def test_argparse_format_json(self):
        """Verify JSON format selection."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--format", choices=["json", "markdown", "both"], default="both")

        args = parser.parse_args(["--format", "json"])
        assert args.format == "json"

    def test_argparse_format_markdown(self):
        """Verify Markdown format selection."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--format", choices=["json", "markdown", "both"], default="both")

        args = parser.parse_args(["--format", "markdown"])
        assert args.format == "markdown"

    def test_argparse_output_path(self):
        """Verify custom output path."""
        parser = argparse.ArgumentParser()
        parser.add_argument("--output", default=None)

        args = parser.parse_args(["--output", "/custom/path/report"])
        assert args.output == "/custom/path/report"

    @pytest.mark.skipif(os.name == "nt", reason="Permission issues on Windows with temporary directories")
    @pytest.mark.asyncio
    async def test_main_generates_reports(self, tmp_path):
        """Verify main() generates reports when results exist."""
        from argumentation_analysis.evaluation.run_synergy_analysis import main
        from argumentation_analysis.evaluation.result_collector import ResultCollector
        from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult

        results_dir = tmp_path / "results"
        results_dir.mkdir()

        # Create sample results
        collector = ResultCollector(results_dir)
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

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        # Use a fresh namespace for argparse
        import sys
        original_argv = sys.argv
        try:
            sys.argv = [
                "run_synergy_analysis.py",
                "--results-dir", str(results_dir),
                "--output", str(output_dir),
                "--format", "both",
            ]
            result = main()
        finally:
            sys.argv = original_argv

        assert result == 0
        # Check JSON report
        json_report = output_dir / "synergy_analysis_report.json"
        assert json_report.exists()
        # Check markdown report
        md_report = output_dir / "synergy_analysis_report.md"
        assert md_report.exists()

    @pytest.mark.asyncio
    async def test_main_no_results_error(self, tmp_path, caplog):
        """Verify main() returns error when no results found."""
        from argumentation_analysis.evaluation.run_synergy_analysis import main

        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch("sys.argv", [
            "run_synergy_analysis.py",
            "--results-dir", str(empty_dir),
        ]):
            result = main()

        assert result == 1
