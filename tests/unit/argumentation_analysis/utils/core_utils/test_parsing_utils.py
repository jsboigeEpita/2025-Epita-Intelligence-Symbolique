# tests/unit/argumentation_analysis/utils/core_utils/test_parsing_utils.py
"""Tests for parsing utility functions."""

import re
import pytest

from argumentation_analysis.core.utils.parsing_utils import (
    parse_colon_separated_string_to_regex_dict,
)


class TestParseColonSeparatedString:
    def test_single_pattern(self):
        result = parse_colon_separated_string_to_regex_dict("config/")
        assert "config_refs" in result
        assert result["config_refs"].search("config/")

    def test_multiple_patterns(self):
        result = parse_colon_separated_string_to_regex_dict("config/:data/:logs/")
        assert len(result) == 3
        assert "config_refs" in result
        assert "data_refs" in result
        assert "logs_refs" in result

    def test_regex_match(self):
        result = parse_colon_separated_string_to_regex_dict("src/")
        assert result["src_refs"].search("path/to/src/file.py") is not None

    def test_escaped_special_chars(self):
        result = parse_colon_separated_string_to_regex_dict("path.ext")
        # With escape_pattern=True (default), the dot should be literal
        assert result["path.ext_refs"].search("path.ext") is not None
        assert result["path.ext_refs"].search("pathXext") is None

    def test_no_escape(self):
        result = parse_colon_separated_string_to_regex_dict(
            "test.*", escape_pattern=False
        )
        assert result["test.*_refs"].search("testing123") is not None

    def test_empty_string(self):
        result = parse_colon_separated_string_to_regex_dict("")
        assert result == {}

    def test_none_input(self):
        result = parse_colon_separated_string_to_regex_dict(None)
        assert result == {}

    def test_default_patterns_used(self):
        defaults = {"default_key": "default_pattern"}
        result = parse_colon_separated_string_to_regex_dict(
            None, default_patterns=defaults
        )
        assert "default_key" in result
        assert result["default_key"].search("default_pattern") is not None

    def test_default_patterns_not_used_when_valid(self):
        defaults = {"default_key": "default_pattern"}
        result = parse_colon_separated_string_to_regex_dict(
            "custom/", default_patterns=defaults
        )
        assert "default_key" not in result
        assert "custom_refs" in result

    def test_custom_key_suffix(self):
        result = parse_colon_separated_string_to_regex_dict(
            "data/", key_suffix="_pattern"
        )
        assert "data_pattern" in result

    def test_strips_whitespace(self):
        result = parse_colon_separated_string_to_regex_dict(" config/ : data/ ")
        assert "config_refs" in result
        assert "data_refs" in result

    def test_empty_between_colons(self):
        result = parse_colon_separated_string_to_regex_dict("a/::/b/")
        assert "a_refs" in result
        assert "b_refs" in result
        assert len(result) == 2  # empty segment skipped

    def test_no_defaults_no_input(self):
        result = parse_colon_separated_string_to_regex_dict(None, default_patterns=None)
        assert result == {}
