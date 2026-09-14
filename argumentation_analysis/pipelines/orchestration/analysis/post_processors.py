#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Post-traitement final des résultats d'orchestration — une fonction libre.

Ce module ne définit **aucune classe de post-processeur**. Il porte
`post_process_orchestration_results` : elle injecte `results["recommendations"]`
(seuils `overall_score > 0.7`) puis le `communication_log`.

La docstring d'origine annonçait cinq classes (`ResultFormattingProcessor`,
`ReportGenerationProcessor`, `DatabaseStorageProcessor`,
`RecommendationProcessor`, `AlertingProcessor`) et un exemple d'appel
(`engine.run_analysis()`, `engine.run_post_processing([...])`) sur un
`ExecutionEngine` — aucun de ces symboles n'existe dans ce dépôt. Elle est
retirée, pas réécrite (#2110).
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def post_process_orchestration_results(
    pipeline: "UnifiedOrchestrationPipeline", results: Dict[str, Any]
) -> Dict[str, Any]:
    """Post-traite les résultats d'orchestration."""
    try:
        recommendations = []

        hierarchical_coord = results.get("hierarchical_coordination", {})
        if hierarchical_coord.get("overall_score", 0) > 0.7:
            recommendations.append("Architecture hiérarchique très performante")

        specialized = results.get("specialized_orchestration", {})
        if specialized.get("results", {}).get("status") == "completed":
            orchestrator_used = specialized.get("orchestrator_used", "inconnu")
            recommendations.append(
                f"Orchestrateur spécialisé '{orchestrator_used}' efficace"
            )

        if not recommendations:
            recommendations.append(
                "Analyse orchestrée complétée - examen des résultats recommandé"
            )

        results["recommendations"] = recommendations

        if pipeline.middleware:
            results["communication_log"] = pipeline._get_communication_log()

    except Exception as e:
        logger.error(f"Erreur post-traitement: {e}")
        results["post_processing_error"] = str(e)

    return results
