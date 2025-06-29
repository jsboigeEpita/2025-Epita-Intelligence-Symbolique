# Fichier: argumentation_analysis/agents/plugins/fallacy_identification_plugin.py
from typing import List
from pydantic import BaseModel, Field
from semantic_kernel.functions.kernel_function_decorator import kernel_function

class IdentifiedFallacy(BaseModel):
    """Modèle de données pour un sophisme identifié."""
    fallacy_type: str = Field(..., description="Le type de sophisme, ex: 'Ad Hominem', 'Homme de paille'.")
    explanation: str = Field(..., description="L'explication de la raison pour laquelle il s'agit de ce sophisme.")
    problematic_quote: str = Field(..., description="La citation exacte du texte qui contient le sophisme.")

class FallacyIdentificationResult(BaseModel):
    """Modèle de données pour la liste des sophismes identifiés."""
    fallacies: List[IdentifiedFallacy]

class FallacyIdentificationPlugin:
    """Plugin qui expose le modèle Pydantic au Kernel comme un 'outil' invocable."""
    
    @kernel_function(
        name="identify_fallacies",
        description="Identifie et liste les sophismes dans un texte donné.",
    )
    def identify_fallacies_tool(self, fallacies: List[IdentifiedFallacy]) -> str:
        """
        Cette méthode est un 'outil' pour le Kernel. Le LLM est forcé de l'appeler,
        validant de fait la structure des données via les types Pydantic.
        La valeur de retour (une chaîne de confirmation) n'est généralement pas utilisée.
        """
        # La validation est effectuée par Pydantic grâce à l'injection de type.
        # On pourrait ajouter une logique supplémentaire ici si nécessaire.
        return f"Validation réussie, {len(fallacies)} sophisme(s) identifié(s)."