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

logger = logging.getLogger(__name__)

async def perform_text_analysis(text: str, services: dict[str, Any], analysis_type: str = "default") -> Any:
    """
    Effectue une analyse de texte en utilisant l'orchestrateur `AnalysisRunnerV2`.

    Cette fonction sert de point d'entrée pour l'analyse, en utilisant le nouvel
    orchestrateur pour effectuer l'analyse.

    :param text: Le texte d'entrée à analyser.
    :param services: Dictionnaire de services, doit contenir 'llm_service'.
    :param analysis_type: Type d'analyse (pour la journalisation).
    :return: Les résultats structurés de l'analyse.
    :raises ValueError: Si le service LLM est manquant.
    :raises Exception: Propage les autres exceptions de l'orchestrateur.
    """
    logger.info(f"Lancement de l'analyse de texte de type '{analysis_type}' sur un texte de {len(text)} caractères.")
    
    llm_service = services.get("llm_service")
    if not llm_service:
        logger.critical("Le service LLM n'est pas disponible dans les services fournis.")
        raise ValueError("Le service LLM est requis pour l'analyse.")

    try:
        from argumentation_analysis.orchestration.analysis_runner_v2 import AnalysisRunnerV2
    except ImportError as e:
        logger.critical(f"Impossible d'importer 'AnalysisRunnerV2': {e}", exc_info=True)
        raise

    try:
        runner = AnalysisRunnerV2(llm_service=llm_service)
        logger.info(f"Lancement de l'analyse principale (type: {analysis_type}) via AnalysisRunnerV2...")
        
        analysis_result = await runner.run_analysis(
            text_content=text
        )
        
        logger.info(f"Analyse principale (type: '{analysis_type}') terminée avec succès via AnalysisRunnerV2.")
        logger.debug(f"RÉSULTAT BRUT de AnalysisRunnerV2: {analysis_result}")
        return analysis_result

    except Exception as e:
        logger.error(f"Erreur lors de l'analyse du texte (type: {analysis_type}): {e}", exc_info=True)
        raise