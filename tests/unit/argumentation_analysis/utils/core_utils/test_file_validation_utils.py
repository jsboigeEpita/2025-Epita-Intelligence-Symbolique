# tests/unit/argumentation_analysis/utils/core_utils/test_file_validation_utils.py
"""Tests for file validation utility functions."""

import json
import pytest
from pathlib import Path

from argumentation_analysis.core.utils.file_validation_utils import (
    check_text_file_readable_and_not_empty,
    check_json_file_valid,
    check_markdown_file_readable_and_basic_structure,
)


# ── check_text_file_readable_and_not_empty ──

class TestCheckTextFile:
    def test_valid_file(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello world", encoding="utf-8")
        valid, msg = check_text_file_readable_and_not_empty(f)
        assert valid is True
        assert "11 caractères" in msg

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        valid, msg = check_text_file_readable_and_not_empty(f)
        assert valid is False
        assert "vide" in msg

    def test_whitespace_only(self, tmp_path):
        f = tmp_path / "spaces.txt"
        f.write_text("   \n  \t  ", encoding="utf-8")
        valid, msg = check_text_file_readable_and_not_empty(f)
        assert valid is False

    def test_file_not_found(self, tmp_path):
        f = tmp_path / "nonexistent.txt"
        valid, msg = check_text_file_readable_and_not_empty(f)
        assert valid is False
        assert "non trouvé" in msg

    def test_directory_path(self, tmp_path):
        valid, msg = check_text_file_readable_and_not_empty(tmp_path)
        assert valid is False

    def test_string_path_conversion(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("content", encoding="utf-8")
        valid, msg = check_text_file_readable_and_not_empty(str(f))
        assert valid is True

    def test_invalid_path_type(self):
        valid, msg = check_text_file_readable_and_not_empty(None)
        assert valid is False
        assert "invalide" in msg


# ── check_json_file_valid ──

class TestCheckJsonFile:
    def test_valid_json_dict(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        valid, msg = check_json_file_valid(f)
        assert valid is True
        assert "non vides" in msg

    def test_valid_json_list(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('[1, 2, 3]', encoding="utf-8")
        valid, msg = check_json_file_valid(f)
        assert valid is True

    def test_empty_dict(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{}', encoding="utf-8")
        valid, msg = check_json_file_valid(f)
        assert valid is False
        assert "vide" in msg

    def test_empty_list(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('[]', encoding="utf-8")
        valid, msg = check_json_file_valid(f)
        assert valid is False

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{bad json", encoding="utf-8")
        valid, msg = check_json_file_valid(f)
        assert valid is False
        assert "invalide" in msg.lower() or "JSON" in msg

    def test_file_not_found(self, tmp_path):
        f = tmp_path / "missing.json"
        valid, msg = check_json_file_valid(f)
        assert valid is False

    def test_string_path(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"a": 1}', encoding="utf-8")
        valid, msg = check_json_file_valid(str(f))
        assert valid is True


# ── check_markdown_file_readable_and_basic_structure ──

class TestCheckMarkdownFile:
    def test_valid_markdown(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# Title\n\nSome content here.", encoding="utf-8")
        valid, msg = check_markdown_file_readable_and_basic_structure(f)
        assert valid is True
        assert "titres" in msg

    def test_no_headings(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("Just some text without headings.", encoding="utf-8")
        valid, msg = check_markdown_file_readable_and_basic_structure(f)
        assert valid is False
        assert "titre" in msg.lower()

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        valid, msg = check_markdown_file_readable_and_basic_structure(f)
        assert valid is False

    def test_file_not_found(self, tmp_path):
        f = tmp_path / "missing.md"
        valid, msg = check_markdown_file_readable_and_basic_structure(f)
        assert valid is False

    def test_h2_heading(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("Some intro\n\n## Section\n\nContent", encoding="utf-8")
        valid, msg = check_markdown_file_readable_and_basic_structure(f)
        assert valid is True

    def test_h3_heading(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("### Subsection\nContent", encoding="utf-8")
        valid, msg = check_markdown_file_readable_and_basic_structure(f)
        assert valid is True
