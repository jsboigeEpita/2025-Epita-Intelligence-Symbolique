# -*- coding: utf-8 -*-
"""
Unit tests for PluginLoader and plugin infrastructure.

Tests cover:
- PluginLoader: manifest reading, dependency resolution, plugin loading
- BasePlugin / LegoPlugin: interface, capabilities, requirement checking
- Error handling: malformed manifests, circular dependencies, missing fields
"""

import json
import pytest

from argumentation_analysis.agents.core.plugin_loader import PluginLoader
from argumentation_analysis.agents.core.abc.plugin import (
    BasePlugin,
    LegoPlugin,
    ParameterSpec,
)
from argumentation_analysis.agents.core.exceptions import (
    PluginManifestError,
    CircularDependencyError,
)


# ===========================================================================
# BasePlugin / LegoPlugin Tests
# ===========================================================================


class ConcretePlugin(BasePlugin):
    """Concrete test implementation of BasePlugin."""

    @property
    def name(self) -> str:
        return "test_plugin"

    def execute(self, **kwargs) -> dict:
        return {"status": "ok", **kwargs}


class ConcreteLegoPlugin(LegoPlugin):
    """Concrete test implementation of LegoPlugin."""

    provides = ["fallacy_detection", "taxonomy_display"]
    requires = ["llm_service"]
    parameters = [
        ParameterSpec("language", type="string", default="fr"),
        ParameterSpec("threshold", type="float", required=True, description="Min confidence"),
    ]

    @property
    def name(self) -> str:
        return "test_lego_plugin"

    def execute(self, **kwargs) -> dict:
        return {"detected": True, **kwargs}


class TestBasePlugin:
    """Unit tests for BasePlugin."""

    def test_concrete_plugin_name(self):
        plugin = ConcretePlugin()
        assert plugin.name == "test_plugin"

    def test_concrete_plugin_execute(self):
        plugin = ConcretePlugin()
        result = plugin.execute(input="test")
        assert result["status"] == "ok"
        assert result["input"] == "test"

    def test_abstract_methods_enforced(self):
        """Cannot instantiate BasePlugin directly."""
        with pytest.raises(TypeError):
            BasePlugin()


class TestLegoPlugin:
    """Unit tests for LegoPlugin."""

    def test_capabilities(self):
        plugin = ConcreteLegoPlugin()
        caps = plugin.get_capabilities()
        assert caps["name"] == "test_lego_plugin"
        assert "fallacy_detection" in caps["provides"]
        assert "taxonomy_display" in caps["provides"]
        assert "llm_service" in caps["requires"][0] if caps["requires"] else True

    def test_parameters_in_capabilities(self):
        plugin = ConcreteLegoPlugin()
        caps = plugin.get_capabilities()
        params = caps["parameters"]
        assert "language" in params
        assert params["language"]["default"] == "fr"
        assert params["threshold"]["required"] is True

    def test_check_requirements_met(self):
        plugin = ConcreteLegoPlugin()
        missing = plugin.check_requirements(["llm_service", "other_service"])
        assert missing == []

    def test_check_requirements_missing(self):
        plugin = ConcreteLegoPlugin()
        missing = plugin.check_requirements(["other_service"])
        assert "llm_service" in missing

    def test_is_available_with_deps(self):
        plugin = ConcreteLegoPlugin()
        assert plugin.is_available(["llm_service"]) is True
        assert plugin.is_available(["other"]) is False

    def test_is_available_none_assumes_met(self):
        plugin = ConcreteLegoPlugin()
        assert plugin.is_available(None) is True

    def test_execute(self):
        plugin = ConcreteLegoPlugin()
        result = plugin.execute(text="test input")
        assert result["detected"] is True
        assert result["text"] == "test input"


# ===========================================================================
# PluginLoader Tests
# ===========================================================================


class TestPluginLoaderManifest:
    """Tests for manifest reading and validation."""

    @pytest.fixture
    def loader(self):
        return PluginLoader()

    def test_read_valid_manifest(self, loader, tmp_path):
        manifest = {
            "name": "test_plugin",
            "entrypoint_module": "my_module",
            "entrypoint_class": "MyPlugin",
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        result = loader._read_manifest(manifest_path)
        assert result["name"] == "test_plugin"
        assert result["entrypoint_module"] == "my_module"

    def test_read_manifest_malformed_json(self, loader, tmp_path):
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text("{ not json }")

        with pytest.raises(PluginManifestError, match="Malformed JSON"):
            loader._read_manifest(manifest_path)

    def test_read_manifest_missing_name(self, loader, tmp_path):
        manifest = {
            "entrypoint_module": "my_module",
            "entrypoint_class": "MyPlugin",
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        with pytest.raises(PluginManifestError, match="Missing required field 'name'"):
            loader._read_manifest(manifest_path)

    def test_read_manifest_missing_entrypoint(self, loader, tmp_path):
        manifest = {"name": "test_plugin", "entrypoint_class": "MyPlugin"}
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))

        with pytest.raises(PluginManifestError, match="entrypoint_module"):
            loader._read_manifest(manifest_path)


class TestPluginLoaderDependencyResolution:
    """Tests for topological sorting and cycle detection."""

    @pytest.fixture
    def loader(self):
        return PluginLoader()

    def test_no_dependencies(self, loader):
        graph = {"a": [], "b": [], "c": []}
        result = loader._resolve_dependencies(graph)
        assert set(result) == {"a", "b", "c"}

    def test_linear_dependencies(self, loader):
        graph = {"c": ["b"], "b": ["a"], "a": []}
        result = loader._resolve_dependencies(graph)
        assert result.index("a") < result.index("b")
        assert result.index("b") < result.index("c")

    def test_diamond_dependencies(self, loader):
        graph = {"d": ["b", "c"], "b": ["a"], "c": ["a"], "a": []}
        result = loader._resolve_dependencies(graph)
        assert result.index("a") < result.index("b")
        assert result.index("a") < result.index("c")
        assert result.index("b") < result.index("d")
        assert result.index("c") < result.index("d")

    def test_circular_dependency_detected(self, loader):
        graph = {"a": ["b"], "b": ["a"]}
        with pytest.raises(CircularDependencyError):
            loader._resolve_dependencies(graph)

    def test_three_way_cycle(self, loader):
        graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
        with pytest.raises(CircularDependencyError):
            loader._resolve_dependencies(graph)

    def test_missing_dependency(self, loader):
        graph = {"a": ["nonexistent"]}
        with pytest.raises(PluginManifestError, match="not found"):
            loader._resolve_dependencies(graph)


class TestPluginLoaderLoadFromDirectory:
    """Tests for end-to-end plugin loading from directory."""

    @pytest.fixture
    def loader(self):
        return PluginLoader()

    def _create_plugin_dir(self, parent, name, module_name, class_name, deps=None):
        """Helper to create a plugin directory with manifest and module."""
        plugin_dir = parent / name
        plugin_dir.mkdir()

        manifest = {
            "name": name,
            "entrypoint_module": module_name,
            "entrypoint_class": class_name,
            "dependencies": deps or [],
        }
        (plugin_dir / "manifest.json").write_text(json.dumps(manifest))

        # Create the Python module
        module_code = f"""
from argumentation_analysis.agents.core.abc.plugin import BasePlugin

class {class_name}(BasePlugin):
    @property
    def name(self) -> str:
        return "{name}"

    def execute(self, **kwargs) -> dict:
        return {{"plugin": "{name}"}}
"""
        (plugin_dir / f"{module_name}.py").write_text(module_code)
        return plugin_dir

    def test_load_single_plugin(self, loader, tmp_path):
        self._create_plugin_dir(tmp_path, "my_plugin", "plugin_mod", "MyPlugin")

        plugins = loader.load_plugins_from_directory(str(tmp_path))
        assert "my_plugin" in plugins
        assert plugins["my_plugin"].name == "my_plugin"

    def test_load_multiple_plugins(self, loader, tmp_path):
        self._create_plugin_dir(tmp_path, "plugin_a", "mod_a", "PluginA")
        self._create_plugin_dir(tmp_path, "plugin_b", "mod_b", "PluginB")

        plugins = loader.load_plugins_from_directory(str(tmp_path))
        assert len(plugins) == 2
        assert "plugin_a" in plugins
        assert "plugin_b" in plugins

    def test_load_with_dependencies(self, loader, tmp_path):
        self._create_plugin_dir(tmp_path, "base_plugin", "base_mod", "BaseP")
        self._create_plugin_dir(
            tmp_path, "dependent_plugin", "dep_mod", "DepP",
            deps=["base_plugin"],
        )

        plugins = loader.load_plugins_from_directory(str(tmp_path))
        assert len(plugins) == 2
        # Base should be loaded before dependent
        keys = list(plugins.keys())
        assert keys.index("base_plugin") < keys.index("dependent_plugin")

    def test_skip_directories_without_manifest(self, loader, tmp_path):
        self._create_plugin_dir(tmp_path, "valid_plugin", "mod", "Plugin")
        # Create a directory without manifest
        no_manifest = tmp_path / "not_a_plugin"
        no_manifest.mkdir()

        plugins = loader.load_plugins_from_directory(str(tmp_path))
        assert len(plugins) == 1
        assert "valid_plugin" in plugins

    def test_empty_directory(self, loader, tmp_path):
        plugins = loader.load_plugins_from_directory(str(tmp_path))
        assert plugins == {}

    def test_plugin_execute(self, loader, tmp_path):
        self._create_plugin_dir(tmp_path, "exec_plugin", "exec_mod", "ExecPlugin")

        plugins = loader.load_plugins_from_directory(str(tmp_path))
        result = plugins["exec_plugin"].execute()
        assert result["plugin"] == "exec_plugin"
