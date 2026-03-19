# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.utils.extract_repair.fix_missing_first_letter
Covers the fix_missing_first_letter function for JSON marker repair.
"""

import pytest
import json
from pathlib import Path
from argumentation_analysis.utils.extract_repair.fix_missing_first_letter import (
    fix_missing_first_letter,
)


@pytest.fixture
def sample_extract_data():
    """Sample extract definitions with fixable markers."""
    return [
        {
            "source_name": "Source A",
            "extracts": [
                {
                    "extract_name": "Extract 1",
                    "start_marker": "ello World",
                    "template_start": "H{0}",
                },
                {
                    "extract_name": "Extract 2",
                    "start_marker": "Hello",
                    "template_start": "H{0}",
                },
            ],
        },
        {
            "source_name": "Source B",
            "extracts": [
                {
                    "extract_name": "Extract 3",
                    "start_marker": "onjour",
                    "template_start": "B{0}",
                },
            ],
        },
    ]


@pytest.fixture
def sample_file(tmp_path, sample_extract_data):
    """Create a sample JSON file."""
    f = tmp_path / "extracts.json"
    f.write_text(json.dumps(sample_extract_data), encoding="utf-8")
    return f


class TestFixMissingFirstLetter:
    def test_fixes_missing_first_letter(self, sample_file):
        count, corrections = fix_missing_first_letter(str(sample_file))
        assert count == 2  # Extract 1 and Extract 3 need fixes
        # Extract 2 already starts with H, so no fix needed

    def test_corrections_details(self, sample_file):
        count, corrections = fix_missing_first_letter(str(sample_file))
        source_a_fixes = [c for c in corrections if c["source_name"] == "Source A"]
        assert len(source_a_fixes) == 1
        assert source_a_fixes[0]["old_marker"] == "ello World"
        assert source_a_fixes[0]["new_marker"] == "Hello World"
        assert source_a_fixes[0]["template"] == "H{0}"

    def test_source_b_fix(self, sample_file):
        count, corrections = fix_missing_first_letter(str(sample_file))
        source_b_fixes = [c for c in corrections if c["source_name"] == "Source B"]
        assert len(source_b_fixes) == 1
        assert source_b_fixes[0]["old_marker"] == "onjour"
        assert source_b_fixes[0]["new_marker"] == "Bonjour"

    def test_no_fix_needed(self, tmp_path):
        data = [
            {
                "source_name": "OK Source",
                "extracts": [
                    {
                        "extract_name": "OK Extract",
                        "start_marker": "Hello",
                        "template_start": "H{0}",
                    }
                ],
            }
        ]
        f = tmp_path / "ok.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        count, corrections = fix_missing_first_letter(str(f))
        assert count == 0
        assert corrections == []

    def test_no_template_start(self, tmp_path):
        data = [
            {
                "source_name": "No Template",
                "extracts": [{"extract_name": "E1", "start_marker": "Hello"}],
            }
        ]
        f = tmp_path / "no_template.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        count, corrections = fix_missing_first_letter(str(f))
        assert count == 0

    def test_template_without_placeholder(self, tmp_path):
        data = [
            {
                "source_name": "Bad Template",
                "extracts": [
                    {
                        "extract_name": "E1",
                        "start_marker": "test",
                        "template_start": "NoPlaceholder",
                    }
                ],
            }
        ]
        f = tmp_path / "bad_template.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        count, corrections = fix_missing_first_letter(str(f))
        assert count == 0

    def test_output_to_different_file(self, sample_file, tmp_path):
        output = tmp_path / "output.json"
        count, corrections = fix_missing_first_letter(str(sample_file), str(output))
        assert count == 2
        assert output.exists()
        # Original should not be modified (it's a separate output)
        result = json.loads(output.read_text(encoding="utf-8"))
        assert isinstance(result, list)

    def test_overwrites_input_by_default(self, sample_file):
        fix_missing_first_letter(str(sample_file))
        result = json.loads(sample_file.read_text(encoding="utf-8"))
        # Verify the fixes were saved
        e1 = result[0]["extracts"][0]
        assert e1["start_marker"] == "Hello World"

    def test_empty_extracts(self, tmp_path):
        data = [{"source_name": "Empty", "extracts": []}]
        f = tmp_path / "empty.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        count, corrections = fix_missing_first_letter(str(f))
        assert count == 0

    def test_empty_start_marker(self, tmp_path):
        data = [
            {
                "source_name": "S",
                "extracts": [
                    {
                        "extract_name": "E",
                        "start_marker": "",
                        "template_start": "X{0}",
                    }
                ],
            }
        ]
        f = tmp_path / "empty_marker.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        count, corrections = fix_missing_first_letter(str(f))
        # Empty start_marker → condition `if start_marker and not start_marker.startswith(...)` → False
        assert count == 0
