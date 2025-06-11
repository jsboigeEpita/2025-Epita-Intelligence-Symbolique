#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour générer un rapport d'analyse complet qui synthétise tous les résultats des tests précédents.

Ce script:
1. Charge les résultats de toutes les analyses précédentes:
   - Résultats de l'analyse rhétorique de base
   - Résultats de l'analyse rhétorique avancée
   - Résultats de la comparaison des performances
2. Synthétise les résultats par corpus:
   - Discours d'Hitler
   - Débats Lincoln Douglas
   - Autres corpus disponibles
3. Analyse la pertinence des agents spécialistes pour chaque type de contenu:
   - Quels agents sont les plus efficaces pour chaque corpus?
   - Quelles sont les forces et faiblesses de chaque agent?
   - Quelles améliorations pourraient être apportées?
4. Génère des recommandations:
   - Pour l'utilisation optimale des agents existants
   - Pour le développement de nouveaux agents spécialistes
   - Pour l'amélioration des agents existants
5. Produit un rapport final au format HTML et Markdown:
   - Résumé exécutif
   - Méthodologie
   - Résultats détaillés
   - Visualisations
   - Recommandations
   - Conclusion
"""

import sys
import io
import logging
import argparse
from pathlib import Path
# from typing import Dict, List, Any, Optional, Tuple, Union # Conservé pour les types si nécessaire, mais probablement géré par le pipeline
# from tqdm import tqdm # Déplacé vers le pipeline si utilisé
# import markdown # Déplacé vers le pipeline
# import shutil # Déplacé vers le pipeline si utilisé

# Configuration pour gérer les erreurs d'encodage sur stdout/stderr
# Cela rendra print() et logging.StreamHandler plus robustes
# Note: sys.stdout.encoding peut être None si la sortie est redirigée.
# Dans ce cas, on utilise 'utf-8' par défaut.
_stdout_encoding = sys.stdout.encoding if sys.stdout.encoding else 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=_stdout_encoding, errors='replace', line_buffering=True)

_stderr_encoding = sys.stderr.encoding if sys.stderr.encoding else 'utf-8'
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding=_stderr_encoding, errors='replace', line_buffering=True)

# Configuration du logging (simplifiée, le pipeline gère sa propre config)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__) # Utilisation de __name__ pour le logger du script lanceur

# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root_path_comprehensive = Path(__file__).resolve().parent.parent.parent
if str(project_root_path_comprehensive) not in sys.path:
    sys.path.insert(0, str(project_root_path_comprehensive))

# Imports des utilitaires et du pipeline
# from argumentation_analysis.utils.core_utils.file_utils import load_json_file, load_text_file, load_csv_file, save_markdown_to_html # Utilisé par le pipeline
# from argumentation_analysis.utils.core_utils.reporting_utils import generate_markdown_report_for_corpus, generate_overall_summary_markdown # Utilisé par le pipeline
from argumentation_analysis.utils.data_processing_utils import group_results_by_corpus # Utilisé par le pipeline
# from argumentation_analysis.analytics.stats_calculator import calculate_average_scores # Utilisé par le pipeline
from argumentation_analysis.pipelines.reporting_pipeline import run_comprehensive_report_pipeline

# La vérification des dépendances est retirée, elle doit être gérée par l'environnement ou le pipeline.
# Les fonctions spécifiques de génération de rapport ont été déplacées vers reporting_pipeline.py

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Les arguments parsés
    """
    parser = argparse.ArgumentParser(description="Génère un rapport d'analyse complet qui synthétise tous les résultats des tests précédents")
    
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
        "--performance-report", "-p",
        help="Chemin du fichier contenant le rapport de performance",
        default=None
    )
    
    parser.add_argument(
        "--performance-metrics", "-m",
        help="Chemin du fichier contenant les métriques de performance",
        default=None
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        help="Répertoire de sortie pour les rapports et visualisations",
        default="results/comprehensive_report"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Affiche des informations de débogage supplémentaires"
    )
    
    return parser.parse_args()

def main():
    """Fonction principale du script pour lancer le pipeline de génération de rapport."""
    args = parse_arguments()

    if args.verbose:
        # Le logger du pipeline sera configuré par le pipeline lui-même.
        # Le logger de ce script est déjà configuré.
        logger.debug("Mode verbeux activé pour le script lanceur.")
    # else: # Le niveau INFO est déjà défini par défaut

    try:
        logger.info("Lancement du pipeline de génération de rapport complet...")

        # Logique pour trouver les fichiers par défaut si non spécifiés
        base_results_file = args.base_results
        if not base_results_file:
            results_dir = Path("results")
            if results_dir.exists():
                result_files = sorted(list(results_dir.glob("rhetorical_analysis_*.json")), key=lambda x: x.stat().st_mtime, reverse=True)
                if result_files:
                    base_results_file = str(result_files[0])
                    logger.info(f"Utilisation du fichier de résultats de base le plus récent: {base_results_file}")
        
        if not base_results_file:
            logger.error("Aucun fichier de résultats de base spécifié ou trouvé.")
            sys.exit(1)

        advanced_results_file = args.advanced_results
        if not advanced_results_file:
            results_dir = Path("results")
            if results_dir.exists():
                result_files = sorted(list(results_dir.glob("advanced_rhetorical_analysis_*.json")), key=lambda x: x.stat().st_mtime, reverse=True)
                if result_files:
                    advanced_results_file = str(result_files[0])
                    logger.info(f"Utilisation du fichier de résultats avancés le plus récent: {advanced_results_file}")

        if not advanced_results_file:
            logger.error("Aucun fichier de résultats avancés spécifié ou trouvé.")
            sys.exit(1)
            
        performance_report_file = args.performance_report
        if not performance_report_file:
            performance_dir = Path("results/performance_comparison")
            if performance_dir.exists():
                report_files = list(performance_dir.glob("rapport_performance.md")) # Devrait en trouver un au plus
                if report_files: # Prend le premier trouvé s'il y en a
                    performance_report_file = str(report_files[0])
                    logger.info(f"Utilisation du fichier de rapport de performance: {performance_report_file}")
            if not performance_report_file: # Si toujours pas trouvé
                 logger.info("Aucun fichier de rapport de performance trouvé par défaut.")


        performance_metrics_file = args.performance_metrics
        if not performance_metrics_file:
            performance_dir = Path("results/performance_comparison")
            if performance_dir.exists():
                metrics_files = list(performance_dir.glob("performance_metrics.csv")) # Devrait en trouver un au plus
                if metrics_files: # Prend le premier trouvé
                    performance_metrics_file = str(metrics_files[0])
                    logger.info(f"Utilisation du fichier de métriques de performance: {performance_metrics_file}")
            if not performance_metrics_file: # Si toujours pas trouvé
                logger.info("Aucun fichier de métriques de performance trouvé par défaut.")


        success = run_comprehensive_report_pipeline(
            base_results_file_path=base_results_file,
            advanced_results_file_path=advanced_results_file,
            performance_report_file_path=performance_report_file, # Peut être None
            performance_metrics_file_path=performance_metrics_file, # Peut être None
            output_dir_str=args.output_dir,
            verbose=args.verbose
        )

        if success:
            logger.info("Pipeline de génération de rapport exécuté avec succès.")
        else:
            logger.error("Le pipeline de génération de rapport a rencontré une erreur.")
            sys.exit(1)

        # La vérification des missing_packages est retirée.

    except Exception as e:
        logger.exception("Une erreur critique est survenue dans le script lanceur.")
        sys.exit(1)

if __name__ == "__main__":
    main()