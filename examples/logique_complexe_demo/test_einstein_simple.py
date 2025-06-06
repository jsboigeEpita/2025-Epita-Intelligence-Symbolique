#!/usr/bin/env python3
# examples/logique_complexe_demo/test_einstein_simple.py

"""
Version simplifiée de test pour l'énigme d'Einstein complexe.
Sans emojis pour éviter les problèmes d'encodage Unicode.
"""

import asyncio
import logging
import sys
import os

# Ajout du chemin du projet pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.agents import ChatCompletionAgent

# Import des composants spécialisés pour l'énigme complexe
from argumentation_analysis.orchestration.logique_complexe_orchestrator import LogiqueComplexeOrchestrator
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent, SherlockTools
from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant

def setup_logging():
    """Configuration du logging pour la démonstration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    logger = logging.getLogger(__name__)
    logger.info("Logging configuré avec le niveau INFO.")
    return logger

async def main():
    """Fonction principale de test de l'énigme d'Einstein complexe."""
    
    logger = setup_logging()
    
    print("[ENIGME] Lancement du test de l'ÉNIGME D'EINSTEIN COMPLEXE...")
    print("[FORCE] Cette énigme FORCE l'utilisation de TweetyProject par Watson!")
    print("[REQUIS] Minimum: 10 clauses logiques + 5 requêtes pour validation")
    print("")
    
    try:
        # Configuration du kernel Semantic Kernel
        kernel = Kernel()
        
        # Configuration du service LLM (OpenAI ou compatible)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("[ERREUR] OPENAI_API_KEY non définie. Impossible de continuer.")
            print("[ERREUR] Variable d'environnement OPENAI_API_KEY manquante!")
            return {"success": False, "error": "API_KEY_MISSING"}
        
        # Service de chat
        chat_service = OpenAIChatCompletion(
            service_id="openai_chat",
            api_key=api_key,
            ai_model_id="gpt-4"  # Modèle puissant requis pour logique complexe
        )
        kernel.add_service(chat_service)
        
        # Création de l'orchestrateur pour énigme complexe
        logger.info("[ORCHESTRATEUR] Initialisation de l'orchestrateur logique complexe...")
        orchestrateur = LogiqueComplexeOrchestrator(kernel)
        
        # Création des agents spécialisés
        logger.info("[SHERLOCK] Création de l'agent Sherlock (coordinateur logique)...")
        sherlock_tools = SherlockTools(kernel)
        kernel.add_plugin(sherlock_tools, plugin_name="SherlockTools")
        
        sherlock_agent = SherlockEnqueteAgent(
            kernel=kernel,
            agent_name="Sherlock"
        )
        
        logger.info("[WATSON] Création de l'agent Watson (spécialiste TweetyProject)...")
        watson_agent = WatsonLogicAssistant(
            kernel=kernel,
            agent_name="Watson"
        )
        
        # Lancement de la résolution de l'énigme complexe
        logger.info("[RESOLUTION] Début de la résolution de l'énigme d'Einstein complexe...")
        print("")
        print("="*80)
        print("[RESOLUTION] ÉNIGME D'EINSTEIN COMPLEXE EN COURS...")
        print("="*80)
        print("")
        
        resultats = await orchestrateur.resoudre_enigme_complexe(sherlock_agent, watson_agent)
        
        # Affichage des résultats détaillés
        print("")
        print("="*80)
        print("[RESULTATS] RÉSULTATS DE LA RÉSOLUTION COMPLEXE")
        print("="*80)
        
        print(f"[STATUS] Énigme résolue: {'OUI' if resultats['enigme_resolue'] else 'NON'}")
        print(f"[TOURS] Tours utilisés: {resultats['tours_utilises']}/{25}")
        
        progression = resultats['progression_logique']
        print(f"")
        print(f"[PROGRESSION] LOGIQUE FORMELLE:")
        print(f"   [CLAUSES] Formulées: {progression['clauses_formulees']}/10 (minimum)")
        print(f"   [REQUETES] Exécutées: {progression['requetes_executees']}/5 (minimum)")
        print(f"   [CONTRAINTES] Traitées: {progression['contraintes_traitees']}")
        print(f"   [VALIDATION] Logique suffisante: {'OUI' if progression['force_logique_formelle'] else 'NON'}")
        
        # Détails des clauses Watson
        if resultats['clauses_watson']:
            print(f"")
            print(f"[CLAUSES] FORMULATIONS DE WATSON ({len(resultats['clauses_watson'])}):")
            for i, clause in enumerate(resultats['clauses_watson'][:5], 1):  # Top 5
                print(f"   {i}. {clause[:100]}...")
        
        # Détails des requêtes
        if resultats['requetes_executees']:
            print(f"")
            print(f"[REQUETES] TWEETYPROJECT EXECUTEES ({len(resultats['requetes_executees'])}):")
            for i, requete in enumerate(resultats['requetes_executees'][:3], 1):  # Top 3
                print(f"   {i}. {requete['requete'][:80]}...")
        
        # Statistiques finales de logique
        stats_logique = orchestrateur.obtenir_statistiques_logique()
        print(f"")
        print(f"[STATS] STATISTIQUES LOGIQUE FINALE:")
        print(f"   [ID] Session: {stats_logique['state_id'][:8]}...")
        print(f"   [DEDUCTIONS] Détaillées: {len(stats_logique['clauses_detaillees'])}")
        print(f"   [SOLUTIONS] Partielles: {len(stats_logique['solution_partielle'])}/5 maisons")
        
        # Message de conclusion
        print("")
        if resultats['enigme_resolue']:
            print(f"[SUCCES] L'énigme d'Einstein a été résolue avec la logique formelle!")
            print(f"[VALIDATION] Watson a utilisé TweetyProject de manière complète.")
        else:
            print(f"[ECHEC] L'énigme n'a pas été résolue selon les critères de logique formelle.")
            print(f"[INSUFFISANT] Watson doit utiliser davantage TweetyProject.")
        
        print("")
        print("="*80)
        print("[FIN] Test terminé.")
        
        return {
            "success": True,
            "resultats": resultats,
            "stats": stats_logique
        }
        
    except Exception as e:
        logger.error(f"[ERREUR] Erreur lors du test: {e}", exc_info=True)
        print(f"[ERREUR] Exception: {e}")
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    """Point d'entrée du script de test."""
    try:
        resultats = asyncio.run(main())
        
        if resultats and resultats.get('success', False) and resultats.get('resultats', {}).get('enigme_resolue', False):
            print("[EXIT] Test réussi - Logique formelle utilisée avec succès!")
            sys.exit(0)  # Succès
        else:
            print("[EXIT] Test échoué - Logique formelle insuffisante.")
            sys.exit(1)  # Échec
            
    except KeyboardInterrupt:
        print("")
        print("[INTERRUPT] Test interrompu par l'utilisateur.")
        sys.exit(130)
    except Exception as e:
        print(f"[FATAL] Erreur fatale: {e}")
        sys.exit(1)