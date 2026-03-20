# Fichier: argumentation_analysis/agents/plugins/project_management_plugin.py
from typing import List
from pydantic import BaseModel, Field
from semantic_kernel.functions.kernel_function_decorator import kernel_function


class AnalysisReport(BaseModel):
    """Modèle de données pour le rapport final d'analyse."""

    final_summary: str = Field(..., description="Un résumé de l'analyse effectuée.")
    # Ce modèle sera enrichi dans les futurs WO pour agréger les résultats.


class ProjectPlan(BaseModel):
    """Modèle de données pour un plan de projet structuré."""

    tasks: List[str] = Field(
        ..., description="La liste des tâches à effectuer pour le projet."
    )


class ProjectManagementPlugin:
    """Plugin pour exposer les outils de gestion de projet au Kernel."""

    @kernel_function(
        name="create_project_plan",
        description="Crée un plan de projet détaillé basé sur un objectif.",
    )
    def create_project_plan(self, tasks: List[str]) -> str:
        """
        Outil qui force la sortie structurée pour un plan de projet.
        Le LLM est contraint de fournir une liste de tâches, qui est validée
        par Pydantic.
        """
        # La validation est effectuée par Pydantic grâce à l'injection de type.
        return f"Plan de projet validé avec succès, contenant {len(tasks)} tâches."

    @kernel_function(
        name="generate_analysis_report",
        description="Génère un rapport d'analyse structuré.",
    )
    def generate_analysis_report(self, summary: str) -> str:
        """
        Outil qui génère un rapport d'analyse structuré.
        Le LLM est contraint de fournir un résumé, qui est validé
        par Pydantic.
        """
        # Pour l'instant, nous ne faisons que valider la présence du résumé.
        # La logique d'agrégation sera ajoutée plus tard.
        return f"Rapport généré avec succès. Sommaire : '{summary[:50]}...'"
