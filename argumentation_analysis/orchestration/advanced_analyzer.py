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
        logger.warning(f"Texte non disponible pour l'extrait '{extract_name}' dans l'orchestrateur. Utilisation d'un texte d'exemple.")
        extract_text = generate_sample_text(extract_name, source_name) # Nécessite generate_sample_text
    
    arguments = split_text_into_arguments(extract_text) # Nécessite split_text_into_arguments
    
    if not arguments:
        arguments = [extract_text] # Utiliser l'extrait entier si pas d'arguments trouvés
    
    # Le contexte peut être plus riche, ici on prend le nom de la source ou ce qui est dans l'extrait.
    # Dans le script original, c'était `extract_definition.get("context", source_name)`
    # On pourrait le passer en argument ou le construire ici. Pour l'instant, on simplifie.
    analysis_context = {"source_name": source_name, "extract_name": extract_name}
    # Si `extract_definition` contient un champ "context", on pourrait l'utiliser :
    # analysis_context.update(extract_definition.get("context", {}))


    results: Dict[str, Any] = {
        "extract_name": extract_name,
        "source_name": source_name,
        "argument_count": len(arguments),
        "timestamp": datetime.now().isoformat(),
        "analyses": {}
    }
    
    # Analyse des sophismes complexes
    if "complex_fallacy_analyzer" in tools:
        try:
            complex_fallacy_analyzer = tools["complex_fallacy_analyzer"]
            complex_fallacy_results = complex_fallacy_analyzer.detect_composite_fallacies(
                arguments, analysis_context # Utiliser analysis_context
            )
            results["analyses"]["complex_fallacies"] = complex_fallacy_results
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des sophismes complexes (orchestrateur): {e}", exc_info=True)
            results["analyses"]["complex_fallacies"] = {"error": str(e)}
    
    # Analyse des sophismes contextuels améliorée
    if "contextual_fallacy_analyzer" in tools:
        try:
            contextual_fallacy_analyzer = tools["contextual_fallacy_analyzer"]
            contextual_fallacy_results = contextual_fallacy_analyzer.analyze_context(
                extract_text, analysis_context # Utiliser analysis_context
            )
            results["analyses"]["contextual_fallacies"] = contextual_fallacy_results
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse contextuelle des sophismes (orchestrateur): {e}", exc_info=True)
            results["analyses"]["contextual_fallacies"] = {"error": str(e)}
    
    # Évaluation de la gravité des sophismes
    if "fallacy_severity_evaluator" in tools:
        try:
            fallacy_severity_evaluator = tools["fallacy_severity_evaluator"]
            severity_results = fallacy_severity_evaluator.evaluate_fallacy_severity(
                arguments, analysis_context # Utiliser analysis_context
            )
            results["analyses"]["fallacy_severity"] = severity_results
        except Exception as e:
            logger.error(f"Erreur lors de l'évaluation de la gravité des sophismes (orchestrateur): {e}", exc_info=True)
            results["analyses"]["fallacy_severity"] = {"error": str(e)}
    
    # Analyse globale des résultats rhétoriques
    if "rhetorical_result_analyzer" in tools:
        try:
            rhetorical_result_analyzer = tools["rhetorical_result_analyzer"]
            
            current_analysis_data = {
                "complex_fallacy_analysis": results["analyses"].get("complex_fallacies", {}),
                "contextual_fallacy_analysis": results["analyses"].get("contextual_fallacies", {}),
                "fallacy_severity_evaluation": results["analyses"].get("fallacy_severity", {})
            }
            
            if base_result: # Intégrer les résultats de base si disponibles
                current_analysis_data["base_contextual_fallacies"] = base_result.get("analyses", {}).get("contextual_fallacies", {})
                current_analysis_data["base_argument_coherence"] = base_result.get("analyses", {}).get("argument_coherence", {})
                current_analysis_data["base_semantic_analysis"] = base_result.get("analyses", {}).get("semantic_analysis", {})
            
            rhetorical_analysis_output = rhetorical_result_analyzer.analyze_rhetorical_results(
                current_analysis_data, analysis_context # Utiliser analysis_context
            )
            results["analyses"]["rhetorical_results"] = rhetorical_analysis_output
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse globale des résultats rhétoriques (orchestrateur): {e}", exc_info=True)
            results["analyses"]["rhetorical_results"] = {"error": str(e)}
    
    # Comparer avec les résultats de l'analyse de base
    if base_result:
        try:
            # compare_rhetorical_analyses attend les résultats complets (avancés et base)
            comparison = compare_rhetorical_analyses(results, base_result) # Nécessite compare_rhetorical_analyses
            results["comparison_with_base"] = comparison
        except Exception as e:
            logger.error(f"Erreur lors de la comparaison avec l'analyse de base (orchestrateur): {e}", exc_info=True)
            results["comparison_with_base"] = {"error": str(e)}
    
    return results