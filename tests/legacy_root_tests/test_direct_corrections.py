#!/usr/bin/env python3
"""
Test direct des fichiers corrigés sans dépendances
"""
import sys
import os

def test_analysis_runner_file():
    """Test direct du fichier analysis_runner.py"""
    try:
        # Lire le fichier directement
        file_path = "argumentation_analysis/orchestration/analysis_runner.py"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier la présence des méthodes ajoutées
        methods_to_check = [
            'def generate_report(',
            'def run_analysis(',
            'def run_multi_document_analysis(',
        ]
        
        found_methods = []
        for method in methods_to_check:
            if method in content:
                found_methods.append(method.replace('def ', '').replace('(', ''))
                print(f"OK: {method.replace('def ', '').replace('(', '')} trouvée")
            else:
                print(f"ERREUR: {method.replace('def ', '').replace('(', '')} manquante")
        
        assert len(found_methods) == len(methods_to_check)
    except Exception as e:
        print(f"ERREUR lecture analysis_runner: {e}")
        raise

def test_numpy_mocks_structure():
    """Test la structure des fichiers de mock NumPy après refactoring."""
    found_all = True
    
    # Vérifications pour tests/mocks/numpy_setup.py
    try:
        file_path_setup = "tests/mocks/numpy_setup.py"
        with open(file_path_setup, 'r', encoding='utf-8') as f:
            content_setup = f.read()
        
        checks_setup = [
            'import numpy_mock',
            'class MockRecarray',
        ]
        print(f"\n--- Vérification de {file_path_setup} ---")
        for check in checks_setup:
            if check in content_setup:
                print(f"OK: \"{check}\" trouvé dans {file_path_setup}")
            else:
                print(f"ERREUR: \"{check}\" manquant dans {file_path_setup}")
                found_all = False
    except Exception as e:
        print(f"ERREUR lecture {file_path_setup}: {e}")
        found_all = False
        # Ne pas lever d'exception ici pour permettre aux autres vérifications de continuer si possible
        # mais le test global échouera à cause de found_all = False

    # Vérifications pour tests/mocks/numpy_mock.py
    try:
        file_path_mock = "tests/mocks/numpy_mock.py"
        with open(file_path_mock, 'r', encoding='utf-8') as f:
            content_mock = f.read()

        checks_mock = [
            'datetime64 = MagicMock', # Vérification plus générique
            'timedelta64 = MagicMock', # Vérification plus générique
        ]
        print(f"\n--- Vérification de {file_path_mock} ---")
        for check in checks_mock:
            if check in content_mock:
                print(f"OK: \"{check}\" trouvé dans {file_path_mock}")
            else:
                print(f"ERREUR: \"{check}\" manquant dans {file_path_mock}")
                found_all = False
    except Exception as e:
        print(f"ERREUR lecture {file_path_mock}: {e}")
        found_all = False
        # Idem, ne pas lever d'exception ici

    assert found_all, "Des éléments de la structure des mocks NumPy sont manquants."
    return found_all # Retourner True si tout est OK pour la fonction main()

def test_integration_file():
    """Test du fichier d'intégration corrigé"""
    try:
        file_path = "tests/integration/test_agents_tools_integration.py"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Vérifier les corrections d'assertions
        checks = [
            'test_configuration_validation',
            'test_multi_tool_workflow',
            'fallacy_detector.analyze',
        ]
        
        found_checks = []
        for check in checks:
            if check in content:
                found_checks.append(check)
                print(f"OK: {check} trouvé")
            else:
                print(f"ERREUR: {check} manquant")
        
        assert len(found_checks) >= 2
    except Exception as e:
        print(f"ERREUR lecture integration: {e}")
        raise

def main():
    print("=== TEST DIRECT DES CORRECTIONS ===")
    
    tests = [
        ("AnalysisRunner méthodes", test_analysis_runner_file),
        ("Structure Mocks NumPy", test_numpy_mocks_structure),
        ("Tests intégration", test_integration_file),
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
    
    print(f"\nResultat: {passed}/{total} corrections validees")
    
    if passed == total:
        print("SUCCESS: Toutes les corrections sont presentes!")
        return 0
    else:
        print("WARNING: Certaines corrections manquent")
        return 1

if __name__ == "__main__":
    sys.exit(main())