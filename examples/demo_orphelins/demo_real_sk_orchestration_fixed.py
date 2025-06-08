#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DÉMONSTRATION ORCHESTRATION RÉELLE SEMANTIC KERNEL + GPT-4o-mini (VERSION CORRIGÉE)
===================================================================================
Version corrigée qui force le ProjectManager à suivre le bon processus étape par étape.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Configuration des chemins
current_script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Imports infrastructure existante
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.orchestration.enhanced_pm_analysis_runner import (
    EnhancedProjectManagerOrchestrator
)

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger("RealSKDemoFixed")


async def run_simplified_orchestration_demo(texte_a_analyser: str, llm_service):
    """
    Version simplifiée qui force le bon processus étape par étape.
    """
    try:
        # Création de l'orchestrateur
        orchestrator = EnhancedProjectManagerOrchestrator(llm_service)
        
        print("\n[DEBUG] Démarrage orchestration simplifiée...")
        
        # Configuration complète de l'orchestration
        print("[DEBUG] Configuration de l'orchestration...")
        setup_success = await orchestrator.setup_enhanced_orchestration(texte_a_analyser)
        
        if not setup_success:
            return {"success": False, "error": "Échec configuration orchestration"}
        
        print("[DEBUG] Orchestration configurée avec succès")
        
        print("[DEBUG] Agents configurés, prêts pour l'orchestration")
        
        # Test simple : vérifier que le PM peut consulter l'état
        print("\n[DEBUG] Test consultation état par PM...")
        
        # Obtenir l'agent PM depuis le group_chat
        pm_agent = None
        for agent in orchestrator.group_chat.agents:
            if hasattr(agent, 'name') and agent.name == "ProjectManagerAgent":
                pm_agent = agent
                break
        
        if pm_agent is None:
            raise Exception("ProjectManagerAgent non trouvé dans group_chat.agents")
        
        print(f"[DEBUG] PM agent trouvé: {pm_agent.name}")
        
        # Test direct de l'état manager
        state_manager = orchestrator.state_manager_plugin
        current_state = state_manager.get_current_state_snapshot(summarize=True)
        print(f"[DEBUG] État actuel (summarize=True): {current_state}")
        
        # Maintenant essayons un tour de conversation simple
        print("\n[DEBUG] Démarrage d'un tour de conversation simple...")
        
        # Message initial très simple
        simple_prompt = """ProjectManagerAgent: Veuillez d'abord consulter l'état actuel en appelant StateManager.get_current_state_snapshot(summarize=True), puis définir la première tâche d'analyse."""
        
        # Essayer d'ajouter le message à l'historique
        try:
            # Créer un ChatMessageContent pour l'historique
            from semantic_kernel.contents import ChatMessageContent, AuthorRole
            user_message = ChatMessageContent(
                role=AuthorRole.USER,
                content=simple_prompt
            )
            
            # Ajouter à l'historique du group_chat
            await orchestrator.group_chat.add_chat_message(user_message)
            
            print("[DEBUG] Message initial ajouté à l'historique")
            
            # Exécuter un tour de conversation
            print("[DEBUG] Invocation du ProjectManagerAgent...")
            
            # Invoke the next agent (should be PM) - invoke() returns an async generator
            async for response in orchestrator.group_chat.invoke():
                print(f"[DEBUG] Réponse PM reçue: {response}")
                break  # Juste le premier message pour le test
            
            return {
                "success": True,
                "pm_response": str(response),
                "state_after": state_manager.get_current_state_snapshot(summarize=True)
            }
            
        except Exception as e:
            print(f"[ERROR] Erreur pendant l'exécution: {e}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
        
    except Exception as e:
        print(f"[ERROR] Erreur configuration orchestration: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def main():
    """Point d'entrée principal de la démonstration corrigée."""
    print("=" * 80)
    print("DEMONSTRATION ORCHESTRATION REELLE SK + GPT-4o-mini (VERSION CORRIGÉE)")
    print("=" * 80)
    print()
    
    # Texte d'exemple pour l'analyse
    texte_test = """L'intelligence artificielle va détruire tous les emplois.
C'est évident puisque ChatGPT peut déjà faire le travail de milliers de personnes.
Tout le monde le dit. De plus, si on n'arrête pas maintenant, ce sera trop tard.
Il faut donc interdire l'IA immédiatement, sinon nous serons tous au chômage."""
    
    print("TEXTE A ANALYSER:")
    print(f'"{texte_test}"')
    print()
    
    # Configuration LLM
    print("CONFIGURATION DU SERVICE LLM...")
    try:
        # Essayer d'abord GPT-4o-mini réel
        llm_service = create_llm_service(service_id="demo_real_orchestration_fixed")
        print(f"[OK] Service LLM configure: {llm_service.ai_model_id}")
    except Exception as e:
        print(f"[WARNING] Erreur service LLM reel: {e}")
        print("[INFO] Utilisation du service Mock pour demo...")
        llm_service = create_llm_service(service_id="demo_real_orchestration_fixed", force_mock=True)
        print(f"[OK] Service LLM Mock configure: {llm_service.ai_model_id}")
    
    print()
    print("DEMARRAGE ORCHESTRATION SIMPLIFIÉE...")
    print("   - Test étape par étape du Project Manager")
    print("   - Vérification consultation état")
    print("   - Test processus correct")
    print()
    
    # Lancement de l'orchestration simplifiée
    try:
        result = asyncio.run(run_simplified_orchestration_demo(
            texte_a_analyser=texte_test,
            llm_service=llm_service
        ))
        
        print()
        print("=" * 80)
        print("RESULTATS DE L'ORCHESTRATION SIMPLIFIÉE")
        print("=" * 80)
        
        if result["success"]:
            print("[SUCCESS] TEST SIMPLIFIÉ RÉUSSI")
            print()
            print("RÉPONSE DU PROJECT MANAGER:")
            print(f"   {result.get('pm_response', 'N/A')}")
            print()
            print("ÉTAT FINAL:")
            print(f"   {result.get('state_after', 'N/A')}")
            
        else:
            print("[ERROR] ÉCHEC DU TEST SIMPLIFIÉ")
            print(f"Erreur: {result.get('error', 'Erreur inconnue')}")
    
    except Exception as e:
        print("[ERROR] ERREUR CRITIQUE:")
        print(f"   {e}")
        logger.error("Erreur orchestration", exc_info=True)
    
    print()
    print("=" * 80)
    print("FIN DE LA DEMONSTRATION CORRIGÉE")
    print("=" * 80)


if __name__ == "__main__":
    main()
