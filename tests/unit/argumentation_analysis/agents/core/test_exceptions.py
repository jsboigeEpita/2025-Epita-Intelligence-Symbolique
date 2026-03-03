# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.agents.core.exceptions
Covers PluginError, PluginManifestError, CircularDependencyError.
"""

import pytest
from argumentation_analysis.agents.core.exceptions import (
    PluginError,
    PluginManifestError,
    CircularDependencyError,
)


class TestPluginError:
    def test_is_exception(self):
        assert issubclass(PluginError, Exception)

    def test_can_raise(self):
        with pytest.raises(PluginError, match="test error"):
            raise PluginError("test error")

    def test_str(self):
        err = PluginError("plugin failed")
        assert str(err) == "plugin failed"

    def test_catch_as_exception(self):
        with pytest.raises(Exception):
            raise PluginError("caught as base")


class TestPluginManifestError:
    def test_is_plugin_error(self):
        assert issubclass(PluginManifestError, PluginError)

    def test_can_raise(self):
        with pytest.raises(PluginManifestError, match="manifest invalid"):
            raise PluginManifestError("manifest invalid")

    def test_catchable_as_plugin_error(self):
        with pytest.raises(PluginError):
            raise PluginManifestError("caught as PluginError")

    def test_catchable_as_exception(self):
        with pytest.raises(Exception):
            raise PluginManifestError("caught as Exception")


class TestCircularDependencyError:
    def test_is_plugin_error(self):
        assert issubclass(CircularDependencyError, PluginError)

    def test_can_raise(self):
        with pytest.raises(CircularDependencyError, match="A -> B -> A"):
            raise CircularDependencyError("A -> B -> A")

    def test_catchable_as_plugin_error(self):
        with pytest.raises(PluginError):
            raise CircularDependencyError("cycle detected")

    def test_inheritance_chain(self):
        err = CircularDependencyError("cycle")
        assert isinstance(err, PluginError)
        assert isinstance(err, Exception)
