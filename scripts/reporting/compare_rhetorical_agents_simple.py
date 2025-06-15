import project_core.core_from_scripts.auto_env
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour comparer les performances des différents agents spécialistes d'analyse rhétorique.

Ce script:
1. Charge les résultats des analyses de base et avancée
2. Compare les performances des agents sur plusieurs critères
3. Génère des métriques quantitatives pour chaque agent
4. Produit des visualisations comparatives
5. Génère un rapport détaillé sur la pertinence des différents agents
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root_path = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root_path))

from argumentation_analysis.utils.core_utils.file_utils import load_json_file
from argumentation_analysis.utils.metrics_calculator import count_fallacies, extract_confidence_scores, analyze_contextual_richness
from argumentation_analysis.utils.core_utils.visualization_utils import generate_performance_visualizations
from argumentation_analysis.utils.core_utils.reporting_utils import generate_performance_comparison_markdown_report

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("CompareRhetoricalAgents")

# Les fonctions count_fallacies, extract_confidence_scores, et analyze_contextual_richness
# ont été déplacées vers argumentation_analysis.utils.metrics_calculator.
# La fonction generate_performance_visualizations a été déplacée vers project_core.utils.visualization_utils.
# La fonction generate_performance_report a été déplacée vers project_core.utils.reporting_utils
# et renommée en generate_performance_comparison_markdown_report.
# Les appels dans main() utiliseront les fonctions importées.

def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(description="Comparaison des performances des agents d'analyse rhétorique")
    
    parser.add_argument(
        "--base-results", "-b",
        help="Chemin du fichier contenant les résultats de l'analyse de base",
        default=None
    )
    
    parser.add_argument(
        "--advanced-results", "-a",
        help="Chemin du fichier contenant les résultats de l'analyse avancée",
        default=None
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        help="Répertoire de sortie pour les visualisations et le rapport",
        default="results/performance_comparison"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Affiche des informations de débogage supplémentaires"
    )
    
    args = parser.parse_args()
    
    # Configurer le niveau de logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé")
    
    logger.info("Démarrage de la comparaison des performances des agents d'analyse rhétorique...")
    
    # Trouver le fichier de résultats de base le plus récent si non spécifié
    base_results_file = args.base_results
    if not base_results_file:
        results_dir = Path("results")
        if results_dir.exists():
            result_files = list(results_dir.glob("rhetorical_analysis_*.json"))
            if result_files:
                # Trier par date de modification (la plus récente en premier)
                result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                base_results_file = result_files[0]
                logger.info(f"Utilisation du fichier de résultats de base le plus récent: {base_results_file}")
    
    if not base_results_file:
        logger.error("Aucun fichier de résultats de base spécifié et aucun fichier de résultats trouvé.")
        sys.exit(1)
    
    base_results_path = Path(base_results_file)
    if not base_results_path.exists():
        logger.error(f"Le fichier de résultats de base {base_results_path} n'existe pas.")
        sys.exit(1)
    
    # Trouver le fichier de résultats avancés le plus récent si non spécifié
    advanced_results_file = args.advanced_results
    if not advanced_results_file:
        results_dir = Path("results")
        if results_dir.exists():
            result_files = list(results_dir.glob("advanced_rhetorical_analysis_*.json"))
            if result_files:
                # Trier par date de modification (la plus récente en premier)
                result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                advanced_results_file = result_files[0]
                logger.info(f"Utilisation du fichier de résultats avancés le plus récent: {advanced_results_file}")
    
    if not advanced_results_file:
        logger.error("Aucun fichier de résultats avancés spécifié et aucun fichier de résultats trouvé.")
        sys.exit(1)
    
    advanced_results_path = Path(advanced_results_file)
    if not advanced_results_path.exists():
        logger.error(f"Le fichier de résultats avancés {advanced_results_path} n'existe pas.")
        sys.exit(1)
    
    # Définir le répertoire de sortie
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Charger les résultats
    base_results_data = load_json_file(base_results_path) # MODIFIÉ: Appel de la fonction importée
    advanced_results_data = load_json_file(advanced_results_path) # MODIFIÉ: Appel de la fonction importée
    
    # load_json_file retourne None en cas d'erreur, ou les données.
    # Il faut s'assurer que ce sont des listes si c'est ce qu'on attend.
    base_results = []
    if isinstance(base_results_data, list):
        base_results = base_results_data
    elif base_results_data is not None: # Si ce n'est pas None mais pas une liste
        logger.warning(f"Les résultats de base chargés depuis {base_results_path} ne sont pas une liste, mais de type {type(base_results_data)}. Traitement comme liste vide.")
        
    advanced_results = []
    if isinstance(advanced_results_data, list):
        advanced_results = advanced_results_data
    elif advanced_results_data is not None: # Si ce n'est pas None mais pas une liste
        logger.warning(f"Les résultats avancés chargés depuis {advanced_results_path} ne sont pas une liste, mais de type {type(advanced_results_data)}. Traitement comme liste vide.")

    if not base_results: # Vérifier après la conversion potentielle
        logger.error("Aucun résultat de base n'a pu être chargé.")
        sys.exit(1)
    
    if not advanced_results:
        logger.error("Aucun résultat avancé n'a pu être chargé.")
        sys.exit(1)
    
    # Générer les métriques de performance
    logger.info("Génération des métriques de performance...")
    
    base_metrics = {
        "fallacy_counts": count_fallacies(base_results),
        "confidence_scores": extract_confidence_scores(base_results),
        "richness_scores": analyze_contextual_richness(base_results)
    }
    
    advanced_metrics = {
        "fallacy_counts": count_fallacies(advanced_results),
        "confidence_scores": extract_confidence_scores(advanced_results),
        "richness_scores": analyze_contextual_richness(advanced_results)
    }
    
    # Générer les visualisations
    logger.info("Génération des visualisations...")
    generate_performance_visualizations(base_metrics, advanced_metrics, output_dir)
    
    # Générer le rapport
    logger.info("Génération du rapport...")
    report_file = output_dir / "rapport_performance.md"
    generate_performance_comparison_markdown_report(base_metrics, advanced_metrics, report_file)
    
    logger.info(f"✅ Comparaison des performances terminée. Résultats sauvegardés dans {output_dir}")

if __name__ == "__main__":
    main()