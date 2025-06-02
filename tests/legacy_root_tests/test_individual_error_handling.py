#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester individuellement les tests de test_informal_error_handling.py
"""

import sys
import os
import unittest
from io import StringIO
import pytest # Ajout de l'import pytest

sys.path.append('.')

@pytest.mark.skip(reason="Test legacy incompatible avec la refonte Pytest de TestInformalErrorHandling")
def test_individual_methods():
    """Teste chaque méthode individuellement"""
    
    try:
        from tests.agents.core.informal.test_informal_error_handling import TestInformalErrorHandling
        
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
                # Note: TestInformalErrorHandling est maintenant une classe Pytest,
                # l'instancier et appeler setUp() directement n'est plus le mode d'emploi standard.
                # Ce script legacy pourrait nécessiter une refonte plus profonde pour fonctionner
                # correctement avec les tests de style Pytest qui attendent l'injection de fixtures.
                # Pour l'instant, on corrige l'import, mais l'exécution pourrait encore échouer.
                test_instance = TestInformalErrorHandling()
                if hasattr(test_instance, 'setUp'): # Vérifier si setUp existe toujours (improbable)
                    test_instance.setUp()
                
                # Exécuter le test
                method = getattr(test_instance, method_name)
                # Les méthodes de test Pytest attendent des fixtures, qui ne seront pas passées ici.
                # Cela va probablement échouer.
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
        print(f"Taux de réussite: {(successes/len(test_methods)*100) if len(test_methods) > 0 else 0:.1f}%")
        
        assert failures == 0, f"{failures} tests failed in TestInformalErrorHandling"
        
    except Exception as e:
        print(f"Erreur lors de l'import ou de l'exécution des tests individuels: {e}")
        import traceback
        traceback.print_exc()
        raise # Re-raise pour que pytest le capture comme une erreur

if __name__ == "__main__":
    test_individual_methods()