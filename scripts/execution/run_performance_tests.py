#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'exécution pour les tests de performance sur extraits de discours.

Ce script est un point d'entrée simplifié pour exécuter les tests de performance
sur différents extraits de discours. Il utilise les services refactorisés et les
modèles centralisés pour analyser les performances de l'agent d'analyse rhétorique.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Ajouter le répertoire racine au chemin de recherche des modules
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RunPerformanceTests")

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    """
    parser = argparse.ArgumentParser(description="Exécute les tests de performance sur extraits de discours")
    
    parser.add_argument(
        "--output", "-o",
        default="performance_report.md",
        help="Fichier de sortie pour le rapport de performance (défaut: performance_report.md)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Activer le mode verbeux"
    )
    
    parser.add_argument(
        "--extrait", "-e",
        action="append",
        help="Chemin vers un extrait spécifique à tester (peut être utilisé plusieurs fois)"
    )
    
    return parser.parse_args()

def main():
    """
    Fonction principale du script.
    """
    # Analyser les arguments
    args = parse_arguments()
    
    # Configurer le niveau de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé")
    
    logger.info("Démarrage des tests de performance sur extraits de discours")
    
    # Importer le module de test de performance
    try:
        from argumentation_analysis.scripts.test_performance_extraits import main as run_tests # MODIFIÉ: Correction de la faute de frappe
        import asyncio
        
        # Exécuter les tests de performance
        logger.info("Exécution des tests de performance...")
        asyncio.run(run_tests())
        
        logger.info(f"Tests de performance terminés. Rapport généré dans le répertoire results/performance_tests/")
        
    except ImportError as e:
        logger.error(f"Erreur lors de l'importation du module de test de performance: {e}")
        return 1
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution des tests de performance: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())