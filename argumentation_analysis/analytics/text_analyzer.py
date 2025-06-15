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
    """Effectue une analyse de texte en fonction du texte, des services et du type d'analyse fournis.

    Cette fonction orchestre l'analyse en appelant les fonctions d'analyse
    sous-jacentes appropriées (actuellement [`run_analysis_conversation`](argumentation_analysis/orchestration/analysis_runner.py:0)).
    Elle s'attend à ce qu'un service LLM initialisé soit présent dans le dictionnaire `services`.

    :param text: Le texte d'entrée à analyser.
    :type text: str
    :param services: Un dictionnaire de services d'analyse initialisés.
                     Doit contenir 'llm_service'. Il peut également contenir
                     le statut 'jvm_ready', bien qu'il ne soit pas directement
                     utilisé par cette fonction mais puisse l'être par les services sous-jacents.
    :type services: Dict[str, Any]
    :param analysis_type: Le type d'analyse à effectuer. Ce paramètre est
                          destiné à une expansion future, permettant le routage vers
                          différentes fonctions d'analyse spécialisées (par exemple, "rhetoric",
                          "fallacies"). Actuellement, il est principalement utilisé pour la journalisation et
                          ne modifie pas la logique d'analyse principale qui utilise par défaut
                          [`run_analysis_conversation`](argumentation_analysis/orchestration/analysis_runner.py:0).
    :type analysis_type: str
    :return: Les résultats de l'analyse. Actuellement, [`run_analysis_conversation`](argumentation_analysis/orchestration/analysis_runner.py:0)
             ne retourne pas explicitement de valeur dans son contexte d'utilisation original ;
             elle journalise les résultats. Cette fonction reflète ce comportement en retournant None
             en cas de succès (impliquant que les résultats sont journalisés ou gérés
             ailleurs) ou en cas d'erreurs critiques comme un service LLM manquant.
             Des améliorations futures pourraient impliquer le retour de résultats d'analyse structurés.
             Retourne None si les services essentiels sont manquants ou si une erreur se produit.
   :rtype: Optional[Any] # Peut retourner None ou propager une exception. Si succès, retourne None implicitement.
   :raises ImportError: Si les composants d'analyse essentiels ne peuvent pas être importés.
    :raises Exception: Pour toute autre erreur survenant pendant le processus d'analyse.
    """
    logger.info(f"Initiating text analysis of type '{analysis_type}' on text of length {len(text)} chars.")

    # --- DEBUT DU CORRECTIF POUR L'IMPORT CIRCULAIRE ---
    # L'import est effectué ici pour briser le cycle de dépendance qui se produit lorsque
    # `text_analyzer` est importé par une chaîne qui dépend de `analysis_runner` qui,
    # à son tour, importe des modules (comme `auto_env`) qui peuvent déclencher une
    # cascade d'imports menant de nouveau à `text_analyzer`.
    try:
        from argumentation_analysis.orchestration.analysis_runner import _run_analysis_conversation as run_analysis_conversation
    except ImportError as e:
        logger.critical(f"Impossible d'importer '_run_analysis_conversation' même avec un import local: {e}", exc_info=True)
        raise
    # --- FIN DU CORRECTIF ---


    llm_service = services.get("llm_service")
    # jvm_ready_status = services.get("jvm_ready", False) # Disponible si nécessaire

    if not llm_service:
        logger.critical(" Le service LLM n'est pas disponible dans les services fournis. L'analyse ne peut pas continuer.")
        return None # Indique un échec critique

    try:
        logger.info(f"Lancement de l'analyse principale (type: {analysis_type}) via run_analysis_conversation...")
        result = await run_analysis_conversation(
            texte_a_analyser=text,
            llm_service=llm_service
        )
        logger.info(f"Analyse principale (type: '{analysis_type}') terminee avec succes (via run_analysis_conversation).")
        return result

    except Exception as e:
        logger.error(f" Erreur lors de l'analyse du texte (type: {analysis_type}): {e}", exc_info=True)
        raise