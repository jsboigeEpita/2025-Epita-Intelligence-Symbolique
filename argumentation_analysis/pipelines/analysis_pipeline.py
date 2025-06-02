#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module pour le pipeline d'analyse argumentative.

Ce module définit la logique d'orchestration pour exécuter une analyse argumentative complète,
depuis la récupération du texte jusqu'à l'exécution de l'analyse.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

# Imports des modules du projet
from project_core.utils.logging_utils import setup_logging
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
    """
    Exécute le pipeline d'analyse argumentative.

    Cette fonction orchestre les étapes suivantes :
    1. Configuration du logging.
    2. Récupération du texte à analyser (fichier, direct, ou UI).
    3. Initialisation des services d'analyse.
    4. Exécution de l'analyse textuelle.
    5. (Optionnel) Sauvegarde des résultats.

    Args:
        input_file_path: Chemin vers un fichier texte à analyser.
        input_text_content: Texte à analyser fourni directement.
        use_ui_input: Si True, utilise l'interface utilisateur pour obtenir le texte.
        log_level: Niveau de logging (par exemple, "INFO", "DEBUG").
        analysis_type: Type d'analyse à effectuer (par exemple, "default", "rhetorical").
        config_for_services: Configuration spécifique pour l'initialisation des services.
                             Si None, une configuration par défaut sera utilisée (notamment pour LIBS_DIR).
        # output_path: Chemin pour sauvegarder les résultats de l'analyse (non implémenté).

    Returns:
        Les résultats de l'analyse, ou None si l'analyse a échoué.
    """
    setup_logging(log_level_str=log_level)
    logging.info(f"Démarrage du pipeline d'analyse argumentative avec log_level={log_level}")

    actual_text_content: Optional[str] = None

    if input_file_path:
        try:
            file_path = Path(input_file_path)
            if not file_path.exists():
                logging.error(f"Le fichier {file_path} n'existe pas.")
                return None
            with open(file_path, 'r', encoding='utf-8') as f:
                actual_text_content = f.read()
            logging.info(f"Texte chargé depuis {file_path} ({len(actual_text_content)} caractères)")
        except Exception as e:
            logging.error(f"Erreur lors de la lecture du fichier '{input_file_path}': {e}", exc_info=True)
            return None
    elif input_text_content:
        actual_text_content = input_text_content
        logging.info(f"Utilisation du texte fourni directement ({len(actual_text_content)} caractères)")
    elif use_ui_input:
        try:
            # Cet import est localisé car il peut dépendre de bibliothèques UI non toujours nécessaires
            from argumentation_analysis.ui.app import configure_analysis_task
            logging.info("Lancement de l'interface utilisateur pour la saisie du texte...")
            actual_text_content = configure_analysis_task() # Cette fonction est synchrone
            if not actual_text_content:
                logging.warning("Aucun texte n'a été sélectionné via l'interface.")
                return None
            logging.info(f"Texte sélectionné via l'interface ({len(actual_text_content)} caractères)")
        except ImportError:
            logging.error("Impossible d'importer 'configure_analysis_task' depuis 'argumentation_analysis.ui.app'. L'option UI n'est pas disponible.", exc_info=True)
            return None
        except Exception as e:
            logging.error(f"Erreur lors de l'utilisation de l'interface pour obtenir le texte: {e}", exc_info=True)
            return None
    else:
        logging.error("Aucune source de texte n'a été fournie (fichier, texte direct ou UI).")
        return None

    if not actual_text_content:
        logging.error("Analyse impossible: contenu textuel vide ou non chargé.")
        return None

    # Configuration des services
    if config_for_services is None:
        try:
            from argumentation_analysis.paths import LIBS_DIR
            config_for_services = {"LIBS_DIR_PATH": LIBS_DIR}
        except ImportError:
            logging.error("Impossible d'importer LIBS_DIR depuis argumentation_analysis.paths. La configuration des services risque d'être incomplète.")
            # On peut tenter de continuer sans, ou retourner une erreur.
            # Pour l'instant, on logue et on continue, initialize_analysis_services gérera l'absence.
            config_for_services = {}


    logging.info("Initialisation des services d'analyse...")
    initialized_services = initialize_analysis_services(config_for_services)
    # llm_service et jvm_ready_status sont dans initialized_services

    logging.info(f"Préparation pour lancer l'analyse de type '{analysis_type}' sur un texte de {len(actual_text_content)} caractères...")
    analysis_results: Optional[Dict[str, Any]] = None
    try:
        analysis_results = await perform_text_analysis(
            text=actual_text_content,
            services=initialized_services,
            analysis_type=analysis_type
        )
        if analysis_results is None:
            logging.error("L'analyse n'a pas pu être complétée (perform_text_analysis a retourné None).")
        else:
            logging.info("L'appel à perform_text_analysis est terminé avec succès.")
            # Ici, on pourrait ajouter la logique pour sauvegarder les résultats si output_path était fourni.
            # from project_core.utils.file_utils import save_json_file
            # if output_path:
            #     save_json_file(analysis_results, output_path)
            #     logging.info(f"Résultats de l'analyse sauvegardés dans {output_path}")

    except ImportError as ie:
        logging.error(f"❌ Erreur d'importation lors de la tentative d'utilisation de text_analyzer: {ie}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"❌ Erreur lors de l'appel à perform_text_analysis: {e}", exc_info=True)
        return None

    return analysis_results

# Exemple d'utilisation (pourrait être dans un bloc if __name__ == "__main__" pour des tests)
# async def example_run():
#     # Assurez-vous que LIBS_DIR est accessible ou configurez config_for_services autrement
#     from argumentation_analysis.paths import LIBS_DIR
#     default_config = {"LIBS_DIR_PATH": LIBS_DIR}
#
#     # Exemple avec un texte direct
#     results = await run_text_analysis_pipeline(
#         input_text_content="Ceci est un exemple de texte. Les oiseaux volent.",
#         log_level="DEBUG",
#         config_for_services=default_config
#     )
#     if results:
#         print("Résultats de l'analyse:", results)
#     else:
#         print("L'analyse a échoué.")

# if __name__ == '__main__':
#     # Pour tester ce module directement (nécessite que l'environnement soit configuré)
#     # asyncio.run(example_run())
#     pass