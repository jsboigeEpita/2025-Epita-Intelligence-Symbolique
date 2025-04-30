#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour exécuter tous les tests unitaires du projet.

Ce script découvre et exécute tous les tests unitaires dans le répertoire tests.
Il génère également un rapport de couverture de code si le module coverage est installé.
"""

import unittest
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Essayer d'importer coverage pour générer un rapport de couverture
try:
    import coverage
    has_coverage = True
except ImportError:
    has_coverage = False
    print("Module 'coverage' non trouvé. Le rapport de couverture ne sera pas généré.")
    print("Pour installer coverage: pip install coverage")


def run_tests():
    """Exécute tous les tests unitaires."""
    # Découvrir et charger tous les tests
    loader = unittest.TestLoader()
    tests = loader.discover(start_dir=current_dir, pattern="test_*.py")
    
    # Créer un runner de test
    runner = unittest.TextTestRunner(verbosity=2)
    
    # Exécuter les tests
    result = runner.run(tests)
    
    # Retourner le code de sortie approprié
    return 0 if result.wasSuccessful() else 1


def run_tests_with_coverage():
    """Exécute tous les tests unitaires avec couverture de code."""
    # Initialiser coverage
    cov = coverage.Coverage(
        source=[str(parent_dir)],
        omit=[
            "*/__pycache__/*",
            "*/tests/*",
            "*/venv/*",
            "*/env/*",
            "*/site-packages/*"
        ]
    )
    
    # Démarrer la mesure de couverture
    cov.start()
    
    try:
        # Exécuter les tests
        result = run_tests()
        
        # Arrêter la mesure de couverture
        cov.stop()
        
        # Générer le rapport
        print("\n--- Rapport de couverture ---")
        cov.report()
        
        # Générer un rapport HTML si le répertoire htmlcov existe ou peut être créé
        try:
            htmlcov_dir = current_dir / "htmlcov"
            htmlcov_dir.mkdir(exist_ok=True)
            cov.html_report(directory=str(htmlcov_dir))
            print(f"\nRapport HTML généré dans {htmlcov_dir}")
        except Exception as e:
            print(f"Impossible de générer le rapport HTML: {e}")
        
        return result
    except Exception as e:
        print(f"Erreur lors de l'exécution des tests avec couverture: {e}")
        return 1


if __name__ == "__main__":
    print("=== Tests Unitaires - Projet d'Analyse Argumentative ===\n")
    
    # Exécuter les tests avec ou sans couverture
    if has_coverage:
        sys.exit(run_tests_with_coverage())
    else:
        sys.exit(run_tests())