#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour effectuer une analyse rhétorique avancée sur les extraits déchiffrés.

Ce script:
1. Charge les extraits déchiffrés et les résultats de l'analyse de base
2. Utilise les outils d'analyse rhétorique améliorés suivants:
   - EnhancedComplexFallacyAnalyzer
   - EnhancedContextualFallacyAnalyzer
   - EnhancedFallacySeverityEvaluator
   - EnhancedRhetoricalResultAnalyzer
3. Analyse chaque extrait avec ces outils avancés
4. Génère un rapport d'analyse avancée pour chaque extrait
5. Compare les résultats avec ceux de l'analyse de base
6. Sauvegarde les résultats dans un format structuré (JSON)
"""

import os
import sys
import json
import logging
import argparse
import time
from pathlib import Path
from project_core.utils.cli_utils import parse_advanced_analysis_arguments
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from tqdm import tqdm

from project_core.utils.file_utils import load_extracts, load_base_analysis_results
from argumentation_analysis.utils.text_processing import split_text_into_arguments
from argumentation_analysis.utils.data_generation import generate_sample_text
from argumentation_analysis.utils.analysis_comparison import compare_rhetorical_analyses
from argumentation_analysis.mocks.advanced_tools import create_mock_advanced_rhetorical_tools
from argumentation_analysis.orchestration.advanced_analyzer import analyze_extract_advanced
from argumentation_analysis.pipelines.advanced_rhetoric import run_advanced_rhetoric_pipeline

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("AdvancedRhetoricalAnalysis")

# Le répertoire racine du projet a déjà été ajouté à sys.path (lignes 21-23)

# Vérifier les dépendances requises
required_packages = ["networkx", "numpy", "tqdm"]
missing_packages = []

for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        missing_packages.append(package)

# Import des outils d'analyse rhétorique améliorés
try:
    from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
    from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
    from argumentation_analysis.agents.tools.analysis.enhanced.rhetorical_result_analyzer import EnhancedRhetoricalResultAnalyzer
    
    logger.info("Outils d'analyse rhétorique améliorés importés avec succès")
except ImportError as e:
    logger.error(f"Erreur d'importation des outils d'analyse rhétorique améliorés: {e}")
    logger.error("Assurez-vous que le package argumentation_analysis est installé ou accessible.")
    sys.exit(1)
except Exception as e:
    logger.error(f"Erreur inattendue lors de l'initialisation: {e}")
    sys.exit(1)

if missing_packages:
    logger.warning(f"Les packages suivants sont manquants: {', '.join(missing_packages)}")
    logger.warning(f"Certaines fonctionnalités peuvent être limitées.")
    logger.warning(f"Pour installer les packages manquants: pip install {' '.join(missing_packages)}")
# La fonction analyze_extract_advanced a été déplacée vers argumentation_analysis.orchestration.advanced_analyzer
# La fonction analyze_extracts_advanced a été déplacée vers argumentation_analysis.pipelines.advanced_rhetoric
# La fonction parse_arguments a été déplacée vers project_core.utils.cli_utils sous le nom parse_advanced_analysis_arguments
def main():
    """Fonction principale du script."""
    # Analyser les arguments
    args = parse_advanced_analysis_arguments()
    
    # Configurer le niveau de logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé")
    
    logger.info("Démarrage de l'analyse rhétorique avancée des extraits...")
    
    # Trouver le fichier d'extraits le plus récent si non spécifié
    extracts_file = args.extracts
    if not extracts_file:
        temp_dir = Path("temp_extracts")
        if temp_dir.exists():
            extract_files = list(temp_dir.glob("extracts_decrypted_*.json"))
            if extract_files:
                # Trier par date de modification (la plus récente en premier)
                extract_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                extracts_file = extract_files[0]
                logger.info(f"Utilisation du fichier d'extraits le plus récent: {extracts_file}")
    
    if not extracts_file:
        logger.error("Aucun fichier d'extraits spécifié et aucun fichier d'extraits trouvé.")
        sys.exit(1)
    
    extracts_path = Path(extracts_file)
    if not extracts_path.exists():
        logger.error(f"Le fichier d'extraits {extracts_path} n'existe pas.")
        sys.exit(1)
    
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
        logger.warning("Aucun fichier de résultats de base spécifié et aucun fichier de résultats trouvé.")
        logger.warning("L'analyse avancée sera effectuée sans comparaison avec l'analyse de base.")
        base_results = []
    else:
        base_results_path = Path(base_results_file)
        if not base_results_path.exists():
            logger.warning(f"Le fichier de résultats de base {base_results_path} n'existe pas.")
            logger.warning("L'analyse avancée sera effectuée sans comparaison avec l'analyse de base.")
            base_results = []
        else:
            # Charger les résultats de l'analyse de base
            base_results = load_base_analysis_results(base_results_path)
            if not base_results:
                logger.warning("Aucun résultat de base n'a pu être chargé.")
                logger.warning("L'analyse avancée sera effectuée sans comparaison avec l'analyse de base.")
    
    # Définir le fichier de sortie si non spécifié
    output_file = args.output
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = Path("results") / f"advanced_rhetorical_analysis_{timestamp}.json"
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Charger les extraits
    extract_definitions = load_extracts(extracts_path)
    if not extract_definitions:
        logger.error("Aucun extrait n'a pu être chargé.")
        sys.exit(1)
    
    # Analyser les extraits avec les outils avancés
    # Le paramètre use_real_tools peut être ajouté ici si on veut le contrôler depuis les args CLI.
    # Pour l'instant, on utilise le comportement par défaut du pipeline (mocks si réels non dispo).
    run_advanced_rhetoric_pipeline(extract_definitions, base_results, output_path)
    
    logger.info("Analyse rhétorique avancée terminée avec succès.")

if __name__ == "__main__":
    main()