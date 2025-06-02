#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour exécuter tous les tests des outils d'analyse rhétorique améliorés.

Ce script exécute tous les tests unitaires, d'intégration et de performance
pour les outils d'analyse rhétorique améliorés et génère un rapport de couverture.
"""

import os
import sys
import unittest
import coverage
import argparse
from pathlib import Path
import time
import datetime

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
parent_dir = current_dir.parent.parent
if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))


def run_tests(test_type="all", verbose=False, coverage_report=False):
    """
    Exécute les tests spécifiés et génère un rapport de couverture si demandé.
    
    Args:
        test_type: Type de tests à exécuter (all, unit, integration, performance)
        verbose: Afficher les détails des tests
        coverage_report: Générer un rapport de couverture
    
    Returns:
        True si tous les tests ont réussi, False sinon
    """
    # Définir le niveau de verbosité
    verbosity = 2 if verbose else 1
    
    # Créer le répertoire de rapports s'il n'existe pas
    reports_dir = current_dir / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Initialiser la couverture si demandé
    cov = None
    if coverage_report:
        cov = coverage.Coverage(
            source=["argumentation_analysis.agents.tools.analysis"],
            omit=["*/__pycache__/*", "*/test_*", "*/__init__.py"]
        )
        cov.start()
    
    # Créer le test loader
    loader = unittest.TestLoader()
    
    # Créer la suite de tests en fonction du type de tests
    suite = unittest.TestSuite()
    
    if test_type in ["all", "unit"]:
        # Ajouter les tests unitaires
        print("Ajout des tests unitaires...")
        unit_tests = [
            "test_enhanced_complex_fallacy_analyzer.py",
            "test_enhanced_contextual_fallacy_analyzer.py",
            "test_enhanced_fallacy_severity_evaluator.py",
            "test_enhanced_rhetorical_result_analyzer.py",
            "test_enhanced_rhetorical_result_visualizer.py",
            "test_semantic_argument_analyzer.py",
            "test_contextual_fallacy_detector.py",
            "test_argument_coherence_evaluator.py",
            "test_argument_structure_visualizer.py"
        ]
        
        for test_file in unit_tests:
            test_path = current_dir / test_file
            if test_path.exists():
                module_name = f"argumentation_analysis.tests.tools.{test_file[:-3]}"
                try:
                    tests = loader.loadTestsFromName(module_name)
                    suite.addTests(tests)
                    print(f"  - {test_file} ajouté")
                except Exception as e:
                    print(f"  - Erreur lors du chargement de {test_file}: {e}")
            else:
                print(f"  - {test_file} non trouvé")
    
    if test_type in ["all", "integration"]:
        # Ajouter les tests d'intégration
        print("Ajout des tests d'intégration...")
        integration_test_file = "test_rhetorical_tools_integration.py"
        test_path = current_dir / integration_test_file
        
        if test_path.exists():
            module_name = f"argumentation_analysis.tests.tools.{integration_test_file[:-3]}"
            try:
                tests = loader.loadTestsFromName(module_name)
                suite.addTests(tests)
                print(f"  - {integration_test_file} ajouté")
            except Exception as e:
                print(f"  - Erreur lors du chargement de {integration_test_file}: {e}")
        else:
            print(f"  - {integration_test_file} non trouvé")
    
    if test_type in ["all", "performance"]:
        # Ajouter les tests de performance
        print("Ajout des tests de performance...")
        performance_test_file = "test_rhetorical_tools_performance.py"
        test_path = current_dir / performance_test_file
        
        if test_path.exists():
            module_name = f"argumentation_analysis.tests.tools.{performance_test_file[:-3]}"
            try:
                tests = loader.loadTestsFromName(module_name)
                suite.addTests(tests)
                print(f"  - {performance_test_file} ajouté")
            except Exception as e:
                print(f"  - Erreur lors du chargement de {performance_test_file}: {e}")
        else:
            print(f"  - {performance_test_file} non trouvé")
    
    # Exécuter les tests
    print("\nExécution des tests...")
    start_time = time.time()
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)
    
    end_time = time.time()
    execution_time = end_time - start_time
    
    # Afficher les résultats
    print(f"\nRésultats des tests:")
    print(f"  - Tests exécutés: {result.testsRun}")
    print(f"  - Tests réussis: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  - Tests échoués: {len(result.failures)}")
    print(f"  - Erreurs: {len(result.errors)}")
    print(f"  - Temps d'exécution: {execution_time:.2f} secondes")
    
    # Générer le rapport de couverture si demandé
    if coverage_report and cov:
        print("\nGénération du rapport de couverture...")
        cov.stop()
        
        # Générer le rapport HTML
        html_report_dir = reports_dir / "coverage_html"
        html_report_dir.mkdir(exist_ok=True)
        cov.html_report(directory=str(html_report_dir))
        
        # Générer le rapport XML
        xml_report_path = reports_dir / "coverage.xml"
        cov.xml_report(outfile=str(xml_report_path))
        
        # Afficher le résumé
        print("\nRésumé de la couverture:")
        cov.report()
        
        print(f"\nRapport HTML généré dans: {html_report_dir}")
        print(f"Rapport XML généré dans: {xml_report_path}")
    
    # Générer un rapport de test
    report_path = reports_dir / f"test_report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"Rapport de Tests des Outils d'Analyse Rhétorique Améliorés\n")
        f.write(f"==========================================================\n\n")
        f.write(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Type de tests: {test_type}\n\n")
        f.write(f"Résultats des tests:\n")
        f.write(f"  - Tests exécutés: {result.testsRun}\n")
        f.write(f"  - Tests réussis: {result.testsRun - len(result.failures) - len(result.errors)}\n")
        f.write(f"  - Tests échoués: {len(result.failures)}\n")
        f.write(f"  - Erreurs: {len(result.errors)}\n")
        f.write(f"  - Temps d'exécution: {execution_time:.2f} secondes\n\n")
        
        if result.failures:
            f.write(f"Tests échoués:\n")
            for i, (test, traceback) in enumerate(result.failures):
                f.write(f"  {i+1}. {test}\n")
                f.write(f"{traceback}\n\n")
        
        if result.errors:
            f.write(f"Erreurs:\n")
            for i, (test, traceback) in enumerate(result.errors):
                f.write(f"  {i+1}. {test}\n")
                f.write(f"{traceback}\n\n")
    
    print(f"\nRapport de test généré dans: {report_path}")
    
    return len(result.failures) == 0 and len(result.errors) == 0


def main():
    """
    Fonction principale.
    """
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="Exécuter les tests des outils d'analyse rhétorique améliorés")
    parser.add_argument("--type", choices=["all", "unit", "integration", "performance"], default="all",
                        help="Type de tests à exécuter (all, unit, integration, performance)")
    parser.add_argument("--verbose", action="store_true", help="Afficher les détails des tests")
    parser.add_argument("--coverage", action="store_true", help="Générer un rapport de couverture")
    
    args = parser.parse_args()
    
    # Exécuter les tests
    success = run_tests(args.type, args.verbose, args.coverage)
    
    # Retourner le code de sortie
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()