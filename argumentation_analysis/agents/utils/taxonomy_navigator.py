import csv
import json
from typing import List, Dict, Any, Optional

class TaxonomyNavigator:
    """
    Handles loading and navigating a taxonomy from a CSV or JSON file.
    """
    def __init__(self, taxonomy_data: List[Dict[str, Any]]):
        self.taxonomy_data = taxonomy_data if taxonomy_data is not None else []
        self.node_map: Dict[str, Dict[str, Any]] = {}
        self.path_map: Dict[str, Dict[str, Any]] = {}  # New: For path-based lookup
        self._build_node_map()

    def _build_node_map(self):
        """Builds the node and path maps from the taxonomy data."""
        if not self.taxonomy_data:
            return
        for node in self.taxonomy_data:
            pk = node.get('PK')
            path = node.get('path')
            if pk:
                self.node_map[pk] = node
            if path:
                self.path_map[path] = node

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a node by its 'PK'.
        """
        return self.node_map.get(node_id)
        
    def get_node_by_path(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a node by its 'path'.
        """
        return self.path_map.get(path)

    def get_root_nodes(self) -> List[Dict[str, Any]]:
        """
        Returns all nodes at the root of the taxonomy (depth 1).
        """
        return [node for node in self.taxonomy_data if node.get('depth') == '1']

    def get_children(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves the direct children of a given node.
        """
        parent_node = self.get_node(node_id)
        if not parent_node:
            return []

        parent_path = parent_node.get('path', '')
        parent_depth = int(parent_node.get('depth', '-1'))
        
        children = []
        for node in self.taxonomy_data:
            # Ensure depth is treated as an integer for comparison
            try:
                node_depth = int(node.get('depth', '-1'))
            except (ValueError, TypeError):
                continue

            node_path = node.get('path', '')
            if node_path.startswith(f"{parent_path}.") and node_depth == parent_depth + 1:
                children.append(node)
        return children

    def get_parent(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves the parent of a given node.
        """
        node = self.get_node(node_id)
        if not node:
            return None

        node_path = node.get('path', '')
        if '.' not in node_path:
            return None # Root node

        parent_path = ".".join(node_path.split('.')[:-1])
        for parent_node in self.taxonomy_data:
            if parent_node.get('path') == parent_path:
                return parent_node
        return None

    def is_leaf(self, node_id: str) -> bool:
        """
        Checks if a node is a leaf (has no children).
        """
        return not self.get_children(node_id)

    def get_branch_as_str(self, node_id: str) -> str:
        """
        Returns a string representation of a branch, including the node
        and its direct children, formatted with indentation.
        """
        node = self.get_node(node_id)
        if not node:
            return "Node not found."

        branch_str = ""
        node_name = node.get('nom_vulgarisé', node.get('PK'))
        branch_str += f"- {node_name} (ID: {node['PK']})\n"

        children = self.get_children(node_id)
        for child in children:
            child_name = child.get('nom_vulgarisé', child.get('PK'))
            branch_str += f"  - {child_name} (ID: {child['PK']})\n"
        
        return branch_str.strip()
