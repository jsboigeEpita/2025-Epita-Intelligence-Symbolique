#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de diagnostic complet de l'environnement pour le projet d'Intelligence Symbolique.

Ce script diagnostique et résout automatiquement les problèmes de dépendances complexes :
1. Configuration Java/JPype
2. Gestion des clés API LLM (optionnel)
3. Tests de validation de l'environnement
"""

import sys
import argparse
import logging
from pathlib import Path

# Ajuster le sys.path pour permettre l'importation depuis project_core
# Cela suppose que le script est exécuté depuis la racine du projet ou que
# le PYTHONPATH est configuré. Pour plus de robustesse, on peut ajouter
# explicitement la racine du projet au sys.path si ce n'est pas déjà fait.
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from project_core.pipelines.diagnostic_pipeline import run_environment_diagnostic_pipeline
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging # Assurez-vous que cette fonction existe et est correcte

# Configuration initiale du logger pour ce script lanceur
# Le pipeline configurera plus finement le logging via setup_logging.
logger = logging.getLogger(__name__) # Utilise le nom du module courant

def main():
    """
    Point d'entrée principal du script de diagnostic de l'environnement.
    Parse les arguments de la ligne de commande et appelle le pipeline de diagnostic.
    """
    parser = argparse.ArgumentParser(
        description="Script de diagnostic complet de l'environnement pour le projet d'Intelligence Symbolique.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--requirements_file",
        type=str,
        default=str(project_root / "requirements.txt"), # Chemin par défaut vers requirements.txt
        help="Chemin vers le fichier requirements.txt à vérifier."
    )
    parser.add_argument(
        "--log_level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Niveau de verbosité du logging."
    )
    
    args = parser.parse_args()

    # Configurer le logging globalement en utilisant la fonction utilitaire
    # setup_logging doit être capable de prendre un niveau de log en string ou int
    try:
        numeric_log_level = getattr(logging, args.log_level.upper())
        if not isinstance(numeric_log_level, int):
            raise ValueError(f"Niveau de log invalide: {args.log_level}")
    except (AttributeError, ValueError) as e:
        print(f"Erreur de configuration du niveau de log: {e}. Utilisation de INFO par défaut.", file=sys.stderr)
        numeric_log_level = logging.INFO
    
    setup_logging(level=numeric_log_level) # Appel de la fonction importée

    logger.info(f"Lancement du diagnostic de l'environnement avec les arguments: {args}")

    # Vérifier l'existence du fichier requirements.txt
    requirements_path = Path(args.requirements_file)
    if not requirements_path.is_file():
        logger.error(f"Le fichier requirements spécifié '{requirements_path}' est introuvable.")
        logger.error("Veuillez fournir un chemin valide vers un fichier requirements.txt.")
        sys.exit(2) # Code d'erreur spécifique pour fichier non trouvé

    # Appel du pipeline de diagnostic
    exit_code = run_environment_diagnostic_pipeline(
        requirements_path=str(requirements_path),
        log_level=args.log_level.upper() # Le pipeline s'attend à un string pour le niveau de log
    )
    
    if exit_code == 0:
        logger.info("Diagnostic de l'environnement terminé avec succès.")
    else:
        logger.warning(f"Diagnostic de l'environnement terminé avec des problèmes (code de sortie: {exit_code}).")
        logger.warning("Consultez les logs et le rapport 'diagnostic_report.json' pour plus de détails.")
        
    sys.exit(exit_code)

if __name__ == "__main__":
    main()