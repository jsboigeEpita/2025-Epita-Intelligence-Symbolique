# tests/unit/argumentation_analysis/utils/core_utils/test_file_loaders.py
"""Tests for file loading utility functions."""

import json
import pytest
from pathlib import Path

from argumentation_analysis.core.utils.file_loaders import (
    load_json_file,
    load_extracts,
    load_text_file,
    load_document_content,
)

# ── load_json_file ──


class TestLoadJsonFile:
    def test_load_dict(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        result = load_json_file(f)
        assert result == {"key": "value"}

    def test_load_list(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text("[1, 2, 3]", encoding="utf-8")
        result = load_json_file(f)
        assert result == [1, 2, 3]

    def test_file_not_found(self, tmp_path):
        f = tmp_path / "missing.json"
        assert load_json_file(f) is None

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("{invalid", encoding="utf-8")
        assert load_json_file(f) is None

    def test_double_encoded_json(self, tmp_path):
        f = tmp_path / "double.json"
        inner = json.dumps({"a": 1})
        f.write_text(json.dumps(inner), encoding="utf-8")
        result = load_json_file(f)
        assert result == {"a": 1}

    def test_double_encoded_invalid(self, tmp_path):
        f = tmp_path / "double_bad.json"
        f.write_text(json.dumps("not valid json {"), encoding="utf-8")
        assert load_json_file(f) is None

    def test_unexpected_type(self, tmp_path):
        f = tmp_path / "num.json"
        f.write_text("42", encoding="utf-8")
        assert load_json_file(f) is None

    def test_nested_dict(self, tmp_path):
        f = tmp_path / "nested.json"
        data = {"a": {"b": [1, 2]}}
        f.write_text(json.dumps(data), encoding="utf-8")
        result = load_json_file(f)
        assert result == data

    def test_empty_list(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]", encoding="utf-8")
        result = load_json_file(f)
        assert result == []


# ── load_extracts ──


class TestLoadExtracts:
    def test_returns_list(self, tmp_path):
        f = tmp_path / "extracts.json"
        f.write_text('[{"text": "hello"}]', encoding="utf-8")
        result = load_extracts(f)
        assert result == [{"text": "hello"}]

    def test_file_not_found_returns_empty(self, tmp_path):
        f = tmp_path / "missing.json"
        assert load_extracts(f) == []

    def test_dict_returns_empty(self, tmp_path):
        f = tmp_path / "dict.json"
        f.write_text('{"not": "a list"}', encoding="utf-8")
        assert load_extracts(f) == []

    def test_empty_list(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]", encoding="utf-8")
        assert load_extracts(f) == []


# ── load_text_file ──


class TestLoadTextFile:
    def test_basic(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("Hello World", encoding="utf-8")
        assert load_text_file(f) == "Hello World"

    def test_file_not_found(self, tmp_path):
        f = tmp_path / "missing.txt"
        assert load_text_file(f) is None

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        assert load_text_file(f) == ""

    def test_unicode_content(self, tmp_path):
        f = tmp_path / "unicode.txt"
        f.write_text("Héllo àçcénts", encoding="utf-8")
        assert load_text_file(f) == "Héllo àçcénts"

    def test_multiline(self, tmp_path):
        f = tmp_path / "multi.txt"
        content = "Line 1\nLine 2\nLine 3"
        f.write_text(content, encoding="utf-8")
        assert load_text_file(f) == content

    def test_wrong_encoding(self, tmp_path):
        f = tmp_path / "latin.txt"
        f.write_bytes(b"\xff\xfe")  # BOM for UTF-16 LE
        result = load_text_file(f, encoding="ascii")
        # Should return None due to UnicodeDecodeError
        assert result is None


# ── load_document_content ──


class TestLoadDocumentContent:
    def test_txt_file(self, tmp_path):
        f = tmp_path / "doc.txt"
        f.write_text("Hello", encoding="utf-8")
        assert load_document_content(f) == "Hello"

    def test_md_file(self, tmp_path):
        f = tmp_path / "doc.md"
        f.write_text("# Title", encoding="utf-8")
        assert load_document_content(f) == "# Title"

    def test_unsupported_extension(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_text("fake pdf", encoding="utf-8")
        assert load_document_content(f) is None

    def test_not_a_file(self, tmp_path):
        assert load_document_content(tmp_path) is None

    def test_missing_file(self, tmp_path):
        f = tmp_path / "missing.txt"
        assert load_document_content(f) is None
