#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour résoudre les problèmes de dépendances pour les tests.

Ce script installe les versions compatibles de numpy, pandas et autres dépendances
nécessaires pour exécuter les tests.
"""
import project_core.core_from_scripts.auto_env

import sys
import argparse
import logging # Gardé pour le logger du script principal si nécessaire
from pathlib import Path

# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root_path = Path(__file__).resolve().parent.parent.parent
if str(project_root_path) not in sys.path:
    sys.path.insert(0, str(project_root_path))

# Importation de la nouvelle fonction pour exécuter des commandes pip
from project_core.setup_core_from_scripts.run_pip_commands import _run_command_in_conda_env
from project_core.core_from_scripts.environment_manager import EnvironmentManager
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging

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
       type=str, # nargs non spécifié, la valeur par défaut est 1
       default="",
       help="Options supplémentaires à passer à la commande pip install, sous forme d'une seule chaîne (ex: \"--no-cache-dir --upgrade\")."
   )
    
    args = parser.parse_args()

    # Configurer le logging pour ce script avant d'appeler le pipeline.
    # Le pipeline lui-même appellera setup_logging avec le log_level fourni.
    setup_logging(args.log_level)
    logger.info(f"Script {Path(__file__).name} démarré.")
    logger.info(f"Appel du pipeline d'installation des dépendances avec les arguments: {args}")

    env_manager = EnvironmentManager(project_root_path=str(project_root_path))
    conda_env_name = env_manager.get_project_env_name()

    if not conda_env_name:
        logger.error("Nom de l'environnement Conda non trouvé. Impossible de continuer.")
        sys.exit(1)

    pip_command = ["pip", "install", "-r", args.requirements_file]
    if args.force_reinstall:
        pip_command.append("--force-reinstall")
    if args.pip_options:
        pip_command.extend(args.pip_options.split())

    logger.info(f"Construction de la commande pip : {' '.join(pip_command)}")
    
    success = _run_command_in_conda_env(
        conda_env_name=conda_env_name,
        command_list=pip_command,
        project_root=str(project_root_path),
        logger_instance=logger
    )

    if success:
        logger.info("Pipeline d'installation des dépendances terminé avec succès.")
        sys.exit(0)
    else:
        logger.error("Le pipeline d'installation des dépendances a rencontré des erreurs.")
        sys.exit(1)

if __name__ == "__main__":
    main()