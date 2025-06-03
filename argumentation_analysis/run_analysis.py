#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour lancer l'analyse argumentative

Ce script permet de lancer facilement l'analyse argumentative depuis la racine du projet.
Il offre plusieurs options pour fournir le texte à analyser (fichier, texte direct, etc.)
et configure automatiquement l'environnement nécessaire.
"""

import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Configuration initiale pour s'assurer que les modules du projet sont accessibles
# Cela est particulièrement utile si le script est exécuté directement.
current_script_path = Path(__file__).resolve()
project_root = current_script_path.parents[1] # Remonter de deux niveaux: run_analysis.py -> argumentation_analysis -> project_root
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Imports des modules du projet après ajustement du path
from project_core.utils.logging_utils import setup_logging # Déjà présent, mais s'assurer qu'il est bien trouvé
from argumentation_analysis.pipelines.analysis_pipeline import run_text_analysis_pipeline
from argumentation_analysis.paths import LIBS_DIR # Nécessaire pour la configuration des services

async def main():
    """
    Fonction principale du script.
    Parse les arguments de la ligne de commande et appelle le pipeline d'analyse.
    """
    parser = argparse.ArgumentParser(description="Analyse argumentative de texte")
    
    # Groupe mutuellement exclusif pour les sources de texte
    text_source = parser.add_mutually_exclusive_group(required=True)
    text_source.add_argument("--file", "-f", type=str, help="Chemin vers un fichier texte à analyser")
    text_source.add_argument("--text", "-t", type=str, help="Texte à analyser (directement en argument)")
    text_source.add_argument("--ui", "-u", action="store_true", help="Utiliser l'interface utilisateur pour sélectionner le texte")
    
    # Options supplémentaires
    parser.add_argument("--verbose", "-v", action="store_true", help="Afficher les logs détaillés")
    
    args = parser.parse_args()
    
    # Configuration du logging (le pipeline s'en chargera, mais on peut initialiser ici aussi si besoin pour le lanceur)
    log_level_launcher = "DEBUG" if args.verbose else "INFO"
    # Note: setup_logging est appelé dans le pipeline, donc cet appel est pour les logs du lanceur lui-même.
    # Si le pipeline gère tous les logs, cette ligne peut être optionnelle ou ajustée.
    setup_logging(log_level_str=log_level_launcher, logger_name="run_analysis_launcher")
    launcher_logger = logging.getLogger("run_analysis_launcher")
    launcher_logger.info(f"Lanceur configuré avec le niveau de log: {log_level_launcher}")

    # Préparation des arguments pour le pipeline
    # Le pipeline gère lui-même la lecture de fichier, le texte direct ou l'UI.
    # Il a besoin de savoir quelle option a été choisie.

    # Configuration pour les services, notamment LIBS_DIR
    # Cette configuration peut être étendue si d'autres paramètres globaux sont nécessaires.
    config_for_services = {"LIBS_DIR_PATH": LIBS_DIR}

    launcher_logger.info("Appel du pipeline d'analyse...")
    analysis_results = await run_text_analysis_pipeline(
        input_file_path=args.file,
        input_text_content=args.text,
        use_ui_input=args.ui,
        log_level=log_level_launcher, # Le pipeline utilisera ce niveau de log
        analysis_type="default", # Peut être rendu configurable via argparse si nécessaire
        config_for_services=config_for_services
    )

    if analysis_results:
        launcher_logger.info("Pipeline d'analyse terminé avec succès.")
        # Ici, on pourrait afficher un résumé des résultats si nécessaire,
        # ou simplement se fier aux logs du pipeline.
        # print("Résultats de l'analyse:", analysis_results) # Décommenter pour affichage direct
    else:
        launcher_logger.error("Le pipeline d'analyse n'a pas retourné de résultats ou a échoué.")

if __name__ == "__main__":
    # S'assurer que l'environnement asyncio est correctement géré
    # Python 3.7+
    asyncio.run(main())