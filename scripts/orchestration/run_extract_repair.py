import argumentation_analysis.core.environment
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'exécution pour la réparation des extraits

Ce script est un point d'entrée simplifié pour exécuter le script de réparation
des bornes défectueuses dans les extraits. Il utilise les services refactorisés
et les modèles centralisés.
"""

import os
import sys
import asyncio
import argparse
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RunExtractRepair")

# Ajouter le répertoire parent au chemin de recherche des modules
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))) # Ancienne méthode
# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# Importer le pipeline de réparation et le parseur d'arguments
from argumentation_analysis.utils.dev_tools.repair_utils import run_extract_repair_pipeline
from argumentation_analysis.utils.core_utils.cli_utils import parse_extract_repair_arguments
# Les imports spécifiques (repair_extract_markers, core_services, etc.)
# sont maintenant gérés à l'intérieur du pipeline.


async def main():
    """Fonction principale."""
    args = parse_extract_repair_arguments()
    
    # Configurer le niveau de journalisation
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")
    
    logger.info("Démarrage du script de réparation des bornes défectueuses...")
    logger.info(f"Répertoire de travail actuel: {os.getcwd()}") # Peut être conservé pour info
    
    # Appel du pipeline modularisé
    await run_extract_repair_pipeline(
        project_root_dir=project_root,
        output_report_path_str=args.output,
        save_changes=args.save,
        hitler_only=args.hitler_only,
        custom_input_path_str=args.input,
        output_json_path_str=args.output_json
        # args.verbose est utilisé pour configurer le logger de ce script,
        # le pipeline utilisera son propre logger configuré ou hérité.
    )
    logger.info("Script de réparation des bornes défectueuses (via pipeline) terminé.")


if __name__ == "__main__":
    asyncio.run(main())