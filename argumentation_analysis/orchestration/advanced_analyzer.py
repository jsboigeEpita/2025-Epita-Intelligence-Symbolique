# -*- coding: utf-8 -*-
"""
Ce module contient des fonctions pour orchestrer des analyses rhétoriques avancées.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Imports potentiellement nécessaires pour la fonction déplacée
# Ces imports devront être vérifiés et ajustés en fonction du contexte d'appel final.
from argumentation_analysis.utils.data_generation import generate_sample_text
from argumentation_analysis.utils.text_processing import split_text_into_arguments
from argumentation_analysis.utils.analysis_comparison import compare_rhetorical_analyses
# Les outils eux-mêmes (Enhanced...Analyzer ou leurs mocks) seront passés en argument.

logger = logging.getLogger(__name__)

def _run_analysis_tool(tool_function, *args, **kwargs) -> Dict[str, Any]:
    """Exécute une fonction d'outil d'analyse et gère les exceptions."""
    try:
        return tool_function(*args, **kwargs)
    except Exception as e:
        tool_name = tool_function.__self__.__class__.__name__ if hasattr(tool_function, '__self__') else tool_function.__name__
        logger.error(f"Erreur lors de l'exécution de l'outil '{tool_name}': {e}", exc_info=True)
        return {"error": str(e)}

def analyze_extract_advanced(
    extract_definition: Dict[str, Any],
    source_name: str,
    base_result: Optional[Dict[str, Any]],
    tools: Dict[str, Any] # Dictionnaire des outils d'analyse pré-initialisés
) -> Dict[str, Any]:
    """
    Analyse un extrait avec les outils d'analyse rhétorique avancés.
    
    Args:
        extract_definition (Dict[str, Any]): Définition de l'extrait.
        source_name (str): Nom de la source.
        base_result (Optional[Dict[str, Any]]): Résultat de l'analyse de base pour cet extrait.
        tools (Dict[str, Any]): Dictionnaire contenant les outils d'analyse avancés pré-initialisés
                                 (ex: "complex_fallacy_analyzer", "contextual_fallacy_analyzer", etc.).
        
    Returns:
        Dict[str, Any]: Résultats de l'analyse avancée.
    """
    extract_name = extract_definition.get("extract_name", "Extrait sans nom")
    logger.debug(f"Orchestration de l'analyse avancée de l'extrait '{extract_name}' de la source '{source_name}'")
    
    extract_text = extract_definition.get("extract_text")
    
    if not extract_text:
        logger.warning(f"Texte non disponible pour l'extrait '{extract_name}'. Utilisation d'un texte d'exemple.")
        extract_text = generate_sample_text(extract_name, source_name)
    
    arguments = split_text_into_arguments(extract_text)
    
    if not arguments:
        arguments = [extract_text]
    
    analysis_context = {"source_name": source_name, "extract_name": extract_name}
    if "context" in extract_definition:
        analysis_context.update(extract_definition["context"])

    results: Dict[str, Any] = {
        "extract_name": extract_name,
        "source_name": source_name,
        "argument_count": len(arguments),
        "timestamp": datetime.now().isoformat(),
        "analyses": {}
    }
    
    # Analyse des sophismes complexes
    if "complex_fallacy_analyzer" in tools:
        analyzer = tools["complex_fallacy_analyzer"]
        results["analyses"]["complex_fallacies"] = _run_analysis_tool(
            analyzer.detect_composite_fallacies, arguments, analysis_context
        )
    
    # Analyse des sophismes contextuels améliorée
    if "contextual_fallacy_analyzer" in tools:
        analyzer = tools["contextual_fallacy_analyzer"]
        results["analyses"]["contextual_fallacies"] = _run_analysis_tool(
            analyzer.analyze_context, extract_text, analysis_context
        )
    
    # Évaluation de la gravité des sophismes
    if "fallacy_severity_evaluator" in tools:
        analyzer = tools["fallacy_severity_evaluator"]
        results["analyses"]["fallacy_severity"] = _run_analysis_tool(
            analyzer.evaluate_fallacy_severity, arguments, analysis_context
        )
    
    # Analyse globale des résultats rhétoriques
    if "rhetorical_result_analyzer" in tools:
        analyzer = tools["rhetorical_result_analyzer"]
        current_analysis_data = {
            key: results["analyses"].get(key.replace('_analysis', 'es'), {})
            for key in [
                "complex_fallacy_analysis",
                "contextual_fallacy_analysis",
                "fallacy_severity_evaluation"
            ]
        }
        
        if base_result:
            base_analyses = base_result.get("analyses", {})
            current_analysis_data.update({
                "base_contextual_fallacies": base_analyses.get("contextual_fallacies", {}),
                "base_argument_coherence": base_analyses.get("argument_coherence", {}),
                "base_semantic_analysis": base_analyses.get("semantic_analysis", {})
            })
        
        results["analyses"]["rhetorical_results"] = _run_analysis_tool(
            analyzer.analyze_rhetorical_results, current_analysis_data, analysis_context
        )
    
    # Comparer avec les résultats de l'analyse de base
    if base_result:
        results["comparison_with_base"] = _run_analysis_tool(
            compare_rhetorical_analyses, results, base_result
        )
    
    return results