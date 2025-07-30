import os
import json
import importlib.util
from typing import List, Dict, Any, Optional

class PluginLoader:
    """
    Handles the discovery and loading of plugins based on their manifests.

    This class scans a given search path for plugin directories, identified
    by the presence of a 'plugin_manifest.json' file. It provides methods
    to discover these plugins and load their metadata.
    """

    def discover_plugins(self, search_path: str) -> List[str]:
        """
        Scans subdirectories of a given path to find plugin manifests.

        Args:
            search_path: The root directory to start scanning from.

        Returns:
            A list of paths to the discovered plugin_manifest.json files.
        """
        discovered_manifests: List[str] = []
        if not os.path.isdir(search_path):
            # Log this event appropriately in a real application
            print(f"Warning: Search path {search_path} does not exist.")
            return discovered_manifests

        for root, _, files in os.walk(search_path):
            if "plugin_manifest.json" in files:
                manifest_path = os.path.join(root, "plugin_manifest.json")
                discovered_manifests.append(manifest_path)
        
        return discovered_manifests

    def load_plugin(self, plugin_manifest_path: str) -> Optional[Dict[str, Any]]:
        """
        Reads and validates a plugin manifest file.

        For now, validation is a simple check for well-formed JSON.

        Args:
            plugin_manifest_path: The full path to the plugin_manifest.json file.

        Returns:
            A dictionary containing the manifest data if successful, otherwise None.
        """
        if not os.path.exists(plugin_manifest_path):
            print(f"Error: Manifest file not found at {plugin_manifest_path}")
            return None

        try:
            with open(plugin_manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            # Basic validation can be expanded here (e.g., with JSON Schema)
            required_keys = ["manifest_version", "plugin_name", "version", "entry_point"]
            if not all(key in manifest_data for key in required_keys):
                print(f"Warning: Manifest {plugin_manifest_path} is missing required keys.")
                return None

            return manifest_data
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {plugin_manifest_path}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while loading plugin {plugin_manifest_path}: {e}")
            return None
