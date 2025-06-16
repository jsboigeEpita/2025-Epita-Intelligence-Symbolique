#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour vérifier que la nouvelle structure du dossier agents fonctionne correctement.

Ce script:
1. Vérifie que tous les répertoires nécessaires existent
2. Vérifie que les fichiers ont été correctement déplacés
3. Vérifie que les imports dans les fichiers déplacés sont corrects
"""

import os
import sys
import importlib
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("VerifyStructure")

# Ajouter le répertoire racine au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
root_dir = parent_dir.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

def check_directories():
    """
    Vérifie que tous les répertoires nécessaires existent.
    
    Returns:
        bool: True si tous les répertoires existent, False sinon
    """
    logger.info("Vérification des répertoires...")
    
    required_dirs = [
        parent_dir / "test_scripts" / "informal",
        parent_dir / "test_scripts" / "orchestration",
        parent_dir / "analysis_scripts" / "informal",
        parent_dir / "analysis_scripts" / "orchestration",
        parent_dir / "optimization_scripts" / "informal",
        parent_dir / "documentation" / "reports",
        parent_dir / "execution_traces" / "informal",
        parent_dir / "execution_traces" / "orchestration",
        parent_dir / "run_scripts"
    ]
    
    all_exist = True
    for directory in required_dirs:
        if not directory.exists():
            logger.error(f"Répertoire manquant: {directory}")
            all_exist = False
        else:
            logger.info(f"Répertoire trouvé: {directory}")
    
    return all_exist

def check_files():
    """
    Vérifie que les fichiers ont été correctement déplacés.
    
    Returns:
        bool: True si tous les fichiers existent, False sinon
    """
    logger.info("Vérification des fichiers...")
    
    required_files = [
        parent_dir / "test_scripts" / "informal" / "test_informal_agent.py",
        parent_dir / "test_scripts" / "orchestration" / "test_orchestration_complete.py",
        parent_dir / "test_scripts" / "orchestration" / "test_orchestration_scale.py",
        parent_dir / "analysis_scripts" / "informal" / "analyse_traces_informal.py",
        parent_dir / "analysis_scripts" / "orchestration" / "analyse_trace_orchestration.py",
        parent_dir / "optimization_scripts" / "informal" / "ameliorer_agent_informal.py",
        parent_dir / "optimization_scripts" / "informal" / "comparer_performances_informal.py",
        parent_dir / "documentation" / "README_optimisation_informal.md",
        parent_dir / "documentation" / "README_test_orchestration_complete.md",
        parent_dir / "documentation" / "reports" / "rapport_test_orchestration_echelle.md",
        parent_dir / "run_scripts" / "run_complete_test_and_analysis.py"
    ]
    
    all_exist = True
    for file_path in required_files:
        if not file_path.exists():
            logger.error(f"Fichier manquant: {file_path}")
            all_exist = False
        else:
            logger.info(f"Fichier trouvé: {file_path}")
    
    return all_exist

def check_imports():
    """
    Vérifie que les imports dans les fichiers déplacés sont corrects.
    
    Returns:
        bool: True si tous les imports sont corrects, False sinon
    """
    logger.info("Vérification des imports...")
    
    # Liste des modules à importer pour vérifier qu'ils sont accessibles
    modules_to_check = [
        "agents.core.informal.informal_definitions",
        "agents.core.pl.pl_definitions",
        "agents.core.pm.pm_definitions",
        "agents.core.extract.extract_definitions"
    ]
    
    all_imports_ok = True
    for module_name in modules_to_check:
        try:
            importlib.import_module(module_name)
            logger.info(f"Module importé avec succès: {module_name}")
        except ImportError as e:
            logger.error(f"Erreur lors de l'import du module {module_name}: {e}")
            all_imports_ok = False
    
    return all_imports_ok

def main():
    """
    Fonction principale du script.
    """
    logger.info("Vérification de la structure du dossier agents...")
    
    # Vérifier les répertoires
    dirs_ok = check_directories()
    
    # Vérifier les fichiers
    files_ok = check_files()
    
    # Vérifier les imports
    imports_ok = check_imports()
    
    # Afficher le résultat global
    if dirs_ok and files_ok and imports_ok:
        logger.info("[OK] La structure du dossier agents est correcte.")
    else:
        logger.error("❌ La structure du dossier agents présente des problèmes.")
        
        if not dirs_ok:
            logger.error("  - Certains répertoires sont manquants.")
        
        if not files_ok:
            logger.error("  - Certains fichiers sont manquants.")
        
        if not imports_ok:
            logger.error("  - Certains imports sont incorrects.")
    
    logger.info("Vérification terminée.")

if __name__ == "__main__":
    main()