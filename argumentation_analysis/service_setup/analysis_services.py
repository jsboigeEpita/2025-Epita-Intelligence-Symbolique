#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Initialisation des services pour l'analyse argumentative.

Ce module fournit la fonction `initialize_analysis_services` qui est responsable
de la configuration et de l'initialisation des services essentiels requis par
le système d'analyse d'argumentation. Cela inclut typiquement :
    - Le chargement des variables d'environnement (ex: clés API).
    - L'initialisation de la Machine Virtuelle Java (JVM) pour l'interaction
      avec des bibliothèques Java comme TweetyProject.
    - La création et configuration du service de Modèle de Langage à Grande Échelle (LLM).

La fonction retourne un dictionnaire indiquant le statut des services initialisés.
"""

import logging
from pathlib import Path
from typing import Dict, Any

from dotenv import load_dotenv, find_dotenv
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.core.llm_service import create_llm_service
from config.unified_config import UnifiedConfig  # Importer UnifiedConfig

try:
    from argumentation_analysis.paths import LIBS_DIR
except ImportError:
    logging.warning("Impossible d'importer LIBS_DIR depuis argumentation_analysis.paths. Fallback.")
    try:
        from ..paths import LIBS_DIR
    except ImportError:
        logging.error("LIBS_DIR n'a pas pu être importé.")
        LIBS_DIR = None

def initialize_analysis_services(config: UnifiedConfig) -> Dict[str, Any]:
    """
    Initialise et configure les services en se basant sur une instance de UnifiedConfig.
    """
    services = {}
    logging.info(f"--- Initialisation des services avec mock_level='{config.mock_level.value}' ---")

    # 1. Chargement des variables d'environnement (toujours utile pour les clés API, etc.)
    loaded = load_dotenv(find_dotenv(), override=True)
    logging.info(f"Résultat du chargement de .env: {loaded}")

    # 2. Initialisation de la JVM (contrôlée par la config)
    if config.enable_jvm:
        libs_dir_path = LIBS_DIR
        if libs_dir_path is None:
            logging.error("enable_jvm=True mais LIBS_DIR n'est pas configuré.")
            services["jvm_ready"] = False
        else:
            logging.info(f"Initialisation de la JVM avec LIBS_DIR: {libs_dir_path}...")
            jvm_ready_status = initialize_jvm(lib_dir_path=libs_dir_path)
            services["jvm_ready"] = jvm_ready_status
            if not jvm_ready_status:
                logging.warning("La JVM n'a pas pu être initialisée.")
    else:
        logging.info("Initialisation de la JVM sautée (enable_jvm=False).")
        services["jvm_ready"] = False

    # 3. Création du Service LLM (contrôlé par la config)
    logging.info("Création du service LLM...")
    try:
        # Le paramètre force_mock est directement déduit de la configuration
        llm_service = create_llm_service(
            service_id="default_llm_service",
            force_mock=config.use_mock_llm
        )
        services["llm_service"] = llm_service
        
        if llm_service:
            service_type = type(llm_service).__name__
            service_id = getattr(llm_service, 'service_id', 'N/A')
            logging.info(f"[OK] Service LLM créé (Type: {service_type}, ID: {service_id}).")
        else:
            logging.warning("create_llm_service a retourné None.")

    except Exception as e:
        logging.critical(f"Échec critique lors de la création du service LLM: {e}", exc_info=True)
        services["llm_service"] = None
    
    return services

if __name__ == '__main__':
    # Exemple d'utilisation (pourrait nécessiter une configuration de logging)
    from argumentation_analysis.core.utils.logging_utils import setup_logging
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