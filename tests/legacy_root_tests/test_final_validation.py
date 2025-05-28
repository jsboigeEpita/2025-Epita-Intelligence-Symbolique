#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Runner de test final pour validation 100%"""

import unittest
import sys
import os
from pathlib import Path
import importlib.util

def setup_test_environment():
    """Configure l'environnement de test"""
    project_root = Path(__file__).parent.absolute()
    
    # Ajout des chemins au PYTHONPATH
    paths = [
        str(project_root),
        str(project_root / "tests"),
        str(project_root / "tests" / "mocks"),
        str(project_root / "argumentation_analysis"),
    ]
    
    for path in paths:
        if path not in sys.path:
            sys.path.insert(0, path)
    
    # Configuration de l'encodage
    os.environ['PYTHONIOENCODING'] = 'utf-8'

def run_final_tests():
    """Exécute tous les tests pour validation finale"""
    setup_test_environment()
    
    # Découverte et exécution des tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # Exécution avec rapport détaillé
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    # Calcul du taux de réussite
    total_tests = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_rate = ((total_tests - failures - errors) / total_tests * 100) if total_tests > 0 else 0
    
    print(f"\n{'='*50}")
    print(f"RÉSULTATS FINAUX")
    print(f"{'='*50}")
    print(f"Tests exécutés: {total_tests}")
    print(f"Échecs: {failures}")
    print(f"Erreurs: {errors}")
    print(f"Taux de réussite: {success_rate:.1f}%")
    
    if success_rate >= 100.0:
        print(f"\n🎉 OBJECTIF ATTEINT : 100% de réussite !")
        return True
    else:
        print(f"\n⚠️  Progrès: {success_rate:.1f}% de réussite")
        return False

if __name__ == "__main__":
    success = run_final_tests()
    sys.exit(0 if success else 1)
