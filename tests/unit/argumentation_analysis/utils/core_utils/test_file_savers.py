# tests/unit/argumentation_analysis/utils/core_utils/test_file_savers.py
"""Tests for file saving utility functions."""

import json
import pytest
from pathlib import Path

from argumentation_analysis.core.utils.file_savers import (
    save_json_file,
    save_text_file,
    save_temp_extracts_json,
)

# ── save_json_file ──


class TestSaveJsonFile:
    def test_save_dict(self, tmp_path):
        f = tmp_path / "out.json"
        result = save_json_file(f, {"key": "value"})
        assert result is True
        assert json.loads(f.read_text(encoding="utf-8")) == {"key": "value"}

    def test_save_list(self, tmp_path):
        f = tmp_path / "out.json"
        result = save_json_file(f, [1, 2, 3])
        assert result is True
        assert json.loads(f.read_text(encoding="utf-8")) == [1, 2, 3]

    def test_creates_parent_dirs(self, tmp_path):
        f = tmp_path / "sub" / "dir" / "out.json"
        result = save_json_file(f, {"a": 1})
        assert result is True
        assert f.exists()

    def test_custom_indent(self, tmp_path):
        f = tmp_path / "out.json"
        save_json_file(f, {"a": 1}, indent=2)
        content = f.read_text(encoding="utf-8")
        assert "  " in content  # 2-space indent

    def test_unicode_preserved(self, tmp_path):
        f = tmp_path / "out.json"
        save_json_file(f, {"key": "valeur française"})
        content = f.read_text(encoding="utf-8")
        assert "française" in content  # ensure_ascii=False

    def test_non_serializable_returns_false(self, tmp_path):
        f = tmp_path / "out.json"
        result = save_json_file(f, {"fn": lambda x: x})
        assert result is False

    def test_overwrite_existing(self, tmp_path):
        f = tmp_path / "out.json"
        save_json_file(f, {"old": True})
        save_json_file(f, {"new": True})
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data == {"new": True}


# ── save_text_file ──


class TestSaveTextFile:
    def test_save_basic(self, tmp_path):
        f = tmp_path / "out.txt"
        result = save_text_file(f, "Hello World")
        assert result is True
        assert f.read_text(encoding="utf-8") == "Hello World"

    def test_creates_parent_dirs(self, tmp_path):
        f = tmp_path / "sub" / "dir" / "out.txt"
        result = save_text_file(f, "content")
        assert result is True
        assert f.exists()

    def test_empty_content(self, tmp_path):
        f = tmp_path / "empty.txt"
        result = save_text_file(f, "")
        assert result is True
        assert f.read_text(encoding="utf-8") == ""

    def test_unicode_content(self, tmp_path):
        f = tmp_path / "unicode.txt"
        result = save_text_file(f, "Héllo àçcénts")
        assert result is True
        assert f.read_text(encoding="utf-8") == "Héllo àçcénts"

    def test_multiline(self, tmp_path):
        f = tmp_path / "multi.txt"
        content = "Line 1\nLine 2\nLine 3"
        save_text_file(f, content)
        assert f.read_text(encoding="utf-8") == content

    def test_overwrite(self, tmp_path):
        f = tmp_path / "out.txt"
        save_text_file(f, "old")
        save_text_file(f, "new")
        assert f.read_text(encoding="utf-8") == "new"


# ── save_temp_extracts_json ──


class TestSaveTempExtractsJson:
    def test_saves_extracts(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        extracts = [{"text": "extract1"}, {"text": "extract2"}]
        result = save_temp_extracts_json(extracts)
        assert result is not None
        assert result.exists()
        data = json.loads(result.read_text(encoding="utf-8"))
        assert len(data) == 2

    def test_custom_dir_name(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = save_temp_extracts_json([{"a": 1}], base_temp_dir_name="custom_dir")
        assert result is not None
        assert "custom_dir" in str(result)

    def test_custom_prefix(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = save_temp_extracts_json([{"a": 1}], filename_prefix="test_prefix_")
        assert result is not None
        assert "test_prefix_" in result.name

    def test_not_a_list_returns_none(self):
        result = save_temp_extracts_json({"not": "a list"})
        assert result is None

    def test_empty_list(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = save_temp_extracts_json([])
        assert result is not None
        data = json.loads(result.read_text(encoding="utf-8"))
        assert data == []
