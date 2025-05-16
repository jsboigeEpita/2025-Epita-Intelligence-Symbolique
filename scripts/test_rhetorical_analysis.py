#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour l'analyse rhétorique des extraits.

Ce script exécute le script d'analyse rhétorique autonome avec des paramètres par défaut
et vérifie que les résultats sont générés correctement.
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("TestRhetoricalAnalysis")

def run_rhetorical_analysis():
    """
    Exécute le script d'analyse rhétorique avec des paramètres par défaut.
    
    Returns:
        bool: True si l'exécution a réussi, False sinon
    """
    logger.info("Exécution du script d'analyse rhétorique...")
    
    # Chemin vers le script d'analyse rhétorique autonome
    script_path = Path(__file__).parent / "rhetorical_analysis_standalone.py"
    
    # Vérifier que le script existe
    if not script_path.exists():
        logger.error(f"Le script {script_path} n'existe pas.")
        return False
    
    # Exécuter le script
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--verbose"],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Afficher la sortie du script
        logger.info("Sortie du script:")
        for line in result.stdout.splitlines():
            logger.info(f"  {line}")
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'exécution du script: {e}")
        logger.error(f"Sortie d'erreur: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return False

def verify_results():
    """
    Vérifie que les résultats de l'analyse rhétorique ont été générés correctement.
    
    Returns:
        bool: True si les résultats sont valides, False sinon
    """
    logger.info("Vérification des résultats...")
    
    # Trouver le fichier de résultats le plus récent
    results_dir = Path("results")
    result_files = list(results_dir.glob("rhetorical_analysis_*.json"))
    
    if not result_files:
        logger.error("Aucun fichier de résultats trouvé.")
        return False
    
    # Trier par date de modification (la plus récente en premier)
    result_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    latest_result_file = result_files[0]
    
    logger.info(f"Fichier de résultats le plus récent: {latest_result_file}")
    
    # Charger les résultats
    try:
        with open(latest_result_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Vérifier que les résultats contiennent des analyses
        if not results:
            logger.error("Le fichier de résultats est vide.")
            return False
        
        # Vérifier que chaque résultat contient les analyses attendues
        for i, result in enumerate(results):
            if "analyses" not in result:
                logger.error(f"Le résultat {i} ne contient pas d'analyses.")
                return False
            
            analyses = result["analyses"]
            if "contextual_fallacies" not in analyses:
                logger.error(f"Le résultat {i} ne contient pas d'analyse de sophismes contextuels.")
                return False
            
            if "argument_coherence" not in analyses:
                logger.error(f"Le résultat {i} ne contient pas d'analyse de cohérence argumentative.")
                return False
            
            if "semantic_analysis" not in analyses:
                logger.error(f"Le résultat {i} ne contient pas d'analyse sémantique.")
                return False
        
        logger.info(f"✅ {len(results)} résultats d'analyse vérifiés avec succès.")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la vérification des résultats: {e}")
        return False

def main():
    """Fonction principale du script."""
    logger.info("Démarrage du test d'analyse rhétorique...")
    
    # Exécuter le script d'analyse rhétorique
    if not run_rhetorical_analysis():
        logger.error("❌ Le test a échoué: erreur lors de l'exécution du script d'analyse rhétorique.")
        sys.exit(1)
    
    # Vérifier les résultats
    if not verify_results():
        logger.error("❌ Le test a échoué: erreur lors de la vérification des résultats.")
        sys.exit(1)
    
    logger.info("✅ Test d'analyse rhétorique réussi.")

if __name__ == "__main__":
    main()