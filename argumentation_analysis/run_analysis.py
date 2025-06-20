#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour lancer l'analyse argumentative

Ce script permet de lancer facilement l'analyse argumentative depuis la racine du projet.
Il offre plusieurs options pour fournir le texte à analyser (fichier, texte direct, etc.)
et configure automatiquement l'environnement nécessaire.
"""

import sys
import io
import asyncio
import argparse
import logging
from pathlib import Path

# Force UTF-8 for stdout and stderr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Configuration initiale pour s'assurer que les modules du projet sont accessibles
# Cela est particulièrement utile si le script est exécuté directement.
current_script_path = Path(__file__).resolve()
project_root = current_script_path.parents[1] # Remonter de deux niveaux: run_analysis.py -> argumentation_analysis -> project_root
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Imports des modules du projet après ajustement du path
from argumentation_analysis.core.utils.logging_utils import setup_logging
from argumentation_analysis.pipelines.analysis_pipeline import run_text_analysis_pipeline
from argumentation_analysis.paths import LIBS_DIR

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
    parser.add_argument("--output-file", type=str, default=None, help="Chemin du fichier où écrire le JSON de sortie.")
    
    args = parser.parse_args()
    
    # Configuration du logging (le pipeline s'en chargera, mais on peut initialiser ici aussi si besoin pour le lanceur)
    log_level_launcher = "DEBUG" if args.verbose else "INFO"
    # Note: setup_logging est appelé dans le pipeline, donc cet appel est pour les logs du lanceur lui-même.
    # Si le pipeline gère tous les logs, cette ligne peut être optionnelle ou ajustée.
    setup_logging(log_level_str=log_level_launcher)
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

    import json
    launcher_logger.info(f"Pipeline a retourné: {analysis_results}")

    # Mesure de débogage : toujours essayer d'imprimer quelque chose et de sortir proprement
    try:
        if analysis_results and 'history' in analysis_results and analysis_results['history']:
            serializable_history = []
            for msg in analysis_results['history']:
                serializable_history.append({
                    "author_name": msg.author_name if hasattr(msg, 'author_name') else 'N/A',
                    "content": msg.content if hasattr(msg, 'content') else str(msg)
                })
            analysis_results['history'] = serializable_history
        
        output_json_str = json.dumps(analysis_results, indent=2, ensure_ascii=False, default=str)
        
        if args.output_file:
            try:
                # Créer le répertoire parent si nécessaire
                output_path = Path(args.output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(output_json_str, encoding='utf-8')
                launcher_logger.info(f"Les résultats de l'analyse ont été sauvegardés dans : {args.output_file}")
            except Exception as write_error:
                launcher_logger.error(f"Impossible d'écrire dans le fichier de sortie {args.output_file}: {write_error}")
                # En cas d'erreur d'écriture, on imprime sur stdout comme solution de repli
                print(output_json_str)
        else:
            # Comportement par défaut : imprimer sur la sortie standard
            print(output_json_str)

    except Exception as e:
        error_json = json.dumps({"status": "error", "message": "Failed to serialize results", "details": str(e)})
        if args.output_file:
             try:
                Path(args.output_file).write_text(error_json, encoding='utf-8')
             except Exception as write_error:
                 launcher_logger.error(f"Impossible d'écrire l'erreur dans le fichier de sortie {args.output_file}: {write_error}")
                 print(error_json) # Fallback
        else:
            print(error_json)

if __name__ == "__main__":
    # S'assurer que l'environnement asyncio est correctement géré
    # Python 3.7+
    asyncio.run(main())