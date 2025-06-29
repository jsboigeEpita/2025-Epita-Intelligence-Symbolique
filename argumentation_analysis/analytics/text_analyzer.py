# -*- coding: utf-8 -*-
"""
Analyseur de texte pour le projet d'analyse d'argumentation.

Ce module fournit la fonction principale `perform_text_analysis` qui sert de
point d'entrée pour effectuer diverses analyses sur un texte donné.
Il s'appuie sur la fonction `run_analysis_conversation` (du package
`argumentation_analysis.orchestration.analysis_runner`) pour orchestrer
l'interaction avec un service LLM et potentiellement d'autres services
d'analyse.

L'objectif est de fournir une interface unifiée pour lancer des analyses
textuelles, avec la possibilité d'étendre les types d'analyses supportées
à l'avenir via le paramètre `analysis_type`.
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# L'importation de run_analysis_conversation a été déplacée dans perform_text_analysis
# pour résoudre une dépendance circulaire.

async def perform_text_analysis(text: str, services: Dict[str, Any], analysis_type: str = "default") -> Any:
    """Effectue une analyse de texte en utilisant l'orchestrateur `EnhancedPMAnalysisRunner`.

    Cette fonction sert de point d'entrée pour l'analyse, en utilisant le nouvel
    orchestrateur amélioré pour effectuer l'analyse.

    :param text: Le texte d'entrée à analyser.
    :param services: Dictionnaire de services. Doit contenir 'llm_service'.
    :param analysis_type: Type d'analyse (pour la journalisation).
    :return: Les résultats structurés de l'analyse.
    :raises Exception: Propage les exceptions de l'orchestrateur.
    """
    logger.info(f"Initiating enhanced text analysis of type '{analysis_type}' on text of length {len(text)} chars.")

    # Utilisation du nouvel orchestrateur. L'import est local pour la clarté.
    try:
        from argumentation_analysis.orchestration.enhanced_pm_analysis_runner import EnhancedPMAnalysisRunner
    except ImportError as e:
        logger.critical(f"Impossible d'importer 'EnhancedPMAnalysisRunner': {e}", exc_info=True)
        raise

    llm_service = services.get("llm_service")
    if not llm_service:
        logger.critical(" Le service LLM n'est pas disponible dans les services fournis. L'analyse ne peut pas continuer.")
        return None

    try:
        runner = EnhancedPMAnalysisRunner()
        logger.info(f"Launching main analysis (type: {analysis_type}) via EnhancedPMAnalysisRunner...")
        
        analysis_result = await runner.run_enhanced_analysis(
            text_content=text,
            llm_service=llm_service
        )
        
        logger.info(f"Main analysis (type: '{analysis_type}') completed successfully via EnhancedPMAnalysisRunner.")
        logger.debug(f"RAW RESULT from EnhancedPMAnalysisRunner: {analysis_result}")
        return analysis_result

    except Exception as e:
        logger.error(f"Error during text analysis (type: {analysis_type}): {e}", exc_info=True)
        raise