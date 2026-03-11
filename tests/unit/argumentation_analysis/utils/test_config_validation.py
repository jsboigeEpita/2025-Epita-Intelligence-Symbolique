# tests/unit/argumentation_analysis/utils/test_config_validation.py
"""Tests for config_validation utility functions."""

import json
import pytest
from pathlib import Path

from argumentation_analysis.utils.config_validation import (
    identify_missing_full_text_segments,
)


class TestIdentifyMissingFullTextSegments:
    def _write_config(self, tmp_path, data):
        f = tmp_path / "config.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        return f

    # ── File handling ──

    def test_file_not_found(self, tmp_path):
        f = tmp_path / "missing.json"
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 0
        assert total == 0
        assert details == []

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid json", encoding="utf-8")
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 0
        assert total == 0

    def test_root_not_list(self, tmp_path):
        f = self._write_config(tmp_path, {"not": "a list"})
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 0
        assert total == 0

    # ── No missing segments ──

    def test_all_segments_present(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "Source1",
                "extracts": [
                    {"extract_name": "e1", "full_text_segment": "text here"},
                    {"extract_name": "e2", "full_text_segment": "more text"},
                ],
            }
        ]
        f = self._write_config(tmp_path, data)
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 0
        assert total == 2
        assert details == []

    # ── Missing segments ──

    def test_segment_is_none(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "Source1",
                "extracts": [
                    {"extract_name": "e1", "full_text_segment": None},
                ],
            }
        ]
        f = self._write_config(tmp_path, data)
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 1
        assert total == 1
        assert len(details) == 1
        assert details[0]["extract_name"] == "e1"

    def test_segment_is_empty_string(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "Source1",
                "extracts": [
                    {"extract_name": "e1", "full_text_segment": ""},
                ],
            }
        ]
        f = self._write_config(tmp_path, data)
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 1
        assert total == 1

    def test_segment_key_absent(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "Source1",
                "extracts": [
                    {"extract_name": "e1"},
                ],
            }
        ]
        f = self._write_config(tmp_path, data)
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 1
        assert total == 1

    # ── Detail fields ──

    def test_detail_fields(self, tmp_path):
        data = [
            {
                "id": "src1",
                "source_name": "MySource",
                "full_text": "some text",
                "extracts": [
                    {
                        "extract_name": "Extract A",
                        "start_marker": "start",
                        "end_marker": "end",
                    },
                ],
            }
        ]
        f = self._write_config(tmp_path, data)
        _, _, details = identify_missing_full_text_segments(f)
        d = details[0]
        assert d["source_id"] == "src1"
        assert d["source_name"] == "MySource"
        assert d["extract_name"] == "Extract A"
        assert d["start_marker"] == "start"
        assert d["end_marker"] == "end"
        assert d["source_has_full_text"] == "PRÉSENT"

    def test_source_without_full_text(self, tmp_path):
        data = [
            {
                "id": "src1",
                "source_name": "NoText",
                "extracts": [{"extract_name": "e1"}],
            }
        ]
        f = self._write_config(tmp_path, data)
        _, _, details = identify_missing_full_text_segments(f)
        assert details[0]["source_has_full_text"] == "ABSENT"

    # ── Mixed data ──

    def test_mixed_present_and_missing(self, tmp_path):
        data = [
            {
                "id": "s1",
                "source_name": "S1",
                "extracts": [
                    {"extract_name": "present", "full_text_segment": "ok"},
                    {"extract_name": "missing"},
                ],
            },
            {
                "id": "s2",
                "source_name": "S2",
                "extracts": [
                    {"extract_name": "also_missing", "full_text_segment": ""},
                ],
            },
        ]
        f = self._write_config(tmp_path, data)
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 2
        assert total == 3
        assert len(details) == 2

    # ── Edge cases ──

    def test_empty_list(self, tmp_path):
        f = self._write_config(tmp_path, [])
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 0
        assert total == 0

    def test_source_without_extracts(self, tmp_path):
        data = [{"id": "s1", "source_name": "S1"}]
        f = self._write_config(tmp_path, data)
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 0
        assert total == 0

    def test_source_with_non_list_extracts(self, tmp_path):
        data = [{"id": "s1", "source_name": "S1", "extracts": "not a list"}]
        f = self._write_config(tmp_path, data)
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 0
        assert total == 0

    def test_non_dict_source(self, tmp_path):
        data = ["not a dict", {"id": "s1", "source_name": "S1", "extracts": []}]
        f = self._write_config(tmp_path, data)
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 0
        assert total == 0

    def test_non_dict_extract(self, tmp_path):
        data = [{"id": "s1", "source_name": "S1", "extracts": ["not a dict"]}]
        f = self._write_config(tmp_path, data)
        missing, total, details = identify_missing_full_text_segments(f)
        assert missing == 0
        assert total == 1

    def test_default_ids_when_missing(self, tmp_path):
        data = [{"extracts": [{"extract_name": "e1"}]}]
        f = self._write_config(tmp_path, data)
        _, _, details = identify_missing_full_text_segments(f)
        assert "SourceInconnue_1" in details[0]["source_id"]

    def test_is_a_directory(self, tmp_path):
        missing, total, details = identify_missing_full_text_segments(tmp_path)
        assert missing == 0
        assert total == 0
