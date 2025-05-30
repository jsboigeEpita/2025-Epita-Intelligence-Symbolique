#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de configuration automatique de l'environnement.
A executer avant d'utiliser le projet.
"""

import sys
import os # Ajout pour la portabilité

# Ajouter le projet au PYTHONPATH
# Obtenir le répertoire du script actuel (qui est la racine du projet)
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
