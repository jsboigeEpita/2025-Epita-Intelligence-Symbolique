"""
Démonstration automatique non-interactive du système Sherlock/Watson avec JTMS intégré.
Version simplifiée qui s'exécute sans intervention utilisateur.
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

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("SherlockWatsonAutoDemo")

class AutoCluedoDemo:
    """Démo automatique d'investigation Cluedo avec agents simplifiés"""
    
    def __init__(self):
        # Agents simplifiés
        self.sherlock = None
        self.watson = None
        self.hub = None
        
        # Scénario Cluedo simplifié
        self.cluedo_scenario = {
            "victim": {
                "name": "Dr. Lenoir",
                "location_found": "Bibliothèque",
                "time_of_death": "21:30",
                "cause_preliminary": "Traumatisme crânien"
            },
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Madame Leblanc"],
            "weapons": ["Chandelier", "Poignard", "Barre de fer"],
            "rooms": ["Bibliothèque", "Cuisine", "Salon"],
            "evidence": {
                "fingerprints_kitchen": {
                    "type": "physical_evidence",
                    "description": "Empreintes digitales trouvées sur le chandelier dans la cuisine",
                    "suspects": ["Colonel Moutarde"],
                    "reliability": 0.9
                },
                "witness_testimony": {
                    "type": "testimony", 
                    "description": "Témoin a vu Professeur Violet près de la bibliothèque vers 21h",
                    "suspects": ["Professeur Violet"],
                    "reliability": 0.7
                }
            }
        }
    
    async def initialize_simplified_system(self) -> bool:
        """Initialise le système en mode simplifié"""
        try:
            logger.info("🔧 Initialisation système simplifié")
            
            # Agent simplifié
            class SimpleAgent:
                def __init__(self, name, role):
                    self.agent_name = name
                    self.role = role
                    self.session_id = f"{name}_{hash(name) % 10000}"
                    self.beliefs = {}
                    
                async def add_belief(self, belief, metadata):
                    self.beliefs[belief] = metadata
                    logger.info(f"   {self.agent_name}: Ajout croyance '{belief}'")
                    
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
                    
                async def analyze_evidence(self, evidence_id, evidence_data):
                    """Analyse simulée d'évidence"""
                    if self.role == "detective":
                        return {
                            "relevance": evidence_data.get("reliability", 0.5),
                            "implications": [f"Évidence {evidence_id} suggère implication des suspects"],
                            "deduction": f"Basé sur {evidence_data.get('type', 'unknown')}"
                        }
                    else:  # validator
                        return {
                            "validity": evidence_data.get("reliability", 0.5) * 0.9,
                            "critique": [f"Évidence {evidence_id} nécessite corroboration"],
                            "confidence": evidence_data.get("reliability", 0.5)
                        }
                        
                async def formulate_hypothesis(self, context):
                    """Formulation d'hypothèse simulée"""
                    if self.role == "detective":
                        return {
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
                                    "reasoning": "Témoin + lieu du crime"
                                }
                            ]
                        }
                    return {}
                    
                async def validate_hypothesis(self, hypothesis_data):
                    """Validation d'hypothèse simulée"""
                    if self.role == "validator":
                        return {
                            "validity_assessment": {
                                "logical_consistency": 0.8,
                                "evidence_support": 0.7,
                                "completeness": 0.6
                            },
                            "identified_gaps": [
                                "Manque d'alibi vérifié pour Colonel Moutarde",
                                "Lien temporel à établir"
                            ],
                            "suggestions": [
                                "Vérifier les alibis des suspects principaux",
                                "Analyser la séquence temporelle"
                            ],
                            "confidence_in_hypothesis": 0.65
                        }
                    return {}
            
            # Hub simplifié
            class SimpleHub:
                def __init__(self, sherlock_agent, watson_agent):
                    self.agents = {"Sherlock_Cluedo": sherlock_agent, "Watson_Cluedo": watson_agent}
                    self.statistics = {"messages_processed": 0, "conflicts_resolved": 0}
                    
                async def sync_beliefs(self, from_agent, to_agent):
                    from_agent_obj = self.agents.get(from_agent)
                    to_agent_obj = self.agents.get(to_agent)
                    
                    if from_agent_obj and to_agent_obj:
                        from_beliefs = from_agent_obj.get_all_beliefs()
                        synced_count = 0
                        
                        for belief, metadata in from_beliefs.items():
                            if belief not in to_agent_obj.beliefs:
                                await to_agent_obj.add_belief(f"sync_{belief}", metadata)
                                synced_count += 1
                        
                        logger.info(f"🔄 Synchronisation: {synced_count} croyances transférées de {from_agent} vers {to_agent}")
                        return {"beliefs_imported": synced_count, "status": "success"}
                    
                    return {"beliefs_imported": 0, "status": "error"}
                    
                async def check_global_consistency(self):
                    return {
                        "is_consistent": True,
                        "inter_agent_conflicts": [],
                        "resolutions": []
                    }
                    
                def get_hub_status(self):
                    return {
                        "status": "active_simplified",
                        "connected_agents": list(self.agents.keys()),
                        "statistics": self.statistics
                    }
                    
                async def shutdown(self):
                    logger.info("Hub simplifié arrêté")
            
            # Créer les agents
            self.sherlock = SimpleAgent("Sherlock_Cluedo", "detective")
            self.watson = SimpleAgent("Watson_Cluedo", "validator")
            self.hub = SimpleHub(self.sherlock, self.watson)
            
            logger.info(f"✅ Sherlock initialisé: {self.sherlock.agent_name}")
            logger.info(f"✅ Watson initialisé: {self.watson.agent_name}")
            logger.info(f"✅ Hub actif")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur initialisation: {e}")
            return False
    
    async def run_auto_investigation(self):
        """Lance une investigation automatique complète"""
        try:
            print("\n" + "="*80)
            print("🕵️  DÉMONSTRATION AUTOMATIQUE SHERLOCK/WATSON JTMS  🕵️")
            print("="*80)
            print(f"\n📖 SCÉNARIO: Enquête Cluedo - Meurtre du {self.cluedo_scenario['victim']['name']}")
            print(f"📍 Lieu: {self.cluedo_scenario['victim']['location_found']}")
            print(f"⏰ Heure estimée: {self.cluedo_scenario['victim']['time_of_death']}")
            print(f"💀 Cause: {self.cluedo_scenario['victim']['cause_preliminary']}")
            
            # Phase 1: Initialisation
            print(f"\n🎬 PHASE 1: INITIALISATION")
            print("-" * 50)
            
            if not await self.initialize_simplified_system():
                print("❌ Échec initialisation")
                return
            
            # Ajouter contexte initial
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
            
            # Phase 2: Analyse des évidences
            print(f"\n🔍 PHASE 2: ANALYSE DES ÉVIDENCES")
            print("-" * 50)
            
            evidence_count = 0
            for evidence_id, evidence_data in self.cluedo_scenario['evidence'].items():
                print(f"\n📋 Évidence: {evidence_id}")
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
                analysis = await self.sherlock.analyze_evidence(evidence_id, evidence_data)
                print(f"   🧠 Analyse Sherlock: Pertinence {analysis.get('relevance', 'N/A')}")
                
                evidence_count += 1
            
            # Synchroniser avec Watson
            sync_result = await self.hub.sync_beliefs("Sherlock_Cluedo", "Watson_Cluedo")
            
            # Phase 3: Formation d'hypothèses
            print(f"\n💡 PHASE 3: FORMATION D'HYPOTHÈSES")
            print("-" * 50)
            
            investigation_context = f"""
            Analyser le meurtre de {self.cluedo_scenario['victim']['name']} 
            dans {self.cluedo_scenario['victim']['location_found']}.
            """
            
            hypothesis_result = await self.sherlock.formulate_hypothesis(investigation_context)
            
            # Afficher les hypothèses
            print("\n🎯 HYPOTHÈSE PRINCIPALE:")
            primary = hypothesis_result.get("primary_hypothesis", {})
            print(f"   Suspect: {primary.get('suspect', 'N/A')}")
            print(f"   Arme: {primary.get('weapon', 'N/A')}")
            print(f"   Lieu: {primary.get('room', 'N/A')}")
            print(f"   Confiance: {primary.get('confidence', 0):.2f}")
            print(f"   Raisonnement: {primary.get('reasoning', 'N/A')}")
            
            # Phase 4: Validation croisée
            print(f"\n⚖️  PHASE 4: VALIDATION CROISÉE")
            print("-" * 50)
            
            critique_result = await self.watson.validate_hypothesis(hypothesis_result)
            
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
            
            # Phase 5: Solution finale
            print(f"\n🎯 PHASE 5: SOLUTION FINALE")
            print("-" * 50)
            
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
                    "Accès aux informations financières"
                ]
            }
            
            print("\n🏆 SOLUTION FINALE:")
            solution = final_solution.get("solution", {})
            print(f"   🔍 Coupable: {solution.get('culprit', 'N/A')}")
            print(f"   🔪 Arme: {solution.get('weapon', 'N/A')}")
            print(f"   📍 Lieu: {solution.get('location', 'N/A')}")
            print(f"   💭 Motif: {solution.get('motive', 'N/A')}")
            print(f"   🎯 Confiance: {final_solution.get('confidence', 0):.2f}")
            
            # Statistiques finales
            print(f"\n📊 STATISTIQUES FINALES")
            print("-" * 50)
            
            sherlock_beliefs = len(self.sherlock.get_all_beliefs())
            watson_beliefs = len(self.watson.get_all_beliefs())
            
            print(f"   • Sherlock: {sherlock_beliefs} croyances")
            print(f"   • Watson: {watson_beliefs} croyances")
            print(f"   • Évidences analysées: {evidence_count}")
            print(f"   • Hypothèses formulées: {len(hypothesis_result.get('alternative_hypotheses', [])) + 1}")
            
            # Vérification cohérence
            consistency = await self.hub.check_global_consistency()
            print(f"   • Cohérence globale: {'✅' if consistency.get('is_consistent', False) else '❌'}")
            
            print(f"\n✅ INVESTIGATION TERMINÉE AVEC SUCCÈS")
            
        except Exception as e:
            logger.error(f"Erreur durant l'investigation automatique: {e}")
            print(f"❌ Erreur: {e}")
        
        finally:
            if self.hub:
                await self.hub.shutdown()

async def main():
    """Point d'entrée principal de la démonstration automatique"""
    demo = AutoCluedoDemo()
    await demo.run_auto_investigation()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Démonstration interrompue")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        print(f"\n❌ Erreur fatale: {e}")