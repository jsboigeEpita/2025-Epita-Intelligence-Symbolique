"""
Package des tests pour le projet d'analyse d'argumentation.

Ce module initialise le package des tests et fournit des fonctions utilitaires
pour résoudre les problèmes d'imports relatifs.
"""

import os
import sys
from pathlib import Path


def setup_import_paths():
    """
    Configure les chemins d'importation pour résoudre les problèmes d'imports relatifs.
    
    Cette fonction ajoute le répertoire parent au chemin de recherche des modules,
    ce qui permet d'importer les modules du projet sans utiliser d'imports relatifs.
    """
    # Obtenir le chemin absolu du répertoire parent (racine du projet)
    parent_dir = Path(__file__).parent.parent.absolute()
    
    # Ajouter le répertoire parent au chemin de recherche des modules
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    # Ajouter également le répertoire du package argumentiation_analysis
    # pour permettre les imports absolus
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    return parent_dir


def fix_relative_imports():
    """
    Corrige les problèmes d'imports relatifs en utilisant des imports absolus.
    
    Cette fonction doit être appelée au début de chaque fichier de test
    qui utilise des imports relatifs.
    """
    # Obtenir le chemin absolu du répertoire parent
    parent_dir = setup_import_paths()
    
    # Afficher un message pour indiquer que les imports relatifs ont été corrigés
    print(f"Imports relatifs corrigés. Répertoire parent: {parent_dir}")


# Configurer les chemins d'importation au chargement du module
setup_import_paths()