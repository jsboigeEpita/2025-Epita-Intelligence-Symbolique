#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour résoudre les problèmes de dépendances pour les tests.

Ce script installe les versions compatibles de numpy, pandas et autres dépendances
nécessaires pour exécuter les tests.
"""

import sys
import argparse
import logging # Gardé pour le logger du script principal si nécessaire
from pathlib import Path

# Importation de la nouvelle fonction de pipeline
from project_core.pipelines.dependency_management_pipeline import run_dependency_installation_pipeline
# setup_logging est maintenant appelé à l'intérieur du pipeline, mais on garde un logger local pour ce script.
from project_core.utils.logging_utils import setup_logging # Pour configurer le logger de ce script

# Configuration du logger pour ce script (avant l'appel au pipeline)
# Le pipeline configurera son propre logging ou utilisera celui configuré globalement.
logger = logging.getLogger(__name__) # Utilisation de __name__ pour le logger

def main():
    """
    Point d'entrée principal du script.
    Parse les arguments de la ligne de commande et appelle le pipeline d'installation des dépendances.
    """
    parser = argparse.ArgumentParser(
        description="Installe ou met à jour les dépendances Python à partir d'un fichier requirements."
    )
    parser.add_argument(
        "requirements_file",
        type=str,
        help="Chemin vers le fichier requirements.txt (ou équivalent)."
    )
    parser.add_argument(
        "--force-reinstall",
        action="store_true",
        help="Force la réinstallation de tous les paquets."
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Niveau de verbosité du logging."
    )
    parser.add_argument(
        "--pip-options",
        type=str,
        nargs='*', # Accepte zéro ou plusieurs options pip
        help="Options supplémentaires à passer à la commande pip install (ex: --no-cache-dir --upgrade)."
    )
    
    args = parser.parse_args()

    # Configurer le logging pour ce script avant d'appeler le pipeline.
    # Le pipeline lui-même appellera setup_logging avec le log_level fourni.
    setup_logging(args.log_level)
    logger.info(f"Script {Path(__file__).name} démarré.")
    logger.info(f"Appel du pipeline d'installation des dépendances avec les arguments: {args}")

    success = run_dependency_installation_pipeline(
        requirements_file_path=args.requirements_file,
        force_reinstall=args.force_reinstall,
        log_level=args.log_level,
        pip_options=args.pip_options
    )

    if success:
        logger.info("Pipeline d'installation des dépendances terminé avec succès.")
        sys.exit(0)
    else:
        logger.error("Le pipeline d'installation des dépendances a rencontré des erreurs.")
        sys.exit(1)

if __name__ == "__main__":
    main()