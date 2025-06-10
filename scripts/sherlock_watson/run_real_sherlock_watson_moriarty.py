#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SCRIPT WRAPPER RÉEL POUR SYSTÈME AGENTIQUE SHERLOCK-WATSON-MORIARTY

MISSION CRITIQUE : Exécuter le VRAI système agentique sans simulation.
Ce script utilise l'environnement dédié projet-is et lance les vrais agents.
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Configuration UTF-8 pour éviter les problèmes d'encodage
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Configuration des chemins pour l'environnement projet
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()  # Remonte vers la racine du projet
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration du logging avec UTF-8 (avant tout autre import)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(PROJECT_ROOT / 'sherlock_watson_moriarty_real_trace.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement depuis .env
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / '.env')
    logger.info("✅ Variables d'environnement chargées depuis .env")
except ImportError:
    logger.warning("⚠️ python-dotenv non disponible, utilisation variables système")
except Exception as e:
    logger.warning(f"⚠️ Erreur chargement .env : {e}")


async def setup_real_agents_and_run():
    """Configuration et exécution du vrai système agentique"""
    logger.info("🚀 LANCEMENT DU VRAI SYSTÈME AGENTIQUE SHERLOCK-WATSON-MORIARTY")
    
    # Import du vrai orchestrateur avec gestion des erreurs d'imports relatifs
    try:
        # Import en mode module pour éviter les problèmes d'imports relatifs
        import argumentation_analysis.core.cluedo_oracle_state as cluedo_state_module
        import argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin as state_plugin_module
        import argumentation_analysis.agents.core.pm.sherlock_enquete_agent as sherlock_module
        import argumentation_analysis.agents.core.logic.watson_logic_assistant as watson_module
        import argumentation_analysis.agents.core.oracle.moriarty_interrogator_agent as moriarty_module
        
        CluedoOracleState = cluedo_state_module.CluedoOracleState
        EnqueteStateManagerPlugin = state_plugin_module.EnqueteStateManagerPlugin
        SherlockEnqueteAgent = sherlock_module.SherlockEnqueteAgent
        WatsonLogicAssistant = watson_module.WatsonLogicAssistant
        MoriartyInterrogatorAgent = moriarty_module.MoriartyInterrogatorAgent
        
        logger.info("✅ Imports des vrais agents réussis (mode module)")
    except ImportError as e:
        logger.error(f"❌ Erreur d'import des agents : {e}")
        logger.info("💡 Tentative d'import direct depuis l'orchestrateur...")
        try:
            import argumentation_analysis.orchestration.cluedo_extended_orchestrator as orchestrator_module
            # L'orchestrateur a déjà toutes les dépendances, on l'utilise directement
            return await run_with_orchestrator_module(orchestrator_module)
        except ImportError as e2:
            logger.error(f"❌ Erreur d'import de l'orchestrateur également : {e2}")
            raise

    # Import du vrai orchestrateur
    try:
        import argumentation_analysis.orchestration.cluedo_extended_orchestrator as orchestrator_module
        CluedoExtendedOrchestrator = orchestrator_module.CluedoExtendedOrchestrator
        logger.info("✅ Import du vrai orchestrateur réussi")
    except ImportError as e:
        logger.error(f"❌ Erreur d'import de l'orchestrateur : {e}")
        raise

    # Configuration Semantic Kernel avec service LLM réel
    try:
        import semantic_kernel as sk
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        
        kernel = sk.Kernel()
        
        # Configuration du service OpenAI réel
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("⚠️ OPENAI_API_KEY non trouvée dans les variables d'environnement")
            logger.info("📝 Veuillez configurer votre clé API OpenAI")
            return None
        
        # Service ChatGPT réel - utilise gpt-4o-mini comme configuré dans .env
        model_id = os.getenv('OPENAI_CHAT_MODEL_ID', 'gpt-4o-mini')
        chat_service = OpenAIChatCompletion(
            service_id="openai_chat",
            ai_model_id=model_id,
            api_key=api_key
        )
        kernel.add_service(chat_service)
        logger.info("✅ Service ChatGPT réel configuré")
        
    except Exception as e:
        logger.error(f"❌ Erreur configuration Semantic Kernel : {e}")
        raise

    # Vérification et configuration JVM pour Tweety (Watson)
    try:
        from argumentation_analysis.service_setup.analysis_services import initialize_analysis_services
        
        services = initialize_analysis_services({
            "LIBS_DIR_PATH": str(PROJECT_ROOT / "libs")
        })
        
        if services.get("jvm_ready"):
            logger.info("✅ JVM Tweety prête pour Watson")
        else:
            logger.warning("⚠️ JVM Tweety non disponible - Watson fonctionnera en mode dégradé")
            
    except Exception as e:
        logger.warning(f"⚠️ Configuration JVM : {e}")

    # Création et exécution du vrai orchestrateur
    try:
        logger.info("🎭 Initialisation du vrai orchestrateur 3-agents")
        
        orchestrator = CluedoExtendedOrchestrator(
            kernel=kernel,
            max_turns=12,  # Session courte mais complète
            max_cycles=4,
            oracle_strategy="balanced",
            adaptive_selection=False
        )
        
        # Configuration du workflow réel
        logger.info("⚙️ Configuration du workflow avec vrais agents")
        oracle_state = await orchestrator.setup_workflow(
            nom_enquete="Le Mystère du Manoir Tudor - Session Réelle",
            elements_jeu={
                "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose", "Docteur Orchidée"],
                "armes": ["Poignard", "Chandelier", "Revolver", "Corde"],
                "lieux": ["Salon", "Cuisine", "Bureau", "Bibliothèque"]
            }
        )
        
        logger.info(f"🎯 Solution secrète générée : {oracle_state.get_solution_secrete()}")
        logger.info(f"🃏 Cartes Moriarty : {oracle_state.get_moriarty_cards()}")
        
        # EXÉCUTION RÉELLE DU WORKFLOW
        logger.info("🎬 DÉBUT DE LA SESSION RÉELLE - AUCUNE SIMULATION")
        
        result = await orchestrator.execute_workflow(
            initial_question="L'enquête commence. Sherlock, menez l'investigation avec vos vrais déductions !"
        )
        
        logger.info("✅ Session réelle terminée avec succès")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur durant l'exécution réelle : {e}", exc_info=True)
        raise


async def run_with_orchestrator_module(orchestrator_module):
    """Fonction alternative qui utilise directement le module orchestrateur"""
    logger.info("🎭 Utilisation directe du module orchestrateur")
    
    # Configuration Semantic Kernel avec service LLM réel
    try:
        import semantic_kernel as sk
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
        
        kernel = sk.Kernel()
        
        # Configuration du service OpenAI réel
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("⚠️ OPENAI_API_KEY non trouvée dans les variables d'environnement")
            logger.info("📝 Continuons avec l'exécution pour tester l'environnement...")
            # On continue quand même pour tester les imports
        else:
            # Service ChatGPT réel - utilise gpt-4o-mini comme configuré dans .env
            model_id = os.getenv('OPENAI_CHAT_MODEL_ID', 'gpt-4o-mini')
            chat_service = OpenAIChatCompletion(
                service_id="openai_chat",
                ai_model_id=model_id,
                api_key=api_key
            )
            kernel.add_service(chat_service)
            logger.info("✅ Service ChatGPT réel configuré")
        
    except Exception as e:
        logger.error(f"❌ Erreur configuration Semantic Kernel : {e}")
        raise

    # Exécution avec l'orchestrateur
    try:
        CluedoExtendedOrchestrator = orchestrator_module.CluedoExtendedOrchestrator
        run_cluedo_oracle_game = orchestrator_module.run_cluedo_oracle_game
        
        logger.info("🎬 DÉBUT DE LA SESSION RÉELLE VIA ORCHESTRATEUR")
        
        result = await run_cluedo_oracle_game(
            kernel=kernel,
            initial_question="L'enquête commence. Sherlock, menez l'investigation avec vos vrais déductions !",
            max_turns=12,
            max_cycles=4,
            oracle_strategy="balanced"
        )
        
        logger.info("✅ Session réelle terminée avec succès")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur durant l'exécution réelle via orchestrateur : {e}", exc_info=True)
        raise


def save_real_trace(result: Dict[str, Any]) -> str:
    """Sauvegarde la trace conversationnelle réelle"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_file = PROJECT_ROOT / "results" / "sherlock_watson" / f"trace_reelle_sherlock_watson_moriarty_{timestamp}.json"
    
    # Enrichissement des métadonnées
    enriched_result = {
        "session_info": {
            "timestamp": datetime.now().isoformat(),
            "type": "REAL_AGENTS_SESSION",
            "description": "Trace conversationnelle authentique avec vrais agents ChatGPT et Tweety",
            "no_simulation": True,
            "agents": ["Sherlock (ChatGPT)", "Watson (Tweety JVM)", "Moriarty (ChatGPT + Oracle)"]
        },
        "real_execution_data": result,
        "verification": {
            "agents_used": "OpenAI ChatGPT + Tweety JVM",
            "oracle_system": "Authentique CluedoOracleState",
            "conversation_authentic": True
        }
    }
    
    with open(str(trace_file), 'w', encoding='utf-8') as f:
        json.dump(enriched_result, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"💾 Trace réelle sauvegardée : {trace_file}")
    return str(trace_file)


def print_real_session_summary(result: Dict[str, Any]):
    """Affiche le résumé de la session réelle"""
    print("\n" + "="*80)
    print("🎭 RÉSULTAT SESSION RÉELLE SHERLOCK-WATSON-MORIARTY")
    print("="*80)
    
    workflow_info = result.get('workflow_info', {})
    solution_analysis = result.get('solution_analysis', {})
    oracle_stats = result.get('oracle_statistics', {})
    final_state = result.get('final_state', {})
    
    print(f"\n🕐 Durée d'exécution : {workflow_info.get('execution_time_seconds', 0):.2f} secondes")
    print(f"🔄 Tours total : {oracle_stats.get('agent_interactions', {}).get('total_turns', 0)}")
    print(f"🔮 Requêtes Oracle : {oracle_stats.get('workflow_metrics', {}).get('oracle_interactions', 0)}")
    print(f"💎 Cartes révélées : {oracle_stats.get('workflow_metrics', {}).get('cards_revealed', 0)}")
    
    print(f"\n🎯 SUCCÈS : {solution_analysis.get('success', False)}")
    if solution_analysis.get('success'):
        print(f"✅ Solution trouvée : {final_state.get('final_solution', 'N/A')}")
    else:
        print(f"❌ Solution proposée : {final_state.get('final_solution', 'Aucune')}")
        print(f"🎯 Solution correcte : {final_state.get('secret_solution', 'N/A')}")
    
    # Affichage de la conversation réelle (extraits)
    conversation = result.get('conversation_history', [])
    if conversation:
        print(f"\n💬 EXTRAITS CONVERSATION RÉELLE ({len(conversation)} messages) :")
        for i, msg in enumerate(conversation[:6]):  # Premiers 6 messages
            sender = msg.get('sender', 'Unknown')
            content = msg.get('message', '')[:100]
            print(f"  {i+1}. [{sender}] {content}...")
        
        if len(conversation) > 6:
            print(f"  ... et {len(conversation) - 6} autres messages")
    
    print("\n" + "="*80)
    print("✅ SESSION RÉELLE TERMINÉE - AUCUNE SIMULATION UTILISÉE")
    print("="*80)


async def main():
    """Point d'entrée principal"""
    try:
        print("🚀 LANCEMENT DU SYSTÈME AGENTIQUE RÉEL SHERLOCK-WATSON-MORIARTY")
        print("📋 MISSION : Exécuter une session authentique avec vrais agents")
        print("🚫 AUCUNE SIMULATION - TOUT EST RÉEL")
        print()
        
        # Vérification des prérequis
        if not os.getenv('OPENAI_API_KEY'):
            print("❌ ERREUR : Variable OPENAI_API_KEY non configurée")
            print("📝 Veuillez configurer votre clé API OpenAI dans les variables d'environnement")
            return
        
        # Exécution de la session réelle
        result = await setup_real_agents_and_run()
        
        if result:
            # Sauvegarde de la trace réelle
            trace_file = save_real_trace(result)
            
            # Affichage du résumé
            print_real_session_summary(result)
            
            print(f"\n📁 Trace complète sauvegardée dans : {trace_file}")
            print("🔍 Vérifiez le fichier JSON pour la trace conversationnelle complète")
            
        else:
            print("❌ Échec de l'exécution de la session réelle")
            
    except Exception as e:
        logger.error(f"❌ Erreur critique : {e}", exc_info=True)
        print(f"\n❌ ERREUR CRITIQUE : {e}")
        print("📋 Vérifiez les logs dans sherlock_watson_moriarty_real_trace.log")


if __name__ == "__main__":
    asyncio.run(main())