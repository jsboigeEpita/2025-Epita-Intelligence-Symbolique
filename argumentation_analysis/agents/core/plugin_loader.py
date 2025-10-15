import json
import importlib
import sys
from pathlib import Path

from argumentation_analysis.agents.core.abc.plugin import BasePlugin
from argumentation_analysis.agents.core.exceptions import (
    PluginManifestError,
    CircularDependencyError,
)


class PluginLoader:
    """
    Discovers and loads plugins from a given path.
    """

    def load_plugins_from_directory(
        self, plugins_directory: str
    ) -> dict[str, BasePlugin]:
        """
        Discovers all plugins in a directory, resolves dependencies,
        and loads them in the correct order.
        """
        plugins_dir = Path(plugins_directory)

        all_manifests = {}
        for potential_plugin_dir in plugins_dir.iterdir():
            if potential_plugin_dir.is_dir():
                manifest_path = potential_plugin_dir / "manifest.json"
                if manifest_path.is_file():
                    manifest = self._read_manifest(manifest_path)
                    plugin_name = manifest.get("name")
                    if plugin_name:
                        all_manifests[plugin_name] = {
                            "manifest": manifest,
                            "path": potential_plugin_dir,
                        }

        dependency_graph = {
            name: data["manifest"].get("dependencies", [])
            for name, data in all_manifests.items()
        }

        sorted_plugins = self._resolve_dependencies(dependency_graph)

        loaded_plugins = {}
        for plugin_name in sorted_plugins:
            plugin_info = all_manifests[plugin_name]
            plugin_instance = self._load_plugin_from_manifest(
                plugin_info["path"], plugin_info["manifest"]
            )
            loaded_plugins[plugin_name] = plugin_instance

        return loaded_plugins

    def _read_manifest(self, manifest_path: Path) -> dict:
        """Reads and validates a plugin manifest."""
        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)
        except json.JSONDecodeError:
            raise PluginManifestError(
                f"Malformed JSON in manifest file: {manifest_path}"
            )

        required_fields = ["name", "entrypoint_module", "entrypoint_class"]
        for field in required_fields:
            if field not in manifest:
                raise PluginManifestError(
                    f"Missing required field '{field}' in manifest: {manifest_path}"
                )
        return manifest

    def _resolve_dependencies(
        self, dependency_graph: dict[str, list[str]]
    ) -> list[str]:
        """
        Sorts plugins topologically based on dependencies and detects cycles.
        """
        sorted_list = []
        visiting = set()
        visited = set()

        def visit(plugin_name):
            if plugin_name not in dependency_graph:
                # Assuming dependencies on non-existent plugins are an error
                # This could be changed to simply ignore them
                raise PluginManifestError(f"Dependency '{plugin_name}' not found.")

            visited.add(plugin_name)
            visiting.add(plugin_name)

            for dependency in dependency_graph.get(plugin_name, []):
                if dependency in visiting:
                    raise CircularDependencyError(
                        f"Circular dependency detected: {plugin_name} -> {dependency}"
                    )
                if dependency not in visited:
                    visit(dependency)

            visiting.remove(plugin_name)
            sorted_list.append(plugin_name)

        for plugin_name in list(
            dependency_graph
        ):  # Use list to allow modification during iteration if needed
            if plugin_name not in visited:
                visit(plugin_name)

        return sorted_list

    def _load_plugin_from_manifest(
        self, plugin_path: Path, manifest: dict
    ) -> BasePlugin:
        """Loads a single plugin from its manifest and path."""
        entrypoint_module_name = manifest["entrypoint_module"]
        entrypoint_class_name = manifest["entrypoint_class"]

        original_sys_path = sys.path[:]
        try:
            # Add the plugin's directory to sys.path to allow direct import
            sys.path.insert(0, str(plugin_path))

            # Invalidate cache for reliable testing with pyfakefs
            if entrypoint_module_name in sys.modules:
                del sys.modules[entrypoint_module_name]

            plugin_module = importlib.import_module(entrypoint_module_name)
            plugin_class = getattr(plugin_module, entrypoint_class_name)

        except (ImportError, AttributeError, KeyError) as e:
            raise PluginManifestError(
                f"Failed to load entrypoint for plugin {manifest['name']}: {e}"
            )
        finally:
            # Restore sys.path
            sys.path[:] = original_sys_path

        if not issubclass(plugin_class, BasePlugin):
            raise TypeError(
                f"Plugin class {entrypoint_class_name} must inherit from BasePlugin."
            )

        return plugin_class()
