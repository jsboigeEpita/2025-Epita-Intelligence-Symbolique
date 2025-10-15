#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Post-Processeurs pour la Finalisation des Pipelines.

Objectif:
    Ce module est dédié aux "post-processeurs" (`PostProcessors`). Ce sont des
    étapes de traitement qui s'exécutent à la toute fin d'un pipeline, une
    fois que toutes les analyses principales (extraction, analyse informelle,
    formelle, etc.) sont terminées. Leur rôle est de préparer les résultats
    finaux pour la présentation, le stockage ou la distribution.

Concept Clé:
    Un post-processeur prend l'état complet et final de l'analyse et effectue
    des opérations de "nettoyage", de formatage, d'enrichissement ou de
    sauvegarde. Contrairement aux processeurs d'analyse, ils ne modifient
    généralement pas les conclusions de l'analyse mais plutôt leur forme.

Post-Processeurs Principaux (Exemples cibles):
    -   `ResultFormattingProcessor`:
        Met en forme les données brutes de l'analyse en formats lisibles
        comme JSON, Markdown, ou un résumé textuel pour la console.
    -   `ReportGenerationProcessor`:
        Génère des artéfacts complexes comme des rapports PDF ou des pages
        HTML interactives à partir des résultats.
    -   `DatabaseStorageProcessor`:
        Prend les résultats finaux et les insère dans une base de données (ex:
        PostgreSQL, MongoDB) pour archivage et analyse ultérieure.
    -   `RecommendationProcessor`:
        Passe en revue l'ensemble des résultats (sophismes, cohérence logique,
        etc.) pour générer une liste finale de recommandations actionnables
        pour l'utilisateur.
    -   `AlertingProcessor`:
        Déclenche des alertes (ex: email, notification Slack) si certains
        seuils sont atteints (ex: plus de 5 sophismes critiques détectés).

Utilisation:
    Les post-processeurs sont généralement invoqués par le moteur d'exécution
    du pipeline (`ExecutionEngine`) après que la boucle principale des
    processeurs d'analyse est terminée.

    Exemple (conceptuel):
    ```python
    engine = ExecutionEngine(state)
    # ... ajout des processeurs d'analyse ...
    await engine.run_analysis()

    # ... exécution des post-processeurs ...
    await engine.run_post_processing([
        RecommendationProcessor(),
        ResultFormattingProcessor(format="json"),
        DatabaseStorageProcessor(db_connection)
    ])
    ```
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
