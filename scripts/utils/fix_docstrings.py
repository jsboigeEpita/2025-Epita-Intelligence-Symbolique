#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour corriger les docstrings dans un fichier Python.
"""

import argumentation_analysis.core.environment
import os
import sys
from pathlib import Path  # NOUVEAU: Pour ajuster sys.path

# Ajout du répertoire parent au chemin pour permettre l'import des modules du projet
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    from argumentation_analysis.utils.dev_tools.format_utils import (
        fix_docstrings_apostrophes,
    )
except ImportError as e:
    print(f"Erreur d'importation: {e}")
    print("Assurez-vous que project_core.dev_utils.format_utils est accessible.")
    print("Vérifiez votre PYTHONPATH ou la structure du projet.")
    sys.exit(1)

# La fonction fix_docstrings a été déplacée et renommée fix_docstrings_apostrophes
# dans project_core.dev_utils.format_utils

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python fix_docstrings.py <file_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.isfile(file_path):
        print(f"Le fichier n'existe pas : {file_path}")
        sys.exit(1)

    print(f"--- Lancement de la correction des apostrophes pour : {file_path} ---")
    success = fix_docstrings_apostrophes(file_path)

    if success:
        print(f"✅ Correction des apostrophes terminée avec succès pour {file_path}.")
    else:
        print(f"❌ Échec de la correction des apostrophes pour {file_path}.")
        sys.exit(1)
