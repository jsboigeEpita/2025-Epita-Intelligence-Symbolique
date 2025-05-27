#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de configuration automatique de l'environnement.
A executer avant d'utiliser le projet.
"""

import sys
from pathlib import Path

# Ajouter le projet au PYTHONPATH
project_root = Path(r"c:\dev\2025-Epita-Intelligence-Symbolique")
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("Configuration de l'environnement pour Intelligence Symbolique")
print(f"Repertoire projet: {project_root}")

# Tester les imports essentiels
try:
    import argumentation_analysis
    print("[OK] Package principal: SUCCES")
except ImportError as e:
    print(f"[ERROR] Package principal: {e}")

# Tester les dependances essentielles
essential_deps = ["numpy", "pandas", "matplotlib", "cryptography"]
for dep in essential_deps:
    try:
        __import__(dep)
        print(f"[OK] {dep}: SUCCES")
    except ImportError:
        print(f"[ERROR] {dep}: MANQUANT")

print("\nPour utiliser le projet:")
print("1. Executez ce script: python setup_env.py")
print("2. Puis utilisez Python normalement")
print("3. Ou importez ce module au debut de vos scripts")
