# -*- coding: utf-8 -*-
"""
Utilitaires pour comparer différents ensembles de résultats d'analyse rhétorique.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def compare_rhetorical_analyses(
    advanced_results: Dict[str, Any],
    base_results: Optional[Dict[str, Any]],
    extract_name: str = "N/A",
) -> Dict[str, Any]:
    """
    Compare les résultats d'une analyse rhétorique avancée avec ceux d'une analyse de base,
    potentiellement pour un extrait spécifique.

    Cette fonction extrait et compare le nombre et les types de sophismes détectés,
    les scores de cohérence, et fournit une note qualitative sur les améliorations.

    :param advanced_results: Dictionnaire contenant les résultats de l'analyse avancée.
                             Attend des clés comme "analyses" -> "contextual_fallacies" (ou "fallacy_detection")
                             et "analyses" -> "rhetorical_results" -> "coherence_analysis" (ou "coherence_evaluation").
    :type advanced_results: Dict[str, Any]
    :param base_results: Dictionnaire optionnel contenant les résultats de l'analyse de base.
                         Structure similaire attendue si fourni.
    :type base_results: Optional[Dict[str, Any]]
    :param extract_name: Nom de l'extrait analysé, pour le logging et le contexte.
    :type extract_name: str
    :return: Un dictionnaire contenant la comparaison détaillée (avec timestamp, comparaison
             des sophismes, de la cohérence, et globale) ou un dictionnaire d'erreur.
    :rtype: Dict[str, Any]
    """
    logger.info(f"Début de la comparaison des analyses pour l'extrait: {extract_name}")

    if not isinstance(advanced_results, dict):
        logger.error(
            f"Résultats avancés invalides pour '{extract_name}'. Attendu: dict, Reçu: {type(advanced_results)}"
        )
        return {
            "error": f"Résultats avancés invalides pour '{extract_name}'.",
            "timestamp": datetime.now().isoformat(),
            "extract_name": extract_name,
        }

    if base_results is not None and not isinstance(base_results, dict):
        logger.error(
            f"Résultats de base invalides pour '{extract_name}'. Attendu: dict, Reçu: {type(base_results)}"
        )
        # On pourrait continuer avec advanced_results seuls, mais pour une comparaison, c'est un problème.
        # Pour l'instant, on retourne une erreur si base_results est fourni mais invalide.
        return {
            "error": f"Résultats de base invalides pour '{extract_name}'.",
            "timestamp": datetime.now().isoformat(),
            "extract_name": extract_name,
        }

    comparison: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "extract_name": extract_name,
        "fallacy_detection_comparison": {},
        "coherence_analysis_comparison": {},
        "overall_comparison": {},
        "comparison_summary": "Initialisation de la comparaison.",
    }

    # Accès sécurisé aux sous-dictionnaires
    adv_analyses = advanced_results.get("analyses", {})
    base_analyses = base_results.get("analyses", {}) if base_results else {}

    # --- Comparaison de la détection des sophismes ---
    adv_fallacies_data = adv_analyses.get(
        "contextual_fallacies", adv_analyses.get("fallacy_detection", {})
    )
    adv_fallacies_list = (
        adv_fallacies_data.get("fallacies", [])
        if isinstance(adv_fallacies_data, dict)
        else (adv_fallacies_data if isinstance(adv_fallacies_data, list) else [])
    )  # Cas où la liste est directe

    # Gestion alternative pour adv_fallacy_count si "contextual_fallacies_count" ou "fallacy_count" existe
    adv_fallacy_count = adv_fallacies_data.get("contextual_fallacies_count")
    if adv_fallacy_count is None:
        adv_fallacy_count = adv_fallacies_data.get("fallacy_count")
    if adv_fallacy_count is None:  # Si toujours None, compter depuis la liste
        adv_arg_results = adv_fallacies_data.get(
            "argument_results", []
        )  # Structure plus ancienne
        if isinstance(adv_arg_results, list) and adv_arg_results:
            adv_fallacy_count = sum(
                len(arg.get("detected_fallacies", []))
                for arg in adv_arg_results
                if isinstance(arg, dict)
            )
        else:  # Fallback sur la longueur de adv_fallacies_list si c'est une liste de sophismes
            adv_fallacy_count = (
                len(adv_fallacies_list) if isinstance(adv_fallacies_list, list) else 0
            )
    adv_fallacy_count = adv_fallacy_count if isinstance(adv_fallacy_count, int) else 0

    adv_fallacy_types = {
        f.get("type")
        for f in adv_fallacies_list
        if isinstance(f, dict) and f.get("type")
    }

    base_fallacy_count = 0
    base_fallacy_types = set()
    newly_identified_fallacies: List[str] = []
    missing_in_advanced: List[str] = []
    common_fallacies: List[str] = []

    if base_results:
        base_fallacies_data = base_analyses.get(
            "contextual_fallacies", base_analyses.get("fallacy_detection", {})
        )
        base_fallacies_list = (
            base_fallacies_data.get("fallacies", [])
            if isinstance(base_fallacies_data, dict)
            else (base_fallacies_data if isinstance(base_fallacies_data, list) else [])
        )

        base_fallacy_count = base_fallacies_data.get("contextual_fallacies_count")
        if base_fallacy_count is None:
            base_fallacy_count = base_fallacies_data.get("fallacy_count")
        if base_fallacy_count is None:
            base_arg_results = base_fallacies_data.get("argument_results", [])
            if isinstance(base_arg_results, list) and base_arg_results:
                base_fallacy_count = sum(
                    len(arg.get("detected_fallacies", []))
                    for arg in base_arg_results
                    if isinstance(arg, dict)
                )
            else:
                base_fallacy_count = (
                    len(base_fallacies_list)
                    if isinstance(base_fallacies_list, list)
                    else 0
                )
        base_fallacy_count = (
            base_fallacy_count if isinstance(base_fallacy_count, int) else 0
        )

        base_fallacy_types = {
            f.get("type")
            for f in base_fallacies_list
            if isinstance(f, dict) and f.get("type")
        }

        newly_identified_fallacies = sorted(
            list(adv_fallacy_types - base_fallacy_types)
        )
        missing_in_advanced = sorted(list(base_fallacy_types - adv_fallacy_types))
        common_fallacies = sorted(
            list(adv_fallacy_types.intersection(base_fallacy_types))
        )
    else:  # Si base_results n'est pas fourni
        newly_identified_fallacies = sorted(list(adv_fallacy_types))

    comparison["fallacy_detection_comparison"] = {
        "advanced_fallacy_count": adv_fallacy_count,
        "base_fallacy_count": base_fallacy_count if base_results is not None else None,
        "difference": adv_fallacy_count - base_fallacy_count if base_results else None,
        "advanced_fallacy_types": sorted(list(adv_fallacy_types)),
        "base_fallacy_types": (
            sorted(list(base_fallacy_types)) if base_results else None
        ),
        "newly_identified_in_advanced": newly_identified_fallacies,
        "missing_from_advanced_vs_base": missing_in_advanced if base_results else None,
        "common_fallacies": common_fallacies if base_results else None,
        "note": "Comparaison des sophismes détectés.",
    }

    # --- Comparer l'analyse de cohérence ---
    adv_coherence = adv_analyses.get("rhetorical_results", {}).get(
        "coherence_analysis", adv_analyses.get("coherence_evaluation", {})
    )
    overall_coherence_value = (
        adv_coherence.get("overall_coherence")
        if isinstance(adv_coherence, dict)
        else None
    )
    adv_coherence_score_data = (
        overall_coherence_value if isinstance(overall_coherence_value, dict) else {}
    )
    adv_coherence_score = adv_coherence_score_data.get(
        "score", adv_coherence.get("score", 0.0)
    )  # Fallback
    adv_coherence_score = (
        adv_coherence_score if isinstance(adv_coherence_score, (int, float)) else 0.0
    )
    adv_coherence_level = adv_coherence_score_data.get(
        "level", adv_coherence.get("level", "N/A")
    )

    base_coherence_score = None
    base_coherence_level = None
    coherence_diff = None

    if base_results is not None:
        base_coherence = base_analyses.get(
            "argument_coherence", base_analyses.get("coherence_evaluation", {})
        )
        base_coherence_score_data = (
            base_coherence.get("overall_coherence", {})
            if isinstance(base_coherence, dict)
            else {}
        )
        base_coherence_score = base_coherence_score_data.get(
            "score", base_coherence.get("score", 0.0)
        )
        base_coherence_score = (
            base_coherence_score
            if isinstance(base_coherence_score, (int, float))
            else 0.0
        )
        base_coherence_level = base_coherence_score_data.get(
            "level", base_coherence.get("level", "N/A")
        )
        coherence_diff = adv_coherence_score - base_coherence_score

    comparison["coherence_analysis_comparison"] = {
        "advanced_coherence_score": adv_coherence_score,
        "base_coherence_score": base_coherence_score,
        "difference": coherence_diff,
        "advanced_coherence_level": adv_coherence_level,
        "base_coherence_level": base_coherence_level,
    }

    # --- Comparaison globale et résumé textuel ---
    adv_overall_analysis = adv_analyses.get("rhetorical_results", {}).get(
        "overall_analysis", {}
    )
    adv_quality = adv_overall_analysis.get("rhetorical_quality", 0.0)
    adv_quality = adv_quality if isinstance(adv_quality, (int, float)) else 0.0

    comparison["overall_comparison"] = {
        "advanced_analysis_depth": adv_overall_analysis.get("analysis_depth", "Élevée"),
        "base_analysis_depth": (
            base_analyses.get("analysis_depth", "Modérée")
            if base_results is not None
            else None
        ),
        "advanced_quality_score": adv_quality,
        "key_improvements_with_advanced": [
            "Détection potentielle de sophismes plus complexes ou contextuels.",
            "Évaluation possible de la gravité des sophismes.",
            "Analyse contextuelle potentiellement plus approfondie.",
            "Recommandations potentiellement plus détaillées et ciblées.",
        ],
    }

    summary_parts = []
    if base_results:
        if adv_fallacy_count > base_fallacy_count:
            summary_parts.append(
                f"L'analyse avancée a identifié plus de sophismes ({adv_fallacy_count} vs {base_fallacy_count})."
            )
        elif adv_fallacy_count < base_fallacy_count:
            summary_parts.append(
                f"L'analyse de base a identifié plus de sophismes ({base_fallacy_count} vs {adv_fallacy_count})."
            )
        else:
            summary_parts.append(
                f"Les deux analyses ont identifié le même nombre de sophismes ({adv_fallacy_count})."
            )

        if newly_identified_fallacies:
            summary_parts.append(
                f"Nouveaux sophismes dans l'avancée: {', '.join(newly_identified_fallacies)}."
            )
        if missing_in_advanced:
            summary_parts.append(
                f"Sophismes de base non trouvés dans l'avancée: {', '.join(missing_in_advanced)}."
            )
    else:
        summary_parts.append(
            f"Analyse avancée: {adv_fallacy_count} sophisme(s) identifié(s) ({', '.join(newly_identified_fallacies) if newly_identified_fallacies else 'aucun type spécifique listé'})."
        )
        summary_parts.append(
            "Résultats de base non fournis pour comparaison directe des sophismes."
        )

    comparison["comparison_summary"] = (
        " ".join(summary_parts)
        if summary_parts
        else "Pas de différences notables ou données insuffisantes pour un résumé."
    )

    logger.debug(f"Comparaison terminée pour '{extract_name}': {comparison}")
    return comparison
