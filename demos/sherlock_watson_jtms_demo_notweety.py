"""
Démonstration interactive du système Sherlock/Watson avec JTMS intégré.
Scénario d'investigation type Cluedo avec raisonnement collaboratif et traçabilité JTMS.

Basé sur les spécifications du RAPPORT_ARCHITECTURE_INTEGRATION_JTMS.md - AXE A
"""

import asyncio
import logging
import json
import os
import sys
from typing import Dict, Any, List
from datetime import datetime

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import semantic_kernel as sk
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent
from argumentation_analysis.agents.watson_jtms_agent import WatsonJTMSAgent
from argumentation_analysis.agents.jtms_communication_hub import (
    JTMSCommunicationHub,
    create_sherlock_watson_communication,
    run_investigation_session
)

# Import pour version sans TweetyProject
try:
    # Test si TweetyProject est disponible
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
    TWEETY_AVAILABLE = True
    print("🟢 TweetyProject disponible - Mode complet activé")
except Exception as e:
    TWEETY_AVAILABLE = False
    print(f"🟡 TweetyProject indisponible ({e}) - Mode démo simple activé")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sherlock_watson_jtms_demo.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("SherlockWatsonJTMSDemo")

class CluedoInvestigationDemo:
    """Démo d'investigation Cluedo avec Sherlock/Watson JTMS"""
    
    def __init__(self):
        self.kernel = None
        self.sherlock = None
        self.watson = None
        self.hub = None
        
        # Scénario Cluedo
        self.cluedo_scenario = {
            "suspects": [
                "Colonel Moutarde", "Professeur Violet", "Révérend Vert",
                "Madame Leblanc", "Mademoiselle Rose", "Madame Pervenche"
            ],
            "weapons": [
                "Corde", "Poignard", "Barre de fer", "Revolver", "Chandelier", "Clé anglaise"
            ],
            "rooms": [
                "Bibliothèque", "Salon", "Salle à manger", "Cuisine", 
                "Hall", "Véranda", "Bureau", "Salle de billard", "Salon de musique"
            ],
            "evidence": {
                "fingerprints_kitchen": {
                    "type": "physical_evidence",
                    "description": "Empreintes digitales trouvées sur le chandelier dans la cuisine",
                    "suspects": ["Colonel Moutarde", "Madame Leblanc"],
                    "reliability": 0.9
                },
                "witness_testimony": {
                    "type": "testimony", 
                    "description": "Témoin a vu Professeur Violet près de la bibliothèque vers 21h",
                    "suspects": ["Professeur Violet"],
                    "reliability": 0.7
                },
                "broken_vase": {
                    "type": "circumstantial",
                    "description": "Vase brisé dans le salon, possibles signes de lutte",
                    "rooms": ["Salon"],
                    "reliability": 0.6
                },
                "missing_weapon": {
                    "type": "inventory",
                    "description": "Le poignard manque de sa vitrine habituelle",
                    "weapons": ["Poignard"],
                    "reliability": 0.8
                },
                "door_locked": {
                    "type": "physical_evidence",
                    "description": "Bureau verrouillé de l'intérieur, clé introuvable",
                    "rooms": ["Bureau"],
                    "reliability": 0.95
                },
                "footprints_garden": {
                    "type": "physical_evidence", 
                    "description": "Empreintes de pas dans le jardin menant vers la véranda",
                    "rooms": ["Véranda"],
                    "reliability": 0.75
                }
            },
            "victim": {
                "name": "Dr. Lenoir",
                "location_found": "Bibliothèque",
                "time_of_death": "21:30",
                "cause_preliminary": "Traumatisme crânien"
            }
        }
        
        self.demo_phases = [
            "initialization",
            "evidence_analysis", 
            "hypothesis_formation",
            "cross_validation",
            "conflict_resolution",
            "final_deduction"
        ]
        
        self.session_state = {
            "current_phase": 0,
            "phase_results": {},
            "investigation_timeline": [],
            "beliefs_evolution": [],
            "conflicts_resolved": [],
            "final_solution": None
        }
    
    async def initialize_system(self) -> bool:
        """Initialise le système Semantic Kernel et les agents JTMS"""
        try:
            logger.info("=== INITIALISATION DU SYSTÈME SHERLOCK/WATSON JTMS ===")
            
            if not TWEETY_AVAILABLE:
                logger.warning("TweetyProject indisponible - Initialisation en mode simplifié")
                return await self._initialize_simplified_system()
            
            # Créer le kernel Semantic Kernel
            self.kernel = Kernel()
            
            # Configuration OpenAI (vous devrez adapter selon votre configuration)
            try:
                api_key = os.getenv("OPENAI_API_KEY")
                if not api_key:
                    # Mode démo sans API - utiliser des réponses simulées
                    logger.warning("Pas de clé API OpenAI - Mode démo avec réponses simulées")
                    self.demo_mode = True
                else:
                    service_id = "openai_chat"
                    self.kernel.add_service(
                        OpenAIChatCompletion(
                            service_id=service_id,
                            api_key=api_key,
                            ai_model_id="gpt-4"
                        )
                    )
                    self.demo_mode = False
                    
            except Exception as e:
                logger.warning(f"Erreur configuration OpenAI: {e} - Mode démo activé")
                self.demo_mode = True
            
            # Créer les agents et le hub
            self.sherlock, self.watson, self.hub = await create_sherlock_watson_communication(
                self.kernel,
                sherlock_config={
                    "name": "Sherlock_Cluedo",
                    "system_prompt": "Expert en déduction et analyse d'indices pour résolution d'enquêtes criminelles type Cluedo."
                },
                watson_config={
                    "name": "Watson_Cluedo",
                    "system_prompt": "Spécialiste en validation logique et critique constructive pour investigations criminelles."
                }
            )
            
            logger.info(f"✅ Sherlock initialisé: {self.sherlock.agent_name}")
            logger.info(f"✅ Watson initialisé: {self.watson.agent_name}")
            logger.info(f"✅ Hub de communication actif")
            
            # Ajouter le contexte Cluedo initial
            await self._initialize_cluedo_context()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            logger.info("🔄 Tentative d'initialisation en mode simplifié...")
            return await self._initialize_simplified_system()
    
    async def _initialize_simplified_system(self) -> bool:
        """Initialise le système en mode simplifié sans TweetyProject"""
        try:
            logger.info("🔧 Initialisation système simplifié (sans TweetyProject)")
            
            # Mode démo forcé
            self.demo_mode = True
            self.kernel = None  # Pas de Semantic Kernel
            
            # Créer des agents simulés
            class SimpleAgent:
                def __init__(self, name, role):
                    self.agent_name = name
                    self.role = role
                    self.session_id = f"{name}_{hash(name) % 10000}"
                    self.beliefs = {}
                    
                async def add_belief(self, belief, metadata):
                    self.beliefs[belief] = metadata
                    
                def get_all_beliefs(self):
                    return self.beliefs
                    
                def get_session_statistics(self):
                    return {
                        "last_modified": datetime.now().isoformat(),
                        "total_beliefs": len(self.beliefs)
                    }
                    
                def export_session_state(self):
                    return {
                        "agent_name": self.agent_name,
                        "session_id": self.session_id,
                        "beliefs": self.beliefs,
                        "role": self.role
                    }
            
            # Créer les agents simplifiés
            self.sherlock = SimpleAgent("Sherlock_Cluedo", "detective")
            self.watson = SimpleAgent("Watson_Cluedo", "validator")
            
            # Hub simplifié
            class SimpleHub:
                def __init__(self, sherlock_agent, watson_agent):
                    self.agents = {"Sherlock_Cluedo": sherlock_agent, "Watson_Cluedo": watson_agent}
                    self.statistics = {"messages_processed": 0, "conflicts_resolved": 0, "sync_operations_completed": 0}
                    
                async def sync_beliefs(self, from_agent, to_agent):
                    return {"beliefs_imported": 0, "status": "simulated"}
                    
                async def check_global_consistency(self):
                    return {
                        "is_consistent": True,
                        "inter_agent_conflicts": [],
                        "resolutions": []
                    }
                    
                async def resolve_belief_conflicts(self, conflicts, strategy):
                    return [{"resolved": True, "conflict_id": i, "reasoning": f"Simulé avec {strategy}"} for i, _ in enumerate(conflicts)]
                    
                def get_hub_status(self):
                    return {
                        "status": "active_simplified",
                        "connected_agents": list(self.agents.keys()),
                        "statistics": self.statistics,
                        "global_consistency": {"is_consistent": True, "last_check": datetime.now().isoformat(), "conflicts_count": 0},
                        "configuration": {"auto_sync_enabled": False, "conflict_resolution_strategy": "simulated", "sync_interval": 0}
                    }
                    
                async def shutdown(self):
                    logger.info("Hub simplifié arrêté")
            
            self.hub = SimpleHub(self.sherlock, self.watson)
            
            logger.info(f"✅ Sherlock simplifié initialisé: {self.sherlock.agent_name}")
            logger.info(f"✅ Watson simplifié initialisé: {self.watson.agent_name}")
            logger.info(f"✅ Hub simplifié actif")
            
            # Ajouter le contexte Cluedo initial
            await self._initialize_cluedo_context()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation simplifiée: {e}")
            return False
    
    async def _initialize_cluedo_context(self):
        """Initialise le contexte Cluedo dans les agents"""
        
        # Ajouter les faits de base dans Sherlock
        basic_facts = [
            f"victim_found_in_{self.cluedo_scenario['victim']['location_found'].lower()}",
            f"time_of_death_{self.cluedo_scenario['victim']['time_of_death'].replace(':', 'h')}",
            f"cause_preliminary_{self.cluedo_scenario['victim']['cause_preliminary'].replace(' ', '_').lower()}"
        ]
        
        for fact in basic_facts:
            await self.sherlock.add_belief(
                fact,
                {"type": "initial_fact", "source": "crime_scene", "confidence": 0.95}
            )
        
        # Ajouter les contraintes du jeu dans Watson
        game_rules = [
            "crime_requires_suspect_weapon_room",
            "exactly_one_suspect_guilty", 
            "exactly_one_weapon_used",
            "exactly_one_room_location"
        ]
        
        for rule in game_rules:
            await self.watson.add_belief(
                rule,
                {"type": "game_constraint", "source": "cluedo_rules", "confidence": 1.0}
            )
        
        logger.info("Contexte Cluedo initialisé dans les agents")
    
    async def run_interactive_demo(self):
        """Lance la démo interactive complète"""
        try:
            if not await self.initialize_system():
                logger.error("Échec initialisation système")
                return
            
            print("\n" + "="*80)
            print("🕵️  DÉMONSTRATION SHERLOCK/WATSON AVEC JTMS INTÉGRÉ  🕵️")
            print("="*80)
            print("\n📖 SCÉNARIO: Enquête Cluedo - Meurtre du Dr. Lenoir")
            print(f"📍 Lieu: {self.cluedo_scenario['victim']['location_found']}")
            print(f"⏰ Heure estimée: {self.cluedo_scenario['victim']['time_of_death']}")
            print(f"💀 Cause: {self.cluedo_scenario['victim']['cause_preliminary']}")
            
            # Menu principal
            while True:
                print("\n" + "-"*60)
                print("🎯 MENU PRINCIPAL")
                print("-"*60)
                print("1. 🔍 Lancer investigation automatique complète")
                print("2. 📝 Phase par phase interactive")
                print("3. 🧠 Analyser évidence spécifique")
                print("4. ⚖️  Tester résolution de conflits")
                print("5. 📊 Voir état système JTMS")
                print("6. 💾 Exporter session")
                print("7. ❌ Quitter")
                
                choice = input("\n🎪 Choisissez une option: ").strip()
                
                if choice == "1":
                    await self._run_automatic_investigation()
                elif choice == "2":
                    await self._run_interactive_phases()
                elif choice == "3":
                    await self._analyze_specific_evidence()
                elif choice == "4":
                    await self._test_conflict_resolution()
                elif choice == "5":
                    await self._show_jtms_status()
                elif choice == "6":
                    await self._export_session()
                elif choice == "7":
                    print("\n👋 Arrêt de la démonstration")
                    break
                else:
                    print("❌ Option invalide")
                    
        except KeyboardInterrupt:
            print("\n\n⏹️  Démonstration interrompue par l'utilisateur")
        except Exception as e:
            logger.error(f"Erreur durant la démo: {e}")
        finally:
            await self._cleanup()
    
    async def _run_automatic_investigation(self):
        """Lance une investigation automatique complète"""
        print("\n🚀 LANCEMENT INVESTIGATION AUTOMATIQUE")
        print("="*50)
        
        investigation_context = {
            "type": "cluedo_murder_case",
            "description": f"Meurtre de {self.cluedo_scenario['victim']['name']} dans {self.cluedo_scenario['victim']['location_found']}",
            "evidence_available": list(self.cluedo_scenario['evidence'].keys()),
            "suspects": self.cluedo_scenario['suspects'],
            "weapons": self.cluedo_scenario['weapons'],
            "rooms": self.cluedo_scenario['rooms']
        }
        
        # Utiliser la fonction utilitaire du hub
        session_results = await run_investigation_session(
            self.sherlock, self.watson, self.hub, investigation_context
        )
        
        # Afficher les résultats
        self._display_session_results(session_results)
        
        # Sauvegarder
        self.session_state["final_solution"] = session_results.get("final_solution")
        self.session_state["session_results"] = session_results
    
    async def _run_interactive_phases(self):
        """Lance l'investigation phase par phase avec interaction"""
        print("\n📚 INVESTIGATION PHASE PAR PHASE")
        print("="*50)
        
        for phase_idx, phase_name in enumerate(self.demo_phases):
            print(f"\n🎭 PHASE {phase_idx + 1}: {phase_name.upper()}")
            print("-" * 40)
            
            if phase_name == "initialization":
                await self._phase_initialization()
            elif phase_name == "evidence_analysis":
                await self._phase_evidence_analysis()
            elif phase_name == "hypothesis_formation":
                await self._phase_hypothesis_formation()
            elif phase_name == "cross_validation":
                await self._phase_cross_validation()
            elif phase_name == "conflict_resolution":
                await self._phase_conflict_resolution()
            elif phase_name == "final_deduction":
                await self._phase_final_deduction()
            
            input("\n⏸️  Appuyez sur Entrée pour continuer...")
    
    async def _phase_initialization(self):
        """Phase d'initialisation"""
        print("🎬 Initialisation des agents et du contexte...")
        
        # Afficher l'état initial
        sherlock_beliefs = len(self.sherlock.get_all_beliefs())
        watson_beliefs = len(self.watson.get_all_beliefs())
        
        print(f"📊 Sherlock: {sherlock_beliefs} croyances initiales")
        print(f"📊 Watson: {watson_beliefs} croyances initiales")
        
        hub_status = self.hub.get_hub_status()
        print(f"🌐 Hub: {len(hub_status['connected_agents'])} agents connectés")
        
        self.session_state["phase_results"]["initialization"] = {
            "sherlock_beliefs": sherlock_beliefs,
            "watson_beliefs": watson_beliefs,
            "hub_connected": len(hub_status['connected_agents'])
        }
    
    async def _phase_evidence_analysis(self):
        """Phase d'analyse des évidences"""
        print("🔍 Analyse des évidences disponibles...")
        
        # Ajouter les évidences une par une dans Sherlock
        evidence_count = 0
        for evidence_id, evidence_data in self.cluedo_scenario['evidence'].items():
            
            print(f"\n📋 Evidence: {evidence_id}")
            print(f"   Type: {evidence_data['type']}")
            print(f"   Description: {evidence_data['description']}")
            print(f"   Fiabilité: {evidence_data['reliability']}")
            
            # Ajouter dans Sherlock
            await self.sherlock.add_belief(
                f"evidence_{evidence_id}",
                {
                    "type": "evidence",
                    "source": evidence_data['type'],
                    "confidence": evidence_data['reliability'],
                    "description": evidence_data['description']
                }
            )
            
            # Analyser avec Sherlock
            if hasattr(self.sherlock, 'evidence_manager'):
                analysis = await self.sherlock.evidence_manager.analyze_evidence(
                    evidence_id, evidence_data
                )
                print(f"   🧠 Analyse Sherlock: Pertinence {analysis.get('relevance', 'N/A')}")
            
            evidence_count += 1
        
        # Synchroniser avec Watson
        sync_result = await self.hub.sync_beliefs("Sherlock_Cluedo", "Watson_Cluedo")
        print(f"\n🔄 Synchronisation: {sync_result.get('beliefs_imported', 0)} croyances transférées")
        
        self.session_state["phase_results"]["evidence_analysis"] = {
            "evidence_processed": evidence_count,
            "sync_result": sync_result
        }
    
    async def _phase_hypothesis_formation(self):
        """Phase de formation d'hypothèses"""
        print("💡 Formation d'hypothèses par Sherlock...")
        
        # Sherlock formule des hypothèses
        investigation_prompt = f"""
        Analyser le meurtre de {self.cluedo_scenario['victim']['name']} 
        dans {self.cluedo_scenario['victim']['location_found']}.
        
        Suspects possibles: {', '.join(self.cluedo_scenario['suspects'])}
        Armes possibles: {', '.join(self.cluedo_scenario['weapons'])}
        Lieux possibles: {', '.join(self.cluedo_scenario['rooms'])}
        """
        
        if self.demo_mode:
            # Mode démo - hypothèses simulées
            hypothesis_result = {
                "primary_hypothesis": {
                    "suspect": "Colonel Moutarde",
                    "weapon": "Chandelier", 
                    "room": "Cuisine",
                    "confidence": 0.75,
                    "reasoning": "Empreintes sur chandelier + présence établie"
                },
                "alternative_hypotheses": [
                    {
                        "suspect": "Professeur Violet",
                        "weapon": "Poignard",
                        "room": "Bibliothèque",
                        "confidence": 0.6,
                        "reasoning": "Témoin + arme manquante + lieu du crime"
                    }
                ]
            }
        else:
            hypothesis_result = await self.sherlock.formulate_hypothesis(investigation_prompt)
        
        # Afficher les hypothèses
        print("\n🎯 HYPOTHÈSE PRINCIPALE:")
        primary = hypothesis_result.get("primary_hypothesis", {})
        print(f"   Suspect: {primary.get('suspect', 'N/A')}")
        print(f"   Arme: {primary.get('weapon', 'N/A')}")
        print(f"   Lieu: {primary.get('room', 'N/A')}")
        print(f"   Confiance: {primary.get('confidence', 0):.2f}")
        print(f"   Raisonnement: {primary.get('reasoning', 'N/A')}")
        
        # Hypothèses alternatives
        alternatives = hypothesis_result.get("alternative_hypotheses", [])
        if alternatives:
            print(f"\n🔄 {len(alternatives)} HYPOTHÈSES ALTERNATIVES:")
            for i, alt in enumerate(alternatives, 1):
                print(f"   {i}. {alt.get('suspect', 'N/A')} avec {alt.get('weapon', 'N/A')} dans {alt.get('room', 'N/A')} (conf: {alt.get('confidence', 0):.2f})")
        
        self.session_state["phase_results"]["hypothesis_formation"] = hypothesis_result
    
    async def _phase_cross_validation(self):
        """Phase de validation croisée"""
        print("⚖️  Validation croisée par Watson...")
        
        hypothesis_data = self.session_state["phase_results"].get("hypothesis_formation", {})
        
        if self.demo_mode:
            # Mode démo - critique simulée
            critique_result = {
                "validity_assessment": {
                    "logical_consistency": 0.8,
                    "evidence_support": 0.7,
                    "completeness": 0.6
                },
                "identified_gaps": [
                    "Manque d'alibi vérifié pour Colonel Moutarde",
                    "Pas d'explication pour le bureau verrouillé",
                    "Lien entre empreintes et heure du crime non établi"
                ],
                "suggestions": [
                    "Vérifier les alibis des suspects principaux",
                    "Analyser la séquence temporelle des événements",
                    "Examiner les moyens d'accès aux armes"
                ],
                "confidence_in_hypothesis": 0.65
            }
        else:
            critique_result = await self.watson.critique_hypothesis(
                hypothesis_data,
                self.sherlock.export_session_state()
            )
        
        # Afficher la critique
        print("\n📝 ÉVALUATION WATSON:")
        validity = critique_result.get("validity_assessment", {})
        print(f"   Cohérence logique: {validity.get('logical_consistency', 0):.2f}")
        print(f"   Support évidentiel: {validity.get('evidence_support', 0):.2f}")
        print(f"   Complétude: {validity.get('completeness', 0):.2f}")
        
        gaps = critique_result.get("identified_gaps", [])
        if gaps:
            print(f"\n🔍 LACUNES IDENTIFIÉES:")
            for gap in gaps:
                print(f"   • {gap}")
        
        suggestions = critique_result.get("suggestions", [])
        if suggestions:
            print(f"\n💡 SUGGESTIONS:")
            for suggestion in suggestions:
                print(f"   • {suggestion}")
        
        print(f"\n🎯 Confiance Watson dans l'hypothèse: {critique_result.get('confidence_in_hypothesis', 0):.2f}")
        
        self.session_state["phase_results"]["cross_validation"] = critique_result
    
    async def _phase_conflict_resolution(self):
        """Phase de résolution de conflits"""
        print("🤝 Résolution de conflits entre agents...")
        
        # Vérifier la cohérence globale
        consistency_check = await self.hub.check_global_consistency()
        
        print(f"\n📊 COHÉRENCE GLOBALE: {'✅ Cohérent' if consistency_check['is_consistent'] else '❌ Conflits détectés'}")
        
        inter_conflicts = consistency_check.get("inter_agent_conflicts", [])
        if inter_conflicts:
            print(f"\n⚠️  {len(inter_conflicts)} CONFLITS INTER-AGENTS:")
            
            for i, conflict in enumerate(inter_conflicts, 1):
                print(f"   {i}. {conflict.get('type', 'N/A')}: {conflict.get('belief1', 'N/A')} vs {conflict.get('belief2', 'N/A')}")
            
            # Résoudre les conflits
            resolutions = await self.hub.resolve_belief_conflicts(inter_conflicts, "evidence_based")
            
            print(f"\n🛠️  RÉSOLUTIONS APPLIQUÉES:")
            for resolution in resolutions:
                if resolution.get("resolved"):
                    print(f"   ✅ {resolution.get('conflict_id', 'N/A')}: {resolution.get('reasoning', 'N/A')}")
                else:
                    print(f"   ❌ {resolution.get('conflict_id', 'N/A')}: Non résolu")
        else:
            print("   ✅ Aucun conflit détecté")
        
        self.session_state["phase_results"]["conflict_resolution"] = {
            "initial_consistency": consistency_check["is_consistent"],
            "conflicts_found": len(inter_conflicts),
            "conflicts_resolved": len([r for r in consistency_check.get("resolutions", []) if r.get("resolved")])
        }
    
    async def _phase_final_deduction(self):
        """Phase de déduction finale"""
        print("🎯 Déduction finale collaborative...")
        
        # Sherlock propose solution finale
        if self.demo_mode:
            final_solution = {
                "solution": {
                    "culprit": "Colonel Moutarde",
                    "weapon": "Chandelier",
                    "location": "Cuisine",
                    "motive": "Différend financier avec la victime"
                },
                "confidence": 0.82,
                "supporting_evidence": [
                    "Empreintes digitales sur l'arme",
                    "Présence établie dans le lieu",
                    "Accès aux informations financières de la victime"
                ],
                "reasoning_chain": [
                    "Dr. Lenoir découvert dans bibliothèque",
                    "Mais empreintes Colonel Moutarde sur chandelier dans cuisine",
                    "Probable déplacement du corps",
                    "Colonel avait accès et motif financier"
                ]
            }
        else:
            investigation_context = {
                "case_summary": f"Meurtre {self.cluedo_scenario['victim']['name']}",
                "all_evidence": self.cluedo_scenario['evidence'],
                "previous_analysis": self.session_state["phase_results"]
            }
            final_solution = await self.sherlock.deduce_solution(investigation_context)
        
        # Watson valide la solution
        if self.demo_mode:
            watson_validation = {
                "logical_validity": 0.85,
                "evidence_consistency": 0.8,
                "completeness_score": 0.75,
                "overall_confidence": 0.8,
                "validation_notes": [
                    "Solution cohérente avec les preuves physiques",
                    "Chaîne de raisonnement logique",
                    "Quelques aspects circonstanciels à consolider"
                ]
            }
        else:
            watson_validation = await self.watson.validate_sherlock_reasoning(
                self.sherlock.export_session_state()
            )
        
        # Afficher la solution finale
        print("\n🏆 SOLUTION FINALE:")
        solution = final_solution.get("solution", {})
        print(f"   🔍 Coupable: {solution.get('culprit', 'N/A')}")
        print(f"   🔪 Arme: {solution.get('weapon', 'N/A')}")
        print(f"   📍 Lieu: {solution.get('location', 'N/A')}")
        print(f"   💭 Motif: {solution.get('motive', 'N/A')}")
        print(f"   🎯 Confiance Sherlock: {final_solution.get('confidence', 0):.2f}")
        print(f"   ⚖️  Validation Watson: {watson_validation.get('overall_confidence', 0):.2f}")
        
        # Chaîne de raisonnement
        reasoning = final_solution.get("reasoning_chain", [])
        if reasoning:
            print(f"\n🧠 CHAÎNE DE RAISONNEMENT:")
            for i, step in enumerate(reasoning, 1):
                print(f"   {i}. {step}")
        
        self.session_state["phase_results"]["final_deduction"] = {
            "solution": final_solution,
            "watson_validation": watson_validation
        }
        
        # Sauvegarder solution finale
        self.session_state["final_solution"] = final_solution
    
    async def _analyze_specific_evidence(self):
        """Analyse d'une évidence spécifique"""
        print("\n🔍 ANALYSE D'ÉVIDENCE SPÉCIFIQUE")
        print("="*50)
        
        # Lister les évidences disponibles
        print("📋 Évidences disponibles:")
        for i, (evidence_id, evidence_data) in enumerate(self.cluedo_scenario['evidence'].items(), 1):
            print(f"   {i}. {evidence_id}: {evidence_data['description'][:50]}...")
        
        try:
            choice = int(input("\n🎯 Choisissez une évidence (numéro): ")) - 1
            evidence_items = list(self.cluedo_scenario['evidence'].items())
            
            if 0 <= choice < len(evidence_items):
                evidence_id, evidence_data = evidence_items[choice]
                
                print(f"\n📊 ANALYSE DÉTAILLÉE: {evidence_id}")
                print("-" * 40)
                print(f"Type: {evidence_data['type']}")
                print(f"Description: {evidence_data['description']}")
                print(f"Fiabilité: {evidence_data['reliability']}")
                
                # Analyse par Sherlock
                print(f"\n🕵️  ANALYSE SHERLOCK:")
                if hasattr(self.sherlock, 'evidence_manager'):
                    sherlock_analysis = await self.sherlock.evidence_manager.analyze_evidence(
                        evidence_id, evidence_data
                    )
                    print(f"   Pertinence: {sherlock_analysis.get('relevance', 'N/A')}")
                    print(f"   Implications: {sherlock_analysis.get('implications', [])}")
                
                # Critique par Watson
                print(f"\n🤖 CRITIQUE WATSON:")
                if self.demo_mode:
                    watson_critique = {
                        "reliability_assessment": evidence_data['reliability'] * 0.9,
                        "logical_implications": [
                            f"Évidence {evidence_id} supporte certaines hypothèses",
                            "Nécessite corroboration avec autres éléments"
                        ],
                        "suggested_follow_up": [
                            "Vérifier cohérence temporelle",
                            "Examiner évidences connexes"
                        ]
                    }
                else:
                    watson_critique = await self.watson.analyze_evidence_validity(evidence_data)
                
                print(f"   Évaluation fiabilité: {watson_critique.get('reliability_assessment', 'N/A')}")
                for implication in watson_critique.get('logical_implications', []):
                    print(f"   • {implication}")
                
            else:
                print("❌ Choix invalide")
                
        except (ValueError, IndexError):
            print("❌ Entrée invalide")
    
    async def _test_conflict_resolution(self):
        """Test des mécanismes de résolution de conflits"""
        print("\n🤝 TEST RÉSOLUTION DE CONFLITS")
        print("="*50)
        
        # Créer un conflit artificiel
        print("🎭 Création d'un conflit artificiel...")
        
        # Sherlock croit que le Colonel est coupable
        await self.sherlock.add_belief(
            "colonel_moutarde_guilty",
            {"type": "hypothesis", "confidence": 0.8, "source": "deduction"}
        )
        
        # Watson croit que le Professeur est coupable
        await self.watson.add_belief(
            "professeur_violet_guilty", 
            {"type": "hypothesis", "confidence": 0.7, "source": "logical_analysis"}
        )
        
        # Aussi ajouter des croyances contradictoires sur la même chose
        await self.sherlock.add_belief(
            "murder_weapon_chandelier",
            {"type": "deduction", "confidence": 0.75}
        )
        
        await self.watson.add_belief(
            "murder_weapon_poignard",
            {"type": "analysis", "confidence": 0.8}
        )
        
        print("✅ Conflit créé:")
        print("   • Sherlock: Colonel Moutarde coupable, arme = chandelier")
        print("   • Watson: Professeur Violet coupable, arme = poignard")
        
        # Détecter les conflits
        consistency_check = await self.hub.check_global_consistency()
        conflicts = consistency_check.get("inter_agent_conflicts", [])
        
        print(f"\n🔍 {len(conflicts)} conflit(s) détecté(s)")
        
        if conflicts:
            # Tester différentes stratégies de résolution
            strategies = ["confidence_based", "evidence_based", "agent_expertise"]
            
            for strategy in strategies:
                print(f"\n🛠️  TEST STRATÉGIE: {strategy}")
                
                resolution_results = await self.hub.resolve_belief_conflicts(
                    conflicts, strategy
                )
                
                for result in resolution_results:
                    if result.get("resolved"):
                        print(f"   ✅ Résolu: {result.get('chosen_belief')} par {result.get('chosen_agent')}")
                        print(f"      Raison: {result.get('reasoning')}")
                    else:
                        print(f"   ❌ Non résolu: {result.get('reasoning', 'Raison inconnue')}")
    
    async def _show_jtms_status(self):
        """Affiche l'état complet du système JTMS"""
        print("\n📊 ÉTAT SYSTÈME JTMS")
        print("="*50)
        
        # État des agents
        print("🤖 AGENTS:")
        for agent_name, agent in [("Sherlock", self.sherlock), ("Watson", self.watson)]:
            if agent:
                stats = agent.get_session_statistics()
                beliefs_count = len(agent.get_all_beliefs())
                print(f"   {agent_name}:")
                print(f"     • Croyances: {beliefs_count}")
                print(f"     • Session: {agent.session_id}")
                print(f"     • Dernière modification: {stats.get('last_modified', 'N/A')}")
        
        # État du hub
        print("\n🌐 HUB DE COMMUNICATION:")
        hub_status = self.hub.get_hub_status()
        stats = hub_status.get("statistics", {})
        
        print(f"   • Statut: {hub_status.get('status', 'N/A')}")
        print(f"   • Agents connectés: {len(hub_status.get('connected_agents', []))}")
        print(f"   • Messages traités: {stats.get('messages_processed', 0)}")
        print(f"   • Conflits résolus: {stats.get('conflicts_resolved', 0)}")
        print(f"   • Synchronisations: {stats.get('sync_operations_completed', 0)}")
        
        # Cohérence globale
        consistency = hub_status.get("global_consistency", {})
        print(f"\n⚖️  COHÉRENCE:")
        print(f"   • État: {'✅ Cohérent' if consistency.get('is_consistent', False) else '❌ Incohérent'}")
        print(f"   • Dernière vérification: {consistency.get('last_check', 'N/A')}")
        print(f"   • Conflits actifs: {consistency.get('conflicts_count', 0)}")
        
        # Configuration
        config = hub_status.get("configuration", {})
        print(f"\n⚙️  CONFIGURATION:")
        print(f"   • Sync automatique: {'✅' if config.get('auto_sync_enabled', False) else '❌'}")
        print(f"   • Stratégie résolution: {config.get('conflict_resolution_strategy', 'N/A')}")
        print(f"   • Intervalle sync: {config.get('sync_interval', 'N/A')}s")
    
    async def _export_session(self):
        """Exporte l'état de la session"""
        print("\n💾 EXPORT DE SESSION")
        print("="*50)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sherlock_watson_session_{timestamp}.json"
        
        # Construire l'export complet
        export_data = {
            "session_metadata": {
                "timestamp": timestamp,
                "demo_version": "1.0",
                "scenario": "cluedo_investigation"
            },
            "scenario": self.cluedo_scenario,
            "session_state": self.session_state,
            "agents_state": {
                "sherlock": self.sherlock.export_session_state() if self.sherlock else None,
                "watson": self.watson.export_session_state() if self.watson else None
            },
            "hub_status": self.hub.get_hub_status() if self.hub else None
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"✅ Session exportée: {filename}")
            print(f"📊 Taille: {os.path.getsize(filename)} bytes")
            
            # Statistiques de l'export
            if self.sherlock:
                sherlock_beliefs = len(self.sherlock.get_all_beliefs())
                print(f"   • Croyances Sherlock: {sherlock_beliefs}")
            
            if self.watson:
                watson_beliefs = len(self.watson.get_all_beliefs())
                print(f"   • Croyances Watson: {watson_beliefs}")
            
            phases_completed = len(self.session_state.get("phase_results", {}))
            print(f"   • Phases complétées: {phases_completed}")
            
        except Exception as e:
            print(f"❌ Erreur export: {e}")
    
    def _display_session_results(self, session_results: Dict):
        """Affiche les résultats d'une session d'investigation"""
        print("\n🎊 RÉSULTATS DE SESSION")
        print("="*50)
        
        if session_results.get("success"):
            print("✅ Investigation terminée avec succès")
            
            duration = session_results.get("total_duration", 0)
            print(f"⏱️  Durée totale: {duration:.2f}s")
            
            phases = session_results.get("phases", [])
            print(f"📋 Phases exécutées: {len(phases)}")
            
            for phase in phases:
                phase_name = phase.get("phase", "N/A")
                agent = phase.get("agent", phase.get("agents", "N/A"))
                phase_duration = phase.get("duration", 0)
                print(f"   • {phase_name}: {agent} ({phase_duration:.2f}s)")
            
            # Solution finale
            final_solution = session_results.get("final_solution")
            if final_solution and isinstance(final_solution, dict):
                solution = final_solution.get("solution", {})
                if solution:
                    print(f"\n🏆 SOLUTION:")
                    print(f"   🔍 Coupable: {solution.get('culprit', 'N/A')}")
                    print(f"   🔪 Arme: {solution.get('weapon', 'N/A')}")
                    print(f"   📍 Lieu: {solution.get('location', 'N/A')}")
                    print(f"   🎯 Confiance: {final_solution.get('confidence', 0):.2f}")
            
            # Statistiques JTMS
            jtms_summary = session_results.get("jtms_summary", {})
            if jtms_summary:
                print(f"\n📊 STATISTIQUES JTMS:")
                
                sherlock_stats = jtms_summary.get("sherlock_statistics", {})
                watson_stats = jtms_summary.get("watson_statistics", {})
                
                print(f"   • Sherlock: {sherlock_stats.get('total_beliefs', 0)} croyances")
                print(f"   • Watson: {watson_stats.get('total_beliefs', 0)} croyances")
                
                global_consistency = jtms_summary.get("global_consistency", {})
                is_consistent = global_consistency.get("is_consistent", False)
                print(f"   • Cohérence finale: {'✅' if is_consistent else '❌'}")
        
        else:
            print("❌ Investigation échouée")
            error = session_results.get("error", "Erreur inconnue")
            print(f"   Erreur: {error}")
    
    async def _cleanup(self):
        """Nettoyage lors de l'arrêt"""
        try:
            if self.hub:
                await self.hub.shutdown()
                logger.info("Hub de communication arrêté")
            
            logger.info("Nettoyage terminé")
            
        except Exception as e:
            logger.error(f"Erreur durant le nettoyage: {e}")

# === POINT D'ENTRÉE ===

async def main():
    """Point d'entrée principal de la démonstration"""
    demo = CluedoInvestigationDemo()
    await demo.run_interactive_demo()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Démonstration interrompue")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        print(f"\n❌ Erreur fatale: {e}")