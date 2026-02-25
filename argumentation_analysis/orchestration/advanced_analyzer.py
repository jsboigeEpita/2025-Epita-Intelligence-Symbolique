# -*- coding: utf-8 -*-
"""
Ce module contient des fonctions pour orchestrer des analyses rhétoriques avancées.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from argumentation_analysis.plugins.analysis_tools.plugin import AnalysisToolsPlugin
from argumentation_analysis.utils.analysis_comparison import compare_rhetorical_analyses
from argumentation_analysis.utils.data_generation import generate_sample_text

logger = logging.getLogger(__name__)


def analyze_extract_advanced(
    extract_definition: Dict[str, Any],
    source_name: str,
    base_result: Optional[Dict[str, Any]],
    plugin: "AnalysisToolsPlugin",
) -> Dict[str, Any]:
    """
    Analyse un extrait en utilisant la façade AnalysisToolsPlugin.

    Args:
        extract_definition (Dict[str, Any]): Définition de l'extrait.
        source_name (str): Nom de la source.
        base_result (Optional[Dict[str, Any]]): Résultat de l'analyse de base (utilisé pour comparaison).
        plugin (AnalysisToolsPlugin): Instance du plugin d'analyse.

    Returns:
        Dict[str, Any]: Résultats de l'analyse avancée.
    """
    extract_name = extract_definition.get("extract_name", "Extrait sans nom")
    extract_text = extract_definition.get("extract_text")
    context = extract_definition.get("context", {})

    logger.debug(
        f"Analyse avancée de l'extrait '{extract_name}' via AnalysisToolsPlugin."
    )

    if not extract_text:
        logger.warning(
            f"Aucun texte à analyser pour l'extrait '{extract_name}', génération d'un échantillon."
        )
        # La fonction generate_sample_text attend maintenant extract_name et source_name
        extract_text = generate_sample_text(extract_name, source_name)

    try:
        # Utiliser directement la méthode de la façade du plugin
        # Le contexte complet doit être passé, pas seulement une sous-clé.
        advanced_analysis_results = plugin.analyze_text(
            text=extract_text, context=context
        )

        results: Dict[str, Any] = {
            "extract_name": extract_name,
            "source_name": source_name,
            "timestamp": datetime.now().isoformat(),
            "analyses": advanced_analysis_results,
        }

        # La comparaison avec les résultats de base est conservée
        if base_result:
            try:
                results["comparison_with_base"] = compare_rhetorical_analyses(
                    results, base_result
                )
            except Exception as e:
                logger.error(
                    f"Erreur lors de la comparaison des analyses pour '{extract_name}': {e}",
                    exc_info=True,
                )
                results["comparison_with_base"] = {"error": str(e)}

        return results

    except Exception as e:
        logger.error(
            f"Erreur lors de l'appel au AnalysisToolsPlugin pour l'extrait '{extract_name}': {e}",
            exc_info=True,
        )
        return {
            "extract_name": extract_name,
            "source_name": source_name,
            "error": f"Erreur du plugin: {str(e)}",
            "timestamp": datetime.now().isoformat(),
        }
