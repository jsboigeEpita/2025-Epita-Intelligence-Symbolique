#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour démontrer l'agent de logique modale.
"""

import os
import sys
import logging
import asyncio
from pathlib import Path

# Ajouter la racine du projet au sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Charger les variables d'environnement
from dotenv import load_dotenv, find_dotenv
env_path = find_dotenv(filename=".env", usecwd=True, raise_error_if_not_found=False)
if env_path:
    print(f"Chargement du fichier .env trouvé à: {env_path}")
    load_dotenv(env_path, override=True)
else:
    print("ATTENTION: Fichier .env non trouvé.")

# Imports des modules du projet
import semantic_kernel as sk
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge

def setup_logging():
    """Configure le logging pour le test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    # Réduire la verbosité de certaines bibliothèques
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

async def test_modal_logic_agent():
    """Test complet de l'agent de logique modale."""
    
    logger = logging.getLogger("ModalLogicAgentTest")
    logger.info("=== DÉBUT DU TEST DE L'AGENT DE LOGIQUE MODALE ===")
    
    try:
        # 1. Configuration des services
        logger.info("Étape 1: Configuration des services LLM et du kernel...")
        
        # Créer le service LLM
        llm_service = create_llm_service()
        if not llm_service:
            logger.error("Impossible de créer le service LLM")
            return False
        
        # Créer le kernel Semantic Kernel
        kernel = sk.Kernel()
        kernel.add_service(llm_service)
        logger.info("✓ Services configurés avec succès")
        
        # 2. Initialisation de l'agent
        logger.info("Étape 2: Initialisation de l'agent de logique modale...")
        
        modal_agent = ModalLogicAgent(kernel=kernel, service_id=llm_service.service_id)
        
        # Setup des composants (initialise TweetyBridge)
        try:
            modal_agent.setup_agent_components(llm_service.service_id)
            logger.info("✓ Agent de logique modale initialisé avec succès")
        except Exception as e:
            logger.warning(f"TweetyBridge non disponible: {e}")
            logger.info("Le test continuera en mode dégradé (sans validation Tweety)")
        
        # 3. Test de conversion texte vers ensemble de croyances modales
        logger.info("Étape 3: Test de conversion texte -> ensemble de croyances modales...")
        
        text_examples = [
            "Il pleut nécessairement. Il est possible que Jean travaille.",
            "S'il pleut, alors il est nécessaire que les routes soient mouillées. Il pleut.",
            "Il est possible que Marie soit présente. Si Marie est présente, alors il est nécessaire que la réunion ait lieu."
        ]
        
        for i, text in enumerate(text_examples, 1):
            logger.info(f"\n--- Test {i}: '{text}' ---")
            
            try:
                belief_set, status = await modal_agent.text_to_belief_set(text)
                
                if belief_set:
                    logger.info(f"✓ Conversion réussie: {status}")
                    logger.info(f"Type de logique: {belief_set.logic_type}")
                    logger.info(f"Contenu de l'ensemble de croyances:")
                    for line in belief_set.content.split('\n'):
                        if line.strip():
                            logger.info(f"  {line}")
                    
                    # 4. Test de génération de requêtes
                    logger.info("Test de génération de requêtes...")
                    queries = await modal_agent.generate_queries(text, belief_set)
                    
                    if queries:
                        logger.info(f"✓ {len(queries)} requêtes générées:")
                        for j, query in enumerate(queries, 1):
                            logger.info(f"  Requête {j}: {query}")
                        
                        # 5. Test d'exécution de requêtes (si TweetyBridge est disponible)
                        if hasattr(modal_agent, '_tweety_bridge') and modal_agent.tweety_bridge.is_jvm_ready():
                            logger.info("Test d'exécution des requêtes...")
                            
                            for j, query in enumerate(queries[:3], 1):  # Limiter à 3 requêtes
                                try:
                                    result, raw_output = modal_agent.execute_query(belief_set, query)
                                    result_str = "True" if result else "False" if result is not None else "Unknown"
                                    logger.info(f"  Requête {j}: {query} -> {result_str}")
                                except Exception as e:
                                    logger.warning(f"  Requête {j}: {query} -> Erreur: {e}")
                        else:
                            logger.info("⚠ TweetyBridge non disponible, exécution des requêtes ignorée")
                        
                        # 6. Test d'interprétation des résultats
                        logger.info("Test d'interprétation des résultats...")
                        mock_results = [(True, "ACCEPTED"), (False, "REJECTED"), (None, "UNKNOWN")][:len(queries)]
                        
                        try:
                            interpretation = await modal_agent.interpret_results(
                                text, belief_set, queries, mock_results
                            )
                            logger.info("✓ Interprétation générée:")
                            logger.info(f"  {interpretation[:200]}...")
                        except Exception as e:
                            logger.warning(f"Erreur lors de l'interprétation: {e}")
                    
                    else:
                        logger.warning("✗ Aucune requête générée")
                
                else:
                    logger.error(f"✗ Conversion échouée: {status}")
            
            except Exception as e:
                logger.error(f"✗ Erreur lors du test {i}: {e}", exc_info=True)
        
        # 7. Test des capacités de l'agent
        logger.info("\nÉtape 7: Test des capacités de l'agent...")
        capabilities = modal_agent.get_agent_capabilities()
        logger.info(f"✓ Capacités de l'agent:")
        logger.info(f"  - Nom: {capabilities.get('name')}")
        logger.info(f"  - Type de logique: {capabilities.get('logic_type')}")
        logger.info(f"  - Description: {capabilities.get('description')}")
        logger.info(f"  - Méthodes disponibles: {list(capabilities.get('methods', {}).keys())}")
        
        logger.info("\n=== TEST COMPLETÉ AVEC SUCCÈS ===")
        return True
        
    except Exception as e:
        logger.error(f"Erreur critique lors du test: {e}", exc_info=True)
        return False

def main():
    """Point d'entrée principal."""
    setup_logging()
    
    logger = logging.getLogger("ModalLogicAgentTest.Main")
    logger.info("Démarrage du test de l'agent de logique modale...")
    
    try:
        # Vérifier la configuration LLM
        if not os.getenv("OPENAI_API_KEY") and not os.getenv("AZURE_OPENAI_API_KEY"):
            logger.error("Configuration LLM manquante. Veuillez configurer OPENAI_API_KEY ou AZURE_OPENAI_API_KEY.")
            return 1
        
        # Exécuter le test
        success = asyncio.run(test_modal_logic_agent())
        
        if success:
            logger.info("✓ Test terminé avec succès")
            return 0
        else:
            logger.error("✗ Test échoué")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Test interrompu par l'utilisateur")
        return 1
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())