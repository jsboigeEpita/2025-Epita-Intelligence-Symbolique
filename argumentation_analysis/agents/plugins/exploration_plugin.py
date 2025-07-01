# Fichier: argumentation_analysis/agents/plugins/exploration_plugin.py
import json
from typing import Annotated
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from argumentation_analysis.agents.utils.taxonomy_utils import Taxonomy

class ExplorationPlugin:
    """Plugin dédié à l'exploration de la taxonomie des sophismes."""

    def __init__(self):
        """Initialise le plugin d'exploration."""
        self.taxonomy = Taxonomy()

    @kernel_function(
        name="explore_branch",
        description="Explore une branche de la taxonomie des sophismes pour voir ses sous-catégories."
    )
    def explore_branch(
        self, node_id: Annotated[str, "L'ID de la branche à explorer (ex: 'relevance', 'fallacy_root')."]
    ) -> Annotated[str, "Une description JSON de la branche et de ses enfants directs."]:
        """Explore une branche de la taxonomie."""
        branch = self.taxonomy.get_branch(node_id)
        if not branch:
            return json.dumps({"error": "Node not found"})
        return json.dumps(branch, indent=2, ensure_ascii=False)