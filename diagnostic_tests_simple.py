#!/usr/bin/env python3
"""
Script de diagnostic simple pour identifier les problèmes de tests
sans dépendre de pytest
"""

import sys
import os
import importlib
import traceback
from pathlib import Path

def test_imports():
    """Test des imports principaux"""
    print("=== TEST DES IMPORTS ===")
    
    # Liste des modules à tester
    modules_to_test = [
        'argumentation_analysis',
        'argumentation_analysis.agents',
        'argumentation_analysis.agents.informal_agent',
        'argumentation_analysis.agents.tactical_coordinator',
        'argumentation_analysis.agents.tactical_monitor',
        'argumentation_analysis.core',
        'argumentation_analysis.core.fallacy_analyzer',
        'argumentation_analysis.core.enhanced_fallacy_analyzer',
        'argumentation_analysis.utils',
        'tests.mocks.jpype_mock',
        'tests.mocks.numpy_mock',
        'tests.mocks.pandas_mock',
    ]
    
    results = {}
    for module in modules_to_test:
        try:
            importlib.import_module(module)
            results[module] = "OK"
            print(f"OK {module}")
        except Exception as e:
            results[module] = f"ERREUR: {str(e)}"
            print(f"ERREUR {module}: {str(e)}")
    
    return results

def test_basic_functionality():
    """Test des fonctionnalités de base"""
    print("\n=== TEST DES FONCTIONNALITÉS DE BASE ===")
    
    try:
        # Test de création d'agent informel
        from argumentation_analysis.agents.informal_agent import InformalAgent
        agent = InformalAgent()
        print("OK Création InformalAgent")
        
        # Test d'analyse simple
        result = agent.analyze_text("Ceci est un test simple.")
        print(f"OK Analyse de texte: {type(result)}")
        
        return True
    except Exception as e:
        print(f"ERREUR Test fonctionnalité de base: {str(e)}")
        traceback.print_exc()
        return False

def test_file_structure():
    """Vérification de la structure des fichiers"""
    print("\n=== VÉRIFICATION STRUCTURE FICHIERS ===")
    
    required_paths = [
        'argumentation_analysis/',
        'argumentation_analysis/agents/',
        'argumentation_analysis/core/',
        'argumentation_analysis/utils/',
        'tests/',
        'tests/mocks/',
        'config/',
        'data/',
    ]
    
    missing_paths = []
    for path in required_paths:
        if not os.path.exists(path):
            missing_paths.append(path)
            print(f"MANQUANT: {path}")
        else:
            print(f"OK {path}")
    
    return len(missing_paths) == 0

def run_simple_tests():
    """Lance les tests simples disponibles"""
    print("\n=== EXÉCUTION TESTS SIMPLES ===")
    
    test_files = [
        'tests/test_minimal.py',
        'tests/test_dependencies.py',
        'tests/test_informal_agent.py',
    ]
    
    results = {}
    for test_file in test_files:
        if os.path.exists(test_file):
            try:
                # Exécution simple du fichier de test
                exec(compile(open(test_file).read(), test_file, 'exec'))
                results[test_file] = "OK"
                print(f"OK {test_file}")
            except Exception as e:
                results[test_file] = f"ERREUR: {str(e)}"
                print(f"ERREUR {test_file}: {str(e)}")
        else:
            results[test_file] = "FICHIER MANQUANT"
            print(f"MANQUANT {test_file}: Fichier manquant")
    
    return results

def count_test_files():
    """Compte les fichiers de test disponibles"""
    print("\n=== INVENTAIRE DES TESTS ===")
    
    test_dirs = ['tests/', 'tests/unit/', 'tests/integration/', 'tests/functional/']
    total_tests = 0
    
    for test_dir in test_dirs:
        if os.path.exists(test_dir):
            test_files = [f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.py')]
            print(f"{test_dir}: {len(test_files)} fichiers de test")
            total_tests += len(test_files)
            
            # Affiche les premiers fichiers pour diagnostic
            for i, test_file in enumerate(test_files[:5]):
                print(f"  - {test_file}")
            if len(test_files) > 5:
                print(f"  ... et {len(test_files) - 5} autres")
    
    print(f"\nTotal: {total_tests} fichiers de test trouvés")
    return total_tests

def main():
    """Fonction principale de diagnostic"""
    print("DIAGNOSTIC COMPLET DES TESTS")
    print("=" * 50)
    
    # Ajout du répertoire courant au PYTHONPATH
    sys.path.insert(0, os.getcwd())
    
    # Tests de diagnostic
    import_results = test_imports()
    structure_ok = test_file_structure()
    functionality_ok = test_basic_functionality()
    test_results = run_simple_tests()
    total_tests = count_test_files()
    
    # Résumé
    print("\n" + "=" * 50)
    print("RÉSUMÉ DU DIAGNOSTIC")
    print("=" * 50)
    
    import_errors = sum(1 for result in import_results.values() if result != "OK")
    test_errors = sum(1 for result in test_results.values() if "ERREUR" in result)
    
    print(f"Imports: {len(import_results) - import_errors}/{len(import_results)} OK")
    print(f"Structure: {'OK' if structure_ok else 'PROBLÈMES'}")
    print(f"Fonctionnalité de base: {'OK' if functionality_ok else 'PROBLÈMES'}")
    print(f"Tests simples: {len(test_results) - test_errors}/{len(test_results)} OK")
    print(f"Total fichiers de test: {total_tests}")
    
    # Recommandations
    print("\nRECOMMANDATIONS:")
    if import_errors > 0:
        print("- Corriger les erreurs d'import")
    if not structure_ok:
        print("- Vérifier la structure des répertoires")
    if not functionality_ok:
        print("- Corriger les problèmes de fonctionnalité de base")
    if test_errors > 0:
        print("- Corriger les erreurs dans les tests simples")
    
    return {
        'import_results': import_results,
        'structure_ok': structure_ok,
        'functionality_ok': functionality_ok,
        'test_results': test_results,
        'total_tests': total_tests
    }

if __name__ == "__main__":
    results = main()