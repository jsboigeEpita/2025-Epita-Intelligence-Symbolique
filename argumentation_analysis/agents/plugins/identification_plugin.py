# Fichier: argumentation_analysis/agents/plugins/identification_plugin.py
from typing import List
from pydantic import BaseModel, Field
from semantic_kernel.functions.kernel_function_decorator import kernel_function

class IdentifiedFallacy(BaseModel):
    """Modèle de données pour un sophisme identifié."""
    fallacy_type: str = Field(..., description="Le type de sophisme, ex: 'Ad Hominem', 'stolen-concept'.")
    explanation: str = Field(..., description="L'explication de la raison pour laquelle il s'agit de ce sophisme.")
    problematic_quote: str = Field(..., description="La citation exacte du texte qui contient le sophisme.")

class IdentificationPlugin:
    """Plugin dédié à l'identification des sophismes."""

    @kernel_function(
        name="identify_fallacies",
        description="Identifie et liste les sophismes informels présents dans un texte donné.",
    )
    def identify_fallacies(self, fallacies: List[IdentifiedFallacy]) -> List[IdentifiedFallacy]:
        """
        Cette méthode est un 'outil' pour le Kernel. Le LLM est forcé de l'appeler,
        validant de fait la structure des données via les types Pydantic.
        """
        return fallacies