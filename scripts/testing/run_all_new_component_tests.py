#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrateur Master de Validation des Nouveaux Composants
========================================================

Script principal pour exécuter tous les nouveaux tests créés et générer
un rapport consolidé de la validation des nouveaux composants.
"""

import subprocess
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


class ComponentTestOrchestrator:
    """
    Orchestrateur master pour la validation de tous les nouveaux composants.
    
    Exécute une suite complète de tests et génère un rapport consolidé.
    """
    
    def __init__(self):
        """Initialise l'orchestrateur de tests."""
        self.project_root = Path(__file__).parent
        self.start_time = datetime.now()
        self.results = {}
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        
        # Tests à exécuter dans l'ordre
        self.test_files = [
            'test_conversation_integration.py',
            'demo_authentic_system.py',
            'test_intelligent_modal_correction.py',
            'test_modal_correction_validation.py',
            'test_final_modal_correction_demo.py',
            'test_advanced_rhetorical_enhanced.py',
            'test_rhetorical_demo_integration.py',
            'test_micro_orchestration.py'
        ]
    
    def run_single_test(self, test_file: str) -> Dict[str, Any]:
        """
        Exécute un test individuel.
        
        Args:
            test_file: Nom du fichier de test
            
        Returns:
            Dict contenant les résultats du test
        """
        print(f"🧪 Exécution: {test_file}")
        
        test_path = self.project_root / test_file
        if not test_path.exists():
            return {
                'status': 'skip',
                'reason': 'file_not_found',
                'output': '',
                'error': f"Fichier non trouvé: {test_path}",
                'duration': 0
            }
        
        try:
            start_time = time.time()
            result = subprocess.run(
                [sys.executable, str(test_path)],
                capture_output=True,
                text=True,
                timeout=60,  # Timeout de 1 minute
                cwd=self.project_root
            )
            duration = time.time() - start_time
            
            status = 'pass' if result.returncode == 0 else 'fail'
            
            print(f"  {'✅' if status == 'pass' else '❌'} {test_file}: {status} ({duration:.2f}s)")
            
            return {
                'status': status,
                'returncode': result.returncode,
                'output': result.stdout,
                'error': result.stderr,
                'duration': duration
            }
            
        except subprocess.TimeoutExpired:
            print(f"  ⏰ {test_file}: timeout (>60s)")
            return {
                'status': 'timeout',
                'reason': 'execution_timeout',
                'output': '',
                'error': 'Test timeout after 60 seconds',
                'duration': 60
            }
            
        except Exception as e:
            print(f"  💥 {test_file}: erreur - {e}")
            return {
                'status': 'error',
                'reason': 'execution_error',
                'output': '',
                'error': str(e),
                'duration': 0
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """
        Exécute tous les tests de la suite.
        
        Returns:
            Dict contenant tous les résultats
        """
        print("🚀 DÉMARRAGE VALIDATION COMPLÈTE DES NOUVEAUX COMPOSANTS")
        print("=" * 70)
        print(f"📅 Début: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Répertoire: {self.project_root}")
        print(f"🧪 Tests à exécuter: {len(self.test_files)}")
        print()
        
        all_results = {}
        
        for test_file in self.test_files:
            self.total_tests += 1
            result = self.run_single_test(test_file)
            all_results[test_file] = result
            
            if result['status'] == 'pass':
                self.passed_tests += 1
            elif result['status'] in ['fail', 'error', 'timeout']:
                self.failed_tests += 1
        
        return all_results
    
    def generate_summary_report(self, results: Dict[str, Any]) -> str:
        """
        Génère un rapport de synthèse.
        
        Args:
            results: Résultats de tous les tests
            
        Returns:
            String contenant le rapport
        """
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        report = f"""
RAPPORT DE VALIDATION - NOUVEAUX COMPOSANTS
==========================================
Généré le: {end_time.strftime('%Y-%m-%d %H:%M:%S')}

RÉSUMÉ EXÉCUTIF
===============
• Total des tests: {self.total_tests}
• Tests réussis: {self.passed_tests}
• Tests échoués: {self.failed_tests}
• Tests ignorés: {self.total_tests - self.passed_tests - self.failed_tests}
• Taux de succès: {success_rate:.1f}%
• Durée totale: {total_duration:.2f}s

DÉTAIL DES RÉSULTATS
===================
"""
        
        for test_file, result in results.items():
            status_icon = {
                'pass': '✅',
                'fail': '❌',
                'error': '💥',
                'timeout': '⏰',
                'skip': '⏭️'
            }.get(result['status'], '❓')
            
            report += f"\n{status_icon} {test_file}"
            report += f"\n   Status: {result['status']}"
            report += f"\n   Durée: {result['duration']:.2f}s"
            
            if result['status'] != 'pass' and result.get('error'):
                report += f"\n   Erreur: {result['error'][:100]}{'...' if len(result['error']) > 100 else ''}"
            
            report += "\n"
        
        # Recommandations
        report += "\nRECOMMANDATIONS\n===============\n"
        
        if success_rate >= 80:
            report += "🎉 Excellente validation ! La majorité des composants fonctionnent correctement.\n"
        elif success_rate >= 60:
            report += "⚠️  Validation modérée. Certains composants nécessitent des corrections.\n"
        else:
            report += "🚨 Validation critique. Plusieurs composants nécessitent une attention urgente.\n"
        
        # Tests échoués
        failed_tests = [name for name, result in results.items() if result['status'] in ['fail', 'error', 'timeout']]
        if failed_tests:
            report += f"\nTests à corriger en priorité:\n"
            for test in failed_tests:
                report += f"  • {test}\n"
        
        return report
    
    def save_detailed_results(self, results: Dict[str, Any]) -> str:
        """
        Sauvegarde les résultats détaillés en JSON.
        
        Args:
            results: Résultats complets
            
        Returns:
            Nom du fichier de sauvegarde
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"test_results_components_{timestamp}.json"
        filepath = self.project_root / filename
        
        # Préparer les données pour JSON
        json_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_tests': self.total_tests,
                'passed_tests': self.passed_tests,
                'failed_tests': self.failed_tests,
                'success_rate': (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
            },
            'results': results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        return filename
    
    def run_orchestration(self) -> bool:
        """
        Lance l'orchestration complète.
        
        Returns:
            True si la validation est globalement réussie
        """
        try:
            # Exécuter tous les tests
            results = self.run_all_tests()
            
            # Générer le rapport
            print("\n📊 GÉNÉRATION DU RAPPORT FINAL")
            print("=" * 70)
            
            summary_report = self.generate_summary_report(results)
            print(summary_report)
            
            # Sauvegarder les résultats détaillés
            json_filename = self.save_detailed_results(results)
            print(f"💾 Résultats détaillés sauvegardés: {json_filename}")
            
            # Sauvegarder le rapport de synthèse
            report_filename = f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(summary_report)
            print(f"📄 Rapport de synthèse sauvegardé: {report_filename}")
            
            # Déterminer le succès global
            success_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
            
            print(f"\n🏁 VALIDATION TERMINÉE")
            print("=" * 70)
            print(f"📈 Taux de succès global: {success_rate:.1f}%")
            
            if success_rate >= 70:
                print("🎉 VALIDATION RÉUSSIE - Les nouveaux composants sont opérationnels!")
                return True
            else:
                print("⚠️  VALIDATION PARTIELLE - Des améliorations sont nécessaires")
                return False
                
        except Exception as e:
            print(f"💥 ERREUR FATALE lors de l'orchestration: {e}")
            return False


def main():
    """Fonction principale d'orchestration."""
    orchestrator = ComponentTestOrchestrator()
    success = orchestrator.run_orchestration()
    
    # Code de sortie basé sur le succès
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
