#!/usr/bin/env python3
"""
Test complet final pour diagnostiquer et corriger tous les problèmes restants
"""

import sys
import os
import importlib
import traceback
import unittest
from unittest.mock import Mock, MagicMock
from pathlib import Path

# Ajout du répertoire courant au PYTHONPATH
sys.path.insert(0, os.getcwd())

def create_mock_tools():
    """Crée des outils mock pour les agents"""
    return {
        'fallacy_detector': Mock(),
        'rhetorical_analyzer': Mock(),
        'contextual_analyzer': Mock(),
        'severity_evaluator': Mock()
    }

def test_agent_creation():
    """Test de création des agents avec les bons paramètres"""
    print("\n=== TEST CRÉATION AGENTS ===")
    
    # Test InformalAgent
    try:
        from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
        
        tools = create_mock_tools()
        agent = InformalAgent(agent_id="test_agent", tools=tools)
        assert isinstance(agent, InformalAgent)
        print("OK InformalAgent créé avec succès")
        
        # Test d'une méthode simple
        try:
            analysis_result = agent.analyze_text("Test simple")
            assert analysis_result is not None # Ou une assertion plus spécifique
            print(f"OK InformalAgent.analyze_text - Type: {type(analysis_result)}")
        except Exception as e_analyze:
            print(f"ERREUR InformalAgent.analyze_text: {str(e_analyze)}")
            raise  # Re-raise pour que pytest le capture
            
    except Exception as e_informal:
        print(f"ERREUR InformalAgent: {str(e_informal)}")
        raise # Re-raise pour que pytest le capture
    
    # Test ExtractAgent
    try:
        from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
        
        extract_agent_instance = ExtractAgent(
            extract_agent=Mock(),
            validation_agent=Mock(),
            extract_plugin=Mock()
        )
        assert isinstance(extract_agent_instance, ExtractAgent)
        print("OK ExtractAgent créé avec succès")
        
    except Exception as e_extract:
        print(f"ERREUR ExtractAgent: {str(e_extract)}")
        raise # Re-raise pour que pytest le capture
    
    # Si toutes les assertions passent et aucune exception n'est levée, le test est réussi.
    # Pytest n'attend pas de valeur de retour.

def run_unittest_tests():
    """Exécute les tests unittest disponibles"""
    print("\n=== TESTS UNITTEST ===")
    
    # Recherche des fichiers de test avec des classes unittest
    test_files = []
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                file_path = os.path.join(root, file)
                
                # Vérifie si le fichier contient des classes unittest
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if 'unittest.TestCase' in content or 'TestCase' in content:
                            test_files.append(file_path)
                except:
                    pass
    
    print(f"Trouvé {len(test_files)} fichiers avec des tests unittest")
    
    results = {}
    total_tests = 0
    total_failures = 0
    total_errors = 0
    
    for test_file in test_files[:10]:  # Limite à 10 pour éviter trop de sortie
        print(f"\n--- {test_file} ---")
        
        try:
            # Chargement du module
            module_name = os.path.basename(test_file)[:-3]
            spec = importlib.util.spec_from_file_location(module_name, test_file)
            test_module = importlib.util.module_from_spec(spec)
            
            # Injection des mocks nécessaires
            test_module.Mock = Mock
            test_module.MagicMock = MagicMock
            
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
                # Exécution des tests
                suite = unittest.TestSuite()
                for test_class in test_classes:
                    tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
                    suite.addTests(tests)
                
                # Runner silencieux pour éviter trop de sortie
                stream = open(os.devnull, 'w')
                runner = unittest.TextTestRunner(stream=stream, verbosity=0)
                result = runner.run(suite)
                stream.close()
                
                total_tests += result.testsRun
                total_failures += len(result.failures)
                total_errors += len(result.errors)
                
                results[test_file] = {
                    'tests': result.testsRun,
                    'failures': len(result.failures),
                    'errors': len(result.errors),
                    'success': result.wasSuccessful()
                }
                
                status = "OK" if result.wasSuccessful() else "ERREURS"
                print(f"  {result.testsRun} tests, {len(result.failures)} échecs, {len(result.errors)} erreurs - {status}")
                
                # Affiche les premières erreurs pour diagnostic
                if result.failures and len(result.failures) <= 3:
                    print("  Échecs:")
                    for test, trace in result.failures:
                        print(f"    - {test}: {trace.split('AssertionError:')[-1].strip()[:100]}...")
                
                if result.errors and len(result.errors) <= 3:
                    print("  Erreurs:")
                    for test, trace in result.errors:
                        error_line = trace.split('\n')[-2] if '\n' in trace else trace
                        print(f"    - {test}: {error_line[:100]}...")
            else:
                results[test_file] = {'error': 'Aucune classe de test'}
                print("  Aucune classe de test trouvée")
                
        except Exception as e:
            results[test_file] = {'error': str(e)}
            print(f"  ERREUR: {str(e)}")
    
    return results, total_tests, total_failures, total_errors

def analyze_common_errors():
    """Analyse les erreurs communes dans les tests"""
    print("\n=== ANALYSE DES ERREURS COMMUNES ===")
    
    common_issues = []
    
    # Vérification des imports problématiques
    problematic_imports = [
        'pytest',
        'jpype',
        'torch',
        'tensorflow'
    ]
    
    for imp in problematic_imports:
        try:
            importlib.import_module(imp)
            print(f"OK {imp} disponible")
        except ImportError:
            common_issues.append(f"Module manquant: {imp}")
            print(f"MANQUANT {imp}")
    
    # Vérification des mocks
    mock_files = [
        'tests/mocks/jpype_mock.py',
        'tests/mocks/numpy_mock.py',
        'tests/mocks/pandas_mock.py'
    ]
    
    for mock_file in mock_files:
        if os.path.exists(mock_file):
            print(f"OK {mock_file} existe")
        else:
            common_issues.append(f"Mock manquant: {mock_file}")
            print(f"MANQUANT {mock_file}")
    
    return common_issues

def create_pytest_alternative():
    """Crée un runner de test alternatif à pytest"""
    print("\n=== CRÉATION RUNNER ALTERNATIF ===")
    
    runner_content = '''#!/usr/bin/env python3
"""
Runner de test alternatif à pytest
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock

# Configuration des mocks globaux
sys.modules['pytest'] = Mock()
sys.modules['jpype'] = Mock()

def run_all_tests():
    """Exécute tous les tests disponibles"""
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print(f"\\nRésultats: {result.testsRun} tests, {len(result.failures)} échecs, {len(result.errors)} erreurs")
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
'''
    
    with open('run_tests_alternative.py', 'w', encoding='utf-8') as f:
        f.write(runner_content)
    
    print("OK Runner alternatif créé: run_tests_alternative.py")

def main():
    """Fonction principale"""
    print("TEST FINAL COMPRÉHENSIF")
    print("=" * 50)
    
    # Test de création des agents
    agent_results = test_agent_creation()
    
    # Analyse des erreurs communes
    common_issues = analyze_common_errors()
    
    # Exécution des tests unittest
    test_results, total_tests, total_failures, total_errors = run_unittest_tests()
    
    # Création d'un runner alternatif
    create_pytest_alternative()
    
    # Résumé final
    print("\n" + "=" * 50)
    print("RÉSUMÉ FINAL")
    print("=" * 50)
    
    print("\nCréation d'agents:")
    for agent, result in agent_results.items():
        status = "OK" if result == "OK" or result.startswith("OK") else "ERREUR"
        print(f"  {agent}: {status}")
    
    print(f"\nTests unittest:")
    print(f"  Total: {total_tests} tests")
    print(f"  Échecs: {total_failures}")
    print(f"  Erreurs: {total_errors}")
    
    if total_tests > 0:
        success_rate = ((total_tests - total_failures - total_errors) / total_tests) * 100
        print(f"  Taux de réussite: {success_rate:.1f}%")
    
    print(f"\nProblèmes identifiés: {len(common_issues)}")
    for issue in common_issues[:5]:  # Affiche les 5 premiers
        print(f"  - {issue}")
    
    # Recommandations
    print("\nRECOMMANDATIONS PRIORITAIRES:")
    if total_errors > total_failures:
        print("1. Corriger les erreurs d'import et de configuration")
    if total_failures > 0:
        print("2. Corriger les assertions et la logique des tests")
    if 'pytest' in str(common_issues):
        print("3. Utiliser le runner alternatif créé")
    
    return {
        'agent_results': agent_results,
        'test_results': test_results,
        'total_tests': total_tests,
        'total_failures': total_failures,
        'total_errors': total_errors,
        'common_issues': common_issues
    }

if __name__ == "__main__":
    results = main()