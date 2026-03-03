# tests/unit/argumentation_analysis/utils/test_correction_utils.py
"""Tests for correction_utils — manual correction data preparation."""

import json
import pytest
from pathlib import Path

from argumentation_analysis.utils.correction_utils import (
    prepare_manual_correction_data,
)


class TestPrepareManualCorrectionData:
    def _write_config(self, tmp_path, data):
        f = tmp_path / "config.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        return f

    # ── File handling ──

    def test_file_not_found(self, tmp_path):
        f = tmp_path / "missing.json"
        result = prepare_manual_correction_data(f, "s1", "e1")
        assert result is None

    def test_directory_not_file(self, tmp_path):
        result = prepare_manual_correction_data(tmp_path, "s1", "e1")
        assert result is None

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{broken", encoding="utf-8")
        result = prepare_manual_correction_data(f, "s1", "e1")
        assert result is None

    def test_root_not_list(self, tmp_path):
        f = self._write_config(tmp_path, {"not": "a list"})
        result = prepare_manual_correction_data(f, "s1", "e1")
        assert result is None

    # ── Source not found ──

    def test_source_not_found(self, tmp_path):
        data = [{"id": "other", "source_name": "Other", "extracts": []}]
        f = self._write_config(tmp_path, data)
        result = prepare_manual_correction_data(f, "missing_id", "e1")
        assert result is None

    # ── Extract not found ──

    def test_extract_not_found(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "Source1",
                "extracts": [{"extract_name": "other_extract"}],
            }
        ]
        f = self._write_config(tmp_path, data)
        result = prepare_manual_correction_data(f, "s1", "missing_extract")
        assert result is None

    # ── Successful extraction ──

    def test_basic_extraction(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "MySource",
                "full_text": "Full document text here",
                "extracts": [
                    {
                        "extract_name": "E1",
                        "start_marker": "start_m",
                        "end_marker": "end_m",
                    }
                ],
            }
        ]
        f = self._write_config(tmp_path, data)
        result = prepare_manual_correction_data(f, "s1", "E1")
        assert result is not None
        assert result["target_source_id"] == "s1"
        assert result["source_name"] == "MySource"
        assert result["target_extract_name"] == "E1"
        assert result["current_start_marker"] == "start_m"
        assert result["current_end_marker"] == "end_m"
        assert result["source_full_text"] == "Full document text here"

    def test_extract_without_markers(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "S1",
                "extracts": [{"extract_name": "E1"}],
            }
        ]
        f = self._write_config(tmp_path, data)
        result = prepare_manual_correction_data(f, "s1", "E1")
        assert result is not None
        assert result["current_start_marker"] == "N/A"
        assert result["current_end_marker"] == "N/A"
        assert result["source_full_text"] is None

    def test_source_without_full_text(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "S1",
                "extracts": [{"extract_name": "E1"}],
            }
        ]
        f = self._write_config(tmp_path, data)
        result = prepare_manual_correction_data(f, "s1", "E1")
        assert result["source_full_text"] is None

    # ── Debug file output ──

    def test_writes_debug_file(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "S1",
                "full_text": "Document content",
                "extracts": [
                    {
                        "extract_name": "E1",
                        "start_marker": "BEGIN",
                        "end_marker": "END",
                    }
                ],
            }
        ]
        f = self._write_config(tmp_path, data)
        debug_file = tmp_path / "debug" / "output.txt"
        result = prepare_manual_correction_data(f, "s1", "E1", debug_file)
        assert result is not None
        assert debug_file.exists()
        content = debug_file.read_text(encoding="utf-8")
        assert "S1" in content
        assert "BEGIN" in content
        assert "Document content" in content

    def test_debug_file_without_full_text(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "S1",
                "extracts": [{"extract_name": "E1"}],
            }
        ]
        f = self._write_config(tmp_path, data)
        debug_file = tmp_path / "debug.txt"
        result = prepare_manual_correction_data(f, "s1", "E1", debug_file)
        assert result is not None
        content = debug_file.read_text(encoding="utf-8")
        assert "ABSENT" in content or "VIDE" in content

    # ── Edge cases ──

    def test_extracts_not_a_list(self, tmp_path):
        data = [{"id": "s1", "source_name": "S1", "extracts": "not a list"}]
        f = self._write_config(tmp_path, data)
        result = prepare_manual_correction_data(f, "s1", "E1")
        assert result is None

    def test_multiple_sources_finds_correct(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "S1",
                "extracts": [{"extract_name": "E1"}],
            },
            {
                "id": "s2",
                "source_name": "S2",
                "extracts": [{"extract_name": "E2"}],
            },
        ]
        f = self._write_config(tmp_path, data)
        result = prepare_manual_correction_data(f, "s2", "E2")
        assert result is not None
        assert result["source_name"] == "S2"
        assert result["target_extract_name"] == "E2"

    def test_multiple_extracts_finds_correct(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "S1",
                "extracts": [
                    {"extract_name": "E1", "start_marker": "M1"},
                    {"extract_name": "E2", "start_marker": "M2"},
                    {"extract_name": "E3", "start_marker": "M3"},
                ],
            }
        ]
        f = self._write_config(tmp_path, data)
        result = prepare_manual_correction_data(f, "s1", "E2")
        assert result is not None
        assert result["current_start_marker"] == "M2"
