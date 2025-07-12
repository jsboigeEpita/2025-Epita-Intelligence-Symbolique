# Fichier: argumentation_analysis/agents/plugins/exploration_plugin.py
import json
from typing import Annotated
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator

class ExplorationPlugin:
    """Plugin dédié à l'exploration de la taxonomie des sophismes."""

    def __init__(self, taxonomy_navigator: TaxonomyNavigator):
        """Initialise le plugin d'exploration."""
        self.taxonomy_navigator = taxonomy_navigator

    @kernel_function(
        name="explore_branch",
        description="Explore une branche de la taxonomie des sophismes pour voir ses sous-catégories."
    )
    def explore_branch(
        self, node_pk: Annotated[str, "Le 'PK' (Primary Key) numérique du nœud à explorer (ex: '1', '70')."]
    ) -> Annotated[str, "Une description JSON de la branche et de ses enfants directs."]:
        """Explore une branche de la taxonomie."""
        node = self.taxonomy_navigator.get_node(node_pk)
        if not node:
            return json.dumps({"error": "Node not found"})

        children = self.taxonomy_navigator.get_children(node_pk)
        
        # Simplifier les enfants pour ne retourner que les informations essentielles
        simplified_children = [
            {"id": child.get("PK"), "name": child.get("nom_vulgarise"), "description": child.get("description_courte")}
            for child in children
        ]

        branch_info = {
            "id": node.get("PK"),
            "name": node.get("nom_vulgarise"),
            "description": node.get("description_courte"),
            "children": simplified_children
        }
        
        return json.dumps(branch_info, indent=2, ensure_ascii=False)

    @kernel_function(
        name="conclude_no_fallacy",
        description="Conclut qu'aucun des sophismes ou catégories proposés n'est pertinent pour le texte analysé."
    )
    def conclude_no_fallacy(
        self, reason: Annotated[str, "L'explication concise expliquant pourquoi aucune branche n'est pertinente."]
    ) -> Annotated[str, "Une confirmation de la conclusion."]:
        """
        Enregistre la conclusion qu'aucun sophisme pertinent n'a été trouvé à cette étape.
        """
        # La fonction n'a pas besoin de faire grand chose, le simple fait de l'appeler est le signal.
        # On pourrait logger la raison pour le débogage.
        return f"Conclusion enregistrée : {reason}"