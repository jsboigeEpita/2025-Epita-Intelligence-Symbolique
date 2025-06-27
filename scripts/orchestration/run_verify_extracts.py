import argumentation_analysis.core.environment
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'exécution pour la vérification des extraits

Ce script est un point d'entrée simplifié pour exécuter le script de vérification
des extraits. Il utilise les services refactorisés et les modèles centralisés.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RunVerifyExtracts")

# Ajouter le répertoire parent au chemin de recherche des modules
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) # Ancienne méthode
# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Importer le pipeline de vérification et le parseur d'arguments
from argumentation_analysis.utils.dev_tools.verification_utils import run_extract_verification_pipeline
from argumentation_analysis.utils.core_utils.cli_utils import parse_extract_verification_arguments
# Les imports spécifiques (verify_extracts, generate_report, core_services, etc.)
# sont maintenant gérés à l'intérieur du pipeline.


def main():
    """Fonction principale."""
    args = parse_extract_verification_arguments()
    
    # Configurer le niveau de journalisation
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")
    
    logger.info("Démarrage du script de vérification des extraits...")
    logger.info(f"Répertoire de travail actuel: {os.getcwd()}")
    
    # Appel du pipeline modularisé
    # Note: run_extract_verification_pipeline est actuellement défini comme async dans verification_utils.py
    # Si ce script ne doit pas utiliser asyncio, le pipeline devrait être synchrone.
    # Pour l'instant, on suppose qu'il est synchrone ou que le script appelant gère l'async.
    # Si run_extract_verification_pipeline devient effectivement async, il faudra faire:
    # asyncio.run(run_extract_verification_pipeline(...)) ici, et importer asyncio.
    # Pour l'instant, je vais le laisser comme un appel direct, en supposant qu'il sera ajusté si nécessaire.
    
    # Si le pipeline est async:
    # import asyncio
    # asyncio.run(run_extract_verification_pipeline(
    # project_root_dir=project_root,
    # output_report_path_str=args.output,
    # custom_input_path_str=args.input,
    # hitler_only=args.hitler_only
    # ))
    
    # En supposant une version synchrone du pipeline pour l'instant pour éviter de changer le if __name__ == "__main__":
    try:
        run_extract_verification_pipeline(
            project_root_dir=project_root,
            output_report_path_str=args.output,
            custom_input_path_str=args.input,
            hitler_only=args.hitler_only
        )
        logger.info("Script de vérification des extraits (via pipeline) terminé.")
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du pipeline de vérification: {e}", exc_info=True)


if __name__ == "__main__":
    main()