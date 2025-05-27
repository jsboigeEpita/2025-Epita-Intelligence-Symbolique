#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test final pour vérifier 100% de réussite des tests.
"""

import sys
import os
import unittest
from io import StringIO

sys.path.append('.')

def test_specific_files():
    """Teste spécifiquement les fichiers qui nous intéressent"""
    
    print("TEST FINAL POUR 100% DE REUSSITE")
    print("=" * 50)
    
    # Test test_informal_agent.py
    print("\n1. Test de test_informal_agent.py")
    print("-" * 30)
    
    try:
        from tests.test_informal_agent import TestInformalAgent
        
        suite = unittest.TestLoader().loadTestsFromTestCase(TestInformalAgent)
        stream = StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=0)
        result = runner.run(suite)
        
        print(f"Tests: {result.testsRun}")
        print(f"Échecs: {len(result.failures)}")
        print(f"Erreurs: {len(result.errors)}")
        
        if result.failures:
            print("ÉCHECS:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print("ERREURS:")
            for test, traceback in result.errors:
                print(f"  - {test}")
        
        if len(result.failures) == 0 and len(result.errors) == 0:
            print("✓ TOUS LES TESTS PASSENT")
        
    except Exception as e:
        print(f"Erreur lors du test: {e}")
    
    # Test test_informal_error_handling.py
    print("\n2. Test de test_informal_error_handling.py")
    print("-" * 30)
    
    try:
        from tests.test_informal_error_handling import TestInformalErrorHandling
        
        suite = unittest.TestLoader().loadTestsFromTestCase(TestInformalErrorHandling)
        stream = StringIO()
        runner = unittest.TextTestRunner(stream=stream, verbosity=0)
        result = runner.run(suite)
        
        print(f"Tests: {result.testsRun}")
        print(f"Échecs: {len(result.failures)}")
        print(f"Erreurs: {len(result.errors)}")
        
        if result.failures:
            print("ÉCHECS:")
            for test, traceback in result.failures:
                print(f"  - {test}")
                print(f"    Erreur: {traceback.split('AssertionError: ')[-1].split('\\n')[0] if 'AssertionError: ' in traceback else 'Erreur inconnue'}")
        
        if result.errors:
            print("ERREURS:")
            for test, traceback in result.errors:
                print(f"  - {test}")
                print(f"    Erreur: {traceback.split('\\n')[-2] if '\\n' in traceback else traceback}")
        
        if len(result.failures) == 0 and len(result.errors) == 0:
            print("✓ TOUS LES TESTS PASSENT")
        
    except Exception as e:
        print(f"Erreur lors du test: {e}")
    
    # Calcul du total
    print("\n" + "=" * 50)
    print("RÉSUMÉ FINAL")
    print("=" * 50)
    
    try:
        from tests.test_informal_agent import TestInformalAgent
        from tests.test_informal_error_handling import TestInformalErrorHandling
        
        # Test test_informal_agent.py
        suite1 = unittest.TestLoader().loadTestsFromTestCase(TestInformalAgent)
        stream1 = StringIO()
        runner1 = unittest.TextTestRunner(stream=stream1, verbosity=0)
        result1 = runner1.run(suite1)
        
        # Test test_informal_error_handling.py
        suite2 = unittest.TestLoader().loadTestsFromTestCase(TestInformalErrorHandling)
        stream2 = StringIO()
        runner2 = unittest.TextTestRunner(stream=stream2, verbosity=0)
        result2 = runner2.run(suite2)
        
        total_tests = result1.testsRun + result2.testsRun
        total_failures = len(result1.failures) + len(result2.failures)
        total_errors = len(result1.errors) + len(result2.errors)
        total_success = total_tests - total_failures - total_errors
        
        success_rate = (total_success / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total tests: {total_tests}")
        print(f"Succès: {total_success}")
        print(f"Échecs: {total_failures}")
        print(f"Erreurs: {total_errors}")
        print(f"Taux de réussite: {success_rate:.1f}%")
        
        if success_rate == 100.0:
            print("\n🎉 100% DE RÉUSSITE ATTEINT! 🎉")
        else:
            print(f"\n⚠️  Il reste {total_failures + total_errors} test(s) à corriger")
        
    except Exception as e:
        print(f"Erreur lors du calcul final: {e}")

if __name__ == "__main__":
    test_specific_files()