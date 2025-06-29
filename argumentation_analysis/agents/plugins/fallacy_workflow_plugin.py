# Fichier: argumentation_analysis/agents/plugins/fallacy_workflow_plugin.py
import asyncio
import json
from typing import Annotated, List

from semantic_kernel.kernel import Kernel
from semantic_kernel.functions.kernel_function_decorator import kernel_function
from semantic_kernel.functions.kernel_arguments import KernelArguments

from ..utils.taxonomy_utils import Taxonomy

class FallacyWorkflowPlugin:
    """
    Un plugin pour orchestrer des workflows complexes d'identification de sophismes.
    Ce plugin est natif et s'appuie sur un kernel injecté pour invoquer d'autres
    fonctions (potentiellment sémantiques) enregistrées auprès du même kernel.
    """
    def __init__(self, kernel: Kernel):
        """
        Initialise le plugin de workflow.

        Args:
            kernel: Une instance du Kernel sémantique que le plugin utilisera pour
                    invoquer d'autres fonctions.
        """
        self.kernel = kernel
        self.taxonomy = Taxonomy()

    @kernel_function(
            name="parallel_exploration",
            description="Explore plusieurs branches de la taxonomie en parallèle et retourne une description agrégée des résultats."
    )
    async def parallel_exploration(
        self,
        nodes: Annotated[List[str], "Liste des ID de noeuds à explorer en parallèle."],
        depth: Annotated[int, "Profondeur de l'exploration pour chaque noeud."] = 1
    ) -> Annotated[str, "Résultats agrégés de l'exploration des branches au format JSON."]:
        """
        Explore plusieurs branches de la taxonomie en parallèle.
        """
        taxonomy_json = self.taxonomy.get_full_taxonomy_json()
        
        # Récupère la fonction sémantique "display_branch" que le TaxonomyDisplayPlugin
        # a déjà dû enregistrer auprès du kernel.
        display_branch_func = self.kernel.plugins["TaxonomyDisplayPlugin"]["display_branch"]

        tasks = []
        for node_id in nodes:
            args = KernelArguments(
                node_id=node_id,
                depth=depth,
                taxonomy=taxonomy_json
            )
            task = asyncio.create_task(
                self.kernel.invoke(display_branch_func, args)
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        aggregated_results = {
            f"branch_{node}": str(result) for node, result in zip(nodes, results)
        }
        
        return json.dumps(aggregated_results, indent=2, ensure_ascii=False)