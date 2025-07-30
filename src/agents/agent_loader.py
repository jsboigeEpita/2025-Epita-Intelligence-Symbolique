import os
import json
from typing import List, Dict, Any, Optional

class AgentLoader:
    """
    Handles the discovery and loading of agents based on their manifests.

    This class scans a given search path for agent directories, identified
    by the presence of an 'agent_manifest.json' file. It provides methods
    to discover these agents and load their metadata.
    """

    def discover_agents(self, search_path: str) -> List[str]:
        """
        Scans subdirectories of a given path to find agent manifests.

        Args:
            search_path: The root directory to start scanning from.

        Returns:
            A list of paths to the discovered agent_manifest.json files.
        """
        discovered_manifests: List[str] = []
        if not os.path.isdir(search_path):
            # Log this event appropriately in a real application
            print(f"Warning: Search path {search_path} does not exist.")
            return discovered_manifests

        for root, _, files in os.walk(search_path):
            if "agent_manifest.json" in files:
                manifest_path = os.path.join(root, "agent_manifest.json")
                discovered_manifests.append(manifest_path)
        
        return discovered_manifests

    def load_agent(self, agent_manifest_path: str) -> Optional[Dict[str, Any]]:
        """
        Reads and validates an agent manifest file.

        For now, validation is a simple check for well-formed JSON.

        Args:
            agent_manifest_path: The full path to the agent_manifest.json file.

        Returns:
            A dictionary containing the manifest data if successful, otherwise None.
        """
        if not os.path.exists(agent_manifest_path):
            print(f"Error: Manifest file not found at {agent_manifest_path}")
            return None

        try:
            with open(agent_manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            # Basic validation can be expanded here (e.g., with JSON Schema)
            required_keys = ["manifest_version", "agent_name", "version", "entry_point"]
            if not all(key in manifest_data for key in required_keys):
                print(f"Warning: Manifest {agent_manifest_path} is missing required keys.")
                return None

            return manifest_data
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {agent_manifest_path}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred while loading agent {agent_manifest_path}: {e}")
            return None