#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Module pour le pipeline d'analyse argumentative.

Ce module fournit la fonction `run_text_analysis_pipeline` qui orchestre
l'ensemble du processus d'analyse argumentative. Cela inclut la configuration,
la récupération des données d'entrée (texte), l'initialisation des services
nécessaires (comme les modèles de NLP et les ponts vers des logiques
formelles), l'exécution de l'analyse elle-même, et potentiellement
la sauvegarde des résultats.

Le pipeline est conçu pour être flexible, acceptant du texte provenant de
diverses sources (fichier, chaîne de caractères directe, ou interface utilisateur)
et permettant une configuration détaillée des services et du type d'analyse.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Imports des modules du projet
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging
from argumentation_analysis.service_setup.analysis_services import initialize_analysis_services
from argumentation_analysis.analytics.text_analyzer import perform_text_analysis
# Les imports pour LIBS_DIR et l'UI seront conditionnels ou gérés différemment
# from argumentation_analysis.paths import LIBS_DIR # Sera nécessaire pour config_for_services
# from argumentation_analysis.ui.app import configure_analysis_task # Si use_ui_input est True

async def run_text_analysis_pipeline(
    input_file_path: Optional[str] = None,
    input_text_content: Optional[str] = None,
    use_ui_input: bool = False,
    log_level: str = "INFO",
    analysis_type: str = "default",
    config_for_services: Optional[Dict[str, Any]] = None,
    # output_path: Optional[str] = None, # Pour une future sauvegarde des résultats
) -> Optional[Dict[str, Any]]:
    """Exécute le pipeline principal d'analyse argumentative.

    Cette fonction orchestre l'ensemble du processus d'analyse, de la récupération
    du texte d'entrée à la production des résultats de l'analyse. Elle gère
    la configuration du logging, la sélection de la source du texte, l'initialisation
    des services d'analyse (y compris les modèles NLP et les outils logiques),
    et l'exécution de l'analyse textuelle via `perform_text_analysis`.

    Étapes principales du pipeline :
    1.  Configuration du système de logging basé sur `log_level`.
    2.  Détermination et chargement du contenu textuel à analyser.
        Priorité : `input_file_path`, puis `input_text_content`, puis `use_ui_input`.
    3.  Initialisation des services d'analyse (`initialize_analysis_services`)
        avec la configuration fournie ou une configuration par défaut.
    4.  Exécution de l'analyse (`perform_text_analysis`) sur le texte obtenu.
    5.  Retour des résultats de l'analyse.

    :param input_file_path: Chemin optionnel vers un fichier texte à analyser.
    :type input_file_path: Optional[str]
    :param input_text_content: Texte optionnel à analyser, fourni directement comme chaîne.
    :type input_text_content: Optional[str]
    :param use_ui_input: Si True, tente d'utiliser une interface utilisateur
                         (si disponible) pour obtenir le texte.
    :type use_ui_input: bool
    :param log_level: Niveau de logging à utiliser (ex: "INFO", "DEBUG").
    :type log_level: str
    :param analysis_type: Type d'analyse à effectuer (ex: "default", "rhetorical", "fallacy_detection").
                          Ce paramètre est transmis à `perform_text_analysis`.
    :type analysis_type: str
    :param config_for_services: Dictionnaire de configuration optionnel pour
                                l'initialisation des services. Peut contenir
                                des chemins vers des bibliothèques externes (`LIBS_DIR_PATH`),
                                des clés API, etc. Si None, une configuration par défaut
                                est tentée.
    :type config_for_services: Optional[Dict[str, Any]]
    :return: Un dictionnaire contenant les résultats de l'analyse, ou None si
             une erreur critique survient ou si l'analyse ne produit aucun résultat.
             La structure exacte du dictionnaire dépend du `analysis_type`.
    :rtype: Optional[Dict[str, Any]]
    :raises FileNotFoundError: Si `input_file_path` est fourni mais que le fichier n'existe pas.
                                (Géré en interne, logue une erreur et retourne None).
    :raises IOError: Si une erreur survient lors de la lecture du fichier `input_file_path`.
                     (Géré en interne, logue une erreur et retourne None).
    :raises ImportError: Si des dépendances optionnelles (ex: pour l'UI ou `LIBS_DIR`)
                         ne sont pas trouvées alors qu'elles sont nécessaires.
                         (Géré en interne, logue une erreur et retourne None ou continue avec des fonctionnalités réduites).
    :raises Exception: Pour d'autres erreurs inattendues durant l'exécution du pipeline,
                       notamment lors de l'initialisation des services ou de l'analyse elle-même.
                       (Géré en interne, logue une erreur et retourne None).
    """
    # Étape 1: Configuration du logging
    setup_logging(log_level_str=log_level)
    logging.info(f"Démarrage du pipeline d'analyse argumentative avec log_level={log_level}")

    actual_text_content: Optional[str] = None

    # Étape 2: Récupération du texte à analyser
    # La priorité est : fichier > contenu direct > UI
    if input_file_path:
        logging.info(f"Tentative de chargement du texte depuis le fichier : {input_file_path}")
        try:
            file_path = Path(input_file_path)
            if not file_path.exists():
                logging.error(f"Le fichier spécifié '{file_path}' n'existe pas.")
                # Conforme à la docstring : :raises FileNotFoundError (géré en interne)
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                actual_text_content = f.read()
            logging.info(f"Texte chargé avec succès depuis {file_path} ({len(actual_text_content)} caractères).")
        except IOError as e: # Plus spécifique que Exception pour les erreurs de lecture
            logging.error(f"Erreur d'E/S lors de la lecture du fichier '{input_file_path}': {e}", exc_info=True)
            # Conforme à la docstring : :raises IOError (géré en interne)
            return None
        except Exception as e: # Catch-all pour autres erreurs de lecture
            logging.error(f"Erreur inattendue lors de la lecture du fichier '{input_file_path}': {e}", exc_info=True)
            return None
    elif input_text_content:
        actual_text_content = input_text_content
        logging.info(f"Utilisation du texte fourni directement ({len(actual_text_content)} caractères).")
    elif use_ui_input:
        logging.info("Tentative de récupération du texte via l'interface utilisateur.")
        try:
            # Cet import est localisé car il peut dépendre de bibliothèques UI
            # qui ne sont pas toujours nécessaires ou installées.
            from argumentation_analysis.ui.app import configure_analysis_task
            logging.info("Lancement de l'interface utilisateur pour la saisie du texte...")
            actual_text_content = configure_analysis_task() # Supposée synchrone ici
            if not actual_text_content:
                logging.warning("Aucun texte n'a été sélectionné ou fourni via l'interface utilisateur.")
                return None # Pas de texte, pas d'analyse
            logging.info(f"Texte récupéré via l'interface utilisateur ({len(actual_text_content)} caractères).")
        except ImportError:
            logging.error("L'option 'use_ui_input' est True, mais le module UI 'argumentation_analysis.ui.app' "
                          "ou la fonction 'configure_analysis_task' n'a pas pu être importé. "
                          "L'interface utilisateur n'est probablement pas disponible.", exc_info=True)
            # Conforme à la docstring : :raises ImportError (géré en interne)
            return None
        except Exception as e:
            logging.error(f"Erreur lors de l'utilisation de l'interface utilisateur pour obtenir le texte: {e}", exc_info=True)
            return None
    else:
        # Cas où aucune source de texte n'est spécifiée
        logging.error("Aucune source de texte n'a été fournie (ni input_file_path, "
                      "ni input_text_content, et use_ui_input est False).")
        return None

    # Vérification finale si le contenu textuel a bien été chargé
    if not actual_text_content:
        logging.error("Le contenu textuel est vide ou n'a pas pu être chargé. Arrêt du pipeline.")
        return None

    # Étape 3: Initialisation des services d'analyse
    # Gère la configuration pour les services, en utilisant une valeur par défaut si nécessaire.
    effective_config_for_services = config_for_services
    if effective_config_for_services is None:
        logging.info("Aucune configuration spécifique fournie pour les services, tentative d'utilisation de la configuration par défaut.")
        try:
            # Tentative d'importation de LIBS_DIR pour la configuration par défaut.
            # Cet import est localisé pour éviter une dépendance stricte si non nécessaire.
            from argumentation_analysis.paths import LIBS_DIR
            effective_config_for_services = {"LIBS_DIR_PATH": LIBS_DIR}
            logging.info(f"Utilisation de LIBS_DIR ({LIBS_DIR}) pour la configuration des services.")
        except ImportError:
            logging.warning("Impossible d'importer LIBS_DIR depuis 'argumentation_analysis.paths'. "
                            "La configuration des services pourrait être incomplète si elle en dépend. "
                            "Continuons avec une configuration vide.", exc_info=True)
            # Conforme à la docstring : :raises ImportError (géré en interne, tentative de continuer)
            effective_config_for_services = {}
        except Exception as e: # Autres erreurs lors de la config par défaut
            logging.error(f"Erreur inattendue lors de la création de la configuration par défaut pour les services: {e}", exc_info=True)
            effective_config_for_services = {}


    logging.info("Initialisation des services d'analyse...")
    try:
        initialized_services = initialize_analysis_services(effective_config_for_services)
        # `initialized_services` contient typiquement `llm_service`, `jvm_ready_status`, etc.
        if not initialized_services: # initialize_analysis_services pourrait retourner None ou un dict vide en cas d'échec partiel
            logging.error("L'initialisation des services a échoué ou n'a retourné aucun service valide.")
            return None
        logging.info("Services d'analyse initialisés avec succès.")
    except Exception as e:
        logging.error(f"Erreur critique lors de l'initialisation des services d'analyse: {e}", exc_info=True)
        # Conforme à la docstring : :raises Exception (géré en interne)
        return None

    # Étape 4: Exécution de l'analyse textuelle
    logging.info(f"Préparation pour lancer l'analyse de type '{analysis_type}' sur un texte de {len(actual_text_content)} caractères...")
    analysis_results: Optional[Dict[str, Any]] = None
    try:
        # Appel à la fonction principale qui effectue l'analyse.
        # Cette fonction est asynchrone et doit être awaited.
        analysis_results = await perform_text_analysis(
            text=actual_text_content,
            services=initialized_services,
            analysis_type=analysis_type
        )

        if analysis_results is None:
            logging.warning("L'analyse textuelle (perform_text_analysis) n'a retourné aucun résultat (None). "
                            "Cela peut être normal pour certains types d'analyse ou indiquer un problème.")
        else:
            logging.info("L'analyse textuelle a été complétée avec succès.")
            # Étape 5 (Optionnel): Sauvegarde des résultats (logique commentée pour l'instant)
            # if output_path:
            #     try:
            #         from argumentation_analysis.utils.core_utils.file_utils import save_json_file
            #         save_json_file(analysis_results, output_path)
            #         logging.info(f"Résultats de l'analyse sauvegardés dans {output_path}")
            #     except Exception as e:
            #         logging.error(f"Erreur lors de la sauvegarde des résultats dans '{output_path}': {e}", exc_info=True)

    except ImportError as ie: # Spécifiquement pour les erreurs d'import dans perform_text_analysis
        logging.error(f"Erreur d'importation lors de la tentative d'exécution de 'perform_text_analysis': {ie}. "
                      "Vérifiez les dépendances de 'argumentation_analysis.analytics.text_analyzer'.", exc_info=True)
        # Conforme à la docstring : :raises ImportError (géré en interne)
        return None
    except Exception as e: # Erreurs générales durant perform_text_analysis
        logging.error(f"Erreur inattendue lors de l'exécution de 'perform_text_analysis': {e}", exc_info=True)
        # Conforme à la docstring : :raises Exception (géré en interne)
        return None

    # Retourne les résultats de l'analyse (peut être None)
    return analysis_results