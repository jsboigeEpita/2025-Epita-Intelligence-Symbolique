"""
Tests unitaires pour le projet d'analyse argumentative.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent (racine du projet) au PYTHONPATH
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))
print(f"Répertoire parent ajouté au PYTHONPATH: {parent_dir}")

def setup_import_paths():
    """
    Configure les chemins d'importation pour résoudre les problèmes d'imports relatifs.
    Cette fonction est utilisée par les tests d'intégration pour s'assurer que tous les modules
    du projet peuvent être importés correctement.
    """
    # Ajouter le répertoire parent (racine du projet) au début du PYTHONPATH
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    return parent_dir