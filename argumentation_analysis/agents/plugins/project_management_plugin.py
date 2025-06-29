# Fichier: argumentation_analysis/agents/plugins/project_management_plugin.py
from pydantic import BaseModel, Field
from semantic_kernel.functions.kernel_function_decorator import kernel_function

class AnalysisReport(BaseModel):
    """Modèle de données pour le rapport final d'analyse."""
    final_summary: str = Field(..., description="Un résumé de l'analyse effectuée.")
    # Ce modèle sera enrichi dans les futurs WO pour agréger les résultats.

class ProjectManagementPlugin:
    """Plugin pour exposer les outils de gestion de projet au Kernel."""

    @kernel_function(
        name="generate_report",
        description="Génère un rapport final résumant les résultats de l'analyse.",
    )
    def generate_analysis_report(self, summary: str) -> str:
        """
        Outil qui force la sortie structurée pour le rapport final.
        La validation est assurée par l'injection du type Pydantic.
        """
        # Pour l'instant, nous ne faisons que valider la présence du résumé.
        # La logique d'agrégation sera ajoutée plus tard.
        return f"Rapport généré avec succès. Sommaire : '{summary[:50]}...'"