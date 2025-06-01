#!/usr/bin/env python3
"""
Script de validation simple des corrections effectuées
"""
import sys
import os
sys.path.insert(0, '.')

def test_analysis_runner():
    """Test AnalysisRunner avec nouvelles méthodes"""
    try:
        from argumentation_analysis.orchestration.analysis_runner import AnalysisRunner
        runner = AnalysisRunner()
        
        methods = ['run_analysis', 'run_multi_document_analysis'] # generate_report retiré
        all_present = True
        
        for method in methods:
            if hasattr(runner, method):
                print(f"OK: {method} disponible")
            else:
                print(f"ERREUR: {method} manquant")
                all_present = False
        
        assert all_present is True
    except Exception as e:
        print(f"ERREUR AnalysisRunner: {e}")
        raise  # Re-raise the exception to fail the test

def test_imports_basic():
    """Test imports de base"""
    try:
        # Test import du module principal
        import argumentation_analysis
        print("OK: argumentation_analysis importé")
        
        # Test import orchestration
        from argumentation_analysis.orchestration import analysis_runner
        print("OK: analysis_runner importé")
        
        # If imports succeed, the test passes implicitly
        pass
    except Exception as e:
        print(f"ERREUR imports: {e}")
        raise  # Re-raise the exception to fail the test

def main():
    print("=== VALIDATION SIMPLE DES CORRECTIONS ===")
    
    tests = [
        ("Imports de base", test_imports_basic),
        ("AnalysisRunner méthodes", test_analysis_runner),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        result = test_func()
        results.append((name, result))
    
    print("\n=== RESUME ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{status}: {name}")
    
    print(f"\nResultat: {passed}/{total} tests passes")
    
    if passed == total:
        print("SUCCESS: Toutes les corrections sont validees!")
        return 0
    else:
        print("WARNING: Certaines corrections necessitent attention")
        return 1

if __name__ == "__main__":
    sys.exit(main())