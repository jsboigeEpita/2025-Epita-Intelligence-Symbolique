# tests/unit/argumentation_analysis/utils/core_utils/test_markdown_utils.py
"""Tests for Markdown to HTML conversion utilities."""

import pytest
from pathlib import Path

from argumentation_analysis.core.utils.markdown_utils import (
    save_markdown_to_html,
    convert_markdown_file_to_html,
)


# ── save_markdown_to_html ──

class TestSaveMarkdownToHtml:
    def test_basic_conversion(self, tmp_path):
        output = tmp_path / "out.html"
        result = save_markdown_to_html("# Title\n\nParagraph.", output)
        assert result is True
        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "<h1>" in content
        assert "Title" in content
        assert "Paragraph" in content

    def test_creates_parent_dirs(self, tmp_path):
        output = tmp_path / "sub" / "dir" / "out.html"
        result = save_markdown_to_html("# Hello", output)
        assert result is True
        assert output.exists()

    def test_html_document_structure(self, tmp_path):
        output = tmp_path / "out.html"
        save_markdown_to_html("Content", output)
        content = output.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "<html" in content
        assert "<head>" in content
        assert "<body>" in content
        assert "<style>" in content

    def test_title_from_filename(self, tmp_path):
        output = tmp_path / "my_report.html"
        save_markdown_to_html("Content", output)
        content = output.read_text(encoding="utf-8")
        assert "my_report" in content

    def test_table_extension(self, tmp_path):
        output = tmp_path / "table.html"
        md = "| A | B |\n|---|---|\n| 1 | 2 |"
        save_markdown_to_html(md, output)
        content = output.read_text(encoding="utf-8")
        assert "<table>" in content or "<table" in content

    def test_fenced_code_extension(self, tmp_path):
        output = tmp_path / "code.html"
        md = "```python\nprint('hello')\n```"
        save_markdown_to_html(md, output)
        content = output.read_text(encoding="utf-8")
        assert "<code>" in content or "<pre>" in content

    def test_empty_content(self, tmp_path):
        output = tmp_path / "empty.html"
        result = save_markdown_to_html("", output)
        assert result is True
        assert output.exists()

    def test_unicode_content(self, tmp_path):
        output = tmp_path / "unicode.html"
        result = save_markdown_to_html("# Héllo àçcénts", output)
        assert result is True
        content = output.read_text(encoding="utf-8")
        assert "Héllo" in content


# ── convert_markdown_file_to_html ──

class TestConvertMarkdownFileToHtml:
    def test_basic_conversion(self, tmp_path):
        md_file = tmp_path / "input.md"
        md_file.write_text("# Title\n\nContent", encoding="utf-8")
        html_file = tmp_path / "output.html"
        result = convert_markdown_file_to_html(md_file, html_file)
        assert result is True
        assert html_file.exists()
        content = html_file.read_text(encoding="utf-8")
        assert "Title" in content

    def test_missing_input_file(self, tmp_path):
        md_file = tmp_path / "missing.md"
        html_file = tmp_path / "output.html"
        result = convert_markdown_file_to_html(md_file, html_file)
        assert result is False

    def test_with_visualization_dir(self, tmp_path):
        md_file = tmp_path / "input.md"
        md_file.write_text("# Title", encoding="utf-8")
        html_file = tmp_path / "output.html"
        viz_dir = tmp_path / "viz"
        viz_dir.mkdir()
        result = convert_markdown_file_to_html(md_file, html_file, visualization_dir=viz_dir)
        assert result is True

    def test_unicode_file(self, tmp_path):
        md_file = tmp_path / "french.md"
        md_file.write_text("# Résumé\n\nLe café est bon.", encoding="utf-8")
        html_file = tmp_path / "french.html"
        result = convert_markdown_file_to_html(md_file, html_file)
        assert result is True
        content = html_file.read_text(encoding="utf-8")
        assert "Résumé" in content
