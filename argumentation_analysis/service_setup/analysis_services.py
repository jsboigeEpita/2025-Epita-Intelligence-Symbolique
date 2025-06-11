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
    """Initialise et configure les services nécessaires à l'analyse argumentative.

    Cette fonction orchestre la mise en place des dépendances clés, telles que
    la machine virtuelle Java (JVM) pour les bibliothèques associées et le
    service de modèle de langage à grande échelle (LLM) pour le traitement
    du langage naturel.

    La configuration des services peut être influencée par des variables
    d'environnement (chargées depuis un fichier .env) et par le dictionnaire
    de configuration fourni.

    :param config: Dictionnaire de configuration contenant potentiellement des
                   chemins spécifiques ou d'autres paramètres pour l'initialisation.
                   Par exemple, `LIBS_DIR_PATH` peut y être spécifié pour
                   localiser les bibliothèques Java.
    :type config: Dict[str, Any]
    :return: Un dictionnaire contenant l'état des services initialisés.
             Clés typiques :
             - "jvm_ready" (bool): True si la JVM est initialisée, False sinon.
             - "llm_service" (Any | None): Instance du service LLM si créé,
                                          None en cas d'échec.
    :rtype: Dict[str, Any]
    :raises Exception: Peut potentiellement lever des exceptions non capturées
                       provenant des fonctions d'initialisation sous-jacentes si
                       elles ne sont pas gérées (bien que la tendance actuelle
                       soit de logger les erreurs plutôt que de les propager
                       directement depuis cette fonction).
    """
    services = {}

    # Section 1: Chargement des variables d'environnement
    # Les variables d'environnement (par exemple, clés API pour le LLM) sont
    # chargées depuis un fichier .env. Ceci est crucial pour la configuration
    # sécurisée et flexible des services.
    loaded = load_dotenv(find_dotenv(), override=True)
    logging.info(f"Résultat du chargement de .env: {loaded}")

    # Section 2: Initialisation de la Machine Virtuelle Java (JVM)
    # La JVM est nécessaire pour utiliser des bibliothèques Java, comme TweetyProject.
    # Le chemin vers les bibliothèques (LIBS_DIR) est essentiel ici.
    # Il peut être fourni via la configuration `config` ou importé.
    libs_dir_path = config.get("LIBS_DIR_PATH", LIBS_DIR)
    if libs_dir_path is None:
        # Si LIBS_DIR n'est pas disponible, la JVM ne peut pas démarrer,
        # ce qui impactera les fonctionnalités dépendant de Java.
        logging.error("Le chemin vers LIBS_DIR n'est pas configuré. L'initialisation de la JVM est compromise.")
        services["jvm_ready"] = False
    else:
        logging.info(f"Initialisation de la JVM avec LIBS_DIR: {libs_dir_path}...")
        jvm_ready_status = initialize_jvm(lib_dir_path=libs_dir_path)
        services["jvm_ready"] = jvm_ready_status
        if not jvm_ready_status:
            logging.warning("⚠️ La JVM n'a pas pu être initialisée. Certains agents (ex: PropositionalLogicAgent) pourraient ne pas fonctionner.")

    # Section 3: Création du Service de Modèle de Langage (LLM)
    # Le service LLM est responsable des capacités de traitement du langage.
    # Sa configuration (clés API, etc.) est généralement gérée par `create_llm_service`
    # qui s'appuie sur les variables d'environnement chargées précédemment.
    logging.info("Création du service LLM...")
    try:
        llm_service = create_llm_service()
        services["llm_service"] = llm_service
        if llm_service:
            logging.info(f"[OK] Service LLM créé avec succès (ID: {getattr(llm_service, 'service_id', 'N/A')}).")
        else:
            # Ce cas peut se produire si create_llm_service est conçu pour retourner None
            # en cas de configuration manquante mais non critique, sans lever d'exception.
            logging.warning("⚠️ Le service LLM n'a pas pu être créé (create_llm_service a retourné None). Vérifiez la configuration des variables d'environnement (ex: clés API).")
    except Exception as e:
        # Une exception ici indique un problème sérieux lors de la configuration ou
        # de l'initialisation du service LLM (par exemple, une clé API invalide ou
        # un problème de connectivité avec le fournisseur du LLM).
        logging.critical(f"❌ Échec critique lors de la création du service LLM: {e}", exc_info=True)
        services["llm_service"] = None
        # Note: La propagation de l'exception est commentée pour permettre au reste de
        # l'application de potentiellement continuer avec des fonctionnalités réduites.
        # Décommenter si le service LLM est absolument critique pour toute opération.
        # raise RuntimeError(f"Impossible de créer le service LLM: {e}") from e
    
    return services

if __name__ == '__main__':
    # Exemple d'utilisation (pourrait nécessiter une configuration de logging)
    from argumentation_analysis.utils.core_utils.logging_utils import setup_logging
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