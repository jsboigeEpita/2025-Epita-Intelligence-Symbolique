# tests/unit/argumentation_analysis/utils/core_utils/test_string_utils.py
"""Tests for string utility functions."""

import pytest

from argumentation_analysis.core.utils.string_utils import (
    get_significant_substrings,
)


class TestGetSignificantSubstrings:
    def test_normal_text(self):
        text = "Hello World, this is a test string with more than thirty characters in total!"
        prefix, suffix = get_significant_substrings(text, length=10)
        assert prefix == "Hello Worl"
        assert suffix == " in total!"

    def test_short_text(self):
        prefix, suffix = get_significant_substrings("Hello", length=30)
        assert prefix == "Hello"
        assert suffix == "Hello"

    def test_exact_length(self):
        text = "a" * 30
        prefix, suffix = get_significant_substrings(text, length=30)
        assert prefix == text
        assert suffix == text

    def test_double_length(self):
        text = "a" * 60
        prefix, suffix = get_significant_substrings(text, length=30)
        assert len(prefix) == 30
        assert len(suffix) == 30

    def test_strips_whitespace(self):
        text = "   Hello   "
        prefix, suffix = get_significant_substrings(text, length=10)
        assert prefix == "Hello"
        assert suffix == "Hello"

    def test_none_input(self):
        prefix, suffix = get_significant_substrings(None)
        assert prefix is None
        assert suffix is None

    def test_empty_string(self):
        prefix, suffix = get_significant_substrings("")
        assert prefix is None
        assert suffix is None

    def test_whitespace_only(self):
        prefix, suffix = get_significant_substrings("    ")
        assert prefix is None
        assert suffix is None

    def test_non_string_input(self):
        prefix, suffix = get_significant_substrings(123)
        assert prefix is None
        assert suffix is None

    def test_custom_length(self):
        text = "ABCDEFGHIJ"
        prefix, suffix = get_significant_substrings(text, length=3)
        assert prefix == "ABC"
        assert suffix == "HIJ"

    def test_default_length(self):
        text = "x" * 100
        prefix, suffix = get_significant_substrings(text)
        assert len(prefix) == 30
        assert len(suffix) == 30
