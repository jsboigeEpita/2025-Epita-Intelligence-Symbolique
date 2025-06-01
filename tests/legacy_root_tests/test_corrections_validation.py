#!/usr/bin/env python3
"""
Script de validation des corrections effectuées
"""
import sys
import os
sys.path.insert(0, '.')

def test_conftest_import():
    """Test import conftest.py"""
    try:
        import tests.conftest
        print("✓ conftest.py importé avec succès")
        # Test passes if import is successful
    except Exception as e:
        print(f"✗ Erreur conftest: {e}")
        raise

def test_analysis_runner():
    """Test AnalysisRunner avec nouvelles méthodes"""
    try:
        from argumentation_analysis.orchestration.analysis_runner import AnalysisRunner
        runner = AnalysisRunner()
        
        methods = ['generate_report', 'run_analysis', 'run_multi_document_analysis']
        all_present = True
        
        for method in methods:
            if hasattr(runner, method):
                print(f"✓ {method} disponible")
            else:
                print(f"✗ {method} manquant")
                all_present = False
        
        assert all_present is True
    except Exception as e:
        print(f"✗ Erreur AnalysisRunner: {e}")
        raise

def test_numpy_mock():
    """Test mock numpy"""
    try:
        # Simuler l'import avec mock
        import unittest.mock
        with unittest.mock.patch.dict('sys.modules', {'numpy': unittest.mock.MagicMock()}):
            import numpy as np
            print("✓ numpy mock fonctionne")
            # Test passes if mock import is successful
    except Exception as e:
        print(f"✗ Erreur numpy mock: {e}")
        raise

def main():
    print("=== VALIDATION DES CORRECTIONS ===")
    
    tests = [
        ("Configuration conftest", test_conftest_import),
        ("AnalysisRunner méthodes", test_analysis_runner),
        ("Mock NumPy", test_numpy_mock),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        result = test_func()
        results.append((name, result))
    
    print("\n=== RÉSUMÉ ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nRésultat: {passed}/{total} tests passés")
    
    if passed == total:
        print("🎉 Toutes les corrections sont validées!")
        return 0
    else:
        print("⚠️  Certaines corrections nécessitent attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())