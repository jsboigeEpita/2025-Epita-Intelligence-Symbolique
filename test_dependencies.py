"""
Script de test pour vérifier uniquement les dépendances externes du projet.
"""

import os
import sys

print("Test des dépendances externes:")

# Liste des dépendances à tester
dependencies = [
    "jpype1",
    "numpy",
    "pandas",
    "matplotlib",
    "cryptography",
    "semantic_kernel",
    "networkx",
    "jupyter_ui_poll",
    "ipywidgets",
    "transformers",
    "torch",
    "scikit-learn",
    "python-dotenv"
]

# Tester chaque dépendance
for dep in dependencies:
    try:
        if dep == "jpype1":
            import jpype
            print(f"✓ {dep} (version {jpype.__version__}) importé avec succès")
        elif dep == "numpy":
            import numpy
            print(f"✓ {dep} (version {numpy.__version__}) importé avec succès")
        elif dep == "pandas":
            import pandas
            print(f"✓ {dep} (version {pandas.__version__}) importé avec succès")
        elif dep == "matplotlib":
            import matplotlib
            print(f"✓ {dep} (version {matplotlib.__version__}) importé avec succès")
        elif dep == "cryptography":
            import cryptography
            print(f"✓ {dep} (version {cryptography.__version__}) importé avec succès")
        elif dep == "semantic_kernel":
            import semantic_kernel
            print(f"✓ {dep} (version {semantic_kernel.__version__}) importé avec succès")
        elif dep == "networkx":
            import networkx
            print(f"✓ {dep} (version {networkx.__version__}) importé avec succès")
        elif dep == "jupyter_ui_poll":
            import jupyter_ui_poll
            print(f"✓ {dep} importé avec succès")
        elif dep == "ipywidgets":
            import ipywidgets
            print(f"✓ {dep} (version {ipywidgets.__version__}) importé avec succès")
        elif dep == "transformers":
            import transformers
            print(f"✓ {dep} (version {transformers.__version__}) importé avec succès")
        elif dep == "torch":
            import torch
            print(f"✓ {dep} (version {torch.__version__}) importé avec succès")
        elif dep == "scikit-learn":
            import sklearn
            print(f"✓ {dep} (version {sklearn.__version__}) importé avec succès")
        elif dep == "python-dotenv":
            import dotenv
            print(f"✓ {dep} (version {dotenv.__version__}) importé avec succès")
    except ImportError as e:
        print(f"✗ {dep} n'a pas pu être importé: {e}")
    except AttributeError as e:
        print(f"✓ {dep} importé avec succès (version non disponible)")

print("\nTest terminé.")