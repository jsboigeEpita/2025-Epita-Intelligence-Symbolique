#!/usr/bin/env python3
# examples/logique_complexe_demo/demo_einstein_workflow.py

"""
Démonstration du workflow de résolution de l'énigme d'Einstein complexe.
Cette énigme FORCE l'utilisation de la logique formelle TweetyProject par Watson.

Contrairement au Cluedo simple, cette énigme:
- Nécessite 10+ clauses logiques formulées
- Require 5+ requêtes TweetyProject exécutées  
- Est impossible à résoudre par raisonnement informel seul
- Valide la solution uniquement après formalisation complète
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
    """Fonction principale de démonstration de l'énigme d'Einstein complexe."""
    
    logger = setup_logging()
    
    print("🧩 Lancement de la démonstration de l'ÉNIGME D'EINSTEIN COMPLEXE...")
    print("⚠️  Cette énigme FORCE l'utilisation de TweetyProject par Watson!")
    print("📋 Minimum requis: 10 clauses logiques + 5 requêtes pour validation\n")
    
    try:
        # Configuration du kernel Semantic Kernel
        kernel = Kernel()
        
        # Configuration du service LLM (OpenAI ou compatible)
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OPENAI_API_KEY non définie. Impossible de continuer.")
            return
        
        # Service de chat
        chat_service = OpenAIChatCompletion(
            service_id="openai_chat",
            api_key=api_key,
            ai_model_id="gpt-4"  # Modèle plus puissant requis pour logique complexe
        )
        kernel.add_service(chat_service)
        
        # Création de l'orchestrateur pour énigme complexe
        logger.info("🎛️ Initialisation de l'orchestrateur logique complexe...")
        orchestrateur = LogiqueComplexeOrchestrator(kernel)
        
        # Création des agents spécialisés
        logger.info("🕵️ Création de l'agent Sherlock (coordinateur logique)...")
        sherlock_tools = SherlockTools(kernel)
        kernel.add_plugin(sherlock_tools, plugin_name="SherlockTools")
        
        sherlock_agent = SherlockEnqueteAgent(
            kernel=kernel,
            agent_name="Sherlock",
            service_id="openai_chat"
        )
        
        logger.info("🧠 Création de l'agent Watson (spécialiste TweetyProject)...")
        watson_agent = WatsonLogicAssistant(
            kernel=kernel,
            agent_name="Watson",
            service_id="openai_chat"
        )
        
        # Lancement de la résolution de l'énigme complexe
        logger.info("🚀 Début de la résolution de l'énigme d'Einstein complexe...")
        print("\n" + "="*80)
        print("🧩 RÉSOLUTION DE L'ÉNIGME D'EINSTEIN COMPLEXE EN COURS...")
        print("="*80 + "\n")
        
        resultats = await orchestrateur.resoudre_enigme_complexe(sherlock_agent, watson_agent)
        
        # Affichage des résultats détaillés
        print("\n" + "="*80)
        print("📊 RÉSULTATS DE LA RÉSOLUTION COMPLEXE")
        print("="*80)
        
        print(f"🎯 Énigme résolue: {'✅ OUI' if resultats['enigme_resolue'] else '❌ NON'}")
        print(f"🔄 Tours utilisés: {resultats['tours_utilises']}/{25}")
        
        progression = resultats['progression_logique']
        print(f"\n📈 PROGRESSION LOGIQUE:")
        print(f"   📝 Clauses formulées: {progression['clauses_formulees']}/10 (minimum)")
        print(f"   🔍 Requêtes exécutées: {progression['requetes_executees']}/5 (minimum)")
        print(f"   🧮 Contraintes traitées: {progression['contraintes_traitees']}")
        print(f"   ⚡ Logique formelle suffisante: {'✅' if progression['force_logique_formelle'] else '❌'}")
        
        # Détails des clauses Watson
        if resultats['clauses_watson']:
            print(f"\n🧠 CLAUSES LOGIQUES FORMULÉES PAR WATSON ({len(resultats['clauses_watson'])}):")
            for i, clause in enumerate(resultats['clauses_watson'][:5], 1):  # Top 5
                print(f"   {i}. {clause[:100]}...")
        
        # Détails des requêtes
        if resultats['requetes_executees']:
            print(f"\n🔍 REQUÊTES TWEETYPROJECT EXÉCUTÉES ({len(resultats['requetes_executees'])}):")
            for i, requete in enumerate(resultats['requetes_executees'][:3], 1):  # Top 3
                print(f"   {i}. {requete['requete'][:80]}...")
        
        # Statistiques finales de logique
        stats_logique = orchestrateur.obtenir_statistiques_logique()
        print(f"\n📊 STATISTIQUES LOGIQUE FINALE:")
        print(f"   🆔 ID Session: {stats_logique['state_id'][:8]}...")
        print(f"   📝 Déductions détaillées: {len(stats_logique['clauses_detaillees'])}")
        print(f"   🏠 Solutions partielles: {len(stats_logique['solution_partielle'])}/5 maisons")
        
        # Message de conclusion
        if resultats['enigme_resolue']:
            print(f"\n🎉 SUCCÈS! L'énigme d'Einstein a été résolue avec la logique formelle!")
            print(f"✅ Watson a utilisé TweetyProject de manière complète et obligatoire.")
        else:
            print(f"\n⚠️  ÉCHEC: L'énigme n'a pas été résolue selon les critères de logique formelle.")
            print(f"❌ Watson doit utiliser davantage TweetyProject pour valider une solution.")
        
        print("\n" + "="*80)
        print("🏁 Démonstration terminée.")
        
        return resultats
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la démonstration: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    """Point d'entrée du script de démonstration."""
    try:
        resultats = asyncio.run(main())
        
        # Code de sortie selon le succès
        if resultats and resultats.get('enigme_resolue', False):
            sys.exit(0)  # Succès
        else:
            sys.exit(1)  # Échec de résolution
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Démonstration interrompue par l'utilisateur.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Erreur fatale: {e}")
        sys.exit(1)