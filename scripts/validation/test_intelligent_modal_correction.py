import argumentation_analysis.core.environment
﻿#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test du système de correction intelligente des erreurs modales avec feedback BNF
===============================================================================

Test complet du système de correction d'erreurs modales avec génération
de feedback BNF constructif pour guider les corrections.
"""

import asyncio
import sys
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ajout du répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer, analyze_tweety_error


class ModalCorrectionTester:
    """
    Testeur pour le système de correction intelligente des erreurs modales.
    
    Teste la capacité du système à détecter et corriger les erreurs
    modales avec génération de feedback BNF approprié.
    """
    
    def __init__(self):
        """Initialise le testeur."""
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
        self.analyzer = TweetyErrorAnalyzer()
        self.test_results = []
        
        # Erreurs de test
        self.test_errors = [
            {
                'type': 'syntax_error',
                'message': 'syntax error at token "rule"',
                'expected_bnf': ['rule ::= head \':-\' body \'.\'']
            },
            {
                'type': 'atom_error', 
                'message': 'atom "undefined_predicate" not defined',
                'expected_bnf': ['atom ::= predicate \'(\' terms \')\'']
            },
            {
                'type': 'variable_error',
                'message': 'singleton variable X in rule',
                'expected_bnf': ['variable ::= uppercase_identifier']
            },
            {
                'type': 'constraint_error',
                'message': 'integrity constraint violated',
                'expected_bnf': ['constraint ::= \':-\' body \'.\'']
            }
        ]
        
        self.logger.info("Testeur de correction modale initialisé")
    
    def setup_logging(self):
        """Configure le logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def test_error_detection(self) -> Dict[str, Any]:
        """
        Test la détection des types d'erreurs.
        
        Returns:
            Résultats du test de détection
        """
        print("🔍 Test de détection des types d'erreurs...")
        
        results = {
            'total_tests': len(self.test_errors),
            'successful_detections': 0,
            'failed_detections': 0,
            'details': []
        }
        
        for i, test_case in enumerate(self.test_errors, 1):
            print(f"  Test {i}: {test_case['type']}")
            
            try:
                feedback = self.analyzer.analyze_error(test_case['message'])
                detected_type = feedback.error_type
                
                if detected_type == test_case['type']:
                    print(f"    ✅ Type détecté correctement: {detected_type}")
                    results['successful_detections'] += 1
                    status = 'success'
                else:
                    print(f"    ❌ Type incorrect: attendu {test_case['type']}, obtenu {detected_type}")
                    results['failed_detections'] += 1
                    status = 'failed'
                
                results['details'].append({
                    'test_case': test_case,
                    'detected_type': detected_type,
                    'status': status,
                    'feedback': feedback
                })
                
            except Exception as e:
                print(f"    💥 Erreur: {e}")
                results['failed_detections'] += 1
                results['details'].append({
                    'test_case': test_case,
                    'error': str(e),
                    'status': 'error'
                })
        
        detection_rate = results['successful_detections'] / results['total_tests'] * 100
        print(f"📊 Taux de détection: {detection_rate:.1f}%")
        
        return results
    
    def test_bnf_generation(self) -> Dict[str, Any]:
        """
        Test la génération de règles BNF.
        
        Returns:
            Résultats du test de génération BNF
        """
        print("\n📝 Test de génération des règles BNF...")
        
        results = {
            'total_tests': len(self.test_errors),
            'successful_generations': 0,
            'failed_generations': 0,
            'details': []
        }
        
        for i, test_case in enumerate(self.test_errors, 1):
            print(f"  Test {i}: {test_case['type']}")
            
            try:
                feedback = self.analyzer.analyze_error(test_case['message'])
                generated_rules = feedback.bnf_rules
                
                if generated_rules and len(generated_rules) > 0:
                    print(f"    ✅ {len(generated_rules)} règles BNF générées")
                    results['successful_generations'] += 1
                    status = 'success'
                    
                    # Vérifier si une règle attendue est présente
                    expected_found = any(
                        expected in rule 
                        for expected in test_case['expected_bnf']
                        for rule in generated_rules
                    )
                    
                    if expected_found:
                        print(f"    ✅ Règle attendue trouvée")
                    else:
                        print(f"    ⚠️  Règle attendue non trouvée")
                        
                else:
                    print(f"    ❌ Aucune règle BNF générée")
                    results['failed_generations'] += 1
                    status = 'failed'
                
                results['details'].append({
                    'test_case': test_case,
                    'generated_rules': generated_rules,
                    'rule_count': len(generated_rules) if generated_rules else 0,
                    'status': status
                })
                
            except Exception as e:
                print(f"    💥 Erreur: {e}")
                results['failed_generations'] += 1
                results['details'].append({
                    'test_case': test_case,
                    'error': str(e),
                    'status': 'error'
                })
        
        generation_rate = results['successful_generations'] / results['total_tests'] * 100
        print(f"📊 Taux de génération BNF: {generation_rate:.1f}%")
        
        return results
    
    def test_feedback_formatting(self) -> Dict[str, Any]:
        """
        Test le formatage du feedback.
        
        Returns:
            Résultats du test de formatage
        """
        print("\n💬 Test de formatage du feedback...")
        
        results = {
            'total_tests': len(self.test_errors),
            'successful_formats': 0,
            'failed_formats': 0,
            'details': []
        }
        
        for i, test_case in enumerate(self.test_errors, 1):
            print(f"  Test {i}: {test_case['type']}")
            
            try:
                # Utiliser la fonction utilitaire
                formatted_feedback = analyze_tweety_error(
                    test_case['message'],
                    attempt_number=i,
                    context={'test': True}
                )
                
                # Vérifier que le feedback contient les sections attendues
                required_sections = [
                    'Analyse d\'erreur Tweety',
                    'Type d\'erreur détecté',
                    'Règles BNF pertinentes',
                    'Suggestions de correction',
                    'Exemple de correction'
                ]
                
                sections_found = sum(
                    1 for section in required_sections 
                    if section in formatted_feedback
                )
                
                if sections_found >= 4:  # Au moins 4/5 sections
                    print(f"    ✅ Feedback bien formaté ({sections_found}/5 sections)")
                    results['successful_formats'] += 1
                    status = 'success'
                else:
                    print(f"    ❌ Feedback mal formaté ({sections_found}/5 sections)")
                    results['failed_formats'] += 1
                    status = 'failed'
                
                results['details'].append({
                    'test_case': test_case,
                    'formatted_feedback': formatted_feedback,
                    'sections_found': sections_found,
                    'total_sections': len(required_sections),
                    'status': status
                })
                
            except Exception as e:
                print(f"    💥 Erreur: {e}")
                results['failed_formats'] += 1
                results['details'].append({
                    'test_case': test_case,
                    'error': str(e),
                    'status': 'error'
                })
        
        format_rate = results['successful_formats'] / results['total_tests'] * 100
        print(f"📊 Taux de formatage réussi: {format_rate:.1f}%")
        
        return results
    
    def test_confidence_calculation(self) -> Dict[str, Any]:
        """
        Test le calcul de confiance.
        
        Returns:
            Résultats du test de confiance
        """
        print("\n🎯 Test de calcul de confiance...")
        
        results = {
            'total_tests': len(self.test_errors),
            'valid_confidences': 0,
            'invalid_confidences': 0,
            'average_confidence': 0,
            'details': []
        }
        
        total_confidence = 0
        
        for i, test_case in enumerate(self.test_errors, 1):
            print(f"  Test {i}: {test_case['type']}")
            
            try:
                feedback = self.analyzer.analyze_error(test_case['message'])
                confidence = feedback.confidence
                
                if 0 <= confidence <= 1:
                    print(f"    ✅ Confiance valide: {confidence:.1%}")
                    results['valid_confidences'] += 1
                    total_confidence += confidence
                    status = 'success'
                else:
                    print(f"    ❌ Confiance invalide: {confidence}")
                    results['invalid_confidences'] += 1
                    status = 'failed'
                
                results['details'].append({
                    'test_case': test_case,
                    'confidence': confidence,
                    'status': status
                })
                
            except Exception as e:
                print(f"    💥 Erreur: {e}")
                results['invalid_confidences'] += 1
                results['details'].append({
                    'test_case': test_case,
                    'error': str(e),
                    'status': 'error'
                })
        
        if results['valid_confidences'] > 0:
            results['average_confidence'] = total_confidence / results['valid_confidences']
        
        confidence_rate = results['valid_confidences'] / results['total_tests'] * 100
        print(f"📊 Taux de confiance valide: {confidence_rate:.1f}%")
        print(f"📊 Confiance moyenne: {results['average_confidence']:.1%}")
        
        return results
    
    def generate_report(self, all_results: Dict[str, Any]) -> str:
        """
        Génère un rapport complet des tests.
        
        Args:
            all_results: Tous les résultats de tests
            
        Returns:
            Rapport formaté
        """
        report = f"""
RAPPORT DE TEST - SYSTÈME DE CORRECTION INTELLIGENTE DES ERREURS MODALES
========================================================================
Généré le: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

RÉSUMÉ EXÉCUTIF
===============
Ce rapport présente les résultats des tests du système de correction
intelligente des erreurs modales avec feedback BNF constructif.

"""
        
        for test_name, results in all_results.items():
            if 'total_tests' in results:
                successful = results.get('successful_detections', 0) + \
                           results.get('successful_generations', 0) + \
                           results.get('successful_formats', 0) + \
                           results.get('valid_confidences', 0)
                
                total = results['total_tests'] * len([k for k in results.keys() if 'successful' in k or 'valid' in k])
                if total == 0:
                    total = results['total_tests']
                
                success_rate = (successful / total * 100) if total > 0 else 0
                
                report += f"\n{test_name.upper().replace('_', ' ')}\n"
                report += "=" * len(test_name) + "\n"
                report += f"• Tests exécutés: {results['total_tests']}\n"
                report += f"• Taux de succès: {success_rate:.1f}%\n"
                
                if 'average_confidence' in results:
                    report += f"• Confiance moyenne: {results['average_confidence']:.1%}\n"
        
        # Recommandations
        report += f"\nRECOMMANDATIONS\n"
        report += "===============\n"
        
        overall_success = all(
            any(k.startswith('successful') and v > 0 for k, v in result.items() if isinstance(v, int))
            for result in all_results.values() if 'total_tests' in result
        )
        
        if overall_success:
            report += "🎉 Le système de correction intelligente fonctionne correctement.\n"
            report += "✅ Tous les composants principaux sont opérationnels.\n"
        else:
            report += "⚠️  Certains composants nécessitent des améliorations.\n"
            report += "🔧 Vérifier la configuration et les patterns d'erreur.\n"
        
        report += f"\n📋 PROCHAINES ÉTAPES\n"
        report += "====================\n"
        report += "1. Intégrer le système dans le pipeline principal\n"
        report += "2. Tester avec des erreurs réelles de production\n"
        report += "3. Affiner les patterns de détection\n"
        report += "4. Enrichir les règles BNF et corrections\n"
        
        return report
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Exécute tous les tests.
        
        Returns:
            Résultats complets de tous les tests
        """
        print("🧪 TESTS DU SYSTÈME DE CORRECTION INTELLIGENTE DES ERREURS MODALES")
        print("=" * 75)
        print("Ce script teste le nouveau système de feedback BNF pour la correction")
        print("d'erreurs modales dans l'analyse d'argumentation.")
        print()
        
        all_results = {}
        
        # Test 1: Détection des erreurs
        all_results['detection'] = self.test_error_detection()
        
        # Test 2: Génération BNF
        all_results['bnf_generation'] = self.test_bnf_generation()
        
        # Test 3: Formatage du feedback
        all_results['feedback_formatting'] = self.test_feedback_formatting()
        
        # Test 4: Calcul de confiance
        all_results['confidence_calculation'] = self.test_confidence_calculation()
        
        return all_results


async def main():
    """Fonction principale."""
    tester = ModalCorrectionTester()
    
    try:
        # Exécuter tous les tests
        results = await tester.run_all_tests()
        
        # Générer et afficher le rapport
        report = tester.generate_report(results)
        print("\n" + report)
        
        # Sauvegarder le rapport
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = f"modal_correction_test_report_{timestamp}.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n💾 Rapport sauvegardé: {report_file}")
        
        # Déterminer le succès global
        success_count = sum(
            1 for result in results.values()
            if 'total_tests' in result and any(
                k.startswith('successful') and v > 0 
                for k, v in result.items() if isinstance(v, int)
            )
        )
        
        total_test_categories = len(results)
        success_rate = success_count / total_test_categories * 100 if total_test_categories > 0 else 0
        
        print(f"\n🏁 RÉSULTAT GLOBAL")
        print("=" * 50)
        print(f"📊 Catégories de test réussies: {success_count}/{total_test_categories}")
        print(f"📈 Taux de succès global: {success_rate:.1f}%")
        
        if success_rate >= 75:
            print("🎉 Tests réussis! Le système est opérationnel.")
            return True
        else:
            print("⚠️  Tests partiellement réussis. Améliorations nécessaires.")
            return False
        
    except Exception as e:
        print(f"💥 Erreur fatale lors des tests: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
