"""Tests for argumentation_analysis.evaluation.opaque_id."""

import os

import pytest

from argumentation_analysis.evaluation.opaque_id import opaque_id


class TestOpaqueIdStability:
    def test_same_input_same_output(self):
        assert opaque_id("Speaker A") == opaque_id("Speaker A")

    def test_different_salt_different_output(self):
        a = opaque_id("Speaker A", salt="salt1")
        b = opaque_id("Speaker A", salt="salt2")
        assert a != b

    def test_different_names_different_ids(self):
        ids = {opaque_id(f"name_{i}") for i in range(100)}
        assert len(ids) == 100  # no collisions


class TestOpaqueIdFormat:
    def test_length_is_8(self):
        result = opaque_id("test")
        assert len(result) == 8

    def test_hex_chars_only(self):
        result = opaque_id("test")
        assert all(c in "0123456789abcdef" for c in result)


class TestOpaqueIdSaltEnv:
    def test_env_salt_used(self, monkeypatch):
        monkeypatch.setenv("OPAQUE_ID_SALT", "env_salt_123")
        a = opaque_id("test")
        b = opaque_id("test", salt="env_salt_123")
        assert a == b

    def test_default_salt_without_env(self, monkeypatch):
        monkeypatch.delenv("OPAQUE_ID_SALT", raising=False)
        result = opaque_id("test")
        assert len(result) == 8  # doesn't crash, uses default


class TestOpaqueIdEdgeCases:
    def test_empty_string(self):
        result = opaque_id("")
        assert len(result) == 8

    def test_unicode_name(self):
        result = opaque_id("François Mitterrand")
        assert len(result) == 8
        assert result == opaque_id("François Mitterrand")  # stable

    def test_very_long_name(self):
        result = opaque_id("x" * 10000)
        assert len(result) == 8
