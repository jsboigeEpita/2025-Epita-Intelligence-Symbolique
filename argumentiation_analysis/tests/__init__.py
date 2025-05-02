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