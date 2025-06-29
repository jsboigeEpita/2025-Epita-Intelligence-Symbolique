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
from typing import Any
from argumentation_analysis.config.settings import AppSettings
from argumentation_analysis.orchestration.analysis_runner import AnalysisRunner

logger = logging.getLogger(__name__)

async def perform_text_analysis(text: str, services: dict[str, Any], analysis_type: str = "default") -> Any:
    """
    Effectue une analyse de texte en utilisant l'orchestrateur `EnhancedPMAnalysisRunner`.

    Cette fonction sert de point d'entrée pour l'analyse, en utilisant le nouvel
    orchestrateur amélioré pour effectuer l'analyse.

    :param text: Le texte d'entrée à analyser.
    :param services: Dictionnaire de services. Doit contenir 'llm_service'.
    :param analysis_type: Type d'analyse (pour la journalisation).
    :return: Les résultats structurés de l'analyse.
    :raises Exception: Propage les exceptions de l'orchestrateur.
    """
    logger.info(f"Lancement de l'analyse de texte améliorée de type '{analysis_type}' sur un texte de {len(text)} caractères.")

    # Utilisation du nouvel orchestrateur. L'import est local pour la clarté.
    try:
        from argumentation_analysis.orchestration.enhanced_pm_analysis_runner import EnhancedPMAnalysisRunner
    except ImportError as e:
        logger.critical(f"Impossible d'importer 'EnhancedPMAnalysisRunner': {e}", exc_info=True)
        raise

    llm_service = services.get("llm_service")
    if not llm_service:
        logger.critical("Le service LLM n'est pas disponible dans les services fournis. L'analyse ne peut pas continuer.")
        return None

    try:
        runner = EnhancedPMAnalysisRunner()
        logger.info(f"Lancement de l'analyse principale (type: {analysis_type}) via EnhancedPMAnalysisRunner...")
        
        analysis_result = await runner.run_enhanced_analysis(
            text_content=text,
            llm_service=llm_service
        )
        
        logger.info(f"Analyse principale (type: '{analysis_type}') terminée avec succès via EnhancedPMAnalysisRunner.")
        logger.debug(f"RÉSULTAT BRUT de EnhancedPMAnalysisRunner: {analysis_result}")
        return analysis_result

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du texte (type: {analysis_type}): {e}", exc_info=True)
        raise