#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script lanceur pour configurer l'environnement de test du projet argumentation_analysis.

Ce script utilise le pipeline de setup défini dans project_core.pipelines.setup_pipeline
pour orchestrer les différentes étapes de configuration, y compris:
- Le diagnostic de l'environnement (implicitement via les autres pipelines).
- Le téléchargement de dépendances (ex: JARs).
import argumentation_analysis.core.environment
- L'installation des paquets Python via un fichier requirements.
- La configuration optionnelle d'un mock pour JPype.

Utilisation:
    python scripts/setup/setup_test_env.py [options]

Options:
    --config-path CONFIG_PATH
                        Chemin vers le fichier de configuration global (optionnel).
    --requirements-path REQUIREMENTS_PATH
                        Chemin vers le fichier requirements.txt (par défaut:
                        PROJECT_ROOT/requirements.txt).
    --mock-jpype        Activer le mock pour JPype.
    --venv-path VENV_PATH
                        Chemin vers l'environnement virtuel à utiliser/créer
                        (par défaut: PROJECT_ROOT/venv_test_setup).
    --project-root PROJECT_ROOT
                        Chemin racine du projet (détecté automatiquement par défaut).
"""

import argparse
import logging
import sys
from pathlib import Path

# Ajout de la racine du projet au sys.path pour permettre les imports de project_core
# Cela suppose que le script est toujours dans scripts/setup/
try:
    current_script_path = Path(__file__).resolve()
    project_root_path = current_script_path.parent.parent.parent 
    if str(project_root_path) not in sys.path:
        sys.path.insert(0, str(project_root_path))
    from argumentation_analysis.pipelines.setup_pipeline import run_test_environment_setup_pipeline
except ImportError as e:
    print(f"Erreur d'import: {e}. Assurez-vous que le PYTHONPATH est correctement configuré ou que le script est exécuté depuis la racine du projet.")
    sys.exit(1)


# Configuration du logger pour ce script
# Il est préférable de configurer le logging au niveau de l'application/pipeline principal
# mais on peut ajouter un handler basique ici pour la sortie du lanceur.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Fonction principale pour parser les arguments et lancer le pipeline de configuration.
    """
    parser = argparse.ArgumentParser(
        description="Configure l'environnement de test pour le projet argumentation_analysis.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # Détection du chemin racine du projet par défaut
    default_project_root = Path(__file__).resolve().parent.parent.parent

    parser.add_argument(
        "--config-path",
        type=Path,
        default=None,
        help="Chemin vers le fichier de configuration global (optionnel, pour le téléchargement de JARs, etc.)."
    )
    parser.add_argument(
        "--requirements-path",
        type=Path,
        default=default_project_root / "requirements.txt", # Ou un fichier requirements-test.txt spécifique
        help="Chemin vers le fichier requirements.txt."
    )
    parser.add_argument(
        "--mock-jpype",
        action="store_true",
        help="Activer le mock pour JPype."
    )
    parser.add_argument(
        "--venv-path",
        type=Path,
        default=default_project_root / "venv_test_setup", # Nom de venv suggéré
        help="Chemin vers l'environnement virtuel à utiliser ou créer."
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=default_project_root,
        help="Chemin racine du projet."
    )

    args = parser.parse_args()

    logger.info("Lancement du script de configuration de l'environnement de test.")
    logger.info(f"  Chemin du projet: {args.project_root}")
    logger.info(f"  Chemin du venv: {args.venv_path}")
    logger.info(f"  Fichier Requirements: {args.requirements_path}")
    if args.config_path:
        logger.info(f"  Fichier de configuration: {args.config_path}")
    logger.info(f"  Mock JPype: {'Activé' if args.mock_jpype else 'Désactivé'}")

    # Vérifier l'existence du fichier requirements
    if not args.requirements_path.exists():
        logger.error(f"Le fichier requirements spécifié n'existe pas: {args.requirements_path}")
        sys.exit(1)
    
    # Vérifier l'existence du fichier de configuration si fourni
    if args.config_path and not args.config_path.exists():
        logger.warning(f"Le fichier de configuration spécifié n'existe pas: {args.config_path}. Il sera ignoré.")
        # On pourrait choisir de sortir avec une erreur ici si config_path est critique
        # args.config_path = None # Optionnel: forcer à None si non trouvé


    success = run_test_environment_setup_pipeline(
        config_path=args.config_path,
        requirements_path=args.requirements_path,
        mock_jpype=args.mock_jpype,
        venv_path=args.venv_path,
        project_root=args.project_root
    )

    if success:
        logger.info("Configuration de l'environnement de test terminée avec succès via le pipeline.")
        # Les instructions pour activer le venv et lancer les tests pourraient être
        # affichées par le pipeline de dépendances s'il crée le venv.
        # Sinon, on peut les ajouter ici si pertinent.
        # Exemple:
        # print("\nPour activer l'environnement de test (si créé/géré par ce script):")
        # if platform.system() == "Windows":
        #     print(f"    {args.venv_path}\\Scripts\\activate")
        # else:
        #     print(f"    source {args.venv_path}/bin/activate")
    else:
        logger.error("La configuration de l'environnement de test via le pipeline a échoué.")
        sys.exit(1)

if __name__ == "__main__":
    main()