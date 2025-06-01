#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester individuellement les tests de test_informal_error_handling.py
"""

import sys
import os
import unittest
from io import StringIO

sys.path.append('.')

def test_individual_methods():
    """Teste chaque méthode individuellement"""
    
    try:
        from tests.test_informal_error_handling import TestInformalErrorHandling
        
        # Liste des méthodes de test
        test_methods = [
            'test_handle_empty_text',
            'test_handle_none_text', 
            'test_handle_fallacy_detector_exception',
            'test_handle_rhetorical_analyzer_exception',
            'test_handle_contextual_analyzer_exception',
            'test_handle_invalid_fallacy_detector_result',
            'test_handle_invalid_rhetorical_analyzer_result',
            'test_handle_missing_required_tool',
            'test_handle_invalid_tool_type',
            'test_handle_invalid_config',
            'test_handle_invalid_confidence_threshold',
            'test_handle_out_of_range_confidence_threshold',
            'test_handle_recovery_from_error'
        ]
        
        print("Test individuel des méthodes de test_informal_error_handling.py")
        print("=" * 70)
        
        successes = 0
        failures = 0
        
        for method_name in test_methods:
            print(f"\nTest: {method_name}")
            print("-" * 50)
            
            try:
                # Créer une nouvelle instance pour chaque test
                test_instance = TestInformalErrorHandling()
                test_instance.setUp()
                
                # Exécuter le test
                method = getattr(test_instance, method_name)
                method()
                
                print("SUCCES")
                successes += 1
                
            except Exception as e:
                print(f"ECHEC: {str(e)}")
                failures += 1
                
                # Afficher plus de détails sur l'erreur
                import traceback
                print("Détails de l'erreur:")
                traceback.print_exc()
        
        print(f"\n" + "=" * 70)
        print(f"RÉSUMÉ:")
        print(f"Succès: {successes}")
        print(f"Échecs: {failures}")
        print(f"Total: {len(test_methods)}")
        print(f"Taux de réussite: {(successes/len(test_methods)*100):.1f}%")
        
        assert failures == 0, f"{failures} tests failed in TestInformalErrorHandling"
        
    except Exception as e:
        print(f"Erreur lors de l'import ou de l'exécution des tests individuels: {e}")
        import traceback
        traceback.print_exc()
        raise # Re-raise pour que pytest le capture comme une erreur

if __name__ == "__main__":
    test_individual_methods()