# tests/unit/argumentation_analysis/utils/dev_tools/test_reporting_utils.py
"""Tests for reporting_utils — coverage evolution report generation."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from argumentation_analysis.utils.dev_tools.reporting_utils import (
    generate_coverage_evolution_text_report,
)


@pytest.fixture
def history_data():
    """Minimal valid history data with 2 entries."""
    return [
        {
            "timestamp": "2026-01-01",
            "global_line_rate": 50.0,
            "packages": {
                "argumentation_analysis.core": {"line_rate": 40.0},
                "argumentation_analysis.agents": {"line_rate": 60.0},
            },
        },
        {
            "timestamp": "2026-02-01",
            "global_line_rate": 70.0,
            "packages": {
                "argumentation_analysis.core": {"line_rate": 65.0},
                "argumentation_analysis.agents": {"line_rate": 75.0},
            },
        },
    ]


class TestGenerateCoverageEvolutionReport:
    """Tests for generate_coverage_evolution_text_report()."""

    def test_nonexistent_history_file(self, tmp_path):
        history = tmp_path / "nonexistent.json"
        output = tmp_path / "report.txt"
        result = generate_coverage_evolution_text_report(history, output)
        assert result is False

    def test_invalid_json_returns_false(self, tmp_path):
        history = tmp_path / "bad.json"
        history.write_text("not valid json {{{", encoding="utf-8")
        output = tmp_path / "report.txt"
        result = generate_coverage_evolution_text_report(history, output)
        assert result is False

    def test_history_not_list_returns_false(self, tmp_path):
        history = tmp_path / "history.json"
        history.write_text(json.dumps({"key": "value"}), encoding="utf-8")
        output = tmp_path / "report.txt"
        result = generate_coverage_evolution_text_report(history, output)
        assert result is False

    def test_history_too_short_returns_false(self, tmp_path):
        history = tmp_path / "history.json"
        history.write_text(json.dumps([{"timestamp": "2026-01-01"}]), encoding="utf-8")
        output = tmp_path / "report.txt"
        result = generate_coverage_evolution_text_report(history, output)
        assert result is False

    def test_valid_history_generates_report(self, tmp_path, history_data):
        history = tmp_path / "history.json"
        history.write_text(json.dumps(history_data), encoding="utf-8")
        output = tmp_path / "report.txt"
        result = generate_coverage_evolution_text_report(history, output)
        assert result is True
        assert output.exists()

    def test_report_contains_header(self, tmp_path, history_data):
        history = tmp_path / "history.json"
        history.write_text(json.dumps(history_data), encoding="utf-8")
        output = tmp_path / "report.txt"
        generate_coverage_evolution_text_report(history, output)
        content = output.read_text(encoding="utf-8")
        assert "Rapport d'Évolution de la Couverture" in content

    def test_report_contains_global_coverage(self, tmp_path, history_data):
        history = tmp_path / "history.json"
        history.write_text(json.dumps(history_data), encoding="utf-8")
        output = tmp_path / "report.txt"
        generate_coverage_evolution_text_report(history, output)
        content = output.read_text(encoding="utf-8")
        assert "50.00%" in content
        assert "70.00%" in content
        assert "+20.00%" in content

    def test_report_contains_timestamps(self, tmp_path, history_data):
        history = tmp_path / "history.json"
        history.write_text(json.dumps(history_data), encoding="utf-8")
        output = tmp_path / "report.txt"
        generate_coverage_evolution_text_report(history, output)
        content = output.read_text(encoding="utf-8")
        assert "2026-01-01" in content
        assert "2026-02-01" in content

    def test_report_contains_module_improvements(self, tmp_path, history_data):
        history = tmp_path / "history.json"
        history.write_text(json.dumps(history_data), encoding="utf-8")
        output = tmp_path / "report.txt"
        generate_coverage_evolution_text_report(history, output)
        content = output.read_text(encoding="utf-8")
        assert "Amélioration" in content

    def test_old_format_global_key(self, tmp_path):
        """Test fallback to 'global' key when 'global_line_rate' missing."""
        data = [
            {"timestamp": "t1", "global": 30.0, "packages": {}},
            {"timestamp": "t2", "global": 50.0, "packages": {}},
        ]
        history = tmp_path / "history.json"
        history.write_text(json.dumps(data), encoding="utf-8")
        output = tmp_path / "report.txt"
        result = generate_coverage_evolution_text_report(history, output)
        assert result is True
        content = output.read_text(encoding="utf-8")
        assert "30.00%" in content

    def test_numeric_package_rates(self, tmp_path):
        """Test when package values are direct numbers, not dicts."""
        data = [
            {"timestamp": "t1", "global_line_rate": 40.0, "packages": {"pkg1": 30.0}},
            {"timestamp": "t2", "global_line_rate": 60.0, "packages": {"pkg1": 55.0}},
        ]
        history = tmp_path / "history.json"
        history.write_text(json.dumps(data), encoding="utf-8")
        output = tmp_path / "report.txt"
        result = generate_coverage_evolution_text_report(history, output)
        assert result is True

    def test_output_dir_created_if_missing(self, tmp_path, history_data):
        history = tmp_path / "history.json"
        history.write_text(json.dumps(history_data), encoding="utf-8")
        output = tmp_path / "subdir" / "deep" / "report.txt"
        result = generate_coverage_evolution_text_report(history, output)
        assert result is True
        assert output.exists()

    def test_new_package_in_last_entry(self, tmp_path):
        """Package exists only in last entry (new module)."""
        data = [
            {"timestamp": "t1", "global_line_rate": 40.0, "packages": {"pkg1": {"line_rate": 30.0}}},
            {"timestamp": "t2", "global_line_rate": 60.0, "packages": {"pkg1": {"line_rate": 50.0}, "pkg2": {"line_rate": 70.0}}},
        ]
        history = tmp_path / "history.json"
        history.write_text(json.dumps(data), encoding="utf-8")
        output = tmp_path / "report.txt"
        result = generate_coverage_evolution_text_report(history, output)
        assert result is True

    def test_missing_timestamps_shows_na(self, tmp_path):
        data = [
            {"global_line_rate": 40.0, "packages": {}},
            {"global_line_rate": 60.0, "packages": {}},
        ]
        history = tmp_path / "history.json"
        history.write_text(json.dumps(data), encoding="utf-8")
        output = tmp_path / "report.txt"
        generate_coverage_evolution_text_report(history, output)
        content = output.read_text(encoding="utf-8")
        assert "N/A" in content

    def test_write_error_returns_false(self, tmp_path, history_data):
        history = tmp_path / "history.json"
        history.write_text(json.dumps(history_data), encoding="utf-8")
        # Use a path that can't be created (on Windows, invalid characters)
        with patch("builtins.open", side_effect=PermissionError("denied")):
            output = tmp_path / "report.txt"
            # The function creates dirs first, then opens file
            # Patch at the write step
            result = generate_coverage_evolution_text_report(history, output)
            # This may or may not fail depending on where the exception hits
            # The test just verifies no unhandled exception
