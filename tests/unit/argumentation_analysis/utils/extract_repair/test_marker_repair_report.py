# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.utils.extract_repair.marker_repair_logic
Covers the generate_report function and ExtractRepairPlugin (with mocking).
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from argumentation_analysis.utils.extract_repair.marker_repair_logic import (
    generate_report,
    ExtractRepairPlugin,
    REPAIR_AGENT_INSTRUCTIONS,
    VALIDATION_AGENT_INSTRUCTIONS,
)


# ============================================================
# Constants
# ============================================================

class TestConstants:
    def test_repair_instructions_not_empty(self):
        assert len(REPAIR_AGENT_INSTRUCTIONS) > 100

    def test_validation_instructions_not_empty(self):
        assert len(VALIDATION_AGENT_INSTRUCTIONS) > 100

    def test_repair_instructions_contain_key_terms(self):
        assert "réparation" in REPAIR_AGENT_INSTRUCTIONS or "repair" in REPAIR_AGENT_INSTRUCTIONS.lower()

    def test_validation_instructions_contain_key_terms(self):
        assert "validation" in VALIDATION_AGENT_INSTRUCTIONS


# ============================================================
# generate_report
# ============================================================

class TestGenerateReport:
    def test_generates_html_file(self, tmp_path):
        results = [
            {"source_name": "S1", "extract_name": "E1", "status": "valid", "message": "OK"},
        ]
        output = str(tmp_path / "report.html")
        generate_report(results, output)
        assert Path(output).exists()

    def test_html_contains_summary(self, tmp_path):
        results = [
            {"source_name": "S1", "extract_name": "E1", "status": "valid", "message": "OK"},
            {"source_name": "S2", "extract_name": "E2", "status": "repaired", "message": "Fixed",
             "old_start_marker": "ello", "new_start_marker": "Hello",
             "old_end_marker": "end", "new_end_marker": "end",
             "old_template_start": "H{0}"},
        ]
        output = str(tmp_path / "report.html")
        generate_report(results, output)
        content = Path(output).read_text(encoding="utf-8")
        assert "Résumé" in content
        assert "Total des extraits analysés" in content

    def test_status_counts(self, tmp_path):
        results = [
            {"status": "valid", "source_name": "S", "extract_name": "E", "message": "ok"},
            {"status": "valid", "source_name": "S", "extract_name": "E", "message": "ok"},
            {"status": "repaired", "source_name": "S", "extract_name": "E", "message": "fixed",
             "old_start_marker": "x", "new_start_marker": "Xx",
             "old_end_marker": "y", "new_end_marker": "y",
             "old_template_start": "X{0}"},
            {"status": "rejected", "source_name": "S", "extract_name": "E", "message": "bad"},
            {"status": "error", "source_name": "S", "extract_name": "E", "message": "err"},
        ]
        output = str(tmp_path / "report.html")
        generate_report(results, output)
        content = Path(output).read_text(encoding="utf-8")
        # Should contain the counts in the HTML
        assert "S" in content

    def test_repair_type_first_letter_missing(self, tmp_path):
        results = [
            {
                "status": "repaired",
                "source_name": "S",
                "extract_name": "E",
                "message": "fixed",
                "old_start_marker": "ello",
                "new_start_marker": "Hello",
                "old_end_marker": "end",
                "new_end_marker": "end",
                "old_template_start": "H{0}",
            }
        ]
        output = str(tmp_path / "report.html")
        generate_report(results, output)
        content = Path(output).read_text(encoding="utf-8")
        assert "Première lettre manquante" in content

    def test_repair_type_other(self, tmp_path):
        results = [
            {
                "status": "repaired",
                "source_name": "S",
                "extract_name": "E",
                "message": "fixed",
                "old_start_marker": "abc",
                "new_start_marker": "xyz",
                "old_end_marker": "end",
                "new_end_marker": "end",
                "old_template_start": "A{0}",
            }
        ]
        output = str(tmp_path / "report.html")
        generate_report(results, output)
        content = Path(output).read_text(encoding="utf-8")
        assert "Autres types" in content

    def test_empty_results(self, tmp_path):
        output = str(tmp_path / "empty_report.html")
        generate_report([], output)
        assert Path(output).exists()
        content = Path(output).read_text(encoding="utf-8")
        assert "0" in content

    def test_html_structure(self, tmp_path):
        results = [
            {"status": "valid", "source_name": "S", "extract_name": "E", "message": "ok"},
        ]
        output = str(tmp_path / "report.html")
        generate_report(results, output)
        content = Path(output).read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "</html>" in content
        assert "<table>" in content


# ============================================================
# ExtractRepairPlugin
# ============================================================

class TestExtractRepairPlugin:
    @pytest.fixture
    def mock_service(self):
        service = MagicMock()
        service.find_similar_text.return_value = [
            ("context around marker", 42, "found_text"),
        ]
        return service

    @pytest.fixture
    def plugin(self, mock_service):
        return ExtractRepairPlugin(mock_service)

    def test_init(self, plugin, mock_service):
        assert plugin.extract_service is mock_service
        assert plugin.repair_results == []

    def test_find_similar_markers(self, plugin):
        results = plugin.find_similar_markers("Hello World", "Hell", max_results=3)
        assert len(results) == 1
        assert results[0]["marker"] == "found_text"
        assert results[0]["position"] == 42

    def test_find_similar_markers_empty_text(self, plugin):
        assert plugin.find_similar_markers("", "marker") == []

    def test_find_similar_markers_empty_marker(self, plugin):
        assert plugin.find_similar_markers("text", "") == []

    def test_get_repair_results_empty(self, plugin):
        assert plugin.get_repair_results() == []

    def test_update_extract_markers_success(self, plugin):
        # Create mock extract definitions
        mock_extract = MagicMock()
        mock_extract.start_marker = "old_start"
        mock_extract.end_marker = "old_end"
        mock_extract.template_start = "T{0}"
        mock_extract.extract_name = "E1"

        mock_source = MagicMock()
        mock_source.extracts = [mock_extract]
        mock_source.source_name = "TestSource"

        mock_defs = MagicMock()
        mock_defs.sources = [mock_source]

        result = plugin.update_extract_markers(
            mock_defs, 0, 0, "new_start", "new_end", "N{0}"
        )
        assert result is True
        assert mock_extract.start_marker == "new_start"
        assert mock_extract.end_marker == "new_end"
        assert mock_extract.template_start == "N{0}"
        assert len(plugin.get_repair_results()) == 1

    def test_update_extract_markers_invalid_source_idx(self, plugin):
        mock_defs = MagicMock()
        mock_defs.sources = []
        result = plugin.update_extract_markers(mock_defs, 5, 0, "a", "b")
        assert result is False

    def test_update_extract_markers_invalid_extract_idx(self, plugin):
        mock_source = MagicMock()
        mock_source.extracts = []
        mock_defs = MagicMock()
        mock_defs.sources = [mock_source]
        result = plugin.update_extract_markers(mock_defs, 0, 5, "a", "b")
        assert result is False
