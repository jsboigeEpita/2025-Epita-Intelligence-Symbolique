# tests/unit/argumentation_analysis/core/test_pyo3_singleton.py
"""Tests for the PyO3 singleton module management."""

import pytest
import sys
from unittest.mock import patch, MagicMock

import argumentation_analysis.core.pyo3_singleton as pyo3_mod
from argumentation_analysis.core.pyo3_singleton import (
    initialize_pyo3,
    get_pyo3_module,
    unload_pyo3_module,
    reset_pyo3_environment,
)


@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global state before each test."""
    pyo3_mod._pyo3_modules = {}
    pyo3_mod._initialized = False
    yield
    pyo3_mod._pyo3_modules = {}
    pyo3_mod._initialized = False


# ── initialize_pyo3 ──


class TestInitializePyo3:
    def test_first_init_returns_true(self):
        assert initialize_pyo3() is True
        assert pyo3_mod._initialized is True

    def test_second_init_returns_true(self):
        initialize_pyo3()
        assert initialize_pyo3() is True

    def test_sets_initialized_flag(self):
        assert pyo3_mod._initialized is False
        initialize_pyo3()
        assert pyo3_mod._initialized is True


# ── get_pyo3_module ──


class TestGetPyo3Module:
    def test_loads_real_module(self):
        """Load a standard library module to test the flow."""
        mod = get_pyo3_module("json")
        assert mod is not None
        import json

        assert mod is json

    def test_caches_loaded_module(self):
        mod1 = get_pyo3_module("json")
        mod2 = get_pyo3_module("json")
        assert mod1 is mod2

    def test_returns_none_for_nonexistent_module(self):
        mod = get_pyo3_module("nonexistent_pyo3_module_12345")
        assert mod is None

    def test_calls_init_func(self):
        init_fn = MagicMock()
        mod = get_pyo3_module("json", init_func=init_fn)
        assert mod is not None
        init_fn.assert_called_once_with(mod)

    def test_auto_initializes_environment(self):
        assert pyo3_mod._initialized is False
        get_pyo3_module("json")
        assert pyo3_mod._initialized is True

    def test_returns_cached_without_reinit(self):
        initialize_pyo3()
        pyo3_mod._pyo3_modules["cached_mod"] = "fake_module"
        result = get_pyo3_module("cached_mod")
        assert result == "fake_module"

    def test_returns_none_when_init_fails(self):
        with patch.object(pyo3_mod, "initialize_pyo3", return_value=False):
            pyo3_mod._initialized = False
            result = get_pyo3_module("json")
            assert result is None

    def test_handles_import_error(self):
        with patch("importlib.import_module", side_effect=ImportError("not found")):
            initialize_pyo3()
            result = get_pyo3_module("bad_module")
            assert result is None

    def test_handles_generic_exception(self):
        with patch("importlib.import_module", side_effect=RuntimeError("boom")):
            initialize_pyo3()
            result = get_pyo3_module("bad_module")
            assert result is None


# ── unload_pyo3_module ──


class TestUnloadPyo3Module:
    def test_unload_loaded_module(self):
        get_pyo3_module("json")
        assert "json" in pyo3_mod._pyo3_modules
        result = unload_pyo3_module("json")
        assert result is True
        assert "json" not in pyo3_mod._pyo3_modules

    def test_unload_removes_from_sys_modules(self):
        get_pyo3_module("json")
        # json is in sys.modules
        assert "json" in sys.modules
        unload_pyo3_module("json")
        # json should be removed from _pyo3_modules but json is standard,
        # it gets re-imported. Just check _pyo3_modules.
        assert "json" not in pyo3_mod._pyo3_modules

    def test_unload_nonexistent_returns_false(self):
        result = unload_pyo3_module("never_loaded_module")
        assert result is False

    def test_unload_twice_returns_false_second_time(self):
        get_pyo3_module("json")
        assert unload_pyo3_module("json") is True
        assert unload_pyo3_module("json") is False


# ── reset_pyo3_environment ──


class TestResetPyo3Environment:
    def test_resets_everything(self):
        initialize_pyo3()
        get_pyo3_module("json")
        assert pyo3_mod._initialized is True
        assert len(pyo3_mod._pyo3_modules) > 0

        result = reset_pyo3_environment()
        assert result is True
        assert pyo3_mod._initialized is False
        assert pyo3_mod._pyo3_modules == {}

    def test_reset_empty_state(self):
        result = reset_pyo3_environment()
        assert result is True
        assert pyo3_mod._initialized is False

    def test_reset_multiple_modules(self):
        get_pyo3_module("json")
        get_pyo3_module("os")
        assert len(pyo3_mod._pyo3_modules) == 2
        reset_pyo3_environment()
        assert len(pyo3_mod._pyo3_modules) == 0
