# Fichier: argumentation_analysis/agents/utils/taxonomy_utils.py
import json
import os
from typing import Any, Dict, Optional

class Taxonomy:
    """Charge et fournit un accès à la taxonomie des sophismes."""

    def __init__(self, file_path: str = "argumentation_analysis/agents/data/fallacy_taxonomy.json"):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier de taxonomie non trouvé à : {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)

    def _find_node_recursive(self, node_id: str, current_node: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Recherche récursive d'un nœud par son ID."""
        if current_node.get("id") == node_id:
            return current_node
        for child in current_node.get("children", []):
            found = self._find_node_recursive(node_id, child)
            if found:
                return found
        return None

    def get_branch(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une branche de la taxonomie par son ID.
        Retourne le nœud et ses enfants directs, sans la descendance des enfants.
        """
        node = self._find_node_recursive(node_id, self._data)
        if not node:
            return None
        
        # Créer une copie pour ne pas modifier l'objet original
        branch_info = {
            "id": node.get("id"),
            "name": node.get("name"),
            "description": node.get("description"),
            "children": [
                {
                    "id": child.get("id"),
                    "name": child.get("name"),
                    "description": child.get("description")
                } for child in node.get("children", [])
            ]
        }
        return branch_info