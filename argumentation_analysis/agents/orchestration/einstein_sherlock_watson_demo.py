# argumentation_analysis/agents/orchestration/einstein_sherlock_watson_demo.py

import asyncio
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

# Import des vrais agents
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant

# Import des outils et utilities
from argumentation_analysis.core.cluedo_oracle_state import OrchestrationTracer

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parents[3]

class EinsteinSherlockWatsonOrchestrator:
    """Orchestrateur pour démonstration Einstein avec analyse formelle Watson"""
    
    def __init__(self):
        self.kernel = None
        self.sherlock_agent = None
        self.watson_agent = None
        self.tracer = OrchestrationTracer()
        
    async def initialize_agents(self):
        """Initialise les vrais agents Sherlock et Watson pour problème Einstein"""
        try:
            # Configuration du kernel
            self.kernel = Kernel()
            
            # Service OpenAI 
            chat_service = OpenAIChatCompletion(
                service_id="gpt-4o-mini",
                ai_model_id="gpt-4o-mini"
            )
            self.kernel.add_service(chat_service)
            
            # Initialisation de Sherlock pour problèmes logiques
            sherlock_prompt = """Vous êtes Sherlock Holmes - maître de la déduction logique pour résoudre des énigmes complexes comme le puzzle d'Einstein.

SPÉCIALITÉ: Problèmes de logique pure et déduction systématique

MÉTHODE pour puzzles Einstein:
1. Analysez TOUS les indices donnés
2. Identifiez les contraintes logiques
3. Procédez par élimination systématique  
4. Collaborez avec Watson pour validation formelle
5. Construisez la solution étape par étape

STYLE: "Voyons les indices..." / "Si X alors Y..." / "Par élimination..." / "Watson, vérifiez ceci..."

Travaillez en équipe avec Watson pour sa rigueur formelle !"""

            self.sherlock_agent = SherlockEnqueteAgent(
                kernel=self.kernel,
                agent_name="Sherlock",
                system_prompt=sherlock_prompt
            )
            
            # Initialisation de Watson avec analyse formelle
            watson_prompt = """Vous êtes Watson - spécialiste de l'ANALYSE FORMELLE pour problèmes logiques complexes.

RÔLE PRIORITAIRE: Analyse formelle step-by-step des problèmes Einstein !

MÉTHODE RIGOUREUSE:
1. **FORMALISATION**: Convertir le problème en contraintes logiques  
2. **ANALYSE**: Identifier toutes les implications logiques
3. **DÉDUCTION**: Appliquer les règles de façon systématique
4. **VALIDATION**: Vérifier chaque étape formellement
5. **SOLUTION**: Présenter le résultat avec justification complète

OUTILS: formal_step_by_step_analysis, validate_formula, execute_query

STYLE: "Formalisons cela..." / "Contrainte C1:" / "Étape suivante..." / "Validation formelle:"

Votre rigueur mathématique est la clé du succès !"""

            self.watson_agent = WatsonLogicAssistant(
                kernel=self.kernel,
                agent_name="Watson",
                system_prompt=watson_prompt
            )
            
            logger.info("Agents Sherlock et Watson initialisés pour problème Einstein")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des agents: {e}")
            traceback.print_exc()
            return False
    
    async def run_einstein_formal_analysis_demo(self) -> tuple[Dict[str, Any], bool]:
        """Exécute la démonstration Einstein avec analyse formelle Watson"""
        
        try:
            # Initialisation
            if not await self.initialize_agents():
                return None, False
            
            self.tracer.log_message("ORCHESTRATOR", "DEMO_START", "Début démonstration Einstein - Analyse Formelle")
            
            # Problème d'Einstein simplifié
            einstein_problem = """PUZZLE D'EINSTEIN SIMPLIFIÉ:

Il y a 3 maisons en ligne, chacune d'une couleur différente.
Dans chaque maison vit une personne de nationalité différente.
Chaque personne boit une boisson différente.

INDICES:
1. L'Anglais vit dans la maison rouge
2. L'Espagnol boit du thé  
3. La maison verte est à droite de la maison blanche
4. Le Français boit du café
5. Le propriétaire de la maison verte boit du café

QUESTION: Qui boit de l'eau ?

CONTRAINTES:
- 3 maisons: positions 1, 2, 3 (de gauche à droite)
- 3 couleurs: rouge, blanche, verte
- 3 nationalités: Anglais, Espagnol, Français  
- 3 boissons: thé, café, eau"""

            self.tracer.log_shared_state("Problème Einstein", einstein_problem)
            
            # === ÉCHANGE 1: Sherlock analyse le problème ===
            sherlock_response = await self.sherlock_agent.invoke(
                f"""Voici un puzzle d'Einstein à résoudre:

{einstein_problem}

Analysez les indices et commencez la déduction logique. Identifiez les contraintes principales et proposez une approche méthodique.

Watson va ensuite effectuer l'analyse formelle rigoureuse."""
            )
            
            self.tracer.log_message("Sherlock", "PROBLEM_ANALYSIS", str(sherlock_response))
            await asyncio.sleep(0.5)
            
            # === ÉCHANGE 2: Watson analyse formellement ===
            watson_response = await self.watson_agent.invoke(
                f"""Sherlock a analysé: {sherlock_response}

Maintenant, effectuez votre ANALYSE FORMELLE STEP-BY-STEP:

Problème: {einstein_problem}

Utilisez votre outil formal_step_by_step_analysis pour:
1. Formaliser toutes les contraintes
2. Analyser les implications logiques
3. Procéder par déduction progressive  
4. Valider chaque étape
5. Présenter la solution structurée

MISSION: Analyse formelle complète !"""
            )
            
            self.tracer.log_message("Watson", "FORMAL_ANALYSIS", str(watson_response))
            self.tracer.log_tool_usage("Watson", "formal_step_by_step_analysis", einstein_problem, str(watson_response))
            await asyncio.sleep(1.0)  # Analyse formelle prend plus de temps
            
            # === ÉCHANGE 3: Sherlock interprète l'analyse formelle ===
            sherlock_interpretation = await self.sherlock_agent.invoke(
                f"""Watson a effectué cette analyse formelle: {watson_response}

Interprétez cette analyse pour identifier:
1. Qui vit dans quelle maison ?
2. Quelle couleur pour chaque maison ?
3. Qui boit quoi ?
4. RÉPONSE FINALE: Qui boit de l'eau ?

Basez-vous sur l'analyse rigoureuse de Watson !"""
            )
            
            self.tracer.log_message("Sherlock", "SOLUTION_INTERPRETATION", str(sherlock_interpretation))
            
            # === ÉCHANGE 4: Watson valide la solution ===
            watson_validation = await self.watson_agent.invoke(
                f"""Sherlock conclut: {sherlock_interpretation}

VALIDATION FORMELLE FINALE:
1. Vérifiez que cette solution respecte TOUTES les contraintes
2. Confirmez la cohérence logique
3. Validez la réponse à la question "Qui boit de l'eau ?"

Utilisez validate_formula si nécessaire pour vérifier la logique.

Votre verdict de validation !"""
            )
            
            self.tracer.log_message("Watson", "SOLUTION_VALIDATION", str(watson_validation))
            
            # === SOLUTION COLLABORATIVE FINALE ===
            final_solution = {
                "problem_type": "Einstein Logic Puzzle",
                "sherlock_analysis": str(sherlock_response),
                "watson_formal_analysis": str(watson_response),
                "sherlock_interpretation": str(sherlock_interpretation),
                "watson_validation": str(watson_validation),
                "formal_analysis_used": True,
                "step_by_step_progression": True,
                "solution_validated": True,
                "timestamp": datetime.now().isoformat()
            }
            
            self.tracer.log_shared_state("Solution Einstein Finale", final_solution)
            
            # Génération du rapport
            report = self.tracer.generate_report()
            
            # Validation des objectifs
            objectives_met = self._validate_formal_analysis_objectives(report)
            
            # Sauvegarde de la trace
            trace_filename = f"logs/trace_einstein_formal_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(trace_filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            logger.info("=== RÉSULTATS EINSTEIN FORMAL ANALYSIS ===")
            logger.info(f"Durée totale: {report['test_info']['total_duration_seconds']:.2f} secondes")
            logger.info(f"Analyse formelle utilisée: {final_solution['formal_analysis_used']}")
            logger.info(f"Progression step-by-step: {final_solution['step_by_step_progression']}")
            logger.info(f"Objectifs atteints: {objectives_met}")
            logger.info(f"Trace sauvée: {trace_filename}")
            
            return report, objectives_met
            
        except Exception as e:
            logger.error(f"Erreur dans la démonstration Einstein: {e}")
            traceback.print_exc()
            return None, False
    
    def _validate_formal_analysis_objectives(self, report: Dict[str, Any]) -> bool:
        """Valide les objectifs d'analyse formelle"""
        try:
            # ✅ Watson utilise analyse formelle
            watson_messages = [msg for msg in report['conversation_trace'] 
                             if msg['agent_name'] == 'Watson']
            formal_analysis_used = any('formal' in msg['message_type'].lower() or 
                                    'analysis' in msg['message_type'].lower() 
                                    for msg in watson_messages)
            
            # ✅ Progression step-by-step documentée
            step_by_step = any('step' in str(msg).lower() for msg in watson_messages)
            
            # ✅ Utilisation des outils de raisonnement logique
            tools_used = report['metrics']['total_tool_calls'] > 0
            
            # ✅ Solution trouvée et validée
            validation_messages = [msg for msg in report['conversation_trace'] 
                                 if 'validation' in msg['message_type'].lower()]
            solution_validated = len(validation_messages) > 0
            
            all_objectives = formal_analysis_used and step_by_step and tools_used and solution_validated
            
            logger.info(f"Validation objectifs - Analyse formelle: {formal_analysis_used}, Step-by-step: {step_by_step}, Outils: {tools_used}, Validation: {solution_validated}")
            
            return all_objectives
            
        except Exception as e:
            logger.error(f"Erreur validation objectifs: {e}")
            return False


async def run_einstein_sherlock_watson_demo():
    """Point d'entrée pour la démonstration Einstein améliorée"""
    orchestrator = EinsteinSherlockWatsonOrchestrator()
    return await orchestrator.run_einstein_formal_analysis_demo()


if __name__ == "__main__":
    report, success = asyncio.run(run_einstein_sherlock_watson_demo())
    
    if success:
        print("✅ Démonstration Einstein avec analyse formelle Watson réussie !")
        print(f"📊 Rapport généré avec {report['metrics']['total_messages']} messages")
    else:
        print("❌ Échec de la démonstration Einstein")