"""Tests for argumentation_analysis.evaluation.opaque_id."""

import os

import pytest

from argumentation_analysis.evaluation.opaque_id import opaque_id


class TestOpaqueIdStability:
    def test_same_input_same_output(self):
        # salt= argument path: stable regardless of env state.
        assert opaque_id("Speaker A", salt="s") == opaque_id("Speaker A", salt="s")

    def test_different_salt_different_output(self):
        a = opaque_id("Speaker A", salt="salt1")
        b = opaque_id("Speaker A", salt="salt2")
        assert a != b

    def test_different_names_different_ids(self):
        ids = {opaque_id(f"name_{i}", salt="s") for i in range(100)}
        assert len(ids) == 100  # no collisions


class TestOpaqueIdFormat:
    def test_length_is_8(self):
        result = opaque_id("test", salt="s")
        assert len(result) == 8

    def test_hex_chars_only(self):
        result = opaque_id("test", salt="s")
        assert all(c in "0123456789abcdef" for c in result)


class TestOpaqueIdSaltEnv:
    def test_env_salt_used(self, monkeypatch):
        monkeypatch.setenv("OPAQUE_ID_SALT", "env_salt_123")
        a = opaque_id("test")
        b = opaque_id("test", salt="env_salt_123")
        assert a == b

    def test_missing_salt_raises_runtime_error(self, monkeypatch):
        """#1973: a public default salt provided no privacy — anyone
        reading the repo could confirm a guessed name against a
        published opaque ID. The function now fails loud instead.
        """
        monkeypatch.delenv("OPAQUE_ID_SALT", raising=False)
        with pytest.raises(RuntimeError, match="OPAQUE_ID_SALT"):
            opaque_id("test")

    def test_missing_salt_with_explicit_none_raises(self, monkeypatch):
        """Passing ``salt=None`` explicitly must still raise when the env
        is unset — there is no implicit fallback to fall back to.
        """
        monkeypatch.delenv("OPAQUE_ID_SALT", raising=False)
        with pytest.raises(RuntimeError, match="OPAQUE_ID_SALT"):
            opaque_id("test", salt=None)

    def test_empty_string_salt_raises(self, monkeypatch):
        """An empty-string salt is treated as absent — its sha256 is
        trivial to invert against a published ID.
        """
        monkeypatch.delenv("OPAQUE_ID_SALT", raising=False)
        with pytest.raises(RuntimeError, match="OPAQUE_ID_SALT"):
            opaque_id("test", salt="")

    def test_salt_with_only_whitespace_raises(self, monkeypatch):
        """A whitespace-only salt is also rejected: it is effectively
        public (an empty effective string is sha256-able offline).
        """
        monkeypatch.delenv("OPAQUE_ID_SALT", raising=False)
        with pytest.raises(RuntimeError, match="OPAQUE_ID_SALT"):
            opaque_id("test", salt="   ")


class TestOpaqueIdEdgeCases:
    def test_empty_string(self):
        result = opaque_id("", salt="s")
        assert len(result) == 8

    def test_unicode_name(self):
        result = opaque_id("Geneviève Béranger", salt="s")
        assert len(result) == 8
        assert result == opaque_id("Geneviève Béranger", salt="s")  # stable

    def test_very_long_name(self):
        result = opaque_id("x" * 10000, salt="s")
        assert len(result) == 8
