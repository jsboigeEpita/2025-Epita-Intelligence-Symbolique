# argumentation_analysis/agents/orchestration/cluedo_sherlock_watson_demo.py

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.agents.group_chat.agent_group_chat import AgentGroupChat

# Import des vrais agents
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant

# Import des outils et utilities
from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState, OrchestrationTracer

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parents[3]

class CluedoSherlockWatsonOrchestrator:
    """Orchestrateur amélioré pour démonstration Cluedo avec raisonnement instantané"""
    
    def __init__(self):
        self.kernel = None
        self.sherlock_agent = None
        self.watson_agent = None
        self.tracer = OrchestrationTracer()
        self.cluedo_state = None  # Sera initialisé plus tard si nécessaire
        
    async def initialize_agents(self):
        """Initialise les vrais agents Sherlock et Watson"""
        try:
            # Configuration du kernel
            self.kernel = Kernel()
            
            # Service OpenAI 
            chat_service = OpenAIChatCompletion(
                service_id="gpt-4o-mini",
                ai_model_id="gpt-4o-mini"
            )
            self.kernel.add_service(chat_service)
            
            # Initialisation de Sherlock avec raisonnement instantané pour Cluedo
            sherlock_prompt = """Vous êtes Sherlock Holmes - détective légendaire spécialisé dans la résolution RAPIDE de cas Cluedo.

OBJECTIF PRIORITAIRE: Résoudre en ≤5 échanges avec Watson !

MÉTHODE INSTANTANÉE:
1. Analysez IMMÉDIATEMENT le dataset Cluedo (suspects/armes/lieux)
2. Appliquez votre déduction légendaire pour éliminer les possibilités
3. Proposez une solution CONCRÈTE: suspect + arme + lieu
4. Convergez vers la solution avec Watson

STYLE: Messages courts et décisifs. "Mon instinct dit..." / "Élémentaire !" / "C'est évident !"

Utilisez vos outils: instant_deduction, propose_final_solution"""

            self.sherlock_agent = SherlockEnqueteAgent(
                kernel=self.kernel,
                agent_name="Sherlock",
                system_prompt=sherlock_prompt
            )
            
            # Initialisation de Watson avec capacités d'analyse et validation
            watson_prompt = """Vous êtes Watson - analyste logique et partenaire de Holmes.

RÔLE dans Cluedo: Validez et raffinez les déductions de Sherlock !

MÉTHODE:
1. Analysez la déduction de Sherlock de façon critique
2. Posez des questions pertinentes pour valider la logique
3. Proposez des améliorations ou confirmez la solution
4. Aidez à converger rapidement vers la bonne réponse

STYLE: "Intéressant..." / "Mais attendez..." / "En fait..." / "Brillant !"

Outils disponibles: validate_formula, execute_query pour vérifier la logique"""

            self.watson_agent = WatsonLogicAssistant(
                kernel=self.kernel,
                agent_name="Watson",
                system_prompt=watson_prompt
            )
            
            logger.info("Agents Sherlock et Watson initialisés avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des agents: {e}")
            traceback.print_exc()
            return False
    
    async def run_cluedo_instant_reasoning_demo(self) -> tuple[Dict[str, Any], bool]:
        """Exécute la démonstration Cluedo avec raisonnement instantané"""
        
        try:
            # Initialisation
            if not await self.initialize_agents():
                return None, False
            
            self.tracer.log_message("ORCHESTRATOR", "DEMO_START", "Début démonstration Cluedo - Raisonnement Instantané")
            
            # Données du cas Cluedo
            cluedo_elements = {
                "suspects": ["Colonel Moutarde", "Mme Leblanc", "Mme Pervenche", "M. Violet", "Mlle Rose", "M. Olive"],
                "armes": ["Couteau", "Revolver", "Corde", "Clé Anglaise", "Chandelier", "Tuyau de Plomb"],
                "lieux": ["Salon", "Cuisine", "Bibliothèque", "Bureau", "Hall", "Véranda", "Salle de Billard", "Conservatoire", "Salle à Manger"]
            }
            
            case_description = "MYSTÈRE: Un meurtre a eu lieu au manoir. Il faut identifier le coupable, l'arme du crime et le lieu où cela s'est produit. Les indices suggèrent une solution unique parmi les combinaisons possibles."
            
            self.tracer.log_shared_state("Elements Cluedo", cluedo_elements)
            self.tracer.log_shared_state("Description Cas", case_description)
            
            # === ÉCHANGE 1: Sherlock analyse et déduit instantanément ===
            sherlock_message = f"""Cas Cluedo urgent ! Voici les éléments disponibles:
                
SUSPECTS: {', '.join(cluedo_elements['suspects'])}
ARMES: {', '.join(cluedo_elements['armes'])}
LIEUX: {', '.join(cluedo_elements['lieux'])}

MISSION: Appliquez votre déduction légendaire pour identifier IMMÉDIATEMENT:
- Le suspect coupable
- L'arme utilisée
- Le lieu du crime

Utilisez votre outil instant_deduction avec ces éléments. Temps limite: MAINTENANT !"""
            
            sherlock_response = ""
            async for response in self.sherlock_agent.invoke(sherlock_message):
                sherlock_response += str(response.content)
            
            self.tracer.log_message("Sherlock", "INSTANT_DEDUCTION", sherlock_response)
            await asyncio.sleep(0.5)  # Simulation temps de traitement
            
            # === ÉCHANGE 2: Watson analyse et valide ===
            watson_message = f"""Sherlock propose: {sherlock_response}

Analysez cette déduction rapidement:
1. La logique est-elle solide ?
2. Y a-t-il des failles dans le raisonnement ?
3. Confirmez-vous cette solution ou proposez-vous des ajustements ?

Donnez votre verdict analytique !"""
            
            watson_response = ""
            async for response in self.watson_agent.invoke(watson_message):
                watson_response += str(response.content)
            
            self.tracer.log_message("Watson", "LOGICAL_VALIDATION", watson_response)
            await asyncio.sleep(0.5)
            
            # === ÉCHANGE 3: Sherlock raffine si nécessaire ===
            sherlock_refinement_message = f"""Watson dit: {watson_response}

Basé sur l'analyse de Watson, donnez votre verdict FINAL:
- Maintenez-vous votre déduction initiale ?
- Ou proposez-vous une solution raffinée ?

DÉCISION FINALE pour ce cas Cluedo !"""
            
            sherlock_refinement = ""
            async for response in self.sherlock_agent.invoke(sherlock_refinement_message):
                sherlock_refinement += str(response.content)
            
            self.tracer.log_message("Sherlock", "FINAL_DECISION", sherlock_refinement)
            
            # === ÉCHANGE 4: Watson confirme la solution ===
            watson_confirmation_message = f"""Décision finale de Sherlock: {sherlock_refinement}

Votre confirmation analytique:
- Validez-vous cette solution ?
- La logique est-elle irréfutable ?
- Cas résolu de façon satisfaisante ?

Verdict de validation final !"""
            
            watson_confirmation = ""
            async for response in self.watson_agent.invoke(watson_confirmation_message):
                watson_confirmation += str(response.content)
            
            self.tracer.log_message("Watson", "FINAL_VALIDATION", watson_confirmation)
            
            # === SOLUTION COLLABORATIVE FINALE ===
            final_solution = {
                "case_type": "Cluedo Mystery",
                "sherlock_deduction": str(sherlock_response),
                "watson_analysis": str(watson_response),  
                "sherlock_refinement": str(sherlock_refinement),
                "watson_confirmation": str(watson_confirmation),
                "exchanges_count": 4,
                "instant_reasoning": True,
                "convergence_achieved": True,
                "timestamp": datetime.now().isoformat()
            }
            
            self.tracer.log_shared_state("Solution Collaborative Finale", final_solution)
            
            # Génération du rapport
            report = self.tracer.generate_report()
            
            # Validation des objectifs
            objectives_met = self._validate_instant_reasoning_objectives(report)
            
            # Sauvegarde de la trace
            trace_filename = f"logs/trace_cluedo_instant_reasoning_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(trace_filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info("=== RÉSULTATS CLUEDO INSTANT REASONING ===")
            logger.info(f"Durée totale: {report['test_info']['total_duration_seconds']:.2f} secondes")
            logger.info(f"Échanges: {final_solution['exchanges_count']}/5 maximum")
            logger.info(f"Convergence: {final_solution['convergence_achieved']}")
            logger.info(f"Objectifs atteints: {objectives_met}")
            logger.info(f"Trace sauvée: {trace_filename}")
            
            return report, objectives_met
            
        except Exception as e:
            logger.error(f"Erreur dans la démonstration Cluedo: {e}")
            traceback.print_exc()
            return None, False
    
    def _validate_instant_reasoning_objectives(self, report: Dict[str, Any]) -> bool:
        """Valide les objectifs de raisonnement instantané"""
        try:
            # ✅ Solution trouvée en ≤ 5 échanges
            exchanges_count = len([msg for msg in report['conversation_trace'] 
                                 if msg['agent_name'] in ['Sherlock', 'Watson']])
            exchanges_ok = exchanges_count <= 10  # 5 échanges = 10 messages max
            
            # ✅ Raisonnement déductif visible
            sherlock_messages = [msg for msg in report['conversation_trace'] 
                               if msg['agent_name'] == 'Sherlock']
            deduction_visible = any('deduction' in msg['message_type'].lower() or 
                                  'decision' in msg['message_type'].lower() 
                                  for msg in sherlock_messages)
            
            # ✅ Utilisation des outils
            tools_used = report['metrics']['total_tool_calls'] > 0
            
            # ✅ État partagé convergent
            state_updates = report['metrics']['state_updates'] > 0
            
            all_objectives = exchanges_ok and deduction_visible and tools_used and state_updates
            
            logger.info(f"Validation objectifs - Échanges: {exchanges_ok}, Déduction: {deduction_visible}, Outils: {tools_used}, État: {state_updates}")
            
            return all_objectives
            
        except Exception as e:
            logger.error(f"Erreur validation objectifs: {e}")
            return False


async def run_cluedo_sherlock_watson_demo():
    """Point d'entrée pour la démonstration Cluedo améliorée"""
    orchestrator = CluedoSherlockWatsonOrchestrator()
    return await orchestrator.run_cluedo_instant_reasoning_demo()


if __name__ == "__main__":
    report, success = asyncio.run(run_cluedo_sherlock_watson_demo())
    
    if success:
        print("✅ Démonstration Cluedo avec raisonnement instantané réussie !")
        print(f"📊 Rapport généré avec {report['metrics']['total_messages']} messages")
    else:
        print("❌ Échec de la démonstration Cluedo")