import json
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from argumentation_analysis.agents.core.plugin_loader import PluginLoader
from argumentation_analysis.agents.core.abc.plugin import BasePlugin
from argumentation_analysis.agents.core.exceptions import (
    PluginManifestError,
    CircularDependencyError,
)

# Helper classes and functions for tests


class MockPluginA(BasePlugin):
    """A mock plugin class for testing purposes that implements abstract methods."""

    @property
    def name(self) -> str:
        return "PluginA"

    def execute(self, **kwargs) -> dict:
        return {"result": "A"}


class MockPluginB(BasePlugin):
    """Another mock plugin class for testing purposes."""

    @property
    def name(self) -> str:
        return "PluginB"

    def execute(self, **kwargs) -> dict:
        return {"result": "B"}


PLUGIN_CODE_TEMPLATE = """
# This code is not actually executed due to mocking
class Dummy: pass
"""


@pytest.fixture
def plugin_test_env(fs):
    plugins_root = "/fake_plugins"
    fs.create_dir(plugins_root)
    # Ensure the root plugin directory is in the path for the real loader logic
    sys.path.insert(0, plugins_root)
    yield plugins_root, fs
    sys.path.pop(0)


def create_fake_plugin(fs, root, manifest):
    plugin_dir_name = manifest["name"].lower()
    plugin_path = os.path.join(root, plugin_dir_name)
    fs.create_dir(plugin_path)

    manifest_path = os.path.join(plugin_path, "manifest.json")
    fs.create_file(manifest_path, contents=json.dumps(manifest))

    module_name = manifest["entrypoint_module"]
    plugin_file_path = os.path.join(plugin_path, f"{module_name}.py")
    fs.create_file(plugin_file_path, contents=PLUGIN_CODE_TEMPLATE)

    # Create __init__.py to make it a package
    init_path = os.path.join(plugin_path, "__init__.py")
    fs.create_file(init_path, contents="")


# Patched tests


@patch("importlib.import_module")
def test_load_single_plugin_no_dependencies(mock_import_module, plugin_test_env):
    plugins_root, fs = plugin_test_env
    loader = PluginLoader()

    manifest = {
        "name": "PluginA",
        "entrypoint_module": "plugin_a",
        "entrypoint_class": "MockPluginA",
    }
    create_fake_plugin(fs, plugins_root, manifest)

    mock_module = MagicMock()
    # The loader will look for 'MockPluginA' class inside the 'plugin_a' module
    setattr(mock_module, "MockPluginA", MockPluginA)
    mock_import_module.return_value = mock_module

    loaded_plugins = loader.load_plugins_from_directory(plugins_root)

    assert "PluginA" in loaded_plugins
    # The loader logic might import plugin modules with their full path-like name
    mock_import_module.assert_called_once_with("plugin_a")
    assert isinstance(loaded_plugins["PluginA"], MockPluginA)
    assert loaded_plugins["PluginA"].name == "PluginA"


@patch("importlib.import_module")
def test_load_plugins_with_valid_dependencies(mock_import_module, plugin_test_env):
    plugins_root, fs = plugin_test_env
    loader = PluginLoader()

    manifest_a = {
        "name": "PluginA",
        "entrypoint_module": "plugin_a",
        "entrypoint_class": "MockPluginA",
    }
    create_fake_plugin(fs, plugins_root, manifest_a)

    manifest_b = {
        "name": "PluginB",
        "dependencies": ["PluginA"],
        "entrypoint_module": "plugin_b",
        "entrypoint_class": "MockPluginB",
    }
    create_fake_plugin(fs, plugins_root, manifest_b)

    def side_effect(module_name):
        mock_module = MagicMock()
        if "plugin_a" == module_name:
            setattr(mock_module, "MockPluginA", MockPluginA)
        elif "plugin_b" == module_name:
            setattr(mock_module, "MockPluginB", MockPluginB)
        else:
            raise ImportError(f"Unexpected module import: {module_name}")
        return mock_module

    mock_import_module.side_effect = side_effect

    loaded_plugins = loader.load_plugins_from_directory(plugins_root)

    assert list(loaded_plugins.keys()) == ["PluginA", "PluginB"]
    assert mock_import_module.call_count == 2
    assert isinstance(loaded_plugins["PluginA"], MockPluginA)
    assert isinstance(loaded_plugins["PluginB"], MockPluginB)
    assert loaded_plugins["PluginA"].name == "PluginA"
    assert loaded_plugins["PluginB"].name == "PluginB"


def test_load_plugins_with_circular_dependency_raises_error(plugin_test_env):
    plugins_root, fs = plugin_test_env
    loader = PluginLoader()

    manifest_a = {
        "name": "PluginA",
        "dependencies": ["PluginB"],
        "entrypoint_module": "plugin_a",
        "entrypoint_class": "MockPluginA",
    }
    create_fake_plugin(fs, plugins_root, manifest_a)

    manifest_b = {
        "name": "PluginB",
        "dependencies": ["PluginA"],
        "entrypoint_module": "plugin_b",
        "entrypoint_class": "MockPluginB",
    }
    create_fake_plugin(fs, plugins_root, manifest_b)

    with pytest.raises(CircularDependencyError) as excinfo:
        loader.load_plugins_from_directory(plugins_root)

    assert "Circular dependency detected" in str(excinfo.value)


if __name__ == "__main__":
    pytest.main([__file__])
