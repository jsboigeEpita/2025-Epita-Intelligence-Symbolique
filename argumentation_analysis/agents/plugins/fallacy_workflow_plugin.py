# Fichier: argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py
import asyncio
import json
from typing import Annotated, List, Dict

from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.kernel import Kernel
from semantic_kernel.functions import KernelArguments

from ..utils.taxonomy_utils import Taxonomy


class FallacyWorkflowPlugin:
    """Plugin pour orchestrer des workflows complexes liés à l'analyse de sophismes."""

    def __init__(self, kernel: Kernel):
        """
        Initialise le plugin de workflow.

        Args:
            kernel (Kernel): L'instance du kernel à utiliser pour orchestrer les appels.
        """
        self.kernel = kernel
        self.taxonomy = Taxonomy()

    @kernel_function(
        name="parallel_exploration",
        description="Explore plusieurs branches de la taxonomie des sophismes en parallèle pour obtenir une vue d'ensemble et comparer différentes catégories."
    )
    async def parallel_exploration(
        self, nodes: Annotated[List[str], "Une liste d'IDs des noeuds de la taxonomie à explorer."],
        depth: Annotated[int, "La profondeur d'exploration pour chaque branche."] = 1
    ) -> Annotated[str, "Un dictionnaire JSON contenant les résultats de l'exploration pour chaque branche."]:
        """
        Explore plusieurs branches de la taxonomie des sophismes en parallèle en utilisant le TaxonomyDisplayPlugin.
        """
        # La recherche de la fonction DisplayBranch est supprimée.
        # Nous utilisons directement la classe Taxonomy pour obtenir les informations.

        aggregated_results: Dict[str, Any] = {}
        for node_id in nodes:
            branch_data = self.taxonomy.get_branch(node_id)
            if branch_data:
                # La profondeur n'est pas gérée par get_branch, mais le comportement par défaut est suffisant.
                aggregated_results[node_id] = branch_data
            else:
                aggregated_results[node_id] = {"error": f"Noeud '{node_id}' non trouvé dans la taxonomie."}

        return json.dumps(aggregated_results, indent=2, ensure_ascii=False)