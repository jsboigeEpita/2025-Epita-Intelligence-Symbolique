"""
Module d'exemples pour l'analyse d'argumentation.

Ce module fournit des exemples de textes et de données pour tester
et démontrer les fonctionnalités du package d'analyse d'argumentation.
"""

import os
from pathlib import Path

# Chemin vers le dossier examples à la racine du projet
EXAMPLES_ROOT = Path(__file__).parent.parent.parent / "examples"

def get_example_path(filename):
    """Retourne le chemin vers un fichier d'exemple."""
    return EXAMPLES_ROOT / filename

def list_examples():
    """Liste tous les fichiers d'exemples disponibles."""
    if EXAMPLES_ROOT.exists():
        return [f.name for f in EXAMPLES_ROOT.iterdir() if f.is_file()]
    return []

def load_example_text(filename):
    """Charge le contenu d'un fichier d'exemple."""
    example_path = get_example_path(filename)
    if example_path.exists():
        with open(example_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise FileNotFoundError(f"Exemple '{filename}' non trouvé dans {EXAMPLES_ROOT}")

# Exemples disponibles
AVAILABLE_EXAMPLES = list_examples() if EXAMPLES_ROOT.exists() else []