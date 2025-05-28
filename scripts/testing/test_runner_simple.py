#!/usr/bin/env python3
"""
Runner de tests simple sans pytest pour diagnostiquer les problèmes
"""

import sys
import os
import importlib
import traceback
import unittest
from pathlib import Path

# Ajout du répertoire courant au PYTHONPATH
sys.path.insert(0, os.getcwd())

def run_tests_in_directory(test_dir):
    """Exécute tous les tests dans un répertoire donné"""
    print(f"\n=== TESTS DANS {test_dir} ===")
    
    if not os.path.exists(test_dir):
        print(f"Répertoire {test_dir} non trouvé")
        return {}
    
    results = {}
    test_files = [f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.py')]
    
    for test_file in test_files:
        test_path = os.path.join(test_dir, test_file)
        module_name = test_file[:-3]  # Enlève .py
        
        print(f"\n--- Test: {test_file} ---")
        
        try:
            # Chargement du module de test
            spec = importlib.util.spec_from_file_location(module_name, test_path)
            test_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(test_module)
            
            # Recherche des classes de test
            test_classes = []
            for name in dir(test_module):
                obj = getattr(test_module, name)
                if (isinstance(obj, type) and 
                    issubclass(obj, unittest.TestCase) and 
                    obj != unittest.TestCase):
                    test_classes.append(obj)
            
            if test_classes:
                # Exécution des tests avec unittest
                suite = unittest.TestSuite()
                for test_class in test_classes:
                    tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
                    suite.addTests(tests)
                
                runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
                result = runner.run(suite)
                
                results[test_file] = {
                    'tests_run': result.testsRun,
                    'failures': len(result.failures),
                    'errors': len(result.errors),
                    'success': result.wasSuccessful()
                }
                
                print(f"Résultat: {result.testsRun} tests, {len(result.failures)} échecs, {len(result.errors)} erreurs")
                
                # Affichage des erreurs détaillées
                if result.failures:
                    print("ÉCHECS:")
                    for test, traceback_str in result.failures:
                        print(f"  - {test}: {traceback_str}")
                
                if result.errors:
                    print("ERREURS:")
                    for test, traceback_str in result.errors:
                        print(f"  - {test}: {traceback_str}")
            else:
                print("Aucune classe de test trouvée")
                results[test_file] = {'error': 'Aucune classe de test'}
                
        except Exception as e:
            print(f"Erreur lors du chargement: {str(e)}")
            traceback.print_exc()
            results[test_file] = {'error': str(e)}
    
    return results

def run_specific_tests():
    """Exécute des tests spécifiques qui devraient fonctionner"""
    print("\n=== TESTS SPÉCIFIQUES ===")
    
    specific_tests = [
        'tests/test_minimal.py',
        'tests/test_informal_agent.py',
        'tests/test_dependencies.py',
    ]
    
    results = {}
    for test_file in specific_tests:
        if os.path.exists(test_file):
            print(f"\n--- {test_file} ---")
            try:
                # Exécution directe du fichier
                with open(test_file, 'r', encoding='utf-8') as f:
                    code = f.read()
                
                # Création d'un namespace pour l'exécution
                test_globals = {
                    '__name__': '__main__',
                    '__file__': test_file,
                    'sys': sys,
                    'os': os,
                }
                
                exec(code, test_globals)
                results[test_file] = 'OK'
                print(f"OK {test_file} exécuté avec succès")
                
            except Exception as e:
                results[test_file] = f'ERREUR: {str(e)}'
                print(f"ERREUR {test_file}: {str(e)}")
                # Affichage de la traceback pour debug
                traceback.print_exc()
        else:
            results[test_file] = 'FICHIER MANQUANT'
            print(f"ERREUR {test_file}: Fichier manquant")
    
    return results

def test_core_functionality():
    """Test des fonctionnalités principales"""
    print("\n=== TEST FONCTIONNALITÉS PRINCIPALES ===")
    
    tests = []
    
    # Test 1: Import de l'agent informel
    try:
        from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
        tests.append(('Import InformalAgent', 'OK'))
        print("OK Import InformalAgent")
        
        # Test 2: Création d'instance
        agent = InformalAgent()
        tests.append(('Création InformalAgent', 'OK'))
        print("OK Création InformalAgent")
        
        # Test 3: Analyse simple
        result = agent.analyze_text("Ceci est un test simple.")
        tests.append(('Analyse texte', f'OK - Type: {type(result)}'))
        print(f"OK Analyse texte - Type: {type(result)}")
        
    except Exception as e:
        tests.append(('InformalAgent', f'ERREUR: {str(e)}'))
        print(f"ERREUR InformalAgent: {str(e)}")
    
    # Test 4: Import de l'agent d'extraction
    try:
        from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
        tests.append(('Import ExtractAgent', 'OK'))
        print("OK Import ExtractAgent")
        
        agent = ExtractAgent()
        tests.append(('Création ExtractAgent', 'OK'))
        print("OK Création ExtractAgent")
        
    except Exception as e:
        tests.append(('ExtractAgent', f'ERREUR: {str(e)}'))
        print(f"ERREUR ExtractAgent: {str(e)}")
    
    # Test 5: Modules de base
    try:
        from argumentation_analysis.core.shared_state import SharedState
        tests.append(('Import SharedState', 'OK'))
        print("OK Import SharedState")
        
    except Exception as e:
        tests.append(('SharedState', f'ERREUR: {str(e)}'))
        print(f"ERREUR SharedState: {str(e)}")
    
    return tests

def main():
    """Fonction principale"""
    print("RUNNER DE TESTS SIMPLE")
    print("=" * 50)
    
    # Test des fonctionnalités principales
    core_tests = test_core_functionality()
    
    # Tests spécifiques
    specific_results = run_specific_tests()
    
    # Tests par répertoire
    test_dirs = ['tests', 'tests/unit', 'tests/integration', 'tests/functional']
    all_results = {}
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            results = run_tests_in_directory(test_dir)
            all_results[test_dir] = results
    
    # Résumé final
    print("\n" + "=" * 50)
    print("RÉSUMÉ FINAL")
    print("=" * 50)
    
    print("\nFonctionnalités principales:")
    for test_name, result in core_tests:
        status = "OK" if "OK" in result else "ERREUR"
        print(f"  {test_name}: {status}")
    
    print("\nTests spécifiques:")
    for test_file, result in specific_results.items():
        status = "OK" if result == "OK" else "ERREUR"
        print(f"  {test_file}: {status}")
    
    print("\nTests par répertoire:")
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    for test_dir, results in all_results.items():
        if results:
            dir_tests = sum(r.get('tests_run', 0) for r in results.values() if isinstance(r, dict))
            dir_failures = sum(r.get('failures', 0) for r in results.values() if isinstance(r, dict))
            dir_errors = sum(r.get('errors', 0) for r in results.values() if isinstance(r, dict))
            
            total_tests += dir_tests
            total_failures += dir_failures
            total_errors += dir_errors
            
            print(f"  {test_dir}: {dir_tests} tests, {dir_failures} échecs, {dir_errors} erreurs")
    
    print(f"\nTOTAL: {total_tests} tests, {total_failures} échecs, {total_errors} erreurs")
    
    success_rate = ((total_tests - total_failures - total_errors) / total_tests * 100) if total_tests > 0 else 0
    print(f"Taux de réussite: {success_rate:.1f}%")
    
    return {
        'core_tests': core_tests,
        'specific_results': specific_results,
        'directory_results': all_results,
        'total_tests': total_tests,
        'total_failures': total_failures,
        'total_errors': total_errors,
        'success_rate': success_rate
    }

if __name__ == "__main__":
    results = main()