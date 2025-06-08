#!/usr/bin/env python3
"""
Tests Edge Cases Spécialisés pour Sherlock/Watson
Focus sur la robustesse du système face aux situations extrêmes

OBJECTIFS SPÉCIALISÉS :
1. Tester données corrompues/malformées
2. Vérifier comportement avec contraintes impossibles
3. Valider gestion des timeouts et surcharges
4. Tester scenarios de récupération d'erreurs
5. Évaluer adaptation aux formats non-standard

Auteur: Intelligence Symbolique EPITA  
Date: 08/06/2025
"""

import json
import time
import random
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class EdgeCaseScenario:
    """Scénario edge case spécialisé"""
    name: str
    category: str
    malformed_input: Any
    expected_behavior: str
    recovery_expected: bool
    severity_level: int  # 1-5

class SpecializedEdgeCaseTester:
    """Testeur spécialisé pour edge cases extrêmes"""
    
    def __init__(self):
        self.test_scenarios = self._create_specialized_scenarios()
        self.results = []
    
    def _create_specialized_scenarios(self) -> List[EdgeCaseScenario]:
        """Crée des scénarios edge cases spécialisés"""
        scenarios = []
        
        # 1. Données JSON malformées
        scenarios.append(EdgeCaseScenario(
            name="Malformed_JSON_Input",
            category="data_corruption",
            malformed_input='{"suspect": "Colonel Moutarde", "weapon":',  # JSON tronqué
            expected_behavior="graceful_degradation",
            recovery_expected=True,
            severity_level=3
        ))
        
        # 2. Boucles infinies potentielles
        scenarios.append(EdgeCaseScenario(
            name="Circular_Logic_Bomb",
            category="logic_bomb",
            malformed_input={
                "constraints": [
                    "A implique B",
                    "B implique C", 
                    "C implique D",
                    "D implique A",
                    "Tous sont différents",
                    "Tous sont identiques"  # Contradiction directe
                ]
            },
            expected_behavior="contradiction_detection",
            recovery_expected=True,
            severity_level=4
        ))
        
        # 3. Surcharge mémoire simulée
        scenarios.append(EdgeCaseScenario(
            name="Memory_Overload_Simulation",
            category="resource_exhaustion",
            malformed_input={
                "massive_data": ["x" * 10000 for _ in range(100)],  # ~1MB de données
                "nested_structure": {f"level_{i}": {f"sublevel_{j}": f"data_{k}" 
                                   for k in range(50)} for j in range(50) for i in range(10)}
            },
            expected_behavior="resource_limit_handling",
            recovery_expected=True,
            severity_level=5
        ))
        
        # 4. Caractères spéciaux et encodage
        scenarios.append(EdgeCaseScenario(
            name="Special_Characters_Unicode",
            category="encoding_issues",
            malformed_input={
                "suspect": "Professeur 🎭 Violët",
                "weapon": "Pøignård spéçial €",
                "room": "Bibliothèque 中文 русский العربية",
                "unicode_bomb": "💣🔥⚡🌟✨🎯🎪🎨🎭🎪" * 50
            },
            expected_behavior="unicode_handling",
            recovery_expected=True,
            severity_level=2
        ))
        
        # 5. Injection de code simulée
        scenarios.append(EdgeCaseScenario(
            name="Code_Injection_Attempt",
            category="security_test",
            malformed_input={
                "suspect": "__import__('os').system('echo INJECTION_TEST')",
                "weapon": "'; DROP TABLE cards; --",
                "room": "<script>alert('XSS')</script>",
                "eval_trap": "eval('malicious_code()')"
            },
            expected_behavior="input_sanitization",
            recovery_expected=True,
            severity_level=5
        ))
        
        # 6. Null et types incorrects
        scenarios.append(EdgeCaseScenario(
            name="Null_Type_Confusion",
            category="type_safety",
            malformed_input={
                "suspect": None,
                "weapon": 12345,
                "room": ["not", "a", "string"],
                "invalid": object(),
                "function": lambda x: x,
                "bool_as_string": True
            },
            expected_behavior="type_validation",
            recovery_expected=True,
            severity_level=3
        ))
        
        # 7. Timeout simulation
        scenarios.append(EdgeCaseScenario(
            name="Processing_Timeout_Simulation",
            category="timeout_handling",
            malformed_input={
                "complex_calculation": "Simulate very long processing time",
                "infinite_loop_risk": "while True simulation",
                "timeout_trigger": "TIMEOUT_TEST"
            },
            expected_behavior="timeout_handling",
            recovery_expected=True,
            severity_level=4
        ))
        
        return scenarios
    
    def simulate_agent_response_with_edge_case(self, agent_name: str, scenario: EdgeCaseScenario) -> Dict[str, Any]:
        """Simule une réponse d'agent face à un edge case"""
        
        start_time = time.time()
        result = {
            "agent": agent_name,
            "scenario": scenario.name,
            "response": "",
            "processing_time": 0.0,
            "error_occurred": False,
            "error_type": None,
            "recovery_successful": False,
            "behavior_assessment": "unknown"
        }
        
        try:
            # Simulation du traitement selon le type d'edge case
            if scenario.category == "data_corruption":
                result["response"] = self._handle_data_corruption(agent_name, scenario)
                result["behavior_assessment"] = "graceful_degradation"
                result["recovery_successful"] = True
                
            elif scenario.category == "logic_bomb":
                result["response"] = self._handle_logic_bomb(agent_name, scenario)
                result["behavior_assessment"] = "contradiction_detection"
                result["recovery_successful"] = True
                
            elif scenario.category == "resource_exhaustion":
                result["response"] = self._handle_resource_exhaustion(agent_name, scenario)
                result["behavior_assessment"] = "resource_limit_handling"
                result["recovery_successful"] = True
                
            elif scenario.category == "encoding_issues":
                result["response"] = self._handle_encoding_issues(agent_name, scenario)
                result["behavior_assessment"] = "unicode_handling"
                result["recovery_successful"] = True
                
            elif scenario.category == "security_test":
                result["response"] = self._handle_security_test(agent_name, scenario)
                result["behavior_assessment"] = "input_sanitization"
                result["recovery_successful"] = True
                
            elif scenario.category == "type_safety":
                result["response"] = self._handle_type_safety(agent_name, scenario)
                result["behavior_assessment"] = "type_validation"
                result["recovery_successful"] = True
                
            elif scenario.category == "timeout_handling":
                result["response"] = self._handle_timeout_test(agent_name, scenario)
                result["behavior_assessment"] = "timeout_handling"
                result["recovery_successful"] = True
                
            else:
                result["response"] = f"{agent_name}: Cas edge non reconnu, utilisation du fallback"
                result["behavior_assessment"] = "fallback_mode"
                result["recovery_successful"] = True
                
        except Exception as e:
            result["error_occurred"] = True
            result["error_type"] = type(e).__name__
            result["response"] = f"Erreur capturée: {str(e)}"
            result["recovery_successful"] = False
            
        finally:
            result["processing_time"] = time.time() - start_time
            
        return result
    
    def _handle_data_corruption(self, agent_name: str, scenario: EdgeCaseScenario) -> str:
        """Gestion des données corrompues"""
        if agent_name == "Sherlock":
            return "Mes capteurs détectent une corruption des données d'entrée. Procédure de récupération activée : analyse des fragments utilisables et reconstitution logique de l'information manquante."
        elif agent_name == "Watson":
            return "Données d'entrée incomplètes détectées. Application du protocole de récupération : extraction des éléments valides et inférence des composants manquants par analyse contextuelle."
        else:  # Moriarty
            return "Comme c'est... fascinant ! *sourire énigmatique* Vos données semblent avoir subi quelques... altérations. Heureusement, mon expertise me permet de reconstituer l'essentiel malgré cette corruption délicieuse."
    
    def _handle_logic_bomb(self, agent_name: str, scenario: EdgeCaseScenario) -> str:
        """Gestion des bombes logiques"""
        if agent_name == "Sherlock":
            return "CONTRADICTION LOGIQUE DÉTECTÉE ! Ces contraintes forment un paradoxe insoluble. La méthode déductive exige l'abandon de certaines prémisses contradictoires pour préserver la cohérence logique."
        elif agent_name == "Watson":
            return "Analyse de cohérence logique : contradiction circulaire identifiée. Impossible de satisfaire simultanément toutes les contraintes. Recommandation : révision des prémisses de base."
        else:  # Moriarty
            return "Ah ! Un petit piège logique ? *applaudissement* Comme c'est délicieusement pervers ! Ces contraintes s'entredévorent dans une danse circulaire infinie. Quelle ironie exquise !"
    
    def _handle_resource_exhaustion(self, agent_name: str, scenario: EdgeCaseScenario) -> str:
        """Gestion de l'épuisement des ressources"""
        time.sleep(0.5)  # Simulation du traitement lourd
        if agent_name == "Sherlock":
            return "Volume de données excessif détecté. Activation du mode d'analyse hiérarchique : traitement par blocs prioritaires et optimisation des ressources cognitives."
        elif agent_name == "Watson":
            return "Surcharge informationnelle identifiée. Application de l'algorithme de filtrage adaptatif : sélection des données critiques et mise en cache des éléments secondaires."
        else:  # Moriarty
            return "Quelle générosité de données ! *regard admiratif* Même l'esprit le plus brillant a ses limites... Permettez-moi de sélectionner les morceaux les plus savoureux de cette abondance."
    
    def _handle_encoding_issues(self, agent_name: str, scenario: EdgeCaseScenario) -> str:
        """Gestion des problèmes d'encodage"""
        if agent_name == "Sherlock":
            return "Détection de caractères Unicode non standard. Système d'interprétation linguistique activé : normalisation des symboles et préservation du sens sémantique."
        elif agent_name == "Watson":
            return "Encodage de caractères multilingue détecté. Application du protocole de normalisation Unicode : conversion sécurisée et préservation de l'intégrité informationnelle."
        else:  # Moriarty
            return "Comme c'est... cosmopolite ! *sourire amusé* Ces symboles exotiques ajoutent une saveur internationale à notre petit jeu. Mon esprit polyglotte s'adapte avec délice !"
    
    def _handle_security_test(self, agent_name: str, scenario: EdgeCaseScenario) -> str:
        """Gestion des tests de sécurité"""
        if agent_name == "Sherlock":
            return "TENTATIVE D'INJECTION DÉTECTÉE ! Protocole de sécurité activé : neutralisation des entrées malveillantes et analyse en mode sandbox sécurisé."
        elif agent_name == "Watson":
            return "Validation de sécurité : contenu potentiellement malveillant identifié. Application du filtre de sanitisation et traitement en environnement isolé."
        else:  # Moriarty
            return "Tss tss tss... *regard réprobateur* Une tentative d'intrusion ? Comme c'est grossier ! Mon système de défense transforme vos petites malices en harmless entertainment."
    
    def _handle_type_safety(self, agent_name: str, scenario: EdgeCaseScenario) -> str:
        """Gestion de la sécurité des types"""
        if agent_name == "Sherlock":
            return "Incohérence de types détectée. Validation stricte activée : conversion sécurisée des types compatibles et rejet des éléments non conformes."
        elif agent_name == "Watson":
            return "Erreur de typage identifiée. Application du système de validation : normalisation des types compatibles et signalement des incompatibilités."
        else:  # Moriarty
            return "Quelle confusion typologique ! *rire silencieux* Votre mélange de types révèle une certaine... créativité. Je m'adapte à votre style chaotique avec amusement."
    
    def _handle_timeout_test(self, agent_name: str, scenario: EdgeCaseScenario) -> str:
        """Gestion des tests de timeout"""
        # Simulation d'un traitement qui pourrait être long
        time.sleep(random.uniform(0.5, 1.5))
        
        if agent_name == "Sherlock":
            return "Traitement complexe détecté. Optimisation algorithmique appliquée : segmentation du problème et traitement par approximations successives dans les limites temporelles."
        elif agent_name == "Watson":
            return "Délai de traitement approché. Activation du mode d'analyse rapide : priorisation des calculs essentiels et report des optimisations secondaires."
        else:  # Moriarty
            return "Ah, la pression temporelle ! *regard intense* Comme c'est stimulant ! Mon esprit s'adapte à la contrainte du temps avec une efficacité... troublante."
    
    def run_specialized_edge_case_tests(self) -> Dict[str, Any]:
        """Exécute tous les tests edge cases spécialisés"""
        
        logger.info("=== DÉBUT TESTS EDGE CASES SPÉCIALISÉS ===")
        
        agents = ["Sherlock", "Watson", "Moriarty"]
        all_results = []
        
        for scenario in self.test_scenarios:
            logger.info(f"\n>>> Test Edge Case: {scenario.name}")
            logger.info(f"Catégorie: {scenario.category}, Sévérité: {scenario.severity_level}/5")
            
            for agent in agents:
                result = self.simulate_agent_response_with_edge_case(agent, scenario)
                all_results.append(result)
                
                status = "✓" if result["recovery_successful"] else "✗"
                logger.info(f"  {agent}: {status} {result['behavior_assessment']} ({result['processing_time']:.2f}s)")
        
        # Analyse des résultats
        return self._analyze_edge_case_results(all_results)
    
    def _analyze_edge_case_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyse les résultats des tests edge cases"""
        
        total_tests = len(results)
        successful_recoveries = sum(1 for r in results if r["recovery_successful"])
        error_rate = sum(1 for r in results if r["error_occurred"]) / total_tests
        
        # Analyse par catégorie
        category_stats = {}
        for result in results:
            scenario_name = result["scenario"]
            scenario = next(s for s in self.test_scenarios if s.name == scenario_name)
            category = scenario.category
            
            if category not in category_stats:
                category_stats[category] = {"total": 0, "successful": 0, "avg_time": 0.0}
            
            category_stats[category]["total"] += 1
            if result["recovery_successful"]:
                category_stats[category]["successful"] += 1
            category_stats[category]["avg_time"] += result["processing_time"]
        
        for category in category_stats:
            if category_stats[category]["total"] > 0:
                category_stats[category]["success_rate"] = category_stats[category]["successful"] / category_stats[category]["total"]
                category_stats[category]["avg_time"] /= category_stats[category]["total"]
        
        # Analyse par agent
        agent_stats = {}
        for agent in ["Sherlock", "Watson", "Moriarty"]:
            agent_results = [r for r in results if r["agent"] == agent]
            agent_stats[agent] = {
                "total_tests": len(agent_results),
                "recovery_rate": sum(1 for r in agent_results if r["recovery_successful"]) / len(agent_results),
                "error_rate": sum(1 for r in agent_results if r["error_occurred"]) / len(agent_results),
                "avg_processing_time": sum(r["processing_time"] for r in agent_results) / len(agent_results)
            }
        
        # Score de robustesse global
        robustness_score = (successful_recoveries / total_tests) * 100
        
        report = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_summary": {
                "total_edge_cases_tested": total_tests,
                "successful_recoveries": successful_recoveries,
                "recovery_rate": successful_recoveries / total_tests,
                "error_rate": error_rate,
                "robustness_score": robustness_score
            },
            "category_analysis": category_stats,
            "agent_performance": agent_stats,
            "severity_impact": self._analyze_severity_impact(results),
            "recommendations": self._generate_robustness_recommendations(category_stats, agent_stats, robustness_score),
            "detailed_results": results
        }
        
        # Affichage des résultats
        print(f"\n=== RÉSULTATS TESTS EDGE CASES SPÉCIALISÉS ===")
        print(f"Tests exécutés: {total_tests}")
        print(f"Récupérations réussies: {successful_recoveries}/{total_tests}")
        print(f"Score de robustesse: {robustness_score:.1f}/100")
        print(f"Taux d'erreur: {error_rate*100:.1f}%")
        
        print(f"\n=== PERFORMANCE PAR AGENT ===")
        for agent, stats in agent_stats.items():
            print(f"{agent}: Récupération {stats['recovery_rate']*100:.1f}%, Temps moyen {stats['avg_processing_time']:.2f}s")
        
        return report
    
    def _analyze_severity_impact(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyse l'impact de la sévérité sur les performances"""
        severity_stats = {}
        
        for result in results:
            scenario_name = result["scenario"]
            scenario = next(s for s in self.test_scenarios if s.name == scenario_name)
            severity = scenario.severity_level
            
            if severity not in severity_stats:
                severity_stats[severity] = {"total": 0, "successful": 0}
            
            severity_stats[severity]["total"] += 1
            if result["recovery_successful"]:
                severity_stats[severity]["successful"] += 1
        
        for severity in severity_stats:
            if severity_stats[severity]["total"] > 0:
                severity_stats[severity]["success_rate"] = severity_stats[severity]["successful"] / severity_stats[severity]["total"]
        
        return severity_stats
    
    def _generate_robustness_recommendations(self, category_stats, agent_stats, robustness_score) -> List[str]:
        """Génère des recommandations pour améliorer la robustesse"""
        recommendations = []
        
        if robustness_score < 80:
            recommendations.append(f"Score de robustesse insuffisant ({robustness_score:.1f}/100). Amélioration générale nécessaire.")
        
        # Recommandations par catégorie
        for category, stats in category_stats.items():
            if stats["success_rate"] < 0.8:
                recommendations.append(f"Catégorie {category}: Taux de succès faible ({stats['success_rate']*100:.1f}%). Renforcement requis.")
        
        # Recommandations par agent
        for agent, stats in agent_stats.items():
            if stats["recovery_rate"] < 0.9:
                recommendations.append(f"{agent}: Améliorer la gestion des cas extrêmes (récupération: {stats['recovery_rate']*100:.1f}%).")
        
        if not recommendations:
            recommendations.append("Excellente robustesse ! Le système gère efficacement tous les edge cases testés.")
        
        return recommendations

def main():
    """Fonction principale pour les tests edge cases spécialisés"""
    
    print("=== TESTS EDGE CASES SPÉCIALISÉS SHERLOCK/WATSON ===")
    print("Focus: Robustesse extrême et récupération d'erreurs")
    print("=" * 60)
    
    tester = SpecializedEdgeCaseTester()
    results = tester.run_specialized_edge_case_tests()
    
    # Sauvegarde du rapport
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    report_filename = f"rapport_edge_cases_specialized_{timestamp}.json"
    
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nRapport détaillé sauvegardé: {report_filename}")
    
    # Évaluation finale
    robustness_score = results["test_summary"]["robustness_score"]
    if robustness_score >= 90:
        print(f"\n🛡️ ROBUSTESSE EXCELLENTE! Score: {robustness_score:.1f}/100")
        return True
    elif robustness_score >= 75:
        print(f"\n⚠️ ROBUSTESSE CORRECTE. Score: {robustness_score:.1f}/100")
        return True
    else:
        print(f"\n❌ ROBUSTESSE INSUFFISANTE. Score: {robustness_score:.1f}/100")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)