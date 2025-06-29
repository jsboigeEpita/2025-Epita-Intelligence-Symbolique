# Fichier: argumentation_analysis/agents/plugins/fallacy_identification_plugin.py
import json
from typing import Annotated, List

from pydantic import BaseModel, Field
from semantic_kernel.functions.kernel_function_decorator import kernel_function

from ..utils.taxonomy_utils import Taxonomy

class IdentifiedFallacy(BaseModel):
    """Modèle de données pour un sophisme identifié."""
    fallacy_type: str = Field(..., description="Le type de sophisme, ex: 'Ad Hominem', 'Homme de paille'.")
    explanation: str = Field(..., description="L'explication de la raison pour laquelle il s'agit de ce sophisme.")
    problematic_quote: str = Field(..., description="La citation exacte du texte qui contient le sophisme.")


class FallacyIdentificationResult(BaseModel):
    """Modèle de données pour la liste des sophismes identifiés."""
    fallacies: List[IdentifiedFallacy]

class FallacyIdentificationPlugin:
    """Un plugin pour identifier les sophismes informels dans un texte."""
    
    def __init__(self):
        """Initialise le plugin, en chargeant la taxonomie."""
        self.taxonomy = Taxonomy()

    @kernel_function(name="explore_branch", description="Explore une branche de la taxonomie des sophismes pour voir ses sous-catégories. A utiliser pour naviguer dans la taxonomie avant d'identifier un sophisme final.")
    def explore_branch(
        self, node_id: Annotated[str, "L'ID de la branche de la taxonomie à explorer (ex: 'relevance', 'ad_hominem'). L'ID racine est 'fallacy_root'."]
    ) -> Annotated[str, "Une description JSON de la branche et de ses enfants directs."]:
        """Explore une branche de la taxonomie."""
        branch = self.taxonomy.get_branch(node_id)
        if not branch:
            return json.dumps({"error": "Node not found"})
        return json.dumps(branch, indent=2, ensure_ascii=False)

    @kernel_function(
        name="identify_fallacies",
        description="Identifie et liste les sophismes informels présents dans un texte donné.",
    )
    def identify_fallacies(self, fallacies: List[IdentifiedFallacy]) -> str:
        """
        Cette méthode est un 'outil' pour le Kernel. Le LLM est forcé de l'appeler,
        validant de fait la structure des données via les types Pydantic.
        La valeur de retour (une chaîne de confirmation) n'est généralement pas utilisée.
        """
        # La validation est effectuée par Pydantic grâce à l'injection de type.
        # On pourrait ajouter une logique supplémentaire ici si nécessaire.
        return f"Validation réussie, {len(fallacies)} sophisme(s) identifié(s)."