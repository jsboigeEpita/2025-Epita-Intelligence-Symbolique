# -*- coding: utf-8 -*-
"""Utilitaires pour comparer différents résultats d'analyse."""

from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def compare_rhetorical_analyses(
    advanced_results: Dict[str, Any],
    base_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compare les résultats d'une analyse rhétorique avancée avec ceux d'une analyse de base.

    Cette fonction extrait et compare spécifiquement le nombre de sophismes détectés
    et les scores de cohérence entre les deux ensembles de résultats. Elle fournit
    également une note qualitative sur les améliorations potentielles de l'analyse avancée.

    :param advanced_results: Un dictionnaire contenant les résultats de l'analyse avancée.
                             La structure attendue inclut des sous-dictionnaires pour
                             "analyses" -> "contextual_fallacies" (ou "fallacy_detection")
                             et "analyses" -> "rhetorical_results" -> "coherence_analysis"
                             (ou "analyses" -> "coherence_evaluation").
    :type advanced_results: Dict[str, Any]
    :param base_results: Un dictionnaire contenant les résultats de l'analyse de base,
                         avec une structure similaire attendue pour les sophismes et la cohérence.
    :type base_results: Dict[str, Any]
    :return: Un dictionnaire contenant la comparaison détaillée, structuré avec les clés
             "timestamp", "fallacy_detection_comparison", "coherence_analysis_comparison",
             et "overall_comparison". Retourne un dictionnaire d'erreur si les entrées
             sont invalides.
    :rtype: Dict[str, Any]
    """
    if not isinstance(advanced_results, dict) or not isinstance(base_results, dict):
        logger.error("Les résultats avancés et de base doivent être des dictionnaires.")
        return {
            "error": "Entrées invalides pour la comparaison.",
            "timestamp": datetime.now().isoformat()
        }

    logger.info("Comparaison des résultats d'analyse avancée et de base.")
    comparison = {
        "timestamp": datetime.now().isoformat(),
        "fallacy_detection_comparison": {},
        "coherence_analysis_comparison": {},
        "overall_comparison": {}
    }

    # Accès sécurisé aux sous-dictionnaires
    adv_analyses = advanced_results.get("analyses", {}) if isinstance(advanced_results, dict) else {}
    base_analyses = base_results.get("analyses", {}) if isinstance(base_results, dict) else {}

    # Comparer la détection des sophismes
    advanced_fallacies_data = adv_analyses.get("contextual_fallacies", {})
    if not isinstance(advanced_fallacies_data, dict) or not advanced_fallacies_data:
        advanced_fallacies_data = adv_analyses.get("fallacy_detection", {})
    advanced_fallacies_data = advanced_fallacies_data if isinstance(advanced_fallacies_data, dict) else {}


    base_fallacies_data = base_analyses.get("contextual_fallacies", {})
    if not isinstance(base_fallacies_data, dict) or not base_fallacies_data:
        base_fallacies_data = base_analyses.get("fallacy_detection", {})
    base_fallacies_data = base_fallacies_data if isinstance(base_fallacies_data, dict) else {}


    adv_fallacy_count = advanced_fallacies_data.get("contextual_fallacies_count")
    if adv_fallacy_count is None:
        adv_arg_results = advanced_fallacies_data.get("argument_results", [])
        adv_arg_results = adv_arg_results if isinstance(adv_arg_results, list) else []
        adv_fallacy_count = sum(len(arg.get("detected_fallacies", [])) for arg in adv_arg_results if isinstance(arg,dict))
    adv_fallacy_count = adv_fallacy_count if isinstance(adv_fallacy_count, int) else 0


    base_fallacy_count = 0
    base_arg_results = base_fallacies_data.get("argument_results", [])
    base_arg_results = base_arg_results if isinstance(base_arg_results, list) else []
    if base_arg_results:
        base_fallacy_count = sum(len(arg.get("detected_fallacies", [])) for arg in base_arg_results if isinstance(arg,dict))
    else:
        base_fallacy_count = base_fallacies_data.get("fallacy_count", 0)
    base_fallacy_count = base_fallacy_count if isinstance(base_fallacy_count, int) else 0


    comparison["fallacy_detection_comparison"] = {
        "advanced_fallacy_count": adv_fallacy_count,
        "base_fallacy_count": base_fallacy_count,
        "difference": adv_fallacy_count - base_fallacy_count,
        "note": "Comparaison basique du nombre de sophismes."
    }

    # Comparer l'analyse de cohérence
    adv_coherence = adv_analyses.get("rhetorical_results", {}).get("coherence_analysis", {})
    if not isinstance(adv_coherence, dict) or not adv_coherence:
        adv_coherence = adv_analyses.get("coherence_evaluation", {})
    adv_coherence = adv_coherence if isinstance(adv_coherence, dict) else {}


    base_coherence = base_analyses.get("argument_coherence", {})
    if not isinstance(base_coherence, dict) or not base_coherence:
        base_coherence = base_analyses.get("coherence_evaluation", {})
    base_coherence = base_coherence if isinstance(base_coherence, dict) else {}

    
    adv_coherence_score_data = adv_coherence.get("overall_coherence", {})
    adv_coherence_score_data = adv_coherence_score_data if isinstance(adv_coherence_score_data, dict) else {}
    adv_coherence_score = adv_coherence_score_data.get("score")
    if adv_coherence_score is None:
        adv_coherence_score = adv_coherence.get("score", 0.0)
    adv_coherence_score = adv_coherence_score if isinstance(adv_coherence_score, (int, float)) else 0.0

    base_coherence_score_data = base_coherence.get("overall_coherence", {})
    base_coherence_score_data = base_coherence_score_data if isinstance(base_coherence_score_data, dict) else {}
    base_coherence_score = base_coherence_score_data.get("score")
    if base_coherence_score is None:
        base_coherence_score = base_coherence.get("score", 0.0)
    base_coherence_score = base_coherence_score if isinstance(base_coherence_score, (int, float)) else 0.0


    comparison["coherence_analysis_comparison"] = {
        "advanced_coherence_score": adv_coherence_score,
        "base_coherence_score": base_coherence_score,
        "difference": adv_coherence_score - base_coherence_score,
        "advanced_coherence_level": adv_coherence_score_data.get("level", adv_coherence.get("level", "N/A")),
        "base_coherence_level": base_coherence_score_data.get("level", base_coherence.get("level", "N/A"))
    }

    # Comparaison globale
    adv_overall_analysis = adv_analyses.get("rhetorical_results", {}).get("overall_analysis", {})
    adv_overall_analysis = adv_overall_analysis if isinstance(adv_overall_analysis, dict) else {}
    adv_quality = adv_overall_analysis.get("rhetorical_quality", 0.0)
    adv_quality = adv_quality if isinstance(adv_quality, (int, float)) else 0.0
    
    comparison["overall_comparison"] = {
        "advanced_analysis_depth": adv_overall_analysis.get("analysis_depth", "Élevée"),
        "base_analysis_depth": base_analyses.get("analysis_depth", "Modérée"),
        "advanced_quality_score": adv_quality,
        "key_improvements_with_advanced": [
            "Détection potentielle de sophismes plus complexes ou contextuels.",
            "Évaluation possible de la gravité des sophismes.",
            "Analyse contextuelle potentiellement plus approfondie.",
            "Recommandations potentiellement plus détaillées et ciblées."
        ]
    }
    
    logger.debug(f"Comparaison terminée: {comparison}")
    return comparison