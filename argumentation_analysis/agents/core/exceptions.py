class PluginError(Exception):
    """Base exception for plugin-related errors."""

    pass


class PluginManifestError(PluginError):
    """Raised for errors related to the plugin manifest."""

    pass


class CircularDependencyError(PluginError):
    """Raised when a circular dependency is detected between plugins."""

    pass
