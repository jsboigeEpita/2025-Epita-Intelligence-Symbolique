import pytest
from argumentation_analysis.plugin_framework.core.plugins.plugin_loader import (
    PluginLoader,
)


def test_plugin_loader_can_be_imported():
    """
    Tests that the PluginLoader class can be imported successfully.
    """
    assert PluginLoader is not None
