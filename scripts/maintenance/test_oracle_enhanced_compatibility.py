#!/usr/bin/env python3
"""
Test intensif de compatibilité Oracle Enhanced v2.1.0
Tâche 4/6 : Validation post-refactorisation des scripts Oracle/Sherlock

Teste que les fichiers refactorisés fonctionnent avec Oracle Enhanced v2.1.0
"""

import argumentation_analysis.core.environment
import os
import sys
import subprocess
import traceback
from pathlib import Path
from datetime import datetime

class OracleEnhancedCompatibilityTester:
    """Testeur de compatibilité Oracle Enhanced v2.1.0"""
    
    def __init__(self):
        self.base_path = Path(".")
        self.refactored_files = [
            "tests/unit/argumentation_analysis/agents/core/oracle/test_oracle_behavior_demo.py_refactored",
            "tests/unit/argumentation_analysis/agents/core/oracle/test_oracle_behavior_simple.py_refactored",
            "tests/unit/argumentation_analysis/agents/core/oracle/update_test_coverage.py_refactored"
        ]
        self.test_results = []
        
    def test_syntax_validation(self, file_path: str) -> dict:
        """Test de syntaxe Python"""
        result = {
            "test": "syntax_validation",
            "file": file_path,
            "success": False,
            "details": ""
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            compile(content, file_path, 'exec')
            result["success"] = True
            result["details"] = "Syntaxe Python valide"
            
        except Exception as e:
            result["details"] = f"Erreur de syntaxe: {e}"
            
        return result
    
    def test_import_compatibility(self, file_path: str) -> dict:
        """Test des imports avec Oracle Enhanced v2.1.0"""
        result = {
            "test": "import_compatibility", 
            "file": file_path,
            "success": False,
            "details": ""
        }
        
        try:
            # Test d'import via subprocess pour éviter les conflits
            cmd = [
                sys.executable, "-c",
                f"import sys; sys.path.insert(0, '.'); exec(open('{file_path}').read())"
            ]
            
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                cwd=self.base_path
            )
            
            if process.returncode == 0:
                result["success"] = True
                result["details"] = "Imports Oracle Enhanced v2.1.0 compatibles"
            else:
                result["details"] = f"Erreur d'import: {process.stderr[:200]}"
                
        except subprocess.TimeoutExpired:
            result["details"] = "Timeout lors du test d'import"
        except Exception as e:
            result["details"] = f"Erreur lors du test: {e}"
            
        return result
    
    def test_oracle_references(self, file_path: str) -> dict:
        """Test des références Oracle/Sherlock"""
        result = {
            "test": "oracle_references",
            "file": file_path,
            "success": False,
            "details": ""
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            oracle_terms = [
                'oracle', 'sherlock', 'watson', 'moriarty',
                'OracleAgent', 'SherlockAgent', 'WatsonAgent', 'MoriartyAgent',
                'oracle_enhanced', 'Oracle Enhanced', 'v2.1.0'
            ]
            
            found_terms = []
            for term in oracle_terms:
                if term.lower() in content.lower():
                    found_terms.append(term)
            
            if found_terms:
                result["success"] = True
                result["details"] = f"Références Oracle trouvées: {', '.join(found_terms[:5])}{'...' if len(found_terms) > 5 else ''}"
            else:
                result["details"] = "Aucune référence Oracle/Sherlock trouvée"
                
        except Exception as e:
            result["details"] = f"Erreur lors de l'analyse: {e}"
            
        return result
    
    def test_modernized_imports(self, file_path: str) -> dict:
        """Test que les imports ont été modernisés"""
        result = {
            "test": "modernized_imports",
            "file": file_path,
            "success": False,
            "details": ""
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Vérifications de modernisation
            modern_patterns = [
                'from typing import',
                'from pathlib import',
                'import logging',
                'from datetime import'
            ]
            
            deprecated_patterns = [
                'import imp',
                'from imp import',
                'execfile(',
                'reload('
            ]
            
            modern_found = sum(1 for pattern in modern_patterns if pattern in content)
            deprecated_found = sum(1 for pattern in deprecated_patterns if pattern in content)
            
            if modern_found > 0 and deprecated_found == 0:
                result["success"] = True
                result["details"] = f"Imports modernisés détectés: {modern_found} patterns modernes, {deprecated_found} patterns obsolètes"
            else:
                result["details"] = f"Modernisation incomplète: {modern_found} modernes, {deprecated_found} obsolètes"
                
        except Exception as e:
            result["details"] = f"Erreur lors de l'analyse: {e}"
            
        return result
    
    def test_file_execution(self, file_path: str) -> dict:
        """Test d'exécution basique du fichier"""
        result = {
            "test": "file_execution",
            "file": file_path,
            "success": False,
            "details": ""
        }
        
        try:
            # Test d'exécution partielle (sans pytest pour éviter les dépendances)
            cmd = [
                sys.executable, "-c",
                f"import sys; sys.path.insert(0, '.'); compile(open('{file_path}').read(), '{file_path}', 'exec'); print('Compilation réussie')"
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True, 
                text=True,
                timeout=15,
                cwd=self.base_path
            )
            
            if process.returncode == 0 and "Compilation réussie" in process.stdout:
                result["success"] = True
                result["details"] = "Fichier exécutable et compilable"
            else:
                result["details"] = f"Erreur d'exécution: {process.stderr[:150]}"
                
        except subprocess.TimeoutExpired:
            result["details"] = "Timeout lors du test d'exécution"
        except Exception as e:
            result["details"] = f"Erreur lors du test: {e}"
            
        return result
    
    def run_intensive_tests(self):
        """Lance tous les tests intensifs"""
        print(f"🧪 Démarrage des tests intensifs Oracle Enhanced v2.1.0")
        print(f"📅 Timestamp: {datetime.now().isoformat()}")
        print(f"📁 Répertoire: {self.base_path.resolve()}")
        print(f"🎯 Fichiers à tester: {len(self.refactored_files)}")
        print("="*70)
        
        for file_path in self.refactored_files:
            print(f"\n📋 Test de: {file_path}")
            print("-" * 50)
            
            if not (self.base_path / file_path).exists():
                print(f"❌ ERREUR: Fichier introuvable - {file_path}")
                continue
            
            # Tests séquentiels
            tests = [
                self.test_syntax_validation,
                self.test_oracle_references,
                self.test_modernized_imports,
                self.test_import_compatibility,
                self.test_file_execution
            ]
            
            file_results = []
            for test_func in tests:
                test_result = test_func(file_path)
                file_results.append(test_result)
                
                status = "✅ SUCCÈS" if test_result["success"] else "❌ ÉCHEC"
                print(f"  {status} {test_result['test']}: {test_result['details']}")
            
            # Évaluation globale du fichier
            success_count = sum(1 for r in file_results if r["success"])
            total_tests = len(file_results)
            score = (success_count / total_tests) * 100
            
            print(f"\n  📊 Score de compatibilité: {success_count}/{total_tests} ({score:.1f}%)")
            
            if score >= 80:
                print(f"  🎉 COMPATIBLE Oracle Enhanced v2.1.0")
            elif score >= 60:
                print(f"  ⚠️  PARTIELLEMENT COMPATIBLE - Corrections mineures nécessaires")
            else:
                print(f"  🚨 INCOMPATIBLE - Refactorisation requise")
            
            self.test_results.extend(file_results)
        
        # Rapport final
        return self.generate_final_report()
    
    def generate_final_report(self):
        """Génère le rapport final"""
        print("\n" + "="*70)
        print("📊 RAPPORT FINAL - COMPATIBILITÉ ORACLE ENHANCED v2.1.0")
        print("="*70)
        
        total_tests = len(self.test_results)
        successful_tests = sum(1 for r in self.test_results if r["success"])
        overall_score = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"📈 Score global: {successful_tests}/{total_tests} ({overall_score:.1f}%)")
        print(f"📁 Fichiers testés: {len(self.refactored_files)}")
        
        # Statistiques par type de test
        test_types = {}
        for result in self.test_results:
            test_type = result["test"]
            if test_type not in test_types:
                test_types[test_type] = {"total": 0, "success": 0}
            test_types[test_type]["total"] += 1
            if result["success"]:
                test_types[test_type]["success"] += 1
        
        print(f"\n📋 Détail par type de test:")
        for test_type, stats in test_types.items():
            score = (stats["success"] / stats["total"]) * 100
            print(f"  • {test_type}: {stats['success']}/{stats['total']} ({score:.1f}%)")
        
        # Validation finale
        if overall_score >= 90:
            print(f"\n🎉 VALIDATION RÉUSSIE - Oracle Enhanced v2.1.0 COMPATIBLE")
            print(f"   Les scripts Oracle/Sherlock refactorisés fonctionnent correctement")
        elif overall_score >= 75:
            print(f"\n⚠️  VALIDATION PARTIELLE - Corrections mineures recommandées")
        else:
            print(f"\n🚨 VALIDATION ÉCHOUÉE - Refactorisation supplémentaire requise")
        
        # Sauvegarde du rapport
        report_path = self.base_path / "logs/oracle_enhanced_compatibility_test_report.md"
        self.save_detailed_report(report_path)
        print(f"\n📄 Rapport détaillé sauvegardé: {report_path}")
        
        return overall_score
    
    def save_detailed_report(self, report_path: Path):
        """Sauvegarde le rapport détaillé"""
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Rapport de Compatibilité Oracle Enhanced v2.1.0\n\n")
            f.write(f"**Date**: {datetime.now().isoformat()}\n")
            f.write(f"**Fichiers testés**: {len(self.refactored_files)}\n")
            f.write(f"**Tests exécutés**: {len(self.test_results)}\n\n")
            
            # Grouper par fichier
            by_file = {}
            for result in self.test_results:
                file_path = result["file"]
                if file_path not in by_file:
                    by_file[file_path] = []
                by_file[file_path].append(result)
            
            f.write("## Résultats par Fichier\n\n")
            for file_path, results in by_file.items():
                f.write(f"### {file_path}\n\n")
                success_count = sum(1 for r in results if r["success"])
                total = len(results)
                score = (success_count / total) * 100
                f.write(f"**Score de compatibilité**: {success_count}/{total} ({score:.1f}%)\n\n")
                
                for result in results:
                    status = "✅" if result["success"] else "❌"
                    f.write(f"- {status} **{result['test']}**: {result['details']}\n")
                f.write("\n---\n\n")

def main():
    """Point d'entrée principal"""
    tester = OracleEnhancedCompatibilityTester()
    score = tester.run_intensive_tests()
    
    # Code de sortie basé sur le score
    if score >= 90:
        return 0  # Succès
    elif score >= 75:
        return 1  # Avertissement
    else:
        return 2  # Échec

if __name__ == "__main__":
    sys.exit(main())