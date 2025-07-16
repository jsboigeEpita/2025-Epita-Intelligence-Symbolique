# Fichier: argumentation_analysis/agents/plugins/exploration_tool.py

import asyncio
from typing import List, Dict
from semantic_kernel.functions import kernel_function

# Assumant que la taxonomie est définie ailleurs, nous importons un type de base
# from ...logic.taxonomy import Taxonomy
# Pour l'instant, nous allons utiliser un mock ou un type simple.

from ..utils.hybrid_decorator import hybrid_function

class ExplorationTool:
    """
    Outil pour générer et explorer des hypothèses de sophismes.
    """
    def __init__(self, taxonomy): # Remplacer "Any" par "Taxonomy" quand elle sera disponible
        """
        Initialise l'outil d'exploration.
        
        Args:
            taxonomy: L'arbre de taxonomie des sophismes à explorer.
        """
        self.taxonomy = taxonomy

    @kernel_function(name="get_exploration_hypotheses", description="Génère des hypothèses d'exploration de sophismes.")
    @hybrid_function(
        prompt_template="À partir de l'argument suivant: {{$input}}, identifie les 3 branches de la taxonomie des sophismes les plus pertinentes à explorer. Réponds avec une liste JSON d'IDs de noeuds de la taxonomie. Voici un exemple de format de sortie attendu : {\"node_ids\": [\"fallacy_1\", \"fallacy_2\", \"fallacy_3\"]}"
    )
    async def get_exploration_hypotheses(self, node_ids: List[str] = None) -> Dict:
        """
        Fonction native qui reçoit les IDs de noeuds du LLM.
        Elle explore ensuite la taxonomie en parallèle pour récupérer les
        informations de chaque branche.
        """
        print(f"IDs de noeuds reçus du LLM pour exploration : {node_ids}")
        # La logique est maintenant purement native et testable
        # Remarque : La méthode `get_branch` de taxonomie doit être thread-safe
        # ou, si elle est asynchrone, doit être attendue directement.
        tasks = [asyncio.to_thread(self.taxonomy.get_branch, node_id) for node_id in node_ids]
        results = await asyncio.gather(*tasks)
        
        # Filtrer les résultats None si une branche n'a pas été trouvée
        valid_results = [res for res in results if res is not None]
        validated_ids = [node_id for node_id, res in zip(node_ids, results) if res is not None]
        
        print(f"Branches de taxonomie récupérées : {validated_ids}")

        return dict(zip(validated_ids, valid_results))

    # Vous pouvez également exposer la fonction native `explore_branch` si nécessaire,
    # bien que `get_exploration_hypotheses` la contienne déjà.
    async def explore_branch(self, node_id: str) -> Dict:
        """
        Expose directement l'exploration d'une branche de la taxonomie.
        C'est une fonction native simple.
        """
        print(f"Exploration manuelle de la branche : {node_id}")
        return self.taxonomy.get_branch(node_id)