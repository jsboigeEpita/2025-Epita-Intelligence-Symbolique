#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vérification rapide de l'environnement - Oracle Enhanced v2.1.0

Script de diagnostic léger pour vérification immédiate de l'environnement.
"""

import sys
import os
from pathlib import Path

# Auto-configuration du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def quick_environment_check():
    """Vérification rapide de l'environnement."""
    print("[LOUPE] VÉRIFICATION RAPIDE ENVIRONNEMENT")
    print("=" * 40)
    
    # 1. Environnement actuel
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', 'N/A')
    virtual_env = os.environ.get('VIRTUAL_ENV')
    
    if conda_env == "projet-is":
        print("[OK] Environnement: OPTIMAL (projet-is)")
        env_status = "optimal"
    elif conda_env and conda_env != "N/A":
        print(f"[ATTENTION]  Environnement: CONDA ({conda_env})")
        env_status = "acceptable"
    elif virtual_env:
        venv_name = Path(virtual_env).name
        print(f"ℹ️  Environnement: VENV ({venv_name})")
        env_status = "acceptable"
    else:
        print("[X] Environnement: SYSTÈME (non recommandé)")
        env_status = "problematic"
    
    # 2. Python
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    if python_version == "3.10":
        print(f"[OK] Python: {python_version} (optimal)")
    else:
        print(f"[ATTENTION]  Python: {python_version} (recommandé: 3.10)")
    
    # 3. PYTHONPATH
    if str(PROJECT_ROOT) in sys.path:
        print("[OK] PYTHONPATH: Configuré")
    else:
        print("[X] PYTHONPATH: Non configuré")
    
    # 4. Dépendances critiques
    critical_imports = ["numpy", "pandas", "semantic_kernel", "pytest"]
    missing = []
    
    for module in critical_imports:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    if not missing:
        print("[OK] Dépendances: Toutes disponibles")
    else:
        print(f"[X] Dépendances: {len(missing)} manquantes ({', '.join(missing)})")
    
    # 5. Résumé
    print("\n" + "=" * 40)
    
    if env_status == "optimal" and not missing:
        print("🎉 STATUT: ENVIRONNEMENT OPTIMAL")
        return 0
    elif env_status != "problematic" and len(missing) <= 2:
        print("[ATTENTION]  STATUT: ENVIRONNEMENT ACCEPTABLE")
        print("[AMPOULE] Améliorations recommandées disponibles")
        return 0
    else:
        print("[X] STATUT: ENVIRONNEMENT PROBLÉMATIQUE")
        print("\n[CLE] SOLUTION RECOMMANDÉE:")
        print("1. Créer l'environnement: conda env create -f environment.yml")
        print("2. Activer: conda activate projet-is")
        print("3. Ou utiliser: .\\setup_project_env.ps1 -CommandToRun \"<votre-commande>\"")
        return 1

def main():
    """Point d'entrée principal."""
    try:
        return quick_environment_check()
    except Exception as e:
        print(f"[X] Erreur lors de la vérification: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())