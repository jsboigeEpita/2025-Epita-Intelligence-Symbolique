# Fichier: argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py
import asyncio
import json
from typing import Annotated, List, Dict

from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.kernel import Kernel
from semantic_kernel.functions.kernel_arguments import KernelArguments

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
        try:
            display_function = self.kernel.plugins["TaxonomyDisplayPlugin"]["DisplayBranch"]
        except KeyError:
            return json.dumps({"error": "La fonction 'DisplayBranch' du plugin 'TaxonomyDisplayPlugin' est introuvable."})

        taxonomy_json = self.taxonomy.get_full_taxonomy_json()
        
        tasks = []
        for node_id in nodes:
            args = KernelArguments(
                node_id=node_id,
                depth=depth,
                taxonomy=taxonomy_json
            )
            tasks.append(self.kernel.invoke(display_function, args))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Agréger les résultats dans un dictionnaire
        aggregated_results: Dict[str, str | Dict] = {}
        for i, res in enumerate(results):
            node_key = f"branch_{nodes[i]}"
            if isinstance(res, Exception):
                aggregated_results[node_key] = {"error": f"Erreur lors de l'exploration du noeud {nodes[i]}: {str(res)}"}
            else:
                # La valeur de retour est un ChatMessageContent, on extrait son contenu.
                aggregated_results[node_key] = str(res.value)

        return json.dumps(aggregated_results, indent=2, ensure_ascii=False)