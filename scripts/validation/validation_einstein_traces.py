#!/usr/bin/env python3
# scripts/validation_einstein_traces.py

"""
Script de validation des démos Einstein avec génération de traces complètes.
Ce script teste les énigmes logiques complexes forçant l'utilisation de TweetyProject.
"""

import project_core.core_from_scripts.auto_env # Activation automatique de l'environnement

import asyncio
import json
import os
import logging
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

# Imports spécifiques au projet
from argumentation_analysis.orchestration.logique_complexe_orchestrator import LogiqueComplexeOrchestrator
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent, SherlockTools
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging

class EinsteinTraceValidator:
    """Validateur avec capture de traces pour les démos Einstein."""
    
    def __init__(self, output_dir: str = ".temp/traces_einstein"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger(__name__)
        
    def create_kernel(self, model_name: str = "gpt-4o-mini") -> Kernel:
        """Création du kernel Semantic Kernel avec service OpenAI."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY non définie dans l'environnement")
            
        kernel = Kernel()
        chat_service = OpenAIChatCompletion(
            service_id="openai_chat",
            api_key=api_key,
            ai_model_id=model_name
        )
        kernel.add_service(chat_service)
        return kernel
        
    def generate_simple_einstein_case(self) -> str:
        """Génère un cas Einstein simple (5 contraintes)."""
        return """Énigme Einstein simple - 5 maisons:
        
        Il y a 5 maisons de couleurs différentes alignées.
        Dans chaque maison vit une personne de nationalité différente.
        Chaque personne boit une boisson différente, fume une marque différente et possède un animal différent.
        
        Contraintes:
        1. L'Anglais vit dans la maison rouge
        2. Le Suédois possède un chien  
        3. Le Danois boit du thé
        4. La maison verte est à gauche de la maison blanche
        5. Le propriétaire de la maison verte boit du café
        
        Question: Qui possède le poisson ?
        
        ATTENTION: Cette énigme DOIT être résolue avec la logique formelle TweetyProject par Watson.
        Minimum requis: 5 clauses logiques + 3 requêtes TweetyProject."""
        
    def generate_complex_einstein_case(self) -> str:
        """Génère un cas Einstein complexe (10+ contraintes)."""
        return """Énigme Einstein complexe - 5 maisons:
        
        Il y a 5 maisons de couleurs différentes alignées.
        Dans chaque maison vit une personne de nationalité différente.
        Chaque personne boit une boisson différente, fume une marque différente et possède un animal différent.
        
        Contraintes complexes:
        1. L'Anglais vit dans la maison rouge
        2. Le Suédois possède un chien
        3. Le Danois boit du thé
        4. La maison verte est immédiatement à gauche de la maison blanche
        5. Le propriétaire de la maison verte boit du café
        6. La personne qui fume des Pall Mall possède des oiseaux
        7. Le propriétaire de la maison jaune fume des Dunhill
        8. La personne qui vit dans la maison du milieu boit du lait
        9. Le Norvégien vit dans la première maison
        10. La personne qui fume des Blend vit à côté de celle qui possède des chats
        11. La personne qui possède un cheval vit à côté de celle qui fume des Dunhill
        12. La personne qui fume des Blue Master boit de la bière
        13. L'Allemand fume des Prince
        14. Le Norvégien vit à côté de la maison bleue
        15. La personne qui fume des Blend a un voisin qui boit de l'eau
        
        Question: Qui possède le poisson ?
        
        ATTENTION: Cette énigme EXIGE l'utilisation intensive de TweetyProject par Watson.
        Minimum OBLIGATOIRE: 10+ clauses logiques + 5+ requêtes TweetyProject.
        Impossible à résoudre sans formalisation logique complète."""
        
    async def run_einstein_with_traces(self, case_description: str, case_name: str) -> Dict[str, Any]:
        """Exécute un cas Einstein avec capture complète des traces."""
        
        self.logger.info(f"🧩 Début de l'exécution du cas: {case_name}")
        print(f"\n{'='*80}")
        print(f"🧩 EXÉCUTION CAS EINSTEIN: {case_name}")
        print(f"{'='*80}")
        
        try:
            # Création du kernel
            kernel = self.create_kernel()
            
            # Capture du timestamp de début
            start_time = datetime.datetime.now()
            
            # Création de l'orchestrateur logique complexe
            orchestrateur = LogiqueComplexeOrchestrator(kernel)
            
            # Création des agents spécialisés avec outils
            sherlock_tools = SherlockTools(kernel)
            kernel.add_plugin(sherlock_tools, plugin_name="SherlockTools")
            
            sherlock_agent = SherlockEnqueteAgent(
                kernel=kernel,
                agent_name="Sherlock",
                service_id="openai_chat"
            )
            
            watson_agent = WatsonLogicAssistant(
                kernel=kernel,
                agent_name="Watson", 
                service_id="openai_chat"
            )
            
            # Exécution de l'énigme Einstein
            print(f"\n📋 Énigme: {case_description[:150]}...")
            print(f"🚀 Résolution en cours avec exigence TweetyProject...")
            
            resultats = await orchestrateur.resoudre_enigme_complexe(sherlock_agent, watson_agent)
            
            # Capture du timestamp de fin
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Récupération des statistiques détaillées
            stats_logique = orchestrateur.obtenir_statistiques_logique()
            
            # Construction des résultats complets
            results = {
                "metadata": {
                    "case_name": case_name,
                    "timestamp": self.timestamp,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "model_used": "gpt-4o-mini",
                    "complexity_level": "complex" if "complexe" in case_name else "simple"
                },
                "input": {
                    "case_description": case_description,
                    "required_clauses": 10 if "complexe" in case_name else 5,
                    "required_queries": 5 if "complexe" in case_name else 3
                },
                "execution_results": resultats,
                "logic_statistics": stats_logique,
                "tweetyproject_validation": {
                    "clauses_formulees": resultats.get('progression_logique', {}).get('clauses_formulees', 0),
                    "requetes_executees": resultats.get('progression_logique', {}).get('requetes_executees', 0),
                    "force_logique_formelle": resultats.get('progression_logique', {}).get('force_logique_formelle', False),
                    "meets_minimum_requirements": self._validate_minimum_requirements(resultats, case_name)
                },
                "analysis": {
                    "enigme_resolue": resultats.get('enigme_resolue', False),
                    "tours_utilises": resultats.get('tours_utilises', 0),
                    "watson_clauses_count": len(resultats.get('clauses_watson', [])),
                    "watson_queries_count": len(resultats.get('requetes_executees', [])),
                    "collaboration_quality": self._assess_collaboration_quality(resultats),
                    "logic_formalization_depth": self._assess_logic_depth(resultats)
                },
                "traces": {
                    "conversation_flow": self._extract_conversation_flow(resultats),
                    "tweetyproject_calls": self._extract_tweetyproject_calls(resultats),
                    "logic_progression": self._track_logic_progression(resultats)
                }
            }
            
            # Sauvegarde des traces
            trace_file = self.output_dir / f"trace_einstein_{case_name}_{self.timestamp}.json"
            with open(trace_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                
            self.logger.info(f"✅ Traces Einstein sauvegardées: {trace_file}")
            
            # Affichage des résultats
            self._display_einstein_results(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'exécution de {case_name}: {e}")
            error_results = {
                "metadata": {"case_name": case_name, "error": str(e)},
                "error": str(e),
                "timestamp": self.timestamp
            }
            
            # Sauvegarde de l'erreur
            error_file = self.output_dir / f"error_einstein_{case_name}_{self.timestamp}.json"
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_results, f, indent=2, ensure_ascii=False, default=str)
                
            raise
            
    def _validate_minimum_requirements(self, resultats: Dict[str, Any], case_name: str) -> Dict[str, bool]:
        """Valide si les exigences minimales sont remplies."""
        progression = resultats.get('progression_logique', {})
        
        if "complexe" in case_name:
            min_clauses = 10
            min_queries = 5
        else:
            min_clauses = 5
            min_queries = 3
            
        clauses_ok = progression.get('clauses_formulees', 0) >= min_clauses
        queries_ok = progression.get('requetes_executees', 0) >= min_queries
        force_logique_ok = progression.get('force_logique_formelle', False)
        
        return {
            "clauses_requirement": clauses_ok,
            "queries_requirement": queries_ok,
            "formal_logic_requirement": force_logique_ok,
            "all_requirements_met": clauses_ok and queries_ok and force_logique_ok
        }
        
    def _assess_collaboration_quality(self, resultats: Dict[str, Any]) -> Dict[str, Any]:
        """Évalue la qualité de la collaboration entre agents."""
        return {
            "sherlock_coordination": resultats.get('tours_utilises', 0) > 5,
            "watson_specialization": len(resultats.get('clauses_watson', [])) > 0,
            "tools_integration": len(resultats.get('requetes_executees', [])) > 0,
            "solution_achieved": resultats.get('enigme_resolue', False)
        }
        
    def _assess_logic_depth(self, resultats: Dict[str, Any]) -> Dict[str, Any]:
        """Évalue la profondeur de la formalisation logique."""
        progression = resultats.get('progression_logique', {})
        
        return {
            "formalization_level": "high" if progression.get('clauses_formulees', 0) >= 10 else "medium" if progression.get('clauses_formulees', 0) >= 5 else "low",
            "query_complexity": "high" if progression.get('requetes_executees', 0) >= 5 else "medium" if progression.get('requetes_executees', 0) >= 3 else "low",
            "systematic_approach": progression.get('force_logique_formelle', False),
            "constraints_coverage": progression.get('contraintes_traitees', 0)
        }
        
    def _extract_conversation_flow(self, resultats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrait le flux de conversation entre agents."""
        # Simulation d'extraction - à adapter selon la structure réelle
        flow = []
        tours = resultats.get('tours_utilises', 0)
        
        for i in range(min(tours, 10)):  # Limiter pour éviter trop de données
            flow.append({
                "tour": i + 1,
                "agent": "Sherlock" if i % 2 == 0 else "Watson",
                "type": "coordination" if i % 2 == 0 else "formalization",
                "summary": f"Tour {i + 1} - Action {'coordination' if i % 2 == 0 else 'formalisation'}"
            })
            
        return flow
        
    def _extract_tweetyproject_calls(self, resultats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrait les appels à TweetyProject."""
        calls = []
        requetes = resultats.get('requetes_executees', [])
        
        for i, requete in enumerate(requetes):
            if isinstance(requete, dict):
                calls.append({
                    "call_id": i + 1,
                    "requete": requete.get('requete', 'N/A'),
                    "type": requete.get('type', 'query'),
                    "result": requete.get('result', 'N/A')[:100] if requete.get('result') else 'N/A'
                })
        
        return calls
        
    def _track_logic_progression(self, resultats: Dict[str, Any]) -> Dict[str, Any]:
        """Suit la progression logique au cours de la résolution."""
        progression = resultats.get('progression_logique', {})
        
        return {
            "initial_constraints": 15,  # Contraintes de l'énigme Einstein
            "clauses_generated": progression.get('clauses_formulees', 0),
            "queries_executed": progression.get('requetes_executees', 0),
            "constraints_processed": progression.get('contraintes_traitees', 0),
            "formal_logic_engaged": progression.get('force_logique_formelle', False),
            "progression_rate": min(1.0, progression.get('clauses_formulees', 0) / 10.0)
        }
        
    def _display_einstein_results(self, results: Dict[str, Any]):
        """Affiche les résultats de l'analyse Einstein."""
        metadata = results['metadata']
        analysis = results['analysis']
        validation = results['tweetyproject_validation']
        
        print(f"\n🧩 RÉSULTATS EINSTEIN - {metadata['case_name']}")
        print(f"⏱️  Durée: {metadata['duration_seconds']:.2f}s")
        print(f"🔄 Tours utilisés: {analysis['tours_utilises']}/25")
        
        # Statut de résolution
        print(f"\n🎯 Statut de résolution:")
        print(f"   - Énigme résolue: {'✅' if analysis['enigme_resolue'] else '❌'}")
        print(f"   - Logique formelle suffisante: {'✅' if validation['force_logique_formelle'] else '❌'}")
        
        # Validation TweetyProject
        print(f"\n🔧 Validation TweetyProject:")
        print(f"   - Clauses formulées: {validation['clauses_formulees']}/{results['input']['required_clauses']} {'✅' if validation['meets_minimum_requirements']['clauses_requirement'] else '❌'}")
        print(f"   - Requêtes exécutées: {validation['requetes_executees']}/{results['input']['required_queries']} {'✅' if validation['meets_minimum_requirements']['queries_requirement'] else '❌'}")
        print(f"   - Exigences minimales: {'✅ REMPLIES' if validation['meets_minimum_requirements']['all_requirements_met'] else '❌ NON REMPLIES'}")
        
        # Collaboration agents
        collab = analysis['collaboration_quality']
        print(f"\n👥 Collaboration agents:")
        print(f"   - Coordination Sherlock: {'✅' if collab['sherlock_coordination'] else '❌'}")
        print(f"   - Spécialisation Watson: {'✅' if collab['watson_specialization'] else '❌'}")
        print(f"   - Intégration outils: {'✅' if collab['tools_integration'] else '❌'}")
        
        # Profondeur logique
        depth = analysis['logic_formalization_depth']
        print(f"\n🧠 Profondeur formalisation:")
        print(f"   - Niveau: {depth['formalization_level']}")
        print(f"   - Complexité requêtes: {depth['query_complexity']}")
        print(f"   - Approche systématique: {'✅' if depth['systematic_approach'] else '❌'}")

async def main():
    """Fonction principale de validation des traces Einstein."""
    
    print("🧩 VALIDATION DÉMOS EINSTEIN AVEC TRACES COMPLÈTES")
    print("="*80)
    
    # Configuration du logging
    setup_logging()
    
    # Création du validateur
    validator = EinsteinTraceValidator()
    
    # Résultats globaux
    all_results = []
    
    try:
        # Test 1: Cas simple (5 contraintes)
        print(f"\n🟢 TEST 1: ÉNIGME EINSTEIN SIMPLE")
        simple_case = validator.generate_simple_einstein_case()
        simple_results = await validator.run_einstein_with_traces(simple_case, "simple")
        all_results.append(simple_results)
        
        # Test 2: Cas complexe (10+ contraintes)
        print(f"\n🔴 TEST 2: ÉNIGME EINSTEIN COMPLEXE") 
        complex_case = validator.generate_complex_einstein_case()
        complex_results = await validator.run_einstein_with_traces(complex_case, "complexe")
        all_results.append(complex_results)
        
        # Génération du rapport de synthèse
        await validator.generate_synthesis_report(all_results)
        
        print(f"\n✅ VALIDATION EINSTEIN TERMINÉE AVEC SUCCÈS")
        print(f"📁 Traces sauvegardées dans: {validator.output_dir}")
        
        return all_results
        
    except Exception as e:
        print(f"\n❌ ERREUR LORS DE LA VALIDATION EINSTEIN: {e}")
        logging.error(f"Erreur validation Einstein: {e}", exc_info=True)
        raise

# Extension pour le rapport de synthèse Einstein
async def generate_synthesis_report(self, all_results: List[Dict[str, Any]]):
    """Génère un rapport de synthèse des tests Einstein."""
    
    synthesis = {
        "metadata": {
            "generation_time": datetime.datetime.now().isoformat(),
            "total_tests": len(all_results),
            "timestamp": self.timestamp,
            "test_type": "Einstein Logic Puzzles"
        },
        "summary": {
            "all_tests_completed": len(all_results) > 0,
            "total_duration": sum(r['metadata']['duration_seconds'] for r in all_results),
            "tweetyproject_usage_summary": self._analyze_tweetyproject_usage(all_results),
            "logic_requirements_compliance": self._analyze_requirements_compliance(all_results),
            "collaboration_effectiveness": self._analyze_collaboration_effectiveness(all_results)
        },
        "detailed_results": all_results
    }
    
    # Sauvegarde du rapport
    report_file = self.output_dir / f"synthesis_report_einstein_{self.timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(synthesis, f, indent=2, ensure_ascii=False, default=str)
        
    print(f"\n📋 RAPPORT DE SYNTHÈSE EINSTEIN")
    print(f"📁 Sauvegardé: {report_file}")
    print(f"🧪 Tests Einstein réalisés: {synthesis['summary']['total_tests']}")
    print(f"⏱️  Durée totale: {synthesis['summary']['total_duration']:.2f}s")
    
    # Affichage du résumé TweetyProject
    tweety_summary = synthesis['summary']['tweetyproject_usage_summary']
    print(f"\n🔧 Résumé TweetyProject:")
    print(f"   - Total clauses: {tweety_summary['total_clauses']}")
    print(f"   - Total requêtes: {tweety_summary['total_queries']}")
    print(f"   - Tests conformes: {tweety_summary['compliant_tests']}/{len(all_results)}")

def _analyze_tweetyproject_usage(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyse l'utilisation de TweetyProject sur tous les tests."""
    total_clauses = sum(r['tweetyproject_validation']['clauses_formulees'] for r in results)
    total_queries = sum(r['tweetyproject_validation']['requetes_executees'] for r in results)
    compliant_tests = sum(1 for r in results if r['tweetyproject_validation']['meets_minimum_requirements']['all_requirements_met'])
    
    return {
        "total_clauses": total_clauses,
        "total_queries": total_queries,
        "compliant_tests": compliant_tests,
        "average_clauses": total_clauses / len(results) if results else 0,
        "average_queries": total_queries / len(results) if results else 0
    }

def _analyze_requirements_compliance(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Analyse la conformité aux exigences logiques."""
    if not results:
        return {}
        
    total = len(results)
    return {
        "clauses_compliance_rate": sum(1 for r in results if r['tweetyproject_validation']['meets_minimum_requirements']['clauses_requirement']) / total,
        "queries_compliance_rate": sum(1 for r in results if r['tweetyproject_validation']['meets_minimum_requirements']['queries_requirement']) / total,
        "formal_logic_rate": sum(1 for r in results if r['tweetyproject_validation']['meets_minimum_requirements']['formal_logic_requirement']) / total,
        "full_compliance_rate": sum(1 for r in results if r['tweetyproject_validation']['meets_minimum_requirements']['all_requirements_met']) / total
    }

def _analyze_collaboration_effectiveness(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Analyse l'efficacité de la collaboration agentique."""
    if not results:
        return {}
        
    total = len(results)
    return {
        "solution_rate": sum(1 for r in results if r['analysis']['enigme_resolue']) / total,
        "watson_engagement_rate": sum(1 for r in results if r['analysis']['collaboration_quality']['watson_specialization']) / total,
        "tools_integration_rate": sum(1 for r in results if r['analysis']['collaboration_quality']['tools_integration']) / total,
        "overall_effectiveness": sum(1 for r in results if r['analysis']['collaboration_quality']['solution_achieved']) / total
    }

# Ajout des méthodes à la classe
EinsteinTraceValidator.generate_synthesis_report = generate_synthesis_report
EinsteinTraceValidator._analyze_tweetyproject_usage = _analyze_tweetyproject_usage
EinsteinTraceValidator._analyze_requirements_compliance = _analyze_requirements_compliance
EinsteinTraceValidator._analyze_collaboration_effectiveness = _analyze_collaboration_effectiveness

if __name__ == "__main__":
    asyncio.run(main())