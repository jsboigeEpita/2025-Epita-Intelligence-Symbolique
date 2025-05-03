#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script principal pour orchestrer l'optimisation de l'agent Informel.

Ce script permet de:
1. Analyser la taxonomie des sophismes
2. Améliorer l'agent Informel
3. Documenter les améliorations
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("OptimizeInformalAgent")

def run_command(cmd, description):
    """
    Exécute une commande système et affiche sa sortie.
    """
    logger.info(f"Exécution de: {description}")
    logger.debug(f"Commande: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        for line in result.stdout.splitlines():
            logger.info(f"[STDOUT] {line}")
        
        if result.stderr:
            for line in result.stderr.splitlines():
                logger.warning(f"[STDERR] {line}")
        
        logger.info(f"Commande terminée avec succès: {description}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"La commande a échoué avec le code de retour {e.returncode}")
        if e.stdout:
            for line in e.stdout.splitlines():
                logger.info(f"[STDOUT] {line}")
        if e.stderr:
            for line in e.stderr.splitlines():
                logger.error(f"[STDERR] {line}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la commande: {e}")
        return False

def analyze_taxonomy():
    """
    Analyse la taxonomie des sophismes.
    """
    logger.info("=== Phase 1: Analyse de la taxonomie des sophismes ===")
    
    script_path = Path("utils/informal_optimization/analyze_taxonomy_usage.py")
    if not script_path.exists():
        logger.error(f"Script d'analyse de la taxonomie non trouvé: {script_path}")
        return False
    
    return run_command(f"python {script_path}", "Analyse de la taxonomie des sophismes")

def improve_agent():
    """
    Améliore l'agent Informel.
    """
    logger.info("=== Phase 2: Amélioration de l'agent Informel ===")
    
    script_path = Path("utils/informal_optimization/improve_informal_agent.py")
    if not script_path.exists():
        logger.error(f"Script d'amélioration de l'agent non trouvé: {script_path}")
        return False
    
    return run_command(f"python {script_path}", "Amélioration de l'agent Informel")

def test_agent():
    """
    Teste l'agent Informel amélioré.
    """
    logger.info("=== Phase 3: Test de l'agent Informel amélioré ===")
    
    script_path = Path("test_informal_agent.py")
    if not script_path.exists():
        logger.error(f"Script de test de l'agent non trouvé: {script_path}")
        return False
    
    return run_command(f"python {script_path}", "Test de l'agent Informel amélioré")

def verify_documentation():
    """
    Vérifie que la documentation des améliorations est présente.
    """
    logger.info("=== Phase 4: Vérification de la documentation ===")
    
    doc_path = Path("utils/informal_optimization/documentation.md")
    if not doc_path.exists():
        logger.error(f"Documentation des améliorations non trouvée: {doc_path}")
        return False
    
    logger.info(f"Documentation des améliorations trouvée: {doc_path}")
    return True

def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage du processus d'optimisation de l'agent Informel...")
    
    # Phase 1: Analyse de la taxonomie
    if not analyze_taxonomy():
        logger.warning("L'analyse de la taxonomie a échoué, mais on continue...")
    
    # Phase 2: Amélioration de l'agent
    if not improve_agent():
        logger.error("L'amélioration de l'agent a échoué.")
        return
    
    # Phase 3: Test de l'agent amélioré
    if not test_agent():
        logger.warning("Le test de l'agent amélioré a échoué, mais on continue...")
    
    # Phase 4: Vérification de la documentation
    if not verify_documentation():
        logger.error("La documentation des améliorations est manquante.")
        return
    
    logger.info("Processus d'optimisation de l'agent Informel terminé avec succès.")
    logger.info("Consultez la documentation pour plus de détails sur les améliorations apportées.")

if __name__ == "__main__":
    main()