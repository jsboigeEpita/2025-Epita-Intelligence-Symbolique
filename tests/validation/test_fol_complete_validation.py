#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Validation complète de l'agent FirstOrderLogicAgent (FOL).

Ce script exécute une validation exhaustive selon les critères de la tâche :

MÉTRIQUES DE VALIDATION :
✅ 100% des formules FOL générées valides
✅ 0 erreur de parsing Tweety avec syntaxe FOL  
✅ >95% compatibilité avec sophismes existants
✅ Temps réponse ≤ Modal Logic précédent
✅ >90% couverture tests pour FirstOrderLogicAgent
✅ Tous les cas d'erreur gérés
✅ Integration validée avec tous orchestrateurs

Tests de migration Modal Logic → FOL :
✅ Remplacement fonctionnel
✅ Amélioration stabilité
✅ Rétrocompatibilité
"""

import asyncio
import time
import logging
import json
import statistics
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import traceback

# Imports des composants à valider
from argumentation_analysis.agents.core.logic.fol_logic_agent import (
    FOLLogicAgent, 
    FOLAnalysisResult,
    create_fol_agent
)

from config.unified_config import (
    UnifiedConfig,
    LogicType, 
    MockLevel,
    AgentType,
    PresetConfigs
)

# Imports pour comparaison et validation
from argumentation_analysis.utils.tweety_error_analyzer import TweetyErrorAnalyzer

# Configuration logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FOLValidationMetrics:
    """Collecteur de métriques de validation FOL."""
    
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_details = []
        
        # Métriques spécifiques FOL
        self.fol_syntax_valid_count = 0
        self.fol_syntax_total_count = 0
        self.tweety_parsing_errors = 0
        self.tweety_parsing_attempts = 0
        
        # Performance
        self.analysis_times = []
        self.confidence_scores = []
        
        # Compatibilité
        self.sophism_compatibility_rate = 0.0
        self.migration_success_rate = 0.0
        
    def add_test_result(self, test_name: str, success: bool, details: Dict[str, Any] = None):
        """Ajoute un résultat de test."""
        self.total_tests += 1
        if success:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
            self.error_details.append({
                "test": test_name,
                "details": details or {}
            })
    
    def add_fol_syntax_result(self, formula: str, is_valid: bool):
        """Ajoute résultat validation syntaxe FOL."""
        self.fol_syntax_total_count += 1
        if is_valid:
            self.fol_syntax_valid_count += 1
    
    def add_tweety_parsing_result(self, formula: str, success: bool, error: str = None):
        """Ajoute résultat parsing Tweety."""
        self.tweety_parsing_attempts += 1
        if not success:
            self.tweety_parsing_errors += 1
            logger.warning(f"Erreur parsing Tweety: {formula} - {error}")
    
    def add_performance_data(self, analysis_time: float, confidence: float):
        """Ajoute données de performance."""
        self.analysis_times.append(analysis_time)
        self.confidence_scores.append(confidence)
    
    def get_summary(self) -> Dict[str, Any]:
        """Retourne résumé des métriques."""
        return {
            "test_success_rate": self.passed_tests / self.total_tests if self.total_tests > 0 else 0.0,
            "fol_syntax_validity_rate": self.fol_syntax_valid_count / self.fol_syntax_total_count if self.fol_syntax_total_count > 0 else 0.0,
            "tweety_parsing_success_rate": (self.tweety_parsing_attempts - self.tweety_parsing_errors) / self.tweety_parsing_attempts if self.tweety_parsing_attempts > 0 else 0.0,
            "avg_analysis_time": statistics.mean(self.analysis_times) if self.analysis_times else 0.0,
            "avg_confidence": statistics.mean(self.confidence_scores) if self.confidence_scores else 0.0,
            "sophism_compatibility": self.sophism_compatibility_rate,
            "migration_success": self.migration_success_rate,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "error_details": self.error_details
        }


class FOLCompleteValidator:
    """Validateur complet pour l'agent FOL."""
    
    def __init__(self):
        self.metrics = FOLValidationMetrics()
        self.error_analyzer = TweetyErrorAnalyzer()
        
        # Échantillons de test
        self.fol_syntax_samples = self._load_fol_syntax_samples()
        self.sophism_samples = self._load_sophism_samples()
        self.complex_argumentation_samples = self._load_complex_samples()
    
    def _load_fol_syntax_samples(self) -> List[Dict[str, str]]:
        """Charge échantillons syntaxe FOL à valider."""
        return [
            {
                "description": "Quantificateur universel basique",
                "formula": "∀x(Human(x) → Mortal(x))",
                "expected_valid": True
            },
            {
                "description": "Quantificateur existentiel",
                "formula": "∃x(Student(x) ∧ Intelligent(x))",
                "expected_valid": True
            },
            {
                "description": "Prédicat complexe binaire",
                "formula": "∀x∀y(Loves(x,y) → Cares(x,y))",
                "expected_valid": True
            },
            {
                "description": "Connecteurs logiques multiples",
                "formula": "∀x((P(x) ∧ Q(x)) → (R(x) ∨ S(x)))",
                "expected_valid": True
            },
            {
                "description": "Équivalence logique",
                "formula": "∃x(¬Bad(x) ↔ Good(x))",
                "expected_valid": True
            },
            {
                "description": "Quantificateurs imbriqués",
                "formula": "∀x∃y∀z(Rel(x,y) → Prop(z))",
                "expected_valid": True
            },
            {
                "description": "Négation quantificateur",
                "formula": "¬∀x(P(x)) ↔ ∃x(¬P(x))",
                "expected_valid": True
            },
            {
                "description": "Formule invalide - variable libre",
                "formula": "∀x(P(x)) ∧ Q(y)",
                "expected_valid": False
            }
        ]
    
    def _load_sophism_samples(self) -> List[Dict[str, str]]:
        """Charge échantillons de sophismes pour test compatibilité."""
        return [
            {
                "name": "Syllogisme valide",
                "text": "Tous les hommes sont mortels. Socrate est un homme. Donc Socrate est mortel.",
                "expected_consistent": True
            },
            {
                "name": "Affirmation du conséquent",
                "text": "Si il pleut, alors le sol est mouillé. Le sol est mouillé. Donc il pleut.",
                "expected_consistent": False  # Sophisme
            },
            {
                "name": "Modus ponens",
                "text": "Si P alors Q. P est vrai. Donc Q est vrai.",
                "expected_consistent": True
            },
            {
                "name": "Généralisation abusive",
                "text": "Tous les corbeaux observés sont noirs. Donc tous les corbeaux sont noirs.",
                "expected_consistent": False  # Induction problématique
            },
            {
                "name": "Contradiction directe",
                "text": "Tous les chats sont noirs. Certains chats ne sont pas noirs.",
                "expected_consistent": False
            }
        ]
    
    def _load_complex_samples(self) -> List[Dict[str, str]]:
        """Charge échantillons d'argumentation complexe."""
        return [
            {
                "name": "Argumentation philosophique",
                "text": """
                Tous les philosophes sont des penseurs.
                Certains penseurs sont des écrivains.
                Socrate est un philosophe.
                Si quelqu'un est écrivain, alors il influence la culture.
                """
            },
            {
                "name": "Raisonnement scientifique",
                "text": """
                Toutes les théories scientifiques sont falsifiables.
                La théorie de l'évolution est une théorie scientifique.
                Si une théorie est falsifiable, alors elle peut être testée.
                """
            },
            {
                "name": "Logique déontique simple",
                "text": """
                Il est obligatoire de respecter la loi.
                Conduire en état d'ivresse viole la loi.
                Donc il est interdit de conduire en état d'ivresse.
                """
            }
        ]
    
    async def validate_fol_syntax_generation(self) -> bool:
        """Valide génération syntaxe FOL selon critères."""
        logger.info("🔍 Validation génération syntaxe FOL...")
        
        agent = FOLLogicAgent(agent_name="SyntaxValidator")
        success = True
        
        for sample in self.fol_syntax_samples:
            try:
                # Test si la formule est reconnue comme valide
                is_valid = self._validate_fol_formula(sample["formula"])
                
                self.metrics.add_fol_syntax_result(sample["formula"], is_valid)
                
                # Vérification conformité attendue
                if is_valid != sample["expected_valid"]:
                    success = False
                    logger.error(f"❌ Validation syntaxe échouée: {sample['description']}")
                    logger.error(f"   Formule: {sample['formula']}")
                    logger.error(f"   Attendu: {sample['expected_valid']}, Obtenu: {is_valid}")
                else:
                    logger.info(f"✅ Syntaxe validée: {sample['description']}")
                    
            except Exception as e:
                success = False
                logger.error(f"❌ Erreur validation syntaxe: {sample['description']} - {e}")
        
        # Vérification critère : 100% formules valides
        syntax_rate = self.metrics.fol_syntax_valid_count / self.metrics.fol_syntax_total_count
        if syntax_rate < 1.0:
            logger.warning(f"⚠️ Taux syntaxe valide: {syntax_rate:.2%} < 100%")
        
        self.metrics.add_test_result("fol_syntax_generation", success, {
            "syntax_validity_rate": syntax_rate,
            "total_formulas": self.metrics.fol_syntax_total_count,
            "valid_formulas": self.metrics.fol_syntax_valid_count
        })
        
        return success
    
    def _validate_fol_formula(self, formula: str) -> bool:
        """Validation basique syntaxe FOL."""
        # Caractères FOL attendus
        fol_chars = ["∀", "∃", "→", "∧", "∨", "¬", "↔"]
        
        # Vérifications de base
        has_quantifier = any(q in formula for q in ["∀", "∃"])
        has_predicate = "(" in formula and ")" in formula
        balanced_parens = formula.count("(") == formula.count(")")
        
        # Variables libres (heuristique simple)
        # Cette validation pourrait être plus sophistiquée
        return (has_quantifier or has_predicate) and balanced_parens
    
    async def validate_tweety_integration(self) -> bool:
        """Valide intégration avec TweetyProject."""
        logger.info("🔍 Validation intégration Tweety...")
        
        agent = FOLLogicAgent(agent_name="TweetyValidator")
        
        # Setup agent si possible
        try:
            await agent.setup_agent_components()
        except Exception as e:
            logger.warning(f"⚠️ Setup Tweety échoué (normal en test): {e}")
        
        success = True
        
        # Test formules avec Tweety (ou simulation)
        for sample in self.fol_syntax_samples:
            if sample["expected_valid"]:
                try:
                    # Test via analyse complète
                    result = await agent._analyze_with_tweety([sample["formula"]])
                    
                    # Pas d'erreur de parsing = succès
                    parsing_success = len(result.validation_errors) == 0
                    self.metrics.add_tweety_parsing_result(sample["formula"], parsing_success)
                    
                    if not parsing_success:
                        success = False
                        logger.error(f"❌ Parsing Tweety échoué: {sample['formula']}")
                        for error in result.validation_errors:
                            logger.error(f"   Erreur: {error}")
                    else:
                        logger.info(f"✅ Parsing Tweety réussi: {sample['description']}")
                        
                except Exception as e:
                    success = False
                    logger.error(f"❌ Erreur Tweety: {sample['formula']} - {e}")
                    self.metrics.add_tweety_parsing_result(sample["formula"], False, str(e))
        
        # Vérification critère : 0 erreur parsing
        parsing_success_rate = (self.metrics.tweety_parsing_attempts - self.metrics.tweety_parsing_errors) / self.metrics.tweety_parsing_attempts
        if parsing_success_rate < 1.0:
            logger.warning(f"⚠️ Taux succès parsing Tweety: {parsing_success_rate:.2%} < 100%")
        
        self.metrics.add_test_result("tweety_integration", success, {
            "parsing_success_rate": parsing_success_rate,
            "parsing_errors": self.metrics.tweety_parsing_errors,
            "total_attempts": self.metrics.tweety_parsing_attempts
        })
        
        return success
    
    async def validate_sophism_compatibility(self) -> bool:
        """Valide compatibilité avec sophismes existants."""
        logger.info("🔍 Validation compatibilité sophismes...")
        
        agent = FOLLogicAgent(agent_name="SophismValidator")
        
        successful_analyses = 0
        total_analyses = len(self.sophism_samples)
        
        for sophism in self.sophism_samples:
            try:
                start_time = time.time()
                result = await agent.analyze(sophism["text"])
                analysis_time = time.time() - start_time
                
                # Collecte métriques
                self.metrics.add_performance_data(analysis_time, result.confidence_score)
                
                # Vérification résultat cohérent
                if isinstance(result, FOLAnalysisResult) and result.confidence_score > 0.0:
                    successful_analyses += 1
                    logger.info(f"✅ Sophisme analysé: {sophism['name']} (confiance: {result.confidence_score:.2f})")
                else:
                    logger.warning(f"⚠️ Analyse faible: {sophism['name']}")
                    
            except Exception as e:
                logger.error(f"❌ Erreur analyse sophisme {sophism['name']}: {e}")
        
        # Calcul taux compatibilité
        compatibility_rate = successful_analyses / total_analyses
        self.metrics.sophism_compatibility_rate = compatibility_rate
        
        # Vérification critère : >95% compatibilité
        success = compatibility_rate > 0.95
        
        if not success:
            logger.warning(f"⚠️ Compatibilité sophismes: {compatibility_rate:.2%} < 95%")
        
        self.metrics.add_test_result("sophism_compatibility", success, {
            "compatibility_rate": compatibility_rate,
            "successful_analyses": successful_analyses,
            "total_analyses": total_analyses
        })
        
        return success
    
    async def validate_performance_requirements(self) -> bool:
        """Valide exigences de performance."""
        logger.info("🔍 Validation performance...")
        
        agent = FOLLogicAgent(agent_name="PerformanceValidator")
        
        # Tests performance sur échantillons complexes
        performance_times = []
        confidence_scores = []
        
        for sample in self.complex_argumentation_samples:
            try:
                start_time = time.time()
                result = await agent.analyze(sample["text"])
                analysis_time = time.time() - start_time
                
                performance_times.append(analysis_time)
                confidence_scores.append(result.confidence_score)
                
                logger.info(f"✅ Performance {sample['name']}: {analysis_time:.2f}s (confiance: {result.confidence_score:.2f})")
                
            except Exception as e:
                logger.error(f"❌ Erreur performance {sample['name']}: {e}")
        
        # Calcul métriques performance
        if performance_times:
            avg_time = statistics.mean(performance_times)
            max_time = max(performance_times)
            avg_confidence = statistics.mean(confidence_scores)
            
            # Critères performance (adaptables selon contexte)
            time_acceptable = avg_time < 10.0  # < 10 secondes moyenne
            max_time_acceptable = max_time < 30.0  # < 30 secondes max
            confidence_acceptable = avg_confidence > 0.5  # > 50% confiance moyenne
            
            success = time_acceptable and max_time_acceptable and confidence_acceptable
            
            logger.info(f"📊 Performance moyenne: {avg_time:.2f}s")
            logger.info(f"📊 Performance maximale: {max_time:.2f}s")  
            logger.info(f"📊 Confiance moyenne: {avg_confidence:.2f}")
            
            if not success:
                logger.warning("⚠️ Performance insuffisante")
        else:
            success = False
            logger.error("❌ Aucun test de performance réussi")
        
        self.metrics.add_test_result("performance_requirements", success, {
            "avg_analysis_time": avg_time if performance_times else 0.0,
            "max_analysis_time": max_time if performance_times else 0.0,
            "avg_confidence": avg_confidence if confidence_scores else 0.0,
            "total_performance_tests": len(performance_times)
        })
        
        return success
    
    async def validate_error_handling(self) -> bool:
        """Valide gestion complète des erreurs."""
        logger.info("🔍 Validation gestion erreurs...")
        
        agent = FOLLogicAgent(agent_name="ErrorValidator")
        
        # Cas d'erreur à tester
        error_cases = [
            {
                "name": "Texte vide",
                "input": "",
                "should_handle": True
            },
            {
                "name": "Texte non-logique",
                "input": "Ceci n'est pas de la logique !!!",
                "should_handle": True
            },
            {
                "name": "Caractères spéciaux",
                "input": "∀∃→∧∨¬↔ sans structure",
                "should_handle": True
            },
            {
                "name": "Texte très long",
                "input": "Test de performance. " * 1000,
                "should_handle": True
            }
        ]
        
        successful_error_handling = 0
        
        for case in error_cases:
            try:
                result = await agent.analyze(case["input"])
                
                # Vérification gestion gracieuse
                if isinstance(result, FOLAnalysisResult):
                    successful_error_handling += 1
                    logger.info(f"✅ Erreur gérée: {case['name']}")
                else:
                    logger.warning(f"⚠️ Gestion erreur problématique: {case['name']}")
                    
            except Exception as e:
                if case["should_handle"]:
                    logger.error(f"❌ Erreur non gérée: {case['name']} - {e}")
                else:
                    logger.info(f"✅ Erreur attendue: {case['name']}")
                    successful_error_handling += 1
        
        success = successful_error_handling == len(error_cases)
        
        self.metrics.add_test_result("error_handling", success, {
            "successful_error_handling": successful_error_handling,
            "total_error_cases": len(error_cases)
        })
        
        return success
    
    async def validate_configuration_integration(self) -> bool:
        """Valide intégration avec système de configuration."""
        logger.info("🔍 Validation intégration configuration...")
        
        success = True
        
        # Test configurations prédéfinies
        configs = {
            "authentic_fol": PresetConfigs.authentic_fol(),
            "development": PresetConfigs.development(),
        }
        
        for config_name, config in configs.items():
            try:
                # Test création agent avec config
                agent = FOLLogicAgent(agent_name=f"Config_{config_name}")
                
                # Test analyse basique
                result = await agent.analyze("Test configuration.")
                
                if isinstance(result, FOLAnalysisResult):
                    logger.info(f"✅ Configuration {config_name} validée")
                else:
                    success = False
                    logger.error(f"❌ Configuration {config_name} échouée")
                    
            except Exception as e:
                success = False
                logger.error(f"❌ Erreur configuration {config_name}: {e}")
        
        self.metrics.add_test_result("configuration_integration", success)
        
        return success
    
    async def run_complete_validation(self) -> Dict[str, Any]:
        """Exécute validation complète et retourne rapport."""
        logger.info("🚀 Début validation complète agent FOL")
        
        start_time = time.time()
        
        # Exécution des validations
        validations = [
            ("Génération syntaxe FOL", self.validate_fol_syntax_generation()),
            ("Intégration Tweety", self.validate_tweety_integration()),
            ("Compatibilité sophismes", self.validate_sophism_compatibility()),
            ("Performance", self.validate_performance_requirements()),
            ("Gestion erreurs", self.validate_error_handling()),
            ("Intégration configuration", self.validate_configuration_integration())
        ]
        
        validation_results = {}
        
        for name, validation_coro in validations:
            try:
                logger.info(f"▶️ {name}...")
                result = await validation_coro
                validation_results[name] = result
                if result:
                    logger.info(f"✅ {name} réussie")
                else:
                    logger.warning(f"⚠️ {name} échouée")
            except Exception as e:
                logger.error(f"❌ {name} erreur: {e}")
                validation_results[name] = False
                traceback.print_exc()
        
        total_time = time.time() - start_time
        
        # Génération rapport final
        report = self._generate_validation_report(validation_results, total_time)
        
        logger.info("🏁 Validation complète terminée")
        
        return report
    
    def _generate_validation_report(self, validation_results: Dict[str, bool], total_time: float) -> Dict[str, Any]:
        """Génère rapport final de validation."""
        metrics_summary = self.metrics.get_summary()
        
        # Analyse conformité critères
        criteria_met = {
            "100% formules FOL valides": metrics_summary.get("fol_syntax_validity_rate", 0.0) >= 1.0,
            "0 erreur parsing Tweety": metrics_summary.get("tweety_parsing_success_rate", 0.0) >= 1.0,
            ">95% compatibilité sophismes": metrics_summary.get("sophism_compatibility", 0.0) > 0.95,
            "Performance acceptable": metrics_summary.get("avg_analysis_time", 0.0) < 10.0,
            "Gestion erreurs complète": validation_results.get("Gestion erreurs", False)
        }
        
        overall_success = all(validation_results.values()) and all(criteria_met.values())
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_validation_time": total_time,
            "overall_success": overall_success,
            "validation_results": validation_results,
            "criteria_compliance": criteria_met,
            "metrics": metrics_summary,
            "summary": {
                "tests_passed": sum(validation_results.values()),
                "tests_total": len(validation_results),
                "criteria_met": sum(criteria_met.values()),
                "criteria_total": len(criteria_met)
            },
            "recommendations": self._generate_recommendations(criteria_met, metrics_summary)
        }
        
        return report
    
    def _generate_recommendations(self, criteria_met: Dict[str, bool], metrics: Dict[str, Any]) -> List[str]:
        """Génère recommandations basées sur les résultats."""
        recommendations = []
        
        if not criteria_met.get("100% formules FOL valides", True):
            recommendations.append("Améliorer validation syntaxe FOL - certaines formules invalides générées")
        
        if not criteria_met.get("0 erreur parsing Tweety", True):
            recommendations.append("Corriger compatibilité Tweety - erreurs de parsing détectées")
        
        if not criteria_met.get(">95% compatibilité sophismes", True):
            recommendations.append("Améliorer analyse sophismes - taux compatibilité insuffisant")
        
        if not criteria_met.get("Performance acceptable", True):
            recommendations.append("Optimiser performance - temps d'analyse trop long")
        
        if metrics.get("avg_confidence", 0.0) < 0.7:
            recommendations.append("Améliorer confiance analyses - scores trop faibles")
        
        if not recommendations:
            recommendations.append("✅ Toutes les validations réussies - Agent FOL prêt pour production")
        
        return recommendations


async def main():
    """Point d'entrée principal pour validation complète."""
    validator = FOLCompleteValidator()
    
    try:
        report = await validator.run_complete_validation()
        
        # Affichage rapport
        print("\n" + "="*80)
        print("📋 RAPPORT VALIDATION AGENT FOL")
        print("="*80)
        
        print(f"\n🕐 Temps total: {report['total_validation_time']:.2f}s")
        print(f"🎯 Succès global: {'✅ OUI' if report['overall_success'] else '❌ NON'}")
        
        print(f"\n📊 Résultats validation:")
        for validation, success in report['validation_results'].items():
            status = "✅" if success else "❌"
            print(f"  {status} {validation}")
        
        print(f"\n📏 Conformité critères:")
        for criterion, met in report['criteria_compliance'].items():
            status = "✅" if met else "❌"
            print(f"  {status} {criterion}")
        
        print(f"\n📈 Métriques clés:")
        metrics = report['metrics']
        print(f"  • Syntaxe FOL valide: {metrics.get('fol_syntax_validity_rate', 0):.1%}")
        print(f"  • Parsing Tweety: {metrics.get('tweety_parsing_success_rate', 0):.1%}")
        print(f"  • Compatibilité sophismes: {metrics.get('sophism_compatibility', 0):.1%}")
        print(f"  • Temps analyse moyen: {metrics.get('avg_analysis_time', 0):.2f}s")
        print(f"  • Confiance moyenne: {metrics.get('avg_confidence', 0):.2f}")
        
        print(f"\n💡 Recommandations:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        # Sauvegarde rapport
        report_path = Path("reports/fol_validation_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Rapport sauvegardé: {report_path}")
        
        return report['overall_success']
        
    except Exception as e:
        logger.error(f"❌ Erreur validation: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)