class PluginError(Exception):
    """Base exception for plugin-related errors."""


class PluginManifestError(PluginError):
    """Raised for errors related to the plugin manifest."""


class CircularDependencyError(PluginError):
    """Raised when a circular dependency is detected between plugins."""
