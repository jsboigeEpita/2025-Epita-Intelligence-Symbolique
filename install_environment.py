#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script d'installation automatique pour les étudiants.
Ce script configure automatiquement l'environnement de développement.
"""

import sys
import subprocess
import os
from pathlib import Path

def run_command(cmd):
    """Exécute une commande et affiche le résultat."""
    print(f"Exécution: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Erreur: {result.stderr}")
        return False
    return True

def main():
    """Installation automatique."""
    print("Installation automatique de l'environnement...")
    print("=" * 50)
    
    # Vérifier Python
    print(f"Python version: {sys.version}")
    
    # Mettre à jour pip
    print("\nMise a jour de pip...")
    run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Installer le package en mode développement
    print("\nInstallation du package en mode developpement...")
    if not run_command([sys.executable, "-m", "pip", "install", "-e", "."]):
        print("❌ Échec de l'installation du package")
        return False
    
    # Installer les dépendances essentielles
    print("\nInstallation des dependances essentielles...")
    essential_deps = [
        "numpy>=1.24.0", "pandas>=2.0.0", "matplotlib>=3.5.0",
        "cryptography>=37.0.0", "cffi>=1.15.0", "psutil>=5.9.0",
        "pytest>=7.0.0", "pytest-cov>=3.0.0"
    ]
    
    if not run_command([sys.executable, "-m", "pip", "install"] + essential_deps):
        print("⚠️  Problème lors de l'installation des dépendances")
    
    # Configurer JPype
    print("\nConfiguration de JPype...")
    python_version = sys.version_info
    if python_version >= (3, 12):
        print("Python 3.12+ détecté, utilisation du mock JPype")
        # Le mock sera configuré automatiquement
    else:
        print("Tentative d'installation de JPype1...")
        run_command([sys.executable, "-m", "pip", "install", "jpype1>=1.4.0"])
    
    # Validation finale
    print("\nValidation de l'installation...")
    validation_result = subprocess.run([
        sys.executable, "scripts/setup/validate_environment.py"
    ], capture_output=True, text=True)
    
    if validation_result.returncode == 0:
        print("Installation reussie!")
        print("\nVous pouvez maintenant:")
        print("  - Exécuter les tests: pytest")
        print("  - Utiliser les notebooks: jupyter notebook")
        print("  - Consulter la documentation: docs/")
    else:
        print("Installation partiellement reussie")
        print("Consultez le rapport de diagnostic pour plus de détails")
    
    return validation_result.returncode == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
