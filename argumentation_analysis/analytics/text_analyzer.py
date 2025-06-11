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

# Importation au niveau du module pour une meilleure clarté
try:
    from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation
except ImportError:
    # Gérer le cas où le script est exécuté d'une manière qui perturbe les imports relatifs
    logging.error("Failed to import 'run_analysis_conversation'. Check PYTHONPATH and module structure.")
    # Rendre la fonction inutilisable si l'import échoue
    async def run_analysis_conversation(*args: Any, **kwargs: Any) -> None: # type: ignore
        """Placeholder if import fails."""
        raise ImportError("run_analysis_conversation could not be imported.")


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
    logging.info(f"Initiating text analysis of type '{analysis_type}' on text of length {len(text)} chars.")

    llm_service = services.get("llm_service")
    # jvm_ready_status = services.get("jvm_ready", False) # Disponible si nécessaire

    if not llm_service:
        logging.critical(" Le service LLM n'est pas disponible dans les services fournis. L'analyse ne peut pas continuer.")
        return None # Indique un échec critique

    # Une logique future pour le routage basé sur analysis_type peut être ajoutée ici.
    # Exemple :
    # if analysis_type == "rhetoric_specific":
    #     return await analyze_rhetoric_specifically(text, llm_service, services)
    # elif analysis_type == "fallacy_specific":
    #     return await detect_fallacies_specifically(text, llm_service, services)

    try:
        logging.info(f"Lancement de l'analyse principale (type: {analysis_type}) via run_analysis_conversation...")
        # `run_analysis_conversation` est attendue. Son utilisation originale dans `run_analysis.py`
        # n'implique pas la capture d'une valeur de retour pour un traitement ultérieur dans ce script.
        # Elle gère sa propre journalisation du succès ou de l'échec.
        await run_analysis_conversation(
            texte_a_analyser=text,
            llm_service=llm_service
            # Si `analysis_type` ou d'autres `services` deviennent pertinents pour `run_analysis_conversation`,
            # ils devront être passés ici.
        )
        logging.info(f"Analyse principale (type: '{analysis_type}') terminee avec succes (via run_analysis_conversation).")
        # Imite le comportement original : aucun résultat explicite retourné par ce chemin, le succès est journalisé.
        return # Ou un indicateur de succès plus spécifique si l'appelant en a besoin.

    except ImportError as ie:
        # Ceci serait typiquement intercepté au chargement du module si run_analysis_conversation est critique.
        logging.error(f" Échec de l'importation ou de l'utilisation des composants d'analyse pour le type '{analysis_type}': {ie}", exc_info=True)
        raise # Propage l'ImportError pour indiquer un problème de dépendance.
    except Exception as e:
        logging.error(f" Erreur lors de l'analyse du texte (type: {analysis_type}): {e}", exc_info=True)
        # Il est important de ne pas masquer l'erreur originale si elle n'est pas gérée spécifiquement.
        # Retourner None ici pourrait masquer la cause racine d'un problème plus large.
        # Si une gestion spécifique de l'erreur est nécessaire, elle doit être ajoutée.
        # Sinon, il est préférable de laisser l'exception se propager ou de la lever à nouveau.
        raise # Propage l'exception pour une gestion d'erreur plus globale.

# Placeholder for more specific analysis functions if `analysis_type` routing is implemented:
# async def analyze_rhetoric_specifically(text: str, llm_service: Any, all_services: Dict[str, Any]):
#     logging.info("Performing specific rhetoric analysis...")
#     # ... specific logic ...
#     return "Rhetoric analysis results"

# async def detect_fallacies_specifically(text: str, llm_service: Any, all_services: Dict[str, Any]):
#     logging.info("Performing specific fallacy detection...")
#     # ... specific logic ...
#     return "Fallacy detection results"