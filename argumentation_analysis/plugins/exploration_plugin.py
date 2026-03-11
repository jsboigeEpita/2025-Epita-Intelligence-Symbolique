"""ExplorationPlugin — constrained kernel functions for taxonomy navigation.

This plugin provides the ONLY tools available to the 'slave' LLM during
hierarchical fallacy detection. The LLM must navigate the taxonomy tree
by calling these functions — it cannot respond freely.

Recovered from commit d2fdd930 and enhanced with structured output.
"""
import json
import logging
from typing import Annotated, Optional

from semantic_kernel.functions.kernel_function_decorator import kernel_function

from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator

logger = logging.getLogger(__name__)


class ExplorationPlugin:
    """Plugin for constrained taxonomy navigation during fallacy detection.

    Provides 3 kernel functions:
    - explore_branch: Navigate to a taxonomy node and see its children
    - confirm_fallacy: Confirm a specific node as the identified fallacy
    - conclude_no_fallacy: Abandon exploration — no fallacy found in this branch
    """

    def __init__(self, taxonomy_navigator: TaxonomyNavigator):
        self.taxonomy_navigator = taxonomy_navigator

    @kernel_function(
        name="explore_branch",
        description=(
            "Navigate to a taxonomy node to see its details and children. "
            "Use this to explore deeper into a branch that might contain "
            "the relevant fallacy. Returns the node info and its children."
        ),
    )
    def explore_branch(
        self,
        node_pk: Annotated[str, "The PK (ID) of the taxonomy node to explore"],
    ) -> Annotated[str, "JSON with node details and children"]:
        """Navigate to a taxonomy node and return its details + children."""
        node = self.taxonomy_navigator.get_node(node_pk)
        if not node:
            return json.dumps({"error": f"Node {node_pk} not found"})

        children = self.taxonomy_navigator.get_children(node_pk)
        branch_info = {
            "node": {
                "pk": node.get("PK", ""),
                "path": node.get("path", ""),
                "name_fr": node.get("text_fr", node.get("nom_vulgarisé", "")),
                "name_en": node.get("text_en", node.get("Simple_name_en", "")),
                "description_fr": node.get("desc_fr", ""),
                "description_en": node.get("desc_en", ""),
                "example_fr": node.get("example_fr", ""),
                "example_en": node.get("example_en", ""),
                "depth": node.get("depth", ""),
                "is_leaf": len(children) == 0,
            },
            "children": [
                {
                    "pk": c.get("PK", ""),
                    "name_fr": c.get("text_fr", c.get("nom_vulgarisé", "")),
                    "name_en": c.get("text_en", c.get("Simple_name_en", "")),
                    "description_fr": c.get("desc_fr", ""),
                    "example_fr": c.get("example_fr", "")[:200],
                }
                for c in children
            ],
            "children_count": len(children),
        }
        return json.dumps(branch_info, ensure_ascii=False)

    @kernel_function(
        name="confirm_fallacy",
        description=(
            "Confirm that a specific taxonomy node is the identified fallacy. "
            "Call this when you are confident that the current node matches "
            "the fallacy in the analyzed text. Provide justification."
        ),
    )
    def confirm_fallacy(
        self,
        node_pk: Annotated[str, "The PK of the confirmed fallacy node"],
        confidence: Annotated[str, "Confidence level: 'high', 'medium', or 'low'"] = "medium",
        justification: Annotated[str, "Why this fallacy matches the text"] = "",
    ) -> Annotated[str, "Confirmation result"]:
        """Confirm a fallacy identification with justification."""
        node = self.taxonomy_navigator.get_node(node_pk)
        if not node:
            return json.dumps({"error": f"Node {node_pk} not found"})

        confidence_map = {"high": 0.9, "medium": 0.7, "low": 0.4}
        confidence_score = confidence_map.get(confidence.lower().strip(), 0.5)

        result = {
            "confirmed": True,
            "pk": node.get("PK", ""),
            "path": node.get("path", ""),
            "name_fr": node.get("text_fr", ""),
            "name_en": node.get("text_en", ""),
            "confidence": confidence_score,
            "justification": justification,
        }
        return json.dumps(result, ensure_ascii=False)

    @kernel_function(
        name="conclude_no_fallacy",
        description=(
            "Conclude that no relevant fallacy was found in the current branch. "
            "Call this when you have explored the branch sufficiently and determined "
            "that none of the nodes match the analyzed text."
        ),
    )
    def conclude_no_fallacy(
        self,
        reason: Annotated[str, "Why no fallacy was found in this branch"],
    ) -> Annotated[str, "Conclusion recorded"]:
        """Conclude that no fallacy was found in this branch."""
        return json.dumps(
            {"confirmed": False, "reason": reason}, ensure_ascii=False
        )
