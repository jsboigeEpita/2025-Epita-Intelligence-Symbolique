#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitaires pour le traitement des données et la génération de rapports d'analyse rhétorique.
Ce module sert maintenant de point d'entrée principal pour les fonctionnalités de reporting,
qui sont implémentées dans des sous-modules spécialisés.
"""

import logging

# Importations depuis les nouveaux sous-modules
from .data_loader import load_results_from_json
from .metrics_extraction import (
    extract_execution_time_from_results,
    count_fallacies_in_results,
    extract_confidence_scores_from_results,
    analyze_contextual_richness_from_results,
    evaluate_coherence_relevance_from_results,
    _calculate_obj_complexity, # Noter que _calculate_obj_complexity est interne
    analyze_result_complexity_from_results
)
from .error_estimation import estimate_false_positives_negatives_rates
from .metrics_aggregation import generate_performance_metrics_for_agents
from .visualization_generator import generate_performance_visualizations, VISUALIZATION_LIBS_AVAILABLE
from .report_generator import generate_markdown_performance_report

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Réexportation explicite pour rendre les fonctions accessibles via ce module
__all__ = [
    "load_results_from_json",
    "extract_execution_time_from_results",
    "count_fallacies_in_results",
    "extract_confidence_scores_from_results",
    "estimate_false_positives_negatives_rates",
    "analyze_contextual_richness_from_results",
    "evaluate_coherence_relevance_from_results",
    "analyze_result_complexity_from_results",
    # "_calculate_obj_complexity", # Ne pas réexporter les fonctions "privées" sauf si nécessaire
    "generate_performance_metrics_for_agents",
    "generate_performance_visualizations",
    "generate_markdown_performance_report",
    "VISUALIZATION_LIBS_AVAILABLE" # Exporter aussi cette constante
]

logger.info("Module reporting_utils initialisé, fonctions importées depuis les sous-modules.")