#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module pour l'initialisation des services d'analyse argumentative.
"""

import logging
from typing import Dict, Any

from dotenv import load_dotenv, find_dotenv
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.core.llm_service import create_llm_service
try:
    from argumentation_analysis.paths import LIBS_DIR
except ImportError:
    # Fallback pour les cas où le script est exécuté directement ou l'environnement n'est pas pleinement configuré
    # Cela suppose que 'paths.py' pourrait être au même niveau ou que LIBS_DIR doit être défini autrement.
    # Pour une modularisation propre, LIBS_DIR devrait idéalement provenir de la configuration.
    logging.warning("Impossible d'importer LIBS_DIR depuis argumentation_analysis.paths. Tentative d'importation alternative ou valeur par défaut.")
    try:
        from ..paths import LIBS_DIR # Tentative d'importation relative si service_setup est un sous-module
    except ImportError:
        logging.error("LIBS_DIR n'a pas pu être importé. L'initialisation de la JVM échouera probablement.")
        LIBS_DIR = None # Ou une valeur par défaut si applicable, ou lever une erreur.


def initialize_analysis_services(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialise les différents composants ou services requis pour l'analyse.

    Cette fonction prend un dictionnaire de configuration et initialise les
    services tels que la JVM, le service LLM, etc.

    Args:
        config: Un dictionnaire de configuration. Actuellement, ce paramètre
                n'est pas directement utilisé car la configuration est chargée
                depuis .env ou des chemins codés en dur. Il est inclus pour
                une future extensibilité.

    Returns:
        Un dictionnaire contenant les services initialisés.
        Par exemple:
        {
            "jvm_ready": True,
            "llm_service": <instance_llm_service>
        }
    """
    services = {}

    # 1. Chargement de l'environnement (.env)
    # La configuration de dotenv pourrait être rendue optionnelle ou gérée par l'application appelante.
    # Pour l'instant, on la garde ici pour maintenir le comportement original.
    loaded = load_dotenv(find_dotenv(), override=True)
    logging.info(f"Résultat du chargement de .env: {loaded}")

    # 2. Initialisation de la JVM
    # LIBS_DIR peut aussi être passé via `config` si nécessaire pour plus de flexibilité.
    libs_dir_path = config.get("LIBS_DIR_PATH", LIBS_DIR)
    if libs_dir_path is None:
        logging.error("Le chemin vers LIBS_DIR n'est pas configuré. L'initialisation de la JVM est compromise.")
        services["jvm_ready"] = False
    else:
        logging.info(f"Initialisation de la JVM avec LIBS_DIR: {libs_dir_path}...")
        jvm_ready_status = initialize_jvm(lib_dir_path=libs_dir_path)
        services["jvm_ready"] = jvm_ready_status
        if not jvm_ready_status:
            logging.warning("⚠️ La JVM n'a pas pu être initialisée. Certains agents (ex: PropositionalLogicAgent) pourraient ne pas fonctionner.")

    # 3. Création du Service LLM
    # La configuration du service LLM (API keys, etc.) est typiquement gérée par `create_llm_service`
    # qui lit les variables d'environnement (chargées par dotenv ci-dessus).
    logging.info("Création du service LLM...")
    try:
        llm_service = create_llm_service()
        services["llm_service"] = llm_service
        if llm_service:
            logging.info(f"✅ Service LLM créé avec succès (ID: {getattr(llm_service, 'service_id', 'N/A')}).")
        else:
            # create_llm_service pourrait retourner None si la configuration est absente mais sans lever d'exception.
            logging.warning("⚠️ Le service LLM n'a pas pu être créé (create_llm_service a retourné None). Vérifiez la configuration.")
            # Il est important que create_llm_service lève une exception si la création est critique et échoue.
    except Exception as e:
        logging.critical(f"❌ Échec critique lors de la création du service LLM: {e}", exc_info=True)
        services["llm_service"] = None
        # Selon la criticité, on pourrait vouloir propager l'exception :
        # raise RuntimeError(f"Impossible de créer le service LLM: {e}") from e
    
    return services

if __name__ == '__main__':
    # Exemple d'utilisation (pourrait nécessiter une configuration de logging)
    from project_core.utils.logging_utils import setup_logging
    setup_logging() # Configuration de base du logging

    # Simuler un dictionnaire de configuration
    sample_config = {
        "LIBS_DIR_PATH": "../libs" # Exemple, ajuster si nécessaire
    }
    
    logging.info("Test de initialize_analysis_services...")
    initialized_services = initialize_analysis_services(sample_config)
    logging.info(f"Services initialisés: {initialized_services}")

    if initialized_services.get("llm_service"):
        logging.info("Service LLM disponible.")
    else:
        logging.warning("Service LLM non disponible.")

    if initialized_services.get("jvm_ready"):
        logging.info("JVM prête.")
    else:
        logging.warning("JVM non prête.")