#!/usr/bin/env python3
"""
Script de démonstration : One-liner auto-activateur intelligent
=============================================================

Ce script montre comment les agents AI peuvent utiliser le one-liner
pour s'assurer automatiquement que l'environnement est actif avant d'exécuter
leur code, sans se soucier de l'état d'activation préalable.

Auteur: Intelligence Symbolique EPITA
Date: 09/06/2025
"""

# ===== ONE-LINER AUTO-ACTIVATEUR =====
# La ligne suivante s'assure que tout l'environnement est configuré.
import argumentation_analysis.core.environment

# ===== SCRIPT PRINCIPAL =====
import sys
import os
from datetime import datetime

def main():
    """Démonstration d'usage du one-liner"""
    
    print("=" * 60)
    print("DEMO : One-liner auto-activateur d'environnement")
    print("=" * 60)
    
    # Vérification que l'environnement est configuré
    print(f"\n[INFO] Python utilisé : {sys.executable}")
    print(f"[INFO] Version Python : {sys.version}")
    print(f"[INFO] Répertoire de travail : {os.getcwd()}")
    
    # Variables d'environnement du projet
    project_root = os.environ.get('PROJECT_ROOT', 'Non défini')
    python_path = os.environ.get('PYTHONPATH', 'Non défini')
    conda_env = os.environ.get('CONDA_DEFAULT_ENV', 'Non défini')
    
    print(f"\n[ENV] PROJECT_ROOT : {project_root}")
    print(f"[ENV] PYTHONPATH : {python_path}")
    print(f"[ENV] CONDA_DEFAULT_ENV : {conda_env}")
    
    # Test d'import de modules du projet
    try:
        from project_core.core_from_scripts.environment_manager import EnvironmentManager
        print(f"\n[OK] Import EnvironmentManager réussi")
        
        manager = EnvironmentManager()
        print(f"[OK] Instanciation EnvironmentManager réussie")
        
        if manager.check_conda_available():
            print(f"[OK] Conda disponible")
        else:
            print(f"[WARN] Conda non disponible")
            
    except ImportError as e:
        print(f"\n[ERROR] Erreur d'import : {e}")
    
    # Simulation d'une tâche que ferait un agent AI
    print(f"\n[TASK] Simulation tâche agent AI...")
    print(f"[TASK] Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"[TASK] Tâche exécutée avec succès dans l'environnement projet !")
    
    print(f"\n[SUCCESS] Démonstration terminée avec succès")
    print("=" * 60)


if __name__ == "__main__":
    # Le one-liner a déjà auto-activé l'environnement à l'import
    # On peut maintenant exécuter notre code en toute sécurité
    main()