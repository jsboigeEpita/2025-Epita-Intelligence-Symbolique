#!/usr/bin/env python3
# scripts/validation_cluedo_traces.py

"""
Script de validation des démos Cluedo avec génération de traces complètes.
Ce script teste les cas simples et complexes avec capture des conversations agentiques.
"""

import scripts.core.auto_env  # Activation automatique de l'environnement

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
from argumentation_analysis.orchestration.cluedo_orchestrator import run_cluedo_game
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging

class CluedoTraceValidator:
    """Validateur avec capture de traces pour les démos Cluedo."""
    
    def __init__(self, output_dir: str = ".temp/traces_cluedo"):
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
        
    def generate_simple_case(self) -> str:
        """Génère un cas de Cluedo simple (3-4 indices)."""
        return """Enquête Cluedo simple: 
        - Témoin A: 'J'ai vu Mme Peacock dans la bibliothèque vers 21h00'
        - Témoin B: 'Le chandelier manquait dans le salon après 21h30'
        - Témoin C: 'Professor Plum était dans la cuisine à 21h15'
        - Indice physique: Traces de cire dans la bibliothèque
        
        Question: Qui a commis le meurtre, avec quelle arme et dans quel lieu ?"""
        
    def generate_complex_case(self) -> str:
        """Génère un cas de Cluedo complexe avec contradictions."""
        return """Enquête Cluedo complexe avec contradictions:
        - Témoin A: 'Mme Peacock était dans la bibliothèque vers 21h00'
        - Témoin B: 'Mme Peacock était dans le salon à 21h00' (CONTRADICTION)
        - Témoin C: 'J'ai entendu un bruit dans la bibliothèque vers 21h15'
        - Témoin D: 'Professor Plum avait le chandelier à 20h45'
        - Témoin E: 'Professor Plum n'avait pas d'arme à 20h45' (CONTRADICTION)
        - Indice: Empreintes de Mme Peacock sur le chandelier
        - Indice: Traces de cire dans la bibliothèque et le salon
        - Indice: Alibi partiel de Professor Plum en cuisine (20h30-21h00)
        - Indice: Porte de la bibliothèque fermée à clé après 21h30
        
        Question: Résolvez cette enquête en gérant les contradictions."""
        
    async def run_cluedo_with_traces(self, case_description: str, case_name: str) -> Dict[str, Any]:
        """Exécute un cas Cluedo avec capture complète des traces."""
        
        self.logger.info(f"🕵️ Début de l'exécution du cas: {case_name}")
        print(f"\n{'='*80}")
        print(f"🕵️ EXÉCUTION CAS CLUEDO: {case_name}")
        print(f"{'='*80}")
        
        try:
            # Création du kernel
            kernel = self.create_kernel()
            
            # Capture du timestamp de début
            start_time = datetime.datetime.now()
            
            # Exécution du jeu Cluedo
            print(f"\n📋 Scénario: {case_description[:100]}...")
            final_history, final_state = await run_cluedo_game(kernel, case_description)
            
            # Capture du timestamp de fin
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Construction des résultats complets
            results = {
                "metadata": {
                    "case_name": case_name,
                    "timestamp": self.timestamp,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "model_used": "gpt-4o-mini"
                },
                "input": {
                    "case_description": case_description,
                    "question": "Qui a commis le meurtre, avec quelle arme et dans quel lieu ?"
                },
                "conversation_history": final_history,
                "final_state": {
                    "final_solution": getattr(final_state, 'final_solution', None),
                    "solution_secrete": getattr(final_state, 'solution_secrete_cluedo', None),
                    "hypotheses": getattr(final_state, 'hypotheses_enquete', []),
                    "tasks": getattr(final_state, 'tasks', {}),
                    "confidence_level": self._extract_confidence(final_state)
                },
                "analysis": {
                    "conversation_length": len(final_history) if final_history else 0,
                    "agent_participation": self._analyze_agent_participation(final_history),
                    "tools_used": self._extract_tools_usage(final_history),
                    "logic_quality": self._assess_logic_quality(final_history, final_state)
                }
            }
            
            # Sauvegarde des traces
            trace_file = self.output_dir / f"trace_{case_name}_{self.timestamp}.json"
            with open(trace_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                
            self.logger.info(f"✅ Traces sauvegardées: {trace_file}")
            
            # Affichage des résultats
            self._display_results(results)
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors de l'exécution de {case_name}: {e}")
            error_results = {
                "metadata": {"case_name": case_name, "error": str(e)},
                "error": str(e),
                "timestamp": self.timestamp
            }
            
            # Sauvegarde de l'erreur
            error_file = self.output_dir / f"error_{case_name}_{self.timestamp}.json"
            with open(error_file, 'w', encoding='utf-8') as f:
                json.dump(error_results, f, indent=2, ensure_ascii=False, default=str)
                
            raise
            
    def _extract_confidence(self, final_state) -> Optional[float]:
        """Extrait le niveau de confiance de la solution."""
        try:
            if hasattr(final_state, 'hypotheses_enquete') and final_state.hypotheses_enquete:
                confidences = [h.get('confidence_score', 0) for h in final_state.hypotheses_enquete 
                             if isinstance(h, dict) and 'confidence_score' in h]
                return max(confidences) if confidences else None
        except:
            pass
        return None
        
    def _analyze_agent_participation(self, history: List) -> Dict[str, int]:
        """Analyse la participation de chaque agent."""
        participation = {}
        if not history:
            return participation
            
        for entry in history:
            if isinstance(entry, dict) and 'sender' in entry:
                sender = entry['sender']
                participation[sender] = participation.get(sender, 0) + 1
                
        return participation
        
    def _extract_tools_usage(self, history: List) -> List[str]:
        """Extrait les outils utilisés pendant la conversation."""
        tools_used = set()
        if not history:
            return list(tools_used)
            
        for entry in history:
            if isinstance(entry, dict) and 'message' in entry:
                message = entry['message'].lower()
                # Recherche de mentions d'outils
                if 'tweetyproject' in message or 'tweety' in message:
                    tools_used.add('TweetyProject')
                if 'semantic_kernel' in message or 'fonction' in message:
                    tools_used.add('SemanticKernel')
                if 'oracle' in message:
                    tools_used.add('Oracle')
                    
        return list(tools_used)
        
    def _assess_logic_quality(self, history: List, final_state) -> Dict[str, Any]:
        """Évalue la qualité du raisonnement logique."""
        return {
            "has_systematic_approach": self._check_systematic_approach(history),
            "handles_contradictions": self._check_contradiction_handling(history),
            "reaches_conclusion": final_state.final_solution is not None if hasattr(final_state, 'final_solution') else False,
            "evidence_based": self._check_evidence_usage(history)
        }
        
    def _check_systematic_approach(self, history: List) -> bool:
        """Vérifie si l'approche est systématique."""
        if not history or len(history) < 3:
            return False
        # Recherche de mots-clés indiquant une approche systématique
        systematic_keywords = ['hypothèse', 'analyse', 'déduction', 'logique', 'raisonnement']
        for entry in history:
            if isinstance(entry, dict) and 'message' in entry:
                message = entry['message'].lower()
                if any(keyword in message for keyword in systematic_keywords):
                    return True
        return False
        
    def _check_contradiction_handling(self, history: List) -> bool:
        """Vérifie si les contradictions sont gérées."""
        if not history:
            return False
        for entry in history:
            if isinstance(entry, dict) and 'message' in entry:
                message = entry['message'].lower()
                if 'contradiction' in message or 'incohéren' in message:
                    return True
        return False
        
    def _check_evidence_usage(self, history: List) -> bool:
        """Vérifie si les preuves sont utilisées."""
        if not history:
            return False
        evidence_keywords = ['preuve', 'indice', 'témoin', 'trace', 'empreinte']
        for entry in history:
            if isinstance(entry, dict) and 'message' in entry:
                message = entry['message'].lower()
                if any(keyword in message for keyword in evidence_keywords):
                    return True
        return False
        
    def _display_results(self, results: Dict[str, Any]):
        """Affiche les résultats de l'analyse."""
        print(f"\n📊 RÉSULTATS ANALYSE - {results['metadata']['case_name']}")
        print(f"⏱️  Durée: {results['metadata']['duration_seconds']:.2f}s")
        print(f"💬 Messages échangés: {results['analysis']['conversation_length']}")
        
        # Participation des agents
        participation = results['analysis']['agent_participation']
        print(f"\n👥 Participation des agents:")
        for agent, count in participation.items():
            print(f"   - {agent}: {count} messages")
            
        # Outils utilisés
        tools = results['analysis']['tools_used']
        print(f"\n🔧 Outils utilisés: {', '.join(tools) if tools else 'Aucun détecté'}")
        
        # Qualité logique
        logic = results['analysis']['logic_quality']
        print(f"\n🧠 Qualité logique:")
        print(f"   - Approche systématique: {'✅' if logic['has_systematic_approach'] else '❌'}")
        print(f"   - Gestion contradictions: {'✅' if logic['handles_contradictions'] else '❌'}")
        print(f"   - Conclusion atteinte: {'✅' if logic['reaches_conclusion'] else '❌'}")
        print(f"   - Basé sur preuves: {'✅' if logic['evidence_based'] else '❌'}")
        
        # Solution finale
        final_solution = results['final_state']['final_solution']
        print(f"\n🎯 Solution finale: {final_solution if final_solution else 'Non résolue'}")

async def main():
    """Fonction principale de validation des traces Cluedo."""
    
    print("🔍 VALIDATION DÉMOS CLUEDO AVEC TRACES COMPLÈTES")
    print("="*80)
    
    # Configuration du logging
    setup_logging()
    
    # Création du validateur
    validator = CluedoTraceValidator()
    
    # Résultats globaux
    all_results = []
    
    try:
        # Test 1: Cas simple
        print(f"\n🟢 TEST 1: CAS CLUEDO SIMPLE")
        simple_case = validator.generate_simple_case()
        simple_results = await validator.run_cluedo_with_traces(simple_case, "simple")
        all_results.append(simple_results)
        
        # Test 2: Cas complexe
        print(f"\n🔴 TEST 2: CAS CLUEDO COMPLEXE") 
        complex_case = validator.generate_complex_case()
        complex_results = await validator.run_cluedo_with_traces(complex_case, "complexe")
        all_results.append(complex_results)
        
        # Génération du rapport de synthèse
        await validator.generate_synthesis_report(all_results)
        
        print(f"\n✅ VALIDATION TERMINÉE AVEC SUCCÈS")
        print(f"📁 Traces sauvegardées dans: {validator.output_dir}")
        
        return all_results
        
    except Exception as e:
        print(f"\n❌ ERREUR LORS DE LA VALIDATION: {e}")
        logging.error(f"Erreur validation: {e}", exc_info=True)
        raise

# Extension pour le rapport de synthèse
async def generate_synthesis_report(self, all_results: List[Dict[str, Any]]):
    """Génère un rapport de synthèse des tests."""
    
    synthesis = {
        "metadata": {
            "generation_time": datetime.datetime.now().isoformat(),
            "total_tests": len(all_results),
            "timestamp": self.timestamp
        },
        "summary": {
            "all_tests_completed": len(all_results) > 0,
            "total_duration": sum(r['metadata']['duration_seconds'] for r in all_results),
            "total_messages": sum(r['analysis']['conversation_length'] for r in all_results),
            "tools_coverage": self._analyze_tools_coverage(all_results),
            "logic_quality_summary": self._summarize_logic_quality(all_results)
        },
        "detailed_results": all_results
    }
    
    # Sauvegarde du rapport
    report_file = self.output_dir / f"synthesis_report_{self.timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(synthesis, f, indent=2, ensure_ascii=False, default=str)
        
    print(f"\n📋 RAPPORT DE SYNTHÈSE")
    print(f"📁 Sauvegardé: {report_file}")
    print(f"🧪 Tests réalisés: {synthesis['summary']['total_tests']}")
    print(f"⏱️  Durée totale: {synthesis['summary']['total_duration']:.2f}s")
    print(f"💬 Messages totaux: {synthesis['summary']['total_messages']}")

def _analyze_tools_coverage(self, results: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analyse la couverture des outils sur tous les tests."""
    tools_count = {}
    for result in results:
        for tool in result['analysis']['tools_used']:
            tools_count[tool] = tools_count.get(tool, 0) + 1
    return tools_count

def _summarize_logic_quality(self, results: List[Dict[str, Any]]) -> Dict[str, float]:
    """Résume la qualité logique sur tous les tests."""
    if not results:
        return {}
        
    total = len(results)
    summary = {
        "systematic_approach_rate": sum(1 for r in results if r['analysis']['logic_quality']['has_systematic_approach']) / total,
        "contradiction_handling_rate": sum(1 for r in results if r['analysis']['logic_quality']['handles_contradictions']) / total,
        "conclusion_rate": sum(1 for r in results if r['analysis']['logic_quality']['reaches_conclusion']) / total,
        "evidence_usage_rate": sum(1 for r in results if r['analysis']['logic_quality']['evidence_based']) / total
    }
    return summary

# Ajout des méthodes à la classe
CluedoTraceValidator.generate_synthesis_report = generate_synthesis_report
CluedoTraceValidator._analyze_tools_coverage = _analyze_tools_coverage
CluedoTraceValidator._summarize_logic_quality = _summarize_logic_quality

if __name__ == "__main__":
    asyncio.run(main())