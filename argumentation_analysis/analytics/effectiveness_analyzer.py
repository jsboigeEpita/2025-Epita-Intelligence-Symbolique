# -*- coding: utf-8 -*-
"""
Ce module fournit des fonctions pour analyser l'efficacité des agents
d'analyse d'argumentation.
"""

import logging
from typing import List, Dict, Any, Tuple  # Ajout de Tuple

logger = logging.getLogger(__name__)


def analyze_agent_effectiveness(
    corpus_results: List[Dict[str, Any]], corpus_name: str = "N/A"
) -> Dict[str, Any]:
    """
    Analyse l'efficacité des différents agents sur un corpus de résultats donné.

    Cette fonction évalue des métriques comme le nombre de sophismes détectés,
    la pertinence des analyses, etc., pour chaque agent ayant traité le corpus.
    Elle peut retourner des statistiques agrégées et identifier le "meilleur" agent
    pour ce corpus basé sur des critères prédéfinis (simplifiés ici).

    :param corpus_results: Une liste de résultats d'analyse pour un corpus spécifique.
                           Chaque résultat doit contenir des informations sur l'agent
                           (par exemple, via 'agent_name') et les métriques d'analyse
                           (par exemple, 'fallacies', 'confidence_score').
    :type corpus_results: List[Dict[str, Any]]
    :param corpus_name: Nom du corpus analysé, pour le logging et le rapport.
    :type corpus_name: str
    :return: Un dictionnaire résumant l'efficacité des agents sur le corpus.
             Exemple de structure :
             {
                 "corpus_name": "...",
                 "total_results_analyzed": X,
                 "agents_evaluated": ["AgentA", "AgentB"],
                 "effectiveness_scores": {
                     "AgentA": 0.75,
                     "AgentB": 0.82
                 },
                 "fallacy_detection_by_agent": {
                     "AgentA": {"total": Y, "types": {...}},
                     "AgentB": {"total": Z, "types": {...}}
                 },
                 "best_agent_overall": "AgentB",
                 "recommendations": ["AgentB est recommandé pour ce type de corpus."]
             }
    :rtype: Dict[str, Any]
    """
    logger.info(
        f"Analyse de l'efficacité des agents pour le corpus: {corpus_name} ({len(corpus_results)} résultats)"
    )

    effectiveness_summary: Dict[str, Any] = {
        "corpus_name": corpus_name,
        "total_results_analyzed": len(corpus_results),
        "agents_evaluated": [],
        "effectiveness_scores": {},  # score simple basé sur nb sophismes et confiance
        "fallacy_detection_by_agent": {},
        "best_agent_overall": "N/A",
        "recommendations": [],
    }

    # Collecter les données par agent
    results_by_agent: Dict[str, List[Dict[str, Any]]] = {}
    for res in corpus_results:
        agent_name = res.get(
            "agent_name", res.get("source_name", "UnknownAgent")
        )  # source_name comme fallback
        results_by_agent.setdefault(agent_name, []).append(res)

    effectiveness_summary["agents_evaluated"] = sorted(list(results_by_agent.keys()))

    max_effectiveness_score = -1.0

    for agent_name, agent_results in results_by_agent.items():
        num_results = len(agent_results)
        total_fallacies = 0
        sum_confidence = 0.0
        fallacy_types_count: Dict[str, int] = {}

        for res in agent_results:
            analysis_data = res.get(
                "analysis", res
            )  # Si 'analysis' n'est pas là, prendre res directement

            fallacies = analysis_data.get("fallacies", [])
            if isinstance(fallacies, list):
                total_fallacies += len(fallacies)
                for f in fallacies:
                    if isinstance(f, dict):
                        f_type = f.get("fallacy_type", f.get("type", "unknown"))
                        fallacy_types_count[f_type] = (
                            fallacy_types_count.get(f_type, 0) + 1
                        )

            confidence = analysis_data.get(
                "confidence_score", analysis_data.get("overall_confidence", 0.0)
            )
            if isinstance(confidence, (int, float)):
                sum_confidence += confidence

        avg_confidence = (sum_confidence / num_results) if num_results > 0 else 0.0

        # Score d'efficacité simple: nb moyen de sophismes * confiance moyenne
        # (Ceci est une heuristique très basique et devrait être affinée)
        avg_fallacies = (total_fallacies / num_results) if num_results > 0 else 0.0
        current_effectiveness_score = (
            avg_fallacies * avg_confidence * 10
        )  # Facteur d'échelle arbitraire

        effectiveness_summary["effectiveness_scores"][agent_name] = round(
            current_effectiveness_score, 2
        )
        effectiveness_summary["fallacy_detection_by_agent"][agent_name] = {
            "total_fallacies_detected": total_fallacies,
            "average_fallacies_per_item": round(avg_fallacies, 2),
            "average_confidence": round(avg_confidence, 2),
            "fallacy_types_summary": fallacy_types_count,
        }

        if current_effectiveness_score > max_effectiveness_score:
            max_effectiveness_score = current_effectiveness_score
            effectiveness_summary["best_agent_overall"] = agent_name

    if effectiveness_summary["best_agent_overall"] != "N/A":
        effectiveness_summary["recommendations"].append(
            f"L'agent '{effectiveness_summary['best_agent_overall']}' semble le plus efficace globalement pour le corpus '{corpus_name}' "
            f"basé sur une combinaison de détection de sophismes et de confiance (score: {max_effectiveness_score:.2f})."
        )
    else:
        effectiveness_summary["recommendations"].append(
            f"Aucun agent ne se distingue clairement pour le corpus '{corpus_name}' avec les métriques actuelles."
        )

    logger.info(
        f"Analyse d'efficacité pour {corpus_name} terminée. Meilleur agent (simpliste): {effectiveness_summary['best_agent_overall']}"
    )
    return effectiveness_summary
