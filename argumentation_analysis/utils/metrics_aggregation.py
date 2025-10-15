#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaire pour l'agrégation des métriques de performance des agents.
"""

import logging
from typing import Dict, List, Any

# Import des fonctions des modules frères
from .metrics_extraction import (
    count_fallacies_in_results,
    extract_confidence_scores_from_results,
    extract_execution_time_from_results,
    analyze_contextual_richness_from_results,
    evaluate_coherence_relevance_from_results,
    analyze_result_complexity_from_results,
)
from .error_estimation import estimate_false_positives_negatives_rates

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def generate_performance_metrics_for_agents(
    base_results: List[Dict[str, Any]], advanced_results: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    Génère un dictionnaire de métriques de performance agrégées pour différents agents/types d'analyse.

    Args:
        base_results (List[Dict[str, Any]]): Liste des résultats d'analyse de base.
        advanced_results (List[Dict[str, Any]]): Liste des résultats d'analyse avancée.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionnaire des métriques de performance.
                                     Clé externe: nom de l'agent/type d'analyse.
                                     Clé interne: nom de la métrique (ex: "fallacy_count", "confidence").
                                     Valeur: valeur de la métrique.
    """
    metrics: Dict[str, Dict[str, Any]] = {
        "base_contextual": {},
        "base_coherence": {},
        "base_semantic": {},
        "advanced_contextual": {},
        "advanced_complex": {},
        "advanced_severity": {},
        "advanced_rhetorical": {},
        "advanced_coherence": {},  # Ajout de l'agent manquant
    }

    # 1. Nombre de sophismes détectés (moyenne par extrait)
    base_fallacy_counts_by_extract = count_fallacies_in_results(base_results)
    adv_fallacy_counts_by_extract = count_fallacies_in_results(advanced_results)

    agent_types_for_fallacies = {
        "base_contextual": [
            d.get("base_contextual", 0)
            for d in base_fallacy_counts_by_extract.values()
            if d.get("base_contextual") is not None
        ],
        "advanced_contextual": [
            d.get("advanced_contextual", 0)
            for d in adv_fallacy_counts_by_extract.values()
            if d.get("advanced_contextual") is not None
        ],
        "advanced_complex": [
            d.get("advanced_complex", 0)
            for d in adv_fallacy_counts_by_extract.values()
            if d.get("advanced_complex") is not None
        ],
    }
    for agent, counts_list in agent_types_for_fallacies.items():
        metrics[agent]["fallacy_count"] = (
            sum(counts_list) / len(counts_list) if counts_list else 0.0
        )

    # 2. Scores de confiance moyens
    base_conf_by_extract = extract_confidence_scores_from_results(base_results)
    adv_conf_by_extract = extract_confidence_scores_from_results(advanced_results)

    agent_types_for_confidence = {
        "base_coherence": [
            d.get("base_coherence", 0.0)
            for d in base_conf_by_extract.values()
            if d.get("base_coherence") is not None
        ],
        "advanced_rhetorical": [
            d.get("advanced_rhetorical", 0.0)
            for d in adv_conf_by_extract.values()
            if d.get("advanced_rhetorical") is not None
        ],
        "advanced_coherence": [
            d.get("advanced_coherence", 0.0)
            for d in adv_conf_by_extract.values()
            if d.get("advanced_coherence") is not None
        ],
        "advanced_severity": [
            d.get("advanced_severity", 0.0)
            for d in adv_conf_by_extract.values()
            if d.get("advanced_severity") is not None
        ],
    }
    for agent, scores_list in agent_types_for_confidence.items():
        metrics[agent]["confidence"] = (
            sum(scores_list) / len(scores_list) if scores_list else 0.0
        )

    # 3. Taux de faux positifs/négatifs estimés
    error_rate_estimates = estimate_false_positives_negatives_rates(
        base_results, advanced_results
    )
    for agent, rates in error_rate_estimates.items():
        if agent in metrics:
            metrics[agent]["false_positive_rate"] = rates.get(
                "false_positive_rate", 0.0
            )
            metrics[agent]["false_negative_rate"] = rates.get(
                "false_negative_rate", 0.0
            )

    # 4. Temps d'exécution moyen (par type d'analyse)
    base_exec_times_by_extract = extract_execution_time_from_results(base_results)
    adv_exec_times_by_extract = extract_execution_time_from_results(advanced_results)

    aggregated_exec_times: Dict[str, List[float]] = {key: [] for key in metrics.keys()}

    for extract_times in base_exec_times_by_extract.values():
        if extract_times.get("contextual_fallacies") is not None:
            aggregated_exec_times["base_contextual"].append(
                extract_times["contextual_fallacies"]
            )
        if extract_times.get("argument_coherence") is not None:
            aggregated_exec_times["base_coherence"].append(
                extract_times["argument_coherence"]
            )
        if extract_times.get("semantic_analysis") is not None:
            aggregated_exec_times["base_semantic"].append(
                extract_times["semantic_analysis"]
            )

    for extract_times in adv_exec_times_by_extract.values():
        if extract_times.get("contextual_fallacies") is not None:
            aggregated_exec_times["advanced_contextual"].append(
                extract_times["contextual_fallacies"]
            )
        if extract_times.get("complex_fallacies") is not None:
            aggregated_exec_times["advanced_complex"].append(
                extract_times["complex_fallacies"]
            )
        if extract_times.get("fallacy_severity") is not None:
            aggregated_exec_times["advanced_severity"].append(
                extract_times["fallacy_severity"]
            )
        if extract_times.get("rhetorical_results") is not None:
            aggregated_exec_times["advanced_rhetorical"].append(
                extract_times["rhetorical_results"]
            )

    for agent, times_list in aggregated_exec_times.items():
        metrics[agent]["execution_time"] = (
            sum(times_list) / len(times_list) if times_list else 0.0
        )

    # 5. Richesse contextuelle moyenne
    base_richness_by_extract = analyze_contextual_richness_from_results(base_results)
    adv_richness_by_extract = analyze_contextual_richness_from_results(advanced_results)

    agent_types_for_richness = {
        "base_contextual": [
            d.get("base_contextual", 0.0)
            for d in base_richness_by_extract.values()
            if d.get("base_contextual") is not None
        ],
        "advanced_contextual": [
            d.get("advanced_contextual", 0.0)
            for d in adv_richness_by_extract.values()
            if d.get("advanced_contextual") is not None
        ],
        "advanced_rhetorical": [
            d.get("advanced_rhetorical", 0.0)
            for d in adv_richness_by_extract.values()
            if d.get("advanced_rhetorical") is not None
        ],
    }
    for agent, richness_list in agent_types_for_richness.items():
        metrics[agent]["contextual_richness"] = (
            sum(richness_list) / len(richness_list) if richness_list else 0.0
        )

    # 6. Pertinence des évaluations de cohérence moyenne
    base_relevance_by_extract = evaluate_coherence_relevance_from_results(base_results)
    adv_relevance_by_extract = evaluate_coherence_relevance_from_results(
        advanced_results
    )

    agent_types_for_relevance = {
        "base_coherence": [
            d.get("base_coherence", 0.0)
            for d in base_relevance_by_extract.values()
            if d.get("base_coherence") is not None
        ],
        "advanced_coherence": [
            d.get("advanced_coherence", 0.0)
            for d in adv_relevance_by_extract.values()
            if d.get("advanced_coherence") is not None
        ],
        "advanced_rhetorical": [
            d.get("advanced_recommendations", 0.0)
            for d in adv_relevance_by_extract.values()
            if d.get("advanced_recommendations") is not None
        ],
    }
    for agent, relevance_list in agent_types_for_relevance.items():
        if agent == "advanced_rhetorical":
            metrics[agent]["recommendation_relevance"] = (
                sum(relevance_list) / len(relevance_list) if relevance_list else 0.0
            )
        else:
            metrics[agent]["relevance"] = (
                sum(relevance_list) / len(relevance_list) if relevance_list else 0.0
            )

    # 7. Complexité moyenne des résultats
    base_complexity_by_extract = analyze_result_complexity_from_results(base_results)
    adv_complexity_by_extract = analyze_result_complexity_from_results(advanced_results)

    aggregated_complexity: Dict[str, List[float]] = {key: [] for key in metrics.keys()}

    for extract_complexities in base_complexity_by_extract.values():
        if extract_complexities.get("contextual_fallacies") is not None:
            aggregated_complexity["base_contextual"].append(
                extract_complexities["contextual_fallacies"]
            )
        if extract_complexities.get("argument_coherence") is not None:
            aggregated_complexity["base_coherence"].append(
                extract_complexities["argument_coherence"]
            )
        if extract_complexities.get("semantic_analysis") is not None:
            aggregated_complexity["base_semantic"].append(
                extract_complexities["semantic_analysis"]
            )

    for extract_complexities in adv_complexity_by_extract.values():
        if extract_complexities.get("contextual_fallacies") is not None:
            aggregated_complexity["advanced_contextual"].append(
                extract_complexities["contextual_fallacies"]
            )
        if extract_complexities.get("complex_fallacies") is not None:
            aggregated_complexity["advanced_complex"].append(
                extract_complexities["complex_fallacies"]
            )
        if extract_complexities.get("fallacy_severity") is not None:
            aggregated_complexity["advanced_severity"].append(
                extract_complexities["fallacy_severity"]
            )
        if extract_complexities.get("rhetorical_results") is not None:
            aggregated_complexity["advanced_rhetorical"].append(
                extract_complexities["rhetorical_results"]
            )

    for agent, complexity_list in aggregated_complexity.items():
        metrics[agent]["complexity"] = (
            sum(complexity_list) / len(complexity_list) if complexity_list else 0.0
        )

    logger.info("Génération des métriques de performance agrégées terminée.")
    return metrics
