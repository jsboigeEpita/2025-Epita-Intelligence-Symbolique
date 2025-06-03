#!/usr/bin/env python3
"""
Script de diagnostic détaillé pour identifier les 13 problèmes restants
(10 échecs + 3 erreurs) dans les tests
"""

import sys
import os
import importlib
import importlib.util
import traceback
import unittest
import io
import io
from pathlib import Path
import json
from datetime import datetime

# Configuration du projet
# Ajout du répertoire parent du répertoire scripts/ (racine du projet) à sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class TestDiagnostic:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'failures_detail': [],
            'errors_detail': [],
            'test_files_analyzed': []
        }
    
    def analyze_test_file(self, test_file_path):
        """Analyse un fichier de test spécifique"""
        print(f"\n=== ANALYSE: {test_file_path} ===")
        
        try:
            # Import du module de test
            module_name = test_file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, test_file_path)
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
            
            if not test_classes:
                print(f"Aucune classe de test trouvée dans {test_file_path}")
                return
            
            # Exécution des tests
            suite = unittest.TestSuite()
            for test_class in test_classes:
                tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
                suite.addTests(tests)
            
            # Runner personnalisé pour capturer les détails
            stream = io.StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=2)
            result = runner.run(suite)
            
            # Mise à jour des statistiques
            self.results['total_tests'] += result.testsRun
            self.results['passed'] += (result.testsRun - len(result.failures) - len(result.errors))
            self.results['failed'] += len(result.failures)
            self.results['errors'] += len(result.errors)
            
            # Détails des échecs
            for test, traceback_str in result.failures:
                failure_detail = {
                    'file': str(test_file_path),
                    'test': str(test),
                    'type': 'FAILURE',
                    'traceback': traceback_str,
                    'category': self._categorize_problem(traceback_str)
                }
                self.results['failures_detail'].append(failure_detail)
                print(f"ÉCHEC: {test}")
                print(f"Catégorie: {failure_detail['category']}")
                print(f"Détail: {traceback_str[:200]}...")
            
            # Détails des erreurs
            for test, traceback_str in result.errors:
                error_detail = {
                    'file': str(test_file_path),
                    'test': str(test),
                    'type': 'ERROR',
                    'traceback': traceback_str,
                    'category': self._categorize_problem(traceback_str)
                }
                self.results['errors_detail'].append(error_detail)
                print(f"ERREUR: {test}")
                print(f"Catégorie: {error_detail['category']}")
                print(f"Détail: {traceback_str[:200]}...")
            
            # Résumé du fichier
            print(f"Résultat: {result.testsRun} tests, {len(result.failures)} échecs, {len(result.errors)} erreurs")
            
            self.results['test_files_analyzed'].append({
                'file': str(test_file_path),
                'tests_run': result.testsRun,
                'failures': len(result.failures),
                'errors': len(result.errors)
            })
            
        except Exception as e:
            print(f"Erreur lors de l'analyse de {test_file_path}: {e}")
            traceback.print_exc()
    
    def _categorize_problem(self, traceback_str):
        """Catégorise le type de problème basé sur la traceback"""
        if 'AttributeError' in traceback_str:
            if 'model_validate' in traceback_str:
                return 'PYDANTIC_COMPATIBILITY'
            elif 'Mock' in traceback_str:
                return 'MOCK_ATTRIBUTE'
            else:
                return 'ATTRIBUTE_ERROR'
        elif 'ImportError' in traceback_str or 'ModuleNotFoundError' in traceback_str:
            return 'IMPORT_ERROR'
        elif 'TypeError' in traceback_str:
            if 'missing' in traceback_str and 'positional arguments' in traceback_str:
                return 'FUNCTION_SIGNATURE'
            else:
                return 'TYPE_ERROR'
        elif 'AssertionError' in traceback_str:
            return 'ASSERTION_FAILURE'
        elif 'KeyError' in traceback_str:
            return 'KEY_ERROR'
        elif 'NameError' in traceback_str:
            return 'NAME_ERROR'
        else:
            return 'OTHER'
    
    def find_test_files(self):
        """Trouve tous les fichiers de test"""
        test_files = []
        tests_dir = PROJECT_ROOT / "tests"
        
        if tests_dir.exists():
            for test_file in tests_dir.rglob("test_*.py"):
                test_files.append(test_file)
        
        return sorted(test_files)
    
    def run_diagnostic(self):
        """Exécute le diagnostic complet"""
        print("=== DIAGNOSTIC DES 13 PROBLÈMES RESTANTS ===")
        print(f"Répertoire de projet: {PROJECT_ROOT}")
        
        test_files = self.find_test_files()
        print(f"Fichiers de test trouvés: {len(test_files)}")
        
        for test_file in test_files:
            self.analyze_test_file(test_file)
        
        # Génération du rapport final
        self.generate_report()
    
    def generate_report(self):
        """Génère le rapport de diagnostic"""
        print("\n" + "="*60)
        print("RAPPORT DE DIAGNOSTIC FINAL")
        print("="*60)
        
        print(f"\nSTATISTIQUES GLOBALES:")
        print(f"Total des tests: {self.results['total_tests']}")
        print(f"Tests réussis: {self.results['passed']}")
        print(f"Échecs: {self.results['failed']}")
        print(f"Erreurs: {self.results['errors']}")
        
        if self.results['total_tests'] > 0:
            success_rate = (self.results['passed'] / self.results['total_tests']) * 100
            print(f"Taux de réussite: {success_rate:.1f}%")
        
        # Analyse par catégorie
        print(f"\nANALYSE PAR CATÉGORIE:")
        categories = {}
        
        for failure in self.results['failures_detail']:
            cat = failure['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        for error in self.results['errors_detail']:
            cat = error['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        for category, count in sorted(categories.items()):
            print(f"  {category}: {count} problèmes")
        
        # Détails des problèmes
        print(f"\nDÉTAILS DES {len(self.results['failures_detail'])} ÉCHECS:")
        for i, failure in enumerate(self.results['failures_detail'], 1):
            print(f"\n{i}. ÉCHEC - {failure['category']}")
            print(f"   Fichier: {Path(failure['file']).name}")
            print(f"   Test: {failure['test']}")
            print(f"   Détail: {failure['traceback'].split('AssertionError:')[-1].strip()[:100]}...")
        
        print(f"\nDÉTAILS DES {len(self.results['errors_detail'])} ERREURS:")
        for i, error in enumerate(self.results['errors_detail'], 1):
            print(f"\n{i}. ERREUR - {error['category']}")
            print(f"   Fichier: {Path(error['file']).name}")
            print(f"   Test: {error['test']}")
            print(f"   Détail: {error['traceback'].split(':')[-1].strip()[:100]}...")
        
        # Sauvegarde du rapport JSON
        report_file = PROJECT_ROOT / "diagnostic_13_problemes_rapport.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False)
        
        print(f"\nRapport détaillé sauvegardé: {report_file}")
        
        # Recommandations
        self.generate_recommendations()
    
    def generate_recommendations(self):
        """Génère des recommandations de correction"""
        print(f"\nRECOMMANDATIONS DE CORRECTION:")
        
        categories = {}
        for failure in self.results['failures_detail']:
            cat = failure['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        for error in self.results['errors_detail']:
            cat = error['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        recommendations = {
            'PYDANTIC_COMPATIBILITY': "Ajouter la méthode model_validate aux classes Pydantic",
            'MOCK_ATTRIBUTE': "Configurer les attributs manquants dans les mocks",
            'FUNCTION_SIGNATURE': "Corriger les signatures de fonctions (paramètres manquants)",
            'IMPORT_ERROR': "Vérifier les imports et les dépendances",
            'ASSERTION_FAILURE': "Revoir la logique des assertions dans les tests",
            'ATTRIBUTE_ERROR': "Vérifier les attributs d'objets utilisés",
            'TYPE_ERROR': "Corriger les types de données passés aux fonctions",
            'KEY_ERROR': "Vérifier les clés de dictionnaires utilisées",
            'NAME_ERROR': "Corriger les noms de variables non définies"
        }
        
        for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            if category in recommendations:
                print(f"\n{count}x {category}:")
                print(f"   → {recommendations[category]}")

def main():
    """Fonction principale"""
    diagnostic = TestDiagnostic()
    diagnostic.run_diagnostic()
    
    return diagnostic.results

if __name__ == "__main__":
    results = main()
    
    # Code de sortie basé sur les résultats
    if results['errors'] > 0 or results['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)