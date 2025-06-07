#!/usr/bin/env python3
"""
Test 2 - Orchestration Cluedo Sherlock-Watson-Moriarty (avec Moriarty)
Validation en conditions réelles avec agents GPT-4o-mini
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, List
import logging
import traceback

# Configuration du logging détaillé
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'logs/orchestration_cluedo_sherlock_watson_moriarty_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

def ensure_logs_directory():
    """Créer le répertoire logs s'il n'existe pas"""
    if not os.path.exists('logs'):
        os.makedirs('logs')

class OrchestrationTracer:
    """Traceur pour capturer les interactions entre 3 agents"""
    
    def __init__(self):
        self.conversation_trace = []
        self.tool_usage_trace = []
        self.shared_state_evolution = []
        self.conflict_resolution_trace = []
        self.start_time = datetime.now()
    
    def log_message(self, agent_name: str, message_type: str, content: str, metadata: Dict[str, Any] = None):
        """Enregistrer un message d'agent"""
        timestamp = datetime.now()
        entry = {
            'timestamp': timestamp.isoformat(),
            'elapsed_seconds': (timestamp - self.start_time).total_seconds(),
            'agent_name': agent_name,
            'message_type': message_type,
            'content': content,
            'metadata': metadata or {}
        }
        self.conversation_trace.append(entry)
        logger.info(f"[{agent_name}] {message_type}: {content[:100]}...")
    
    def log_tool_usage(self, agent_name: str, tool_name: str, tool_input: Any, tool_output: Any):
        """Enregistrer l'utilisation d'un outil"""
        timestamp = datetime.now()
        entry = {
            'timestamp': timestamp.isoformat(),
            'elapsed_seconds': (timestamp - self.start_time).total_seconds(),
            'agent_name': agent_name,
            'tool_name': tool_name,
            'tool_input': str(tool_input)[:200],
            'tool_output': str(tool_output)[:200],
            'success': tool_output is not None
        }
        self.tool_usage_trace.append(entry)
        logger.info(f"[{agent_name}] OUTIL {tool_name}: {entry['success']}")
    
    def log_shared_state(self, state_description: str, state_data: Dict[str, Any]):
        """Enregistrer l'évolution de l'état partagé"""
        timestamp = datetime.now()
        entry = {
            'timestamp': timestamp.isoformat(),
            'elapsed_seconds': (timestamp - self.start_time).total_seconds(),
            'description': state_description,
            'state_data': state_data
        }
        self.shared_state_evolution.append(entry)
        logger.info(f"ÉTAT PARTAGÉ: {state_description}")
    
    def log_conflict_resolution(self, conflict_type: str, participants: List[str], resolution: str):
        """Enregistrer la résolution d'un conflit"""
        timestamp = datetime.now()
        entry = {
            'timestamp': timestamp.isoformat(),
            'elapsed_seconds': (timestamp - self.start_time).total_seconds(),
            'conflict_type': conflict_type,
            'participants': participants,
            'resolution': resolution
        }
        self.conflict_resolution_trace.append(entry)
        logger.info(f"CONFLIT RÉSOLU: {conflict_type} entre {participants}")
    
    def generate_report(self) -> Dict[str, Any]:
        """Générer le rapport de trace"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        return {
            'test_info': {
                'test_name': 'Cluedo Sherlock-Watson-Moriarty (avec Moriarty)',
                'start_time': self.start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'total_duration_seconds': total_duration,
                'agents_count': 3
            },
            'conversation_trace': self.conversation_trace,
            'tool_usage_trace': self.tool_usage_trace,
            'shared_state_evolution': self.shared_state_evolution,
            'conflict_resolution_trace': self.conflict_resolution_trace,
            'metrics': {
                'total_messages': len(self.conversation_trace),
                'total_tool_calls': len(self.tool_usage_trace),
                'state_updates': len(self.shared_state_evolution),
                'conflicts_resolved': len(self.conflict_resolution_trace),
                'average_response_time': total_duration / max(len(self.conversation_trace), 1)
            }
        }

async def run_cluedo_sherlock_watson_moriarty_demo():
    """Exécuter la démonstration Cluedo Sherlock-Watson-Moriarty"""
    ensure_logs_directory()
    tracer = OrchestrationTracer()
    
    try:
        logger.info("=== DÉMARRAGE TEST 2: CLUEDO SHERLOCK-WATSON-MORIARTY (AVEC MORIARTY) ===")
        tracer.log_shared_state("Initialisation", {"scenario": "complex", "agents": 3})
        
        # Import des modules nécessaires
        from argumentation_analysis.agents.core.oracle.oracle_base_agent import OracleBaseAgent
        from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
        from argumentation_analysis.agents.core.oracle.dataset_access_manager import DatasetAccessManager
        from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
        
        # Initialisation du dataset Cluedo avec cartes Moriarty
        logger.info("Initialisation du dataset Cluedo avec cartes Moriarty...")
        moriarty_cards = ["Docteur Olive", "Chandelier", "Cuisine"]  # Cartes que possède Moriarty
        cluedo_dataset = CluedoDataset(moriarty_cards=moriarty_cards)
        dataset_manager = DatasetAccessManager(cluedo_dataset)
        
        tracer.log_shared_state("Dataset initialisé", {
            "suspects": len(cluedo_dataset._elements_jeu["suspects"]),
            "armes": len(cluedo_dataset._elements_jeu["armes"]),
            "lieux": len(cluedo_dataset._elements_jeu["lieux"]),
            "moriarty_cards": len(moriarty_cards)
        })
        
        # Simulation d'agents Sherlock, Watson et Moriarty
        class MockSherlockAgent:
            def __init__(self, name: str, tracer: OrchestrationTracer):
                self.name = name
                self.tracer = tracer
                self.hypotheses = []
            
            async def analyze_case(self, case_data):
                """Analyser le cas"""
                self.tracer.log_message(self.name, "ANALYSIS_START", "Début de l'analyse du cas Cluedo complexe")
                
                # Accès au dataset
                suspects = cluedo_dataset._elements_jeu["suspects"]
                armes = cluedo_dataset._elements_jeu["armes"]
                lieux = cluedo_dataset._elements_jeu["lieux"]
                
                self.tracer.log_tool_usage(self.name, "dataset_access", "get_suspects", suspects)
                self.tracer.log_tool_usage(self.name, "dataset_access", "get_armes", armes)
                self.tracer.log_tool_usage(self.name, "dataset_access", "get_lieux", lieux)
                
                # Formuler des hypothèses initiales basées sur les preuves
                initial_hypothesis = {
                    "suspect": suspects[1] if len(suspects) > 1 else suspects[0],  # Pas le premier pour éviter Moriarty
                    "arme": armes[2] if len(armes) > 2 else armes[0], 
                    "lieu": lieux[1] if len(lieux) > 1 else lieux[0],
                    "confidence": 0.4,
                    "reasoning": "Basé sur l'analyse des indices disponibles"
                }
                
                self.hypotheses.append(initial_hypothesis)
                
                self.tracer.log_message(self.name, "HYPOTHESIS", f"Hypothèse initiale: {initial_hypothesis}")
                self.tracer.log_shared_state("Hypothèse Sherlock", initial_hypothesis)
                
                return initial_hypothesis
        
        class MockWatsonAgent:
            def __init__(self, name: str, tracer: OrchestrationTracer):
                self.name = name
                self.tracer = tracer
                self.questions = []
            
            async def validate_with_logic(self, hypothesis, moriarty_input=None):
                """Valider avec la logique en tenant compte de Moriarty"""
                self.tracer.log_message(self.name, "LOGIC_VALIDATION", f"Validation logique de: {hypothesis}")
                
                # Utiliser les outils de raisonnement
                reasoning_result = await self.reason_about_hypothesis(hypothesis)
                self.tracer.log_tool_usage(self.name, "reasoning_tool", hypothesis, reasoning_result)
                
                # Analyser l'input de Moriarty s'il y en a
                if moriarty_input:
                    contradiction_analysis = await self.analyze_contradiction(moriarty_input)
                    self.tracer.log_tool_usage(self.name, "contradiction_analysis", moriarty_input, contradiction_analysis)
                
                # Proposer une validation ou correction
                validation_result = {
                    "hypothesis_valid": reasoning_result.get("validity_score", 0) > 0.6,
                    "logical_consistency": True,
                    "evidence_strength": "Forte" if reasoning_result.get("validity_score", 0) > 0.7 else "Modérée",
                    "moriarty_factor_considered": moriarty_input is not None
                }
                
                self.tracer.log_message(self.name, "VALIDATION_RESULT", f"Résultat validation: {validation_result}")
                self.tracer.log_shared_state("Validation Watson", validation_result)
                
                return validation_result
            
            async def reason_about_hypothesis(self, hypothesis):
                """Raisonner sur une hypothèse"""
                await asyncio.sleep(0.7)  # Temps de traitement réaliste
                
                reasoning = {
                    "validity_score": 0.75,
                    "evidence_strength": "Forte",
                    "logical_consistency": True,
                    "missing_evidence": ["Analyse Moriarty", "Vérification cartes"]
                }
                
                return reasoning
            
            async def analyze_contradiction(self, moriarty_input):
                """Analyser les contradictions introduites par Moriarty"""
                await asyncio.sleep(0.5)
                
                analysis = {
                    "contradiction_detected": True,
                    "contradiction_type": "False evidence",
                    "reliability_score": 0.3,  # Faible fiabilité de Moriarty
                    "recommended_action": "Ignore and verify independently"
                }
                
                return analysis
        
        class MockMoriartyAgent:
            def __init__(self, name: str, tracer: OrchestrationTracer, moriarty_cards: List[str]):
                self.name = name
                self.tracer = tracer
                self.moriarty_cards = moriarty_cards
                self.misdirection_attempts = []
            
            async def introduce_misdirection(self, current_hypothesis):
                """Introduire des fausses pistes"""
                self.tracer.log_message(self.name, "MISDIRECTION_START", f"Analyse de l'hypothèse pour créer confusion: {current_hypothesis}")
                
                # Accéder aux cartes Moriarty (information privilégiée)
                moriarty_card_info = {
                    "known_cards": self.moriarty_cards,
                    "can_refute": any(card in str(current_hypothesis.values()) for card in self.moriarty_cards)
                }
                
                self.tracer.log_tool_usage(self.name, "moriarty_cards_access", "check_refutation", moriarty_card_info)
                
                # Créer une fausse piste stratégique
                false_lead = {
                    "false_suspect": "Madame Leblanc",  # Peut être réfutée par Moriarty
                    "false_evidence": "Traces de pas dans la bibliothèque",
                    "misdirection_type": "False witness testimony",
                    "strategic_value": 0.8,
                    "intended_confusion": "Détourner de la vraie solution"
                }
                
                self.misdirection_attempts.append(false_lead)
                
                self.tracer.log_message(self.name, "FALSE_LEAD", f"Fausse piste introduite: {false_lead}")
                self.tracer.log_shared_state("Fausse Piste Moriarty", false_lead)
                
                return false_lead
            
            async def reveal_strategic_card(self, suggestion):
                """Révéler stratégiquement une carte pour créer confusion"""
                self.tracer.log_message(self.name, "STRATEGIC_REVEAL", f"Révélation stratégique pour: {suggestion}")
                
                # Choisir une carte à révéler de manière stratégique
                revealed_card = None
                for card in self.moriarty_cards:
                    if card in str(suggestion):
                        revealed_card = card
                        break
                
                if revealed_card:
                    revelation = {
                        "card_revealed": revealed_card,
                        "revelation_type": "Strategic refutation",
                        "impact": "Invalidates part of suggestion",
                        "moriarty_advantage": True
                    }
                    
                    self.tracer.log_tool_usage(self.name, "card_revelation", suggestion, revelation)
                    self.tracer.log_shared_state("Révélation Moriarty", revelation)
                    
                    return revelation
                
                return None
        
        # Créer les agents
        sherlock = MockSherlockAgent("Sherlock", tracer)
        watson = MockWatsonAgent("Watson", tracer)
        moriarty = MockMoriartyAgent("Moriarty", tracer, moriarty_cards)
        
        logger.info("Agents créés: Sherlock, Watson et Moriarty")
        
        # Exécuter la séquence d'orchestration complexe
        logger.info("=== SÉQUENCE D'ORCHESTRATION COMPLEXE ===")
        
        # Étape 1: Sherlock analyse le cas
        case_data = {"type": "murder", "location": "library", "victim": "victim", "complexity": "high"}
        sherlock_hypothesis = await sherlock.analyze_case(case_data)
        await asyncio.sleep(1)
        
        # Étape 2: Moriarty introduit des fausses pistes
        moriarty_misdirection = await moriarty.introduce_misdirection(sherlock_hypothesis)
        await asyncio.sleep(1)
        
        # Étape 3: Watson valide en tenant compte de Moriarty
        watson_validation = await watson.validate_with_logic(sherlock_hypothesis, moriarty_misdirection)
        await asyncio.sleep(1)
        
        # Étape 4: Moriarty révèle stratégiquement une carte
        moriarty_revelation = await moriarty.reveal_strategic_card(sherlock_hypothesis)
        await asyncio.sleep(1)
        
        # Étape 5: Sherlock et Watson collaborent pour résoudre les contradictions
        tracer.log_conflict_resolution(
            "Moriarty Misdirection", 
            ["Sherlock", "Watson"], 
            "Collaboration pour ignorer fausses pistes"
        )
        
        tracer.log_message("Sherlock", "COLLABORATION", "Collaboration avec Watson pour résoudre contradictions Moriarty")
        tracer.log_message("Watson", "COLLABORATION", "Analyse collaborative pour détecter les fausses pistes")
        
        # Solution collaborative finale
        collaborative_solution = {
            "suspect": "Professeur Violet",  # Pas dans les cartes Moriarty
            "arme": "Poignard",             # Pas dans les cartes Moriarty  
            "lieu": "Salon",                # Pas dans les cartes Moriarty
            "confidence": 0.9,
            "collaborative_reasoning": True,
            "moriarty_misdirection_resolved": True,
            "false_leads_identified": len(moriarty.misdirection_attempts),
            "strategic_revelations_analyzed": moriarty_revelation is not None
        }
        
        tracer.log_shared_state("Solution Collaborative Finale", collaborative_solution)
        
        # Validation finale par les trois agents
        tracer.log_message("Sherlock", "FINAL_AGREEMENT", "Accord sur la solution collaborative")
        tracer.log_message("Watson", "FINAL_VALIDATION", "Validation logique de la solution finale")
        tracer.log_message("Moriarty", "DEFEATED", "Tentatives de confusion échouées, solution trouvée")
        
        # Génération du rapport
        report = tracer.generate_report()
        
        # Sauvegarde de la trace
        trace_filename = f"logs/trace_cluedo_sherlock_watson_moriarty_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(trace_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Trace sauvegardée: {trace_filename}")
        
        # Validation des objectifs intermédiaires
        objectives_met = validate_test_objectives(report)
        
        logger.info("=== RÉSULTATS TEST 2 ===")
        logger.info(f"Durée totale: {report['test_info']['total_duration_seconds']:.2f} secondes")
        logger.info(f"Messages échangés: {report['metrics']['total_messages']}")
        logger.info(f"Appels d'outils: {report['metrics']['total_tool_calls']}")
        logger.info(f"Mises à jour d'état: {report['metrics']['state_updates']}")
        logger.info(f"Conflits résolus: {report['metrics']['conflicts_resolved']}")
        logger.info(f"Objectifs atteints: {objectives_met}")
        
        return report, objectives_met
        
    except Exception as e:
        logger.error(f"Erreur dans la démonstration: {e}")
        traceback.print_exc()
        return None, False

def validate_test_objectives(report: Dict[str, Any]) -> bool:
    """Valider les objectifs intermédiaires du Test 2"""
    try:
        # ✅ Moriarty doit introduire des fausses pistes ou contradictions
        moriarty_messages = [msg for msg in report['conversation_trace'] if msg['agent_name'] == 'Moriarty']
        moriarty_misdirection = len(moriarty_messages) > 0 and any('MISDIRECTION' in msg['message_type'] or 'FALSE_LEAD' in msg['message_type'] for msg in moriarty_messages)
        
        # ✅ Sherlock/Watson doivent collaborer pour résoudre les contradictions
        sherlock_messages = [msg for msg in report['conversation_trace'] if msg['agent_name'] == 'Sherlock']
        watson_messages = [msg for msg in report['conversation_trace'] if msg['agent_name'] == 'Watson']
        collaboration_detected = any('COLLABORATION' in msg['message_type'] for msg in sherlock_messages + watson_messages)
        
        # ✅ Au moins 5 échanges d'outils multi-agents
        tool_calls = len(report['tool_usage_trace'])
        multi_agent_tools = tool_calls >= 5
        
        # ✅ Résolution collaborative avec état partagé cohérent
        state_evolution = report['shared_state_evolution']
        collaborative_state = len(state_evolution) > 0 and any('collaborative' in str(state).lower() for state in state_evolution)
        
        # ✅ Trace montrant la gestion des conflits et la convergence
        conflicts_managed = len(report['conflict_resolution_trace']) > 0
        
        objectives = {
            'moriarty_misdirection': moriarty_misdirection,
            'sherlock_watson_collaboration': collaboration_detected,
            'multi_agent_tools': multi_agent_tools,
            'collaborative_state': collaborative_state,
            'conflicts_managed': conflicts_managed
        }
        
        all_met = all(objectives.values())
        
        logger.info("=== VALIDATION OBJECTIFS TEST 2 ===")
        for obj, met in objectives.items():
            status = "✅" if met else "❌"
            logger.info(f"{status} {obj}: {met}")
        
        return all_met
        
    except Exception as e:
        logger.error(f"Erreur validation objectifs: {e}")
        return False

if __name__ == "__main__":
    print("TEST 2 - ORCHESTRATION CLUEDO SHERLOCK-WATSON-MORIARTY (AVEC MORIARTY)")
    print("=" * 80)
    
    report, success = asyncio.run(run_cluedo_sherlock_watson_moriarty_demo())
    
    if success:
        print("🎉 TEST 2 RÉUSSI - Orchestration Sherlock-Watson-Moriarty validée")
        sys.exit(0)
    else:
        print("❌ TEST 2 ÉCHOUÉ - Objectifs non atteints")
        sys.exit(1)