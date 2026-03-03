# tests/unit/argumentation_analysis/utils/core_utils/test_json_utils.py
"""Tests for JSON utility functions."""

import json
import pytest
from pathlib import Path

from argumentation_analysis.core.utils.json_utils import (
    load_json_from_file,
    save_json_to_file,
    filter_list_in_json_data,
)


# ── load_json_from_file ──

class TestLoadJsonFromFile:
    def test_load_dict(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        result = load_json_from_file(f)
        assert result == {"key": "value"}

    def test_load_list(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text('[1, 2, 3]', encoding="utf-8")
        result = load_json_from_file(f)
        assert result == [1, 2, 3]

    def test_file_not_found(self, tmp_path):
        f = tmp_path / "nonexistent.json"
        result = load_json_from_file(f)
        assert result is None

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not valid json {", encoding="utf-8")
        result = load_json_from_file(f)
        assert result is None

    def test_directory_path(self, tmp_path):
        result = load_json_from_file(tmp_path)
        assert result is None

    def test_unicode(self, tmp_path):
        f = tmp_path / "unicode.json"
        f.write_text('{"text": "café résumé"}', encoding="utf-8")
        result = load_json_from_file(f)
        assert result["text"] == "café résumé"


# ── save_json_to_file ──

class TestSaveJsonToFile:
    def test_save_dict(self, tmp_path):
        f = tmp_path / "out.json"
        result = save_json_to_file({"key": "value"}, f)
        assert result is True
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data["key"] == "value"

    def test_save_list(self, tmp_path):
        f = tmp_path / "out.json"
        result = save_json_to_file([1, 2, 3], f)
        assert result is True
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data == [1, 2, 3]

    def test_creates_parents(self, tmp_path):
        f = tmp_path / "sub" / "dir" / "out.json"
        result = save_json_to_file({"a": 1}, f)
        assert result is True
        assert f.exists()

    def test_custom_indent(self, tmp_path):
        f = tmp_path / "out.json"
        save_json_to_file({"a": 1}, f, indent=4)
        content = f.read_text(encoding="utf-8")
        assert "    " in content

    def test_ensure_ascii_false(self, tmp_path):
        f = tmp_path / "out.json"
        save_json_to_file({"text": "café"}, f, ensure_ascii=False)
        content = f.read_text(encoding="utf-8")
        assert "café" in content

    def test_ensure_ascii_true(self, tmp_path):
        f = tmp_path / "out.json"
        save_json_to_file({"text": "café"}, f, ensure_ascii=True)
        content = f.read_text(encoding="utf-8")
        assert "\\u" in content

    def test_non_serializable_returns_false(self, tmp_path):
        f = tmp_path / "out.json"
        result = save_json_to_file({"func": lambda x: x}, f)
        assert result is False


# ── filter_list_in_json_data ──

class TestFilterListInJsonData:
    def test_filter_root_list(self):
        data = [
            {"id": 1, "status": "active"},
            {"id": 2, "status": "deleted"},
            {"id": 3, "status": "active"},
        ]
        result, count = filter_list_in_json_data(data, "status", "deleted")
        assert count == 1
        assert len(result) == 2
        assert all(item["status"] == "active" for item in result)

    def test_filter_nested_list(self):
        data = {
            "users": [
                {"name": "Alice"},
                {"name": "Bob"},
            ]
        }
        result, count = filter_list_in_json_data(data, "name", "Alice", "users")
        assert count == 1
        assert len(result["users"]) == 1
        assert result["users"][0]["name"] == "Bob"

    def test_no_match(self):
        data = [{"id": 1, "status": "active"}]
        result, count = filter_list_in_json_data(data, "status", "deleted")
        assert count == 0
        assert len(result) == 1

    def test_all_removed(self):
        data = [
            {"status": "deleted"},
            {"status": "deleted"},
        ]
        result, count = filter_list_in_json_data(data, "status", "deleted")
        assert count == 2
        assert result == []

    def test_invalid_list_path_key(self):
        data = {"users": [{"name": "A"}]}
        result, count = filter_list_in_json_data(data, "name", "A", "nonexistent")
        assert count == 0

    def test_list_path_key_not_list(self):
        data = {"users": "not a list"}
        result, count = filter_list_in_json_data(data, "name", "A", "users")
        assert count == 0

    def test_unsupported_type(self):
        result, count = filter_list_in_json_data("a string", "key", "val")
        assert count == 0

    def test_mixed_items_non_dict(self):
        data = [{"id": 1, "status": "active"}, "not a dict", 42]
        result, count = filter_list_in_json_data(data, "status", "active")
        assert count == 1
        assert len(result) == 2  # "not a dict" and 42 remain
