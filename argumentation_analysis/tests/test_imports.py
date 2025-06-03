# -*- coding: utf-8 -*-
"""
Script temporaire pour tester les importations.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent (racine du projet) au PYTHONPATH
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))
print(f"Répertoire parent ajouté au PYTHONPATH: {parent_dir}")

# Test d'importation simple
try:
    from argumentation_analysis.core import shared_state
    from argumentation_analysis.agents.extract import extract_agent
    from argumentation_analysis.orchestration import analysis_runner
    print("[SUCCES] Importations réussies!")
except ImportError as e:
    print(f"[ERREUR] Erreur d'importation: {e}")