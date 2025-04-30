#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour exécuter les tests unitaires avec couverture de code.

Ce script exécute tous les tests unitaires et génère un rapport de couverture
détaillé au format HTML. Il définit également un objectif de couverture minimal.
"""

import unittest
import sys
import os
import webbrowser
from pathlib import Path

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

# Objectif de couverture minimal (en pourcentage)
COVERAGE_TARGET = 80

# Essayer d'importer coverage
try:
    import coverage
    has_coverage = True
except ImportError:
    has_coverage = False
    print("Module 'coverage' non trouvé. Le rapport de couverture ne sera pas généré.")
    print("Pour installer coverage: pip install coverage")


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
            "*/.venv/*",
            "*/site-packages/*",
            "*/dist-packages/*",
            "*/ui/*",  # Exclure l'interface utilisateur
            "*/main_*.py",  # Exclure les scripts principaux
            "*/run_*.py",  # Exclure les scripts d'exécution
        ]
    )
    
    # Démarrer la mesure de couverture
    cov.start()
    
    try:
        # Découvrir et charger tous les tests
        loader = unittest.TestLoader()
        tests = loader.discover(start_dir=current_dir, pattern="test_*.py")
        
        # Créer un runner de test
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Exécuter les tests
        print("\n=== Exécution des tests unitaires avec couverture ===\n")
        result = runner.run(tests)
        
        # Arrêter la mesure de couverture
        cov.stop()
        
        # Générer le rapport
        print("\n=== Rapport de couverture ===\n")
        total_coverage = cov.report()
        
        # Générer un rapport HTML
        htmlcov_dir = current_dir / "htmlcov"
        htmlcov_dir.mkdir(exist_ok=True)
        cov.html_report(directory=str(htmlcov_dir))
        
        # Générer un rapport XML pour l'intégration CI/CD
        cov.xml_report(outfile=str(current_dir / "coverage.xml"))
        
        print(f"\nRapport HTML généré dans {htmlcov_dir}")
        print(f"Rapport XML généré dans {current_dir / 'coverage.xml'}")
        
        # Vérifier si l'objectif de couverture est atteint
        if total_coverage < COVERAGE_TARGET:
            print(f"\n⚠️ ATTENTION: La couverture de code ({total_coverage:.2f}%) est inférieure à l'objectif ({COVERAGE_TARGET}%).")
            print("Veuillez ajouter plus de tests pour améliorer la couverture.")
        else:
            print(f"\n✅ SUCCÈS: La couverture de code ({total_coverage:.2f}%) atteint l'objectif ({COVERAGE_TARGET}%).")
        
        # Ouvrir le rapport HTML dans le navigateur
        index_html = htmlcov_dir / "index.html"
        if index_html.exists():
            try:
                print("\nOuverture du rapport HTML dans le navigateur...")
                webbrowser.open(f"file://{index_html}")
            except Exception as e:
                print(f"Impossible d'ouvrir le navigateur: {e}")
                print(f"Veuillez ouvrir manuellement le fichier: {index_html}")
        
        # Retourner le code de sortie approprié
        return 0 if result.wasSuccessful() and total_coverage >= COVERAGE_TARGET else 1
    
    except Exception as e:
        print(f"Erreur lors de l'exécution des tests avec couverture: {e}")
        return 1


def run_tests_without_coverage():
    """Exécute tous les tests unitaires sans couverture de code."""
    try:
        # Découvrir et charger tous les tests
        loader = unittest.TestLoader()
        tests = loader.discover(start_dir=current_dir, pattern="test_*.py")
        
        # Créer un runner de test
        runner = unittest.TextTestRunner(verbosity=2)
        
        # Exécuter les tests
        print("\n=== Exécution des tests unitaires sans couverture ===\n")
        result = runner.run(tests)
        
        # Retourner le code de sortie approprié
        return 0 if result.wasSuccessful() else 1
    
    except Exception as e:
        print(f"Erreur lors de l'exécution des tests: {e}")
        return 1


if __name__ == "__main__":
    print("=== Tests Unitaires - Projet d'Analyse Argumentative ===\n")
    
    # Exécuter les tests avec ou sans couverture
    if has_coverage:
        print("Exécution des tests avec couverture de code...")
        exit_code = run_tests_with_coverage()
    else:
        print("Exécution des tests sans couverture de code...")
        exit_code = run_tests_without_coverage()
    
    # Sortir avec le code approprié
    sys.exit(exit_code)