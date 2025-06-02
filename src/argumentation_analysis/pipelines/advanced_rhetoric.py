# -*- coding: utf-8 -*-
"""
Pipeline pour l'analyse rhétorique avancée de multiples extraits.
"""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm

# Imports des outils réels (à gérer avec try-except si nécessaire dans un contexte plus large)
try:
    from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
    from argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_analyzer import EnhancedRhetoricalResultAnalyzer
    REAL_TOOLS_AVAILABLE = True
except ImportError:
    REAL_TOOLS_AVAILABLE = False

# Import des outils mocks et de l'orchestrateur d'analyse d'extrait
from argumentation_analysis.mocks.advanced_tools import create_mock_advanced_rhetorical_tools
from argumentation_analysis.orchestration.advanced_analyzer import analyze_extract_advanced


logger = logging.getLogger(__name__)

def run_advanced_rhetoric_pipeline(
    extract_definitions: List[Dict[str, Any]],
    base_results: List[Dict[str, Any]],
    output_file: Path,
    use_real_tools: bool = False # Paramètre pour choisir entre outils réels et mocks
) -> None:
    """
    Analyse tous les extraits avec les outils avancés et sauvegarde les résultats.
    Cette fonction est une version modulaire de l'ancienne analyze_extracts_advanced.

    Args:
        extract_definitions (List[Dict[str, Any]]): Définitions des extraits.
        base_results (List[Dict[str, Any]]): Résultats de l'analyse de base.
        output_file (Path): Chemin du fichier de sortie pour les résultats.
        use_real_tools (bool): Si True et que les outils réels sont disponibles, les utilise.
                               Sinon, utilise les mocks.
    """
    logger.info("Démarrage du pipeline d'analyse rhétorique avancée...")
    
    # Initialiser les outils d'analyse avancés
    tools: Dict[str, Any]
    if use_real_tools and REAL_TOOLS_AVAILABLE:
        try:
            tools = {
                "complex_fallacy_analyzer": EnhancedComplexFallacyAnalyzer(),
                "contextual_fallacy_analyzer": EnhancedContextualFallacyAnalyzer(),
                "fallacy_severity_evaluator": EnhancedFallacySeverityEvaluator(),
                "rhetorical_result_analyzer": EnhancedRhetoricalResultAnalyzer()
            }
            logger.info("✅ Outils d'analyse rhétorique avancés (réels) initialisés.")
        except Exception as e: # Attraper une exception plus large au cas où l'init échoue
            logger.warning(f"Erreur lors de l'initialisation des outils réels: {e}. Utilisation des mocks.")
            tools = create_mock_advanced_rhetorical_tools()
    else:
        if use_real_tools and not REAL_TOOLS_AVAILABLE:
            logger.warning("Les outils réels ont été demandés mais ne sont pas disponibles. Utilisation des mocks.")
        tools = create_mock_advanced_rhetorical_tools()
        logger.info("✅ Outils d'analyse rhétorique avancés (mocks) initialisés.")
            
    base_results_dict: Dict[str, Dict[str, Any]] = {}
    for result in base_results:
        extract_name = result.get("extract_name")
        source_name = result.get("source_name")
        if extract_name and source_name:
            key = f"{source_name}:{extract_name}"
            base_results_dict[key] = result
    
    total_extracts = sum(len(source.get("extracts", [])) for source in extract_definitions)
    logger.info(f"Pipeline d'analyse avancée pour {total_extracts} extraits...")
    
    all_pipeline_results: List[Dict[str, Any]] = []
    
    progress_bar = tqdm(total=total_extracts, desc="Pipeline d'analyse avancée", unit="extrait")
    
    for source in extract_definitions:
        source_name = source.get("source_name", "Source sans nom")
        extracts_in_source = source.get("extracts", [])
        
        for extract_def in extracts_in_source:
            extract_name = extract_def.get("extract_name", "Extrait sans nom")
            key = f"{source_name}:{extract_name}"
            base_result_for_extract = base_results_dict.get(key)
            
            try:
                # Appel à la fonction d'orchestration pour un seul extrait
                single_extract_results = analyze_extract_advanced(
                    extract_def, source_name, base_result_for_extract, tools
                )
                all_pipeline_results.append(single_extract_results)
            except Exception as e:
                logger.error(f"Erreur dans le pipeline pour l'extrait '{extract_name}': {e}", exc_info=True)
                all_pipeline_results.append({
                    "extract_name": extract_name,
                    "source_name": source_name,
                    "error": f"Erreur de pipeline: {str(e)}"
                })
            
            progress_bar.update(1)
    
    progress_bar.close()
    
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True) # S'assurer que le répertoire parent existe
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_pipeline_results, f, ensure_ascii=False, indent=2)
        logger.info(f"✅ Résultats du pipeline d'analyse avancée sauvegardés dans {output_file}")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la sauvegarde des résultats du pipeline: {e}", exc_info=True)