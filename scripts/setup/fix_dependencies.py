#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour résoudre les problèmes de dépendances pour les tests.

Ce script installe les versions compatibles de numpy, pandas et autres dépendances
nécessaires pour exécuter les tests.
"""

import subprocess
import sys
import os
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("fix_dependencies")

def install_package(package, version=None):
    """
    Installe un package Python avec pip.
    
    Args:
        package: Nom du package à installer
        version: Version spécifique à installer (optionnel)
    
    Returns:
        True si l'installation a réussi, False sinon
    """
    try:
        if version:
            package_spec = f"{package}=={version}"
        else:
            package_spec = package
        
        logger.info(f"Installation de {package_spec}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_spec])
        logger.info(f"Installation de {package_spec} réussie.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors de l'installation de {package_spec}: {e}")
        return False

def fix_numpy():
    """
    Résout les problèmes d'importation de numpy.
    
    Returns:
        True si la résolution a réussi, False sinon
    """
    # Installer une version spécifique de numpy connue pour être compatible
    return install_package("numpy", "1.24.3")

def fix_pandas():
    """
    Résout les problèmes d'importation de pandas.
    
    Returns:
        True si la résolution a réussi, False sinon
    """
    # Installer une version spécifique de pandas connue pour être compatible
    return install_package("pandas", "2.0.3")

def fix_jpype():
    """
    Résout les problèmes d'importation de jpype.
    
    Returns:
        True si la résolution a réussi, False sinon
    """
    # Installer une version spécifique de jpype connue pour être compatible
    return install_package("JPype1", "1.4.1")

def fix_all_dependencies():
    """
    Résout tous les problèmes de dépendances.
    
    Returns:
        True si toutes les résolutions ont réussi, False sinon
    """
    success = True
    
    # Résoudre les problèmes de numpy
    if not fix_numpy():
        success = False
    
    # Résoudre les problèmes de pandas
    if not fix_pandas():
        success = False
    
    # Résoudre les problèmes de jpype
    if not fix_jpype():
        success = False
    
    return success

if __name__ == "__main__":
    logger.info("Résolution des problèmes de dépendances pour les tests...")
    
    if fix_all_dependencies():
        logger.info("Tous les problèmes de dépendances ont été résolus avec succès.")
        sys.exit(0)
    else:
        logger.error("Certains problèmes de dépendances n'ont pas pu être résolus.")
        sys.exit(1)