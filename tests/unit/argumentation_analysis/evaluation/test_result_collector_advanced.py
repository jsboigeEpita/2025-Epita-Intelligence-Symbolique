"""
Advanced tests for ResultCollector.

Tests cover:
- JSONL persistence and append-only behavior
- Unicode handling (accents, emojis, special characters)
- CSV export functionality
- Query filtering and aggregation
"""

import csv
import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

from argumentation_analysis.evaluation.result_collector import ResultCollector
from argumentation_analysis.evaluation.benchmark_runner import BenchmarkResult


@pytest.mark.unit
class TestJSONLPersistence:
    """Test JSONL append-only persistence."""

    def test_single_result_persistence(self, tmp_path):
        """Test that a single result is correctly persisted to JSONL."""
        collector = ResultCollector(tmp_path)

        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="light",
            model_name="gpt-4",
            document_index=0,
            document_name="doc1.txt",
            success=True,
            duration_seconds=5.2,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={"key": "value"},
        )
        collector.save(result)

        # Verify file was created
        assert collector._results_file.exists()

        # Load and verify content
        loaded = collector.load_all()
        assert len(loaded) == 1
        assert loaded[0]["workflow_name"] == "light"
        assert loaded[0]["success"] is True

    def test_append_only_behavior(self, tmp_path):
        """Test that results are appended, not overwritten."""
        collector = ResultCollector(tmp_path)

        # Save first result
        result1 = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="light",
            model_name="gpt-4",
            document_index=0,
            document_name="doc1.txt",
            success=True,
            duration_seconds=5.2,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={},
        )
        collector.save(result1)

        # Save second result
        result2 = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="standard",
            model_name="gpt-4",
            document_index=1,
            document_name="doc2.txt",
            success=True,
            duration_seconds=8.5,
            phases_completed=5,
            phases_total=5,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={},
        )
        collector.save(result2)

        # Verify both are present
        loaded = collector.load_all()
        assert len(loaded) == 2
        assert loaded[0]["workflow_name"] == "light"
        assert loaded[1]["workflow_name"] == "standard"

    def test_batch_save(self, tmp_path):
        """Test saving multiple results in batch."""
        collector = ResultCollector(tmp_path)

        results = [
            BenchmarkResult(
                timestamp=datetime.now().isoformat(),
                workflow_name="light",
                model_name="gpt-4",
                document_index=i,
                document_name=f"doc{i}.txt",
                success=True,
                duration_seconds=5.0 + i,
                phases_completed=3,
                phases_total=3,
                phases_failed=0,
                phases_skipped=0,
                error=None,
                state_snapshot={},
            )
            for i in range(10)
        ]

        collector.save_batch(results)

        loaded = collector.load_all()
        assert len(loaded) == 10
        assert all(r["success"] for r in loaded)

    def test_load_from_existing_file(self, tmp_path):
        """Test loading from an existing JSONL file."""
        # Create a JSONL file manually
        jsonl_path = tmp_path / "benchmark_results.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for i in range(3):
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "workflow_name": "light",
                    "model_name": "gpt-4",
                    "document_index": i,
                    "document_name": f"doc{i}.txt",
                    "success": True,
                    "duration_seconds": 5.0,
                    "phases_completed": 3,
                    "phases_total": 3,
                    "phases_failed": 0,
                    "phases_skipped": 0,
                }
                f.write(json.dumps(data, ensure_ascii=False) + "\n")

        # Create collector and load
        collector = ResultCollector(tmp_path)
        loaded = collector.load_all()

        assert len(loaded) == 3
        assert loaded[0]["document_index"] == 0
        assert loaded[2]["document_index"] == 2


@pytest.mark.unit
class TestUnicodeHandling:
    """Test proper handling of Unicode characters."""

    def test_french_accents(self, tmp_path):
        """Test handling of French accented characters."""
        collector = ResultCollector(tmp_path)

        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="light",
            model_name="gpt-4",
            document_index=0,
            document_name="document_français.txt",
            success=True,
            duration_seconds=5.2,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={"message": "Analyse terminée avec succès"},
        )
        collector.save(result)

        # Load and verify accents are preserved
        loaded = collector.load_all()
        assert len(loaded) == 1
        assert loaded[0]["document_name"] == "document_français.txt"
        assert loaded[0]["state_snapshot"]["message"] == "Analyse terminée avec succès"

    def test_emoji_in_results(self, tmp_path):
        """Test handling of emoji characters."""
        collector = ResultCollector(tmp_path)

        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="standard",
            model_name="gpt-4",
            document_index=0,
            document_name="doc_emoji.txt",
            success=True,
            duration_seconds=5.2,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={
                "status": "✅ Success",
                "flags": ["🔍 Analysis", "📊 Results", "⚠️ Warning"],
                "metrics": {"quality": "🌟 Excellent"}
            },
        )
        collector.save(result)

        # Load and verify emojis are preserved
        loaded = collector.load_all()
        assert len(loaded) == 1
        assert loaded[0]["state_snapshot"]["status"] == "✅ Success"
        assert "🔍 Analysis" in loaded[0]["state_snapshot"]["flags"]
        assert loaded[0]["state_snapshot"]["metrics"]["quality"] == "🌟 Excellent"

    def test_special_unicode_characters(self, tmp_path):
        """Test handling of various special Unicode characters."""
        collector = ResultCollector(tmp_path)

        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="full",
            model_name="gpt-4",
            document_index=0,
            document_name="αρχή.document.txt",  # Greek
            success=True,
            duration_seconds=5.2,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error=None,
            state_snapshot={
                "arabic": "مرحبا",  # Arabic
                "chinese": "你好",  # Chinese
                "russian": "Привет",  # Russian
                "math": "∑(n=1→∞)1/n² = π²/6",  # Math symbols
                "currency": "€100 = $110 = ¥9500",  # Currency symbols
            },
        )
        collector.save(result)

        # Load and verify all characters are preserved
        loaded = collector.load_all()
        assert len(loaded) == 1
        assert "αρχή" in loaded[0]["document_name"]
        assert loaded[0]["state_snapshot"]["arabic"] == "مرحبا"
        assert loaded[0]["state_snapshot"]["chinese"] == "你好"
        assert loaded[0]["state_snapshot"]["russian"] == "Привет"
        assert "∑" in loaded[0]["state_snapshot"]["math"]
        assert "€" in loaded[0]["state_snapshot"]["currency"]


@pytest.mark.unit
class TestCSVExport:
    """Test CSV export functionality."""

    def test_basic_csv_export(self, tmp_path):
        """Test basic CSV export creates valid file."""
        collector = ResultCollector(tmp_path)

        # Add sample results
        for i in range(3):
            result = BenchmarkResult(
                timestamp=datetime.now().isoformat(),
                workflow_name="light",
                model_name="gpt-4",
                document_index=i,
                document_name=f"doc{i}.txt",
                success=True,
                duration_seconds=5.0 + i,
                phases_completed=3,
                phases_total=3,
                phases_failed=0,
                phases_skipped=0,
                error=None,
                state_snapshot={},
            )
            collector.save(result)

        # Export to CSV
        csv_path = collector.export_csv()
        assert csv_path.exists()

        # Verify CSV content
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["workflow_name"] == "light"
        assert rows[0]["success"] == "True"

    def test_csv_custom_path(self, tmp_path):
        """Test CSV export to custom path."""
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

        # Create parent directory first (export_csv doesn't create directories)
        custom_dir = tmp_path / "custom_export"
        custom_dir.mkdir(parents=True, exist_ok=True)
        custom_path = custom_dir / "results.csv"
        result_path = collector.export_csv(custom_path)

        assert result_path == custom_path
        assert custom_path.exists()

    def test_csv_with_unicode(self, tmp_path):
        """Test that CSV preserves Unicode characters."""
        collector = ResultCollector(tmp_path)

        result = BenchmarkResult(
            timestamp=datetime.now().isoformat(),
            workflow_name="standard",
            model_name="gpt-4",
            document_index=0,
            document_name="document_français_émoji_✅.txt",
            success=True,
            duration_seconds=5.0,
            phases_completed=3,
            phases_total=3,
            phases_failed=0,
            phases_skipped=0,
            error="Erreur: échéance dépassée",
            state_snapshot={"message": "Analyse terminée 🎉"},
        )
        collector.save(result)

        csv_path = collector.export_csv()

        # Verify Unicode is preserved in CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            content = f.read()

        assert "français" in content
        assert "✅" in content  # Emoji in document_name (exported to CSV)
        assert "Erreur: échéance" in content
        # Note: state_snapshot is NOT exported to CSV, so 🎉 won't be present

    def test_csv_with_failed_results(self, tmp_path):
        """Test CSV export includes failed results."""
        collector = ResultCollector(tmp_path)

        # Mix of successful and failed results
        for i in range(3):
            result = BenchmarkResult(
                timestamp=datetime.now().isoformat(),
                workflow_name="light",
                model_name="gpt-4",
                document_index=i,
                document_name=f"doc{i}.txt",
                success=(i != 1),  # Second one fails
                duration_seconds=5.0 if i != 1 else 0,
                phases_completed=3 if i != 1 else 0,
                phases_total=3,
                phases_failed=0 if i != 1 else 3,
                phases_skipped=0,
                error=None if i != 1 else "Timeout exceeded",
                state_snapshot={},
            )
            collector.save(result)

        csv_path = collector.export_csv()

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 3
        assert rows[0]["success"] == "True"
        assert rows[1]["success"] == "False"
        assert rows[1]["error"] == "Timeout exceeded"
        assert rows[2]["success"] == "True"

    def test_csv_export_empty_results(self, tmp_path):
        """Test CSV export with no results returns path without creating file."""
        collector = ResultCollector(tmp_path)

        csv_path = collector.export_csv()
        # When there are no results, the file is NOT created
        # The function returns the path but logs a warning
        assert not csv_path.exists()


@pytest.mark.unit
class TestQueryFiltering:
    """Test query filtering functionality."""

    def test_filter_by_workflow(self, tmp_path):
        """Test filtering results by workflow name."""
        collector = ResultCollector(tmp_path)

        # Add results for different workflows
        for workflow in ["light", "standard", "full"]:
            result = BenchmarkResult(
                timestamp=datetime.now().isoformat(),
                workflow_name=workflow,
                model_name="gpt-4",
                document_index=0,
                document_name=f"{workflow}_doc.txt",
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

        # Query for specific workflow
        light_results = collector.query(workflow_name="light")
        assert len(light_results) == 1
        assert light_results[0]["workflow_name"] == "light"

    def test_filter_by_model(self, tmp_path):
        """Test filtering results by model name."""
        collector = ResultCollector(tmp_path)

        # Add results for different models
        for model in ["gpt-4", "gpt-3.5-turbo", "claude-3"]:
            result = BenchmarkResult(
                timestamp=datetime.now().isoformat(),
                workflow_name="light",
                model_name=model,
                document_index=0,
                document_name=f"{model}_doc.txt",
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

        # Query for specific model
        gpt4_results = collector.query(model_name="gpt-4")
        assert len(gpt4_results) == 1
        assert gpt4_results[0]["model_name"] == "gpt-4"

    def test_filter_success_only(self, tmp_path):
        """Test filtering for only successful results."""
        collector = ResultCollector(tmp_path)

        # Add mix of successful and failed results
        for i in range(5):
            result = BenchmarkResult(
                timestamp=datetime.now().isoformat(),
                workflow_name="light",
                model_name="gpt-4",
                document_index=i,
                document_name=f"doc{i}.txt",
                success=(i % 2 == 0),  # Even indices succeed
                duration_seconds=5.0,
                phases_completed=3 if i % 2 == 0 else 0,
                phases_total=3,
                phases_failed=0 if i % 2 == 0 else 3,
                phases_skipped=0,
                error=None if i % 2 == 0 else "Failed",
                state_snapshot={},
            )
            collector.save(result)

        success_results = collector.query(success_only=True)
        assert len(success_results) == 3  # Indices 0, 2, 4
        assert all(r["success"] for r in success_results)

    def test_combined_filters(self, tmp_path):
        """Test combining multiple filters."""
        collector = ResultCollector(tmp_path)

        # Add various combinations
        workflows = ["light", "standard"]
        models = ["gpt-4", "gpt-3.5-turbo"]
        idx = 0
        for workflow in workflows:
            for model in models:
                for success in [True, False]:
                    result = BenchmarkResult(
                        timestamp=datetime.now().isoformat(),
                        workflow_name=workflow,
                        model_name=model,
                        document_index=idx,
                        document_name=f"doc{idx}.txt",
                        success=success,
                        duration_seconds=5.0,
                        phases_completed=3 if success else 0,
                        phases_total=3,
                        phases_failed=0 if success else 3,
                        phases_skipped=0,
                        error=None if success else "Failed",
                        state_snapshot={},
                    )
                    collector.save(result)
                    idx += 1

        # Query with combined filters
        results = collector.query(
            workflow_name="light",
            model_name="gpt-4",
            success_only=True
        )
        assert len(results) == 1  # Only one result matches all criteria
        assert results[0]["workflow_name"] == "light"
        assert results[0]["model_name"] == "gpt-4"
        assert results[0]["success"] is True
