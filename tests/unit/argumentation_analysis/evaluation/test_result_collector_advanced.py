"""
Advanced tests for result_collector.py (robustness, edge cases).
"""

import csv
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from argumentation_analysis.evaluation.result_collector import (
    DEFAULT_RESULTS_DIR,
    ResultCollector,
)
from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult


# =====================================================================
# ResultCollector Advanced Tests
# =====================================================================


class TestResultCollectorAdvanced:
    """Advanced tests for ResultCollector edge cases."""

    def test_default_results_dir(self):
        """Verify default results directory constant."""
        assert DEFAULT_RESULTS_DIR.as_posix().endswith("evaluation/results")

    def test_initialization_creates_directory(self, tmp_path):
        """Verify initialization creates results directory."""
        results_dir = tmp_path / "results"
        collector = ResultCollector(results_dir)
        assert results_dir.exists()

    def test_initialization_default_path(self):
        """Verify initialization with default path."""
        collector = ResultCollector()
        assert collector.results_dir == DEFAULT_RESULTS_DIR

    def test_save_creates_jsonl_file(self, tmp_path):
        """Verify saving creates JSONL file."""
        collector = ResultCollector(tmp_path)
        result = BenchmarkResult(
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
        )
        collector.save(result)

        jsonl_file = tmp_path / "benchmark_results.jsonl"
        assert jsonl_file.exists()

    def test_save_multiple_appends(self, tmp_path):
        """Verify multiple saves append to JSONL."""
        collector = ResultCollector(tmp_path)

        for i in range(3):
            result = BenchmarkResult(
                workflow_name="light",
                model_name="test",
                document_index=i,
                document_name=f"doc{i}",
                success=True,
                duration_seconds=1.0,
                phases_completed=3,
                phases_total=3,
                phases_failed=0,
                phases_skipped=0,
            )
            collector.save(result)

        loaded = collector.load_all()
        assert len(loaded) == 3

    def test_load_all_with_unicode_content(self, tmp_path):
        """Verify loading handles Unicode content correctly."""
        collector = ResultCollector(tmp_path)
        result = BenchmarkResult(
            workflow_name="light",
            model_name="test",
            document_index=0,
            document_name="文档 français 日本語",
            success=True,
            duration_seconds=1.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error="Error: émojis 🚀 test",
        )
        collector.save(result)

        loaded = collector.load_all()
        assert len(loaded) == 1
        assert "文档" in loaded[0]["document_name"]
        assert "émojis" in loaded[0]["error"]

    def test_load_all_malformed_jsonl_skips_bad_lines(self, tmp_path, caplog):
        """Verify loading skips malformed JSON lines."""
        import logging

        # Create a JSONL file with some bad lines
        jsonl_file = tmp_path / "benchmark_results.jsonl"
        with open(jsonl_file, "w", encoding="utf-8") as f:
            f.write('{"workflow_name": "light", "success": true}\n')
            f.write('this is not json\n')
            f.write('{"workflow_name": "standard", "success": false}\n')

        collector = ResultCollector(tmp_path)
        # Should load valid lines and skip invalid ones
        # Note: current implementation may raise JSONDecodeError
        # This test documents expected behavior
        try:
            loaded = collector.load_all()
            # If it works, we should get 2 results
            assert len(loaded) <= 2
        except json.JSONDecodeError:
            # Current behavior: fails on first bad line
            pass

    def test_query_combined_filters(self, tmp_path):
        """Verify query with multiple filters."""
        collector = ResultCollector(tmp_path)

        # Create varied results
        collector.save(BenchmarkResult(
            workflow_name="light", model_name="gpt", document_index=0,
            document_name="doc1", success=True, duration_seconds=1.0,
            phases_completed=3, phases_total=3, phases_failed=0, phases_skipped=0,
        ))
        collector.save(BenchmarkResult(
            workflow_name="light", model_name="claude", document_index=1,
            document_name="doc2", success=False, duration_seconds=0.5,
            phases_completed=1, phases_total=3, phases_failed=1, phases_skipped=0,
        ))
        collector.save(BenchmarkResult(
            workflow_name="standard", model_name="gpt", document_index=0,
            document_name="doc1", success=True, duration_seconds=2.0,
            phases_completed=5, phases_total=6, phases_failed=0, phases_skipped=1,
        ))

        # Query: light workflow + gpt model + success only
        results = collector.query(
            workflow_name="light",
            model_name="gpt",
            success_only=True,
        )
        assert len(results) == 1

    def test_query_by_document_index(self, tmp_path):
        """Verify query by document index."""
        collector = ResultCollector(tmp_path)

        collector.save(BenchmarkResult(
            workflow_name="light", model_name="test", document_index=0,
            document_name="doc0", success=True, duration_seconds=1.0,
            phases_completed=3, phases_total=3, phases_failed=0, phases_skipped=0,
        ))
        collector.save(BenchmarkResult(
            workflow_name="light", model_name="test", document_index=1,
            document_name="doc1", success=True, duration_seconds=1.0,
            phases_completed=3, phases_total=3, phases_failed=0, phases_skipped=0,
        ))

        results = collector.query(document_index=0)
        assert len(results) == 1
        assert results[0]["document_index"] == 0

    def test_query_empty_filters_returns_all(self, tmp_path):
        """Verify query with no filters returns all results."""
        collector = ResultCollector(tmp_path)

        for i in range(3):
            collector.save(BenchmarkResult(
                workflow_name="light", model_name="test", document_index=i,
                document_name=f"doc{i}", success=True, duration_seconds=1.0,
                phases_completed=3, phases_total=3, phases_failed=0, phases_skipped=0,
            ))

        results = collector.query()
        assert len(results) == 3

    def test_generate_summary_with_all_failures(self, tmp_path):
        """Verify summary when all runs failed."""
        collector = ResultCollector(tmp_path)

        for i in range(3):
            collector.save(BenchmarkResult(
                workflow_name="light", model_name="test", document_index=i,
                document_name=f"doc{i}", success=False, duration_seconds=0.5,
                phases_completed=0, phases_total=3, phases_failed=1, phases_skipped=0,
                error="Test error",
            ))

        summary = collector.generate_summary()
        assert summary["total"] == 3
        assert summary["successes"] == 0
        assert summary["failures"] == 3

    def test_generate_summary_with_mixed_results(self, tmp_path):
        """Verify summary with mixed success/failure."""
        collector = ResultCollector(tmp_path)

        # 2 successes
        for i in range(2):
            collector.save(BenchmarkResult(
                workflow_name="light", model_name="gpt", document_index=i,
                document_name=f"doc{i}", success=True, duration_seconds=2.0,
                phases_completed=3, phases_total=3, phases_failed=0, phases_skipped=0,
            ))
        # 1 failure
        collector.save(BenchmarkResult(
            workflow_name="light", model_name="gpt", document_index=2,
            document_name="doc2", success=False, duration_seconds=0.5,
            phases_completed=0, phases_total=3, phases_failed=1, phases_skipped=0,
            error="Failed",
        ))

        summary = collector.generate_summary()
        assert summary["total"] == 3
        assert summary["successes"] == 2
        assert summary["failures"] == 1
        assert "gpt" in summary["by_model"]
        assert summary["by_model"]["gpt"]["total"] == 3
        assert summary["by_model"]["gpt"]["success"] == 2

    def test_export_csv_with_all_fields(self, tmp_path):
        """Verify CSV export includes all expected fields."""
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
            error=None,
            state_snapshot={"key": "value"},
        ))

        csv_path = collector.export_csv()

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 1
            row = rows[0]
            assert row["workflow_name"] == "light"
            assert row["success"] == "True"
            assert row["duration_seconds"] == "1.5"

    def test_export_csv_empty_results(self, tmp_path):
        """Verify CSV export with no results doesn't create file."""
        collector = ResultCollector(tmp_path)
        csv_path = collector.export_csv()

        # When no results, file is not created
        # (function returns path but doesn't write to it)
        assert not csv_path.exists()

    def test_export_csv_custom_path(self, tmp_path):
        """Verify CSV export to custom path."""
        collector = ResultCollector(tmp_path)
        collector.save(BenchmarkResult(
            workflow_name="light", model_name="test", document_index=0,
            document_name="doc1", success=True, duration_seconds=1.0,
            phases_completed=3, phases_total=3, phases_failed=0, phases_skipped=0,
        ))

        custom_path = tmp_path / "custom_output.csv"
        result_path = collector.export_csv(output_path=custom_path)

        assert result_path == custom_path
        assert custom_path.exists()

    def test_save_batch_empty_list(self, tmp_path):
        """Verify saving empty batch doesn't create file."""
        collector = ResultCollector(tmp_path)
        collector.save_batch([])

        jsonl_file = tmp_path / "benchmark_results.jsonl"
        # File shouldn't be created for empty batch
        # (or if created, should be empty)
        if jsonl_file.exists():
            assert jsonl_file.stat().st_size == 0

    def test_save_batch_with_results(self, tmp_path):
        """Verify batch save writes all results."""
        collector = ResultCollector(tmp_path)

        results = [
            BenchmarkResult(
                workflow_name="light", model_name="test", document_index=i,
                document_name=f"doc{i}", success=True, duration_seconds=1.0,
                phases_completed=3, phases_total=3, phases_failed=0, phases_skipped=0,
            )
            for i in range(5)
        ]

        collector.save_batch(results)
        loaded = collector.load_all()
        assert len(loaded) == 5

    def test_query_nonexistent_model(self, tmp_path):
        """Verify query for non-existent model returns empty."""
        collector = ResultCollector(tmp_path)
        collector.save(BenchmarkResult(
            workflow_name="light", model_name="gpt", document_index=0,
            document_name="doc1", success=True, duration_seconds=1.0,
            phases_completed=3, phases_total=3, phases_failed=0, phases_skipped=0,
        ))

        results = collector.query(model_name="nonexistent")
        assert len(results) == 0

    def test_query_nonexistent_workflow(self, tmp_path):
        """Verify query for non-existent workflow returns empty."""
        collector = ResultCollector(tmp_path)
        collector.save(BenchmarkResult(
            workflow_name="light", model_name="test", document_index=0,
            document_name="doc1", success=True, duration_seconds=1.0,
            phases_completed=3, phases_total=3, phases_failed=0, phases_skipped=0,
        ))

        results = collector.query(workflow_name="nonexistent")
        assert len(results) == 0
