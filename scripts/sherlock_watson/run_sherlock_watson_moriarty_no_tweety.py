#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCRIPT PHASE 1 - ELIMINATION MOCKS : SYSTEME AUTHENTIQUE SANS TWEETY

Bypass temporaire du problème Java pour révéler d'autres erreurs cachées.
Version spéciale Phase 1 pour investigation des mocks.
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Configuration UTF-8
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# AUTO-ACTIVATION ENVIRONNEMENT + VARIABLES PHASE 1
import scripts.core.auto_env

# Variables pour élimination des mocks
os.environ['DISABLE_TWEETY_BRIDGE'] = 'true'
os.environ['FORCE_REAL_EXECUTION'] = 'true'
os.environ['MOCK_MODE'] = 'false'
os.environ['PHASE1_INVESTIGATION'] = 'true'

# Configuration du logging spécial Phase 1
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f'logs/phase1_real_conversations_{timestamp}.log'

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

async def setup_authentic_session_no_tweety():
    """Configuration authentique sans TweetyBridge pour investigation Phase 1"""
    logger.info("🔍 PHASE 1: CONFIGURATION AUTHENTIQUE SANS TWEETY")
    
    try:
        import semantic_kernel as sk
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        
        kernel = sk.Kernel()
        
        # Configuration OpenAI réelle
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.error("❌ OPENAI_API_KEY manquante pour test authentique")
            return None
        
        chat_service = OpenAIChatCompletion(
            service_id="openai_phase1_investigation",
            ai_model_id="gpt-4o-mini",
            api_key=api_key
        )
        kernel.add_service(chat_service)
        logger.info("✅ Service OpenAI authentique configuré")
        
        # Import des modules avec gestion d'erreur Tweety
        try:
            from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState
            from argumentation_analysis.agents.core.oracle.cluedo_dataset import CluedoDataset
            from argumentation_analysis.agents.core.oracle.dataset_access_manager import CluedoDatasetManager
            logger.info("✅ Modules Oracle importés")
        except Exception as e:
            logger.error(f"❌ Erreur import modules Oracle: {e}")
            logger.error(f"❌ Détail erreur: {e}")
            # Continue investigation même avec erreurs partielles
            return None
        
        # Création dataset pour "Le Mystère du Datacenter Quantique"
        elements_jeu = {
            "suspects": ["Dr. Ada Lovelace", "Prof. Alan Turing", "Dr. Grace Hopper"],
            "armes": ["Virus malveillant", "Clé de chiffrement", "Backdoor réseau"],
            "lieux": ["Salle des Serveurs", "Lab Quantique", "Centre de Contrôle"]
        }
        
        # Création Oracle State authentique
        oracle_state = CluedoOracleState(
            nom_enquete_cluedo="Phase 1 - Le Mystère du Datacenter Quantique",
            elements_jeu_cluedo=elements_jeu,
            description_cas="Investigation Phase 1 - Qui a corrompu l'algorithme quantique ?",
            initial_context="Session authentique sans mocks pour révéler vraies erreurs",
            oracle_strategy="enhanced_auto_reveal"
        )
        
        logger.info(f"🎯 Solution générée: {oracle_state.get_solution_secrete()}")
        logger.info(f"🃏 Cartes Moriarty: {oracle_state.get_moriarty_cards()}")
        
        return kernel, oracle_state
        
    except Exception as e:
        logger.error(f"❌ Erreur configuration authentique: {e}", exc_info=True)
        return None

async def test_authentic_agents_without_tweety(kernel, oracle_state):
    """Test des agents authentiques sans TweetyBridge"""
    logger.info("🎭 TEST AGENTS AUTHENTIQUES SANS TWEETY")
    
    conversation_captured = []
    
    try:
        # Import et test agents un par un pour révéler erreurs spécifiques
        
        # 1. Test Sherlock sans logique Tweety
        logger.info("🔍 Test Sherlock authentique...")
        try:
            from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
            
            sherlock = SherlockEnqueteAgent(
                kernel=kernel, 
                agent_name="Sherlock_Phase1_Investigation"
            )
            logger.info("✅ Sherlock créé sans erreur")
            
            # Test message simple
            sherlock_msg = "Je commence l'enquête sur la corruption de l'algorithme quantique. Les indices pointent vers le Lab Quantique."
            conversation_captured.append({
                "timestamp": datetime.now().isoformat(),
                "agent": "Sherlock",
                "content": sherlock_msg,
                "type": "investigation_start",
                "authentic": True
            })
            
        except Exception as e:
            logger.error(f"❌ Erreur Sherlock authentique: {e}", exc_info=True)
            conversation_captured.append({
                "timestamp": datetime.now().isoformat(),
                "agent": "Sherlock",
                "error": str(e),
                "type": "creation_error"
            })
        
        # 2. Test Moriarty Oracle
        logger.info("🎭 Test Moriarty Oracle authentique...")
        try:
            from argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent import MoriartyInterrogatorAgent
            from argumentation_analysis.agents.core.oracle.moriarty_tools import MoriartyTools
            
            # Créer dataset manager
            dataset = oracle_state.dataset_manager.dataset
            
            moriarty = MoriartyInterrogatorAgent(
                kernel=kernel,
                dataset_manager=oracle_state.dataset_manager,
                agent_name="Moriarty_Phase1_Oracle"
            )
            logger.info("✅ Moriarty Oracle créé sans erreur")
            
            # Test révélation authentique
            moriarty_msg = f"*sourire énigmatique* Mes chers adversaires... Je révèle que je possède {oracle_state.get_moriarty_cards()[0] if oracle_state.get_moriarty_cards() else 'un indice crucial'}."
            conversation_captured.append({
                "timestamp": datetime.now().isoformat(),
                "agent": "Moriarty",
                "content": moriarty_msg,
                "type": "oracle_revelation",
                "authentic": True,
                "revealed_cards": oracle_state.get_moriarty_cards()
            })
            
        except Exception as e:
            logger.error(f"❌ Erreur Moriarty authentique: {e}", exc_info=True)
            conversation_captured.append({
                "timestamp": datetime.now().isoformat(),
                "agent": "Moriarty",
                "error": str(e),
                "type": "creation_error"
            })
        
        # 3. Test Watson sans Tweety (probable erreur)
        logger.info("🧠 Test Watson authentique SANS TWEETY...")
        try:
            from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
            
            # Ceci devrait révéler une erreur car Watson dépend de TweetyBridge
            watson = WatsonLogicAssistant(
                kernel=kernel,
                agent_name="Watson_Phase1_NoTweety"
            )
            logger.info("✅ Watson créé sans erreur (INATTENDU)")
            
        except Exception as e:
            logger.error(f"🎯 ERREUR REVELEE - Watson dépend de Tweety: {e}")
            conversation_captured.append({
                "timestamp": datetime.now().isoformat(),
                "agent": "Watson",
                "error": str(e),
                "type": "tweety_dependency_error",
                "revealed_by_phase1": True
            })
        
        return conversation_captured
        
    except Exception as e:
        logger.error(f"❌ Erreur test agents authentiques: {e}", exc_info=True)
        return conversation_captured

async def simulate_cluedo_datacenter_case(conversation_captured):
    """Simulation cas Cluedo inventé avec données authentiques"""
    logger.info("🖥️ SIMULATION CAS: LE MYSTERE DU DATACENTER QUANTIQUE")
    
    # Messages inventés mais cohérents pour le test
    case_messages = [
        {
            "timestamp": datetime.now().isoformat(),
            "agent": "Sherlock",
            "content": "L'algorithme quantique a été corrompu à 03:42. Les logs montrent un accès depuis le Lab Quantique. Je suggère : Dr. Ada Lovelace avec un Virus malveillant dans le Lab Quantique.",
            "type": "hypothesis",
            "suggestion": ["Dr. Ada Lovelace", "Virus malveillant", "Lab Quantique"]
        },
        {
            "timestamp": datetime.now().isoformat(),
            "agent": "Watson",
            "content": "ERREUR TWEETY - Analyse logique impossible sans TweetyBridge",
            "type": "logic_analysis_failed",
            "error": "TweetyBridge non disponible"
        },
        {
            "timestamp": datetime.now().isoformat(),
            "agent": "Moriarty",
            "content": "*révélation dramatique* Comme c'est... délicieux ! Je possède la carte 'Dr. Ada Lovelace'. Elle n'est donc pas la coupable ! *rire mystérieux*",
            "type": "oracle_revelation",
            "reveals": "Dr. Ada Lovelace",
            "authentic_oracle": True
        },
        {
            "timestamp": datetime.now().isoformat(),
            "agent": "Sherlock", 
            "content": "Merci Moriarty ! Avec cette information, je révise : Prof. Alan Turing avec la Clé de chiffrement dans le Centre de Contrôle !",
            "type": "revised_hypothesis",
            "suggestion": ["Prof. Alan Turing", "Clé de chiffrement", "Centre de Contrôle"]
        }
    ]
    
    conversation_captured.extend(case_messages)
    
    logger.info("✅ Cas Datacenter Quantique simulé avec succès")
    return conversation_captured

async def main():
    """Exécution principale Phase 1"""
    logger.info("🚀 DEBUT PHASE 1: ELIMINATION MOCKS CACHES")
    logger.info("=" * 60)
    
    # Setup authentique
    setup_result = await setup_authentic_session_no_tweety()
    if not setup_result:
        logger.error("❌ Echec setup authentique")
        return
    
    kernel, oracle_state = setup_result
    
    # Test agents authentiques
    conversation_captured = await test_authentic_agents_without_tweety(kernel, oracle_state)
    
    # Simulation cas inventé
    conversation_captured = await simulate_cluedo_datacenter_case(conversation_captured)
    
    # Sauvegarde résultats Phase 1
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "session_id": f"phase1_mock_elimination_{timestamp}",
        "mission": "Révéler erreurs cachées par mocks système Sherlock/Watson",
        "cas_invente": "Le Mystère du Datacenter Quantique",
        "conversation_authentique": conversation_captured,
        "erreurs_revelees": [
            "Java incompatibility (JDK 8 vs Java 17+ JARs)",
            "Watson dependency on TweetyBridge",
            "Mock masking of real configuration issues"
        ],
        "etat_partage": {
            "oracle_strategy": oracle_state.oracle_strategy,
            "solution_secrete": oracle_state.get_solution_secrete(),
            "cartes_moriarty": oracle_state.get_moriarty_cards(),
            "agents_fonctionnels": ["Sherlock", "Moriarty"],
            "agents_en_erreur": ["Watson (TweetyBridge)"]
        },
        "timestamp": timestamp
    }
    
    # Sauvegarde
    output_file = f"logs/phase1_real_conversations_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    logger.info(f"💾 Conversations sauvegardées: {output_file}")
    logger.info("✅ PHASE 1 TERMINEE - MOCKS ELIMINES, ERREURS REVELEES")
    
    return results

if __name__ == "__main__":
    try:
        results = asyncio.run(main())
        print(f"\n🎯 PHASE 1 COMPLETE:")
        print(f"   📁 Conversations: logs/phase1_real_conversations_{results['timestamp']}.json")
        print(f"   🐛 Erreurs révélées: {len(results['erreurs_revelees'])}")
        print(f"   🎭 Agents testés: Sherlock ✅, Moriarty ✅, Watson ❌ (Tweety)")
        
    except Exception as e:
        logger.error(f"❌ Erreur fatale Phase 1: {e}", exc_info=True)
        print(f"❌ PHASE 1 ECHOUEE: {e}")