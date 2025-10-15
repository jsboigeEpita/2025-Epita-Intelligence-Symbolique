# Fichier: argumentation_analysis/agents/plugins/aggregation_tool.py

from typing import List, Dict, Any

from ..utils.hybrid_decorator import hybrid_function


class AggregationTool:
    """
    Outil pour agréger et synthétiser les rapports de validation.
    """

    def __init__(self):
        """
        Initialise l'outil d'agrégation.
        """
        print("AggregationTool initialisé.")

    @hybrid_function(
        prompt_template=(
            "À partir des rapports d'analyse de sophismes suivants : \n\n"
            "{{$reports}}\n\n"
            "Rédige un résumé exécutif de 3 à 4 phrases qui met en évidence les sophismes les plus probables et leur impact global sur l'argument. "
            "Ensuite, produis un classement des sophismes identifiés, du plus confiant au moins confiant. "
            "Enfin, fournis une conclusion générale sur la robustesse de l'argument analysé. "
            "Le résultat doit être un JSON contenant les clés 'executive_summary', 'ranked_fallacies' et 'overall_conclusion'."
        )
    )
    async def summarize_reports(
        self,
        reports: List[Dict[str, Any]],
        executive_summary: str,
        ranked_fallacies: List[Dict[str, Any]],
        overall_conclusion: str,
    ) -> Dict[str, Any]:
        """
        Fonction native qui reçoit un résumé, un classement et une conclusion du LLM.

        Args:
            reports: La liste brute des rapports de validation.
            executive_summary: Le résumé généré par le LLM.
            ranked_fallacies: La liste des sophismes classés par le LLM.
            overall_conclusion: La conclusion générale générée par le LLM.

        Returns:
            Un rapport final unifié.
        """
        print(f"Agrégation de {len(reports)} rapports de validation.")

        # Le LLM a déjà fait le gros du travail de synthèse.
        # Cette fonction native peut enrichir le rapport final avec des métadonnées
        # supplémentaires ou des statistiques calculées à partir des rapports bruts.

        average_confidence = 0
        if reports:
            fallacious_reports = [r for r in reports if r.get("is_fallacious")]
            if fallacious_reports:
                average_confidence = sum(
                    r["confidence"] for r in fallacious_reports
                ) / len(fallacious_reports)

        final_report = {
            "executive_summary": executive_summary,
            "ranked_fallacies": ranked_fallacies,
            "overall_conclusion": overall_conclusion,
            "metadata": {
                "total_reports": len(reports),
                "fallacies_found": len(ranked_fallacies),
                "average_confidence_if_fallacious": f"{average_confidence:.2f}",
            },
            "raw_reports": reports,  # Inclure les rapports bruts pour la traçabilité
        }

        print("Rapport d'agrégation final généré.")

        return final_report
