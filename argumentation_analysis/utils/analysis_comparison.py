# -*- coding: utf-8 -*-
"""
Utilitaires pour comparer différents ensembles de résultats d'analyse rhétorique.
"""

import logging
from typing import Dict, Any, List, Optional # Ajout de List et Optional

logger = logging.getLogger(__name__)

def compare_rhetorical_analyses(
    advanced_results: Dict[str, Any],
    base_results: Optional[Dict[str, Any]], # Rendre base_results optionnel
    extract_name: str = "N/A" # Ajouter un nom d'extrait pour le contexte
) -> Dict[str, Any]:
    """
    Compare les résultats d'une analyse rhétorique avancée avec ceux d'une analyse de base
    pour un extrait spécifique.

    Cette fonction identifie les différences et similitudes clés entre les deux ensembles
    de résultats. Elle peut par exemple comparer le nombre de sophismes détectés,
    les types de sophismes, les scores de confiance, la richesse contextuelle, etc.

    :param advanced_results: Dictionnaire contenant les résultats de l'analyse avancée
                             pour un extrait.
    :type advanced_results: Dict[str, Any]
    :param base_results: Dictionnaire contenant les résultats de l'analyse de base
                         pour le même extrait. Peut être None si non disponible.
    :type base_results: Optional[Dict[str, Any]]
    :param extract_name: Nom de l'extrait analysé, pour le logging.
    :type extract_name: str
    :return: Un dictionnaire résumant la comparaison. La structure exacte de ce
             dictionnaire dépendra des métriques spécifiques comparées.
             Exemple de structure possible :
             {
                 "extract_name": "...",
                 "comparison_summary": "Advanced analysis identified more fallacies.",
                 "advanced_fallacy_count": 5,
                 "base_fallacy_count": 2,
                 "newly_identified_fallacies": ["sophisme_A", "sophisme_B"],
                 "missing_in_advanced": ["sophisme_C"],
                 "confidence_score_diff": 0.15
             }
    :rtype: Dict[str, Any]
    """
    logger.info(f"Comparaison des analyses pour l'extrait: {extract_name}")
    comparison_output: Dict[str, Any] = {
        "extract_name": extract_name,
        "comparison_summary": "Comparaison non implémentée en détail.",
        "advanced_data_present": bool(advanced_results),
        "base_data_present": bool(base_results)
    }

    if not advanced_results:
        logger.warning(f"Aucun résultat avancé fourni pour l'extrait {extract_name}. Comparaison limitée.")
        comparison_output["comparison_summary"] = "Résultats avancés manquants."
        return comparison_output

    if not base_results:
        logger.info(f"Aucun résultat de base fourni pour l'extrait {extract_name}. Pas de comparaison directe possible.")
        comparison_output["comparison_summary"] = "Résultats de base manquants, pas de comparaison directe."
        # On pourrait quand même inclure des stats sur les résultats avancés seuls
        adv_fallacies = advanced_results.get("fallacies", [])
        comparison_output["advanced_fallacy_count"] = len(adv_fallacies)
        comparison_output["advanced_fallacies_detected"] = [f.get("type", "N/A") for f in adv_fallacies]
        return comparison_output

    # Exemple de comparaison simple : nombre de sophismes
    adv_fallacies = advanced_results.get("fallacies", [])
    base_fallacies = base_results.get("fallacies", [])
    
    comparison_output["advanced_fallacy_count"] = len(adv_fallacies)
    comparison_output["base_fallacy_count"] = len(base_fallacies)

    adv_fallacy_types = {f.get("type") for f in adv_fallacies if f.get("type")}
    base_fallacy_types = {f.get("type") for f in base_fallacies if f.get("type")}

    comparison_output["newly_identified_fallacies"] = sorted(list(adv_fallacy_types - base_fallacy_types))
    comparison_output["missing_in_advanced"] = sorted(list(base_fallacy_types - adv_fallacy_types))
    comparison_output["common_fallacies"] = sorted(list(adv_fallacy_types.intersection(base_fallacy_types)))

    summary_parts = []
    if comparison_output["advanced_fallacy_count"] > comparison_output["base_fallacy_count"]:
        summary_parts.append(f"L'analyse avancée a identifié plus de sophismes ({comparison_output['advanced_fallacy_count']} vs {comparison_output['base_fallacy_count']}).")
    elif comparison_output["advanced_fallacy_count"] < comparison_output["base_fallacy_count"]:
        summary_parts.append(f"L'analyse de base a identifié plus de sophismes ({comparison_output['base_fallacy_count']} vs {comparison_output['advanced_fallacy_count']}).")
    else:
        summary_parts.append(f"Les deux analyses ont identifié le même nombre de sophismes ({comparison_output['advanced_fallacy_count']}).")

    if comparison_output["newly_identified_fallacies"]:
        summary_parts.append(f"Nouveaux sophismes dans l'avancée: {', '.join(comparison_output['newly_identified_fallacies'])}.")
    if comparison_output["missing_in_advanced"]:
        summary_parts.append(f"Sophismes de base non trouvés dans l'avancée: {', '.join(comparison_output['missing_in_advanced'])}.")

    comparison_output["comparison_summary"] = " ".join(summary_parts) if summary_parts else "Pas de différences notables dans le nombre ou les types de sophismes."
    
    # D'autres métriques pourraient être comparées ici :
    # - Scores de confiance moyens
    # - Richesse contextuelle
    # - Sévérité des sophismes
    # - Etc.

    logger.info(f"Résumé de la comparaison pour {extract_name}: {comparison_output['comparison_summary']}")
    return comparison_output