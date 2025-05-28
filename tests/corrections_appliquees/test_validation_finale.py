#!/usr/bin/env python3
"""
Runner de test simple pour validation des corrections
"""

import sys
import os
import unittest
import io
from pathlib import Path

# Configuration du projet
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

def run_specific_tests():
    """Exécuter des tests spécifiques pour validation"""
    print("=== VALIDATION DES CORRECTIONS ===")
    
    test_results = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'errors': 0
    }
    
    # Tests à valider
    test_cases = [
        ('tests.test_extract_agent_adapter', 'TestExtractAgentAdapter', 'test_initialization'),
        ('tests.test_load_extract_definitions', 'TestLoadExtractDefinitions', 'test_load_definitions_no_file'),
    ]
    
    for module_name, class_name, test_name in test_cases:
        try:
            print(f"\nTest: {module_name}.{class_name}.{test_name}")
            
            # Import du module
            module = __import__(module_name, fromlist=[class_name])
            test_class = getattr(module, class_name)
            
            # Création de la suite de test
            suite = unittest.TestSuite()
            suite.addTest(test_class(test_name))
            
            # Exécution du test
            stream = io.StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=0)
            result = runner.run(suite)
            
            test_results['total'] += result.testsRun
            test_results['passed'] += (result.testsRun - len(result.failures) - len(result.errors))
            test_results['failed'] += len(result.failures)
            test_results['errors'] += len(result.errors)
            
            if result.wasSuccessful():
                print("[OK] Test reussi")
            else:
                print(f"[WARN] Test echoue: {len(result.failures)} echecs, {len(result.errors)} erreurs")
                
        except Exception as e:
            print(f"[ERROR] Erreur test {module_name}: {e}")
            test_results['errors'] += 1
    
    # Résumé
    print(f"\n=== RESUME VALIDATION ===")
    print(f"Total tests: {test_results['total']}")
    print(f"Reussis: {test_results['passed']}")
    print(f"Echecs: {test_results['failed']}")
    print(f"Erreurs: {test_results['errors']}")
    
    if test_results['total'] > 0:
        success_rate = (test_results['passed'] / test_results['total']) * 100
        print(f"Taux de reussite: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("[OK] Corrections validees avec succes")
            return True
        else:
            print("[WARN] Corrections partiellement validees")
            return False
    else:
        print("[WARN] Aucun test execute")
        return False

if __name__ == "__main__":
    success = run_specific_tests()
    sys.exit(0 if success else 1)
