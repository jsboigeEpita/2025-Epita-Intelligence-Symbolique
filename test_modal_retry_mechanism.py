#!/usr/bin/env python3
"""
Script de test pour démontrer le mécanisme de retry automatique corrigé
pour les erreurs de syntaxe TweetyProject dans ModalLogicAgent.

Ce script compare le comportement de l'agent original vs l'agent corrigé.
"""

import asyncio
import logging
import sys
import traceback
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

# Configuration du logging pour voir les tentatives de retry
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_original_agent_behavior():
    """Test avec l'agent original (sans retry automatique)."""
    logger.info("=" * 80)
    logger.info("TEST 1: Agent Modal Logic ORIGINAL (sans retry automatique)")
    logger.info("=" * 80)
    
    try:
        # Initialiser le kernel
        kernel = Kernel()
        
        # Configurer le service LLM (remplacez par votre configuration)
        service_id = "openai"
        kernel.add_service(
            OpenAIChatCompletion(
                service_id=service_id,
                ai_model_id="gpt-4",
                api_key="your-api-key-here"  # Remplacez par votre clé API
            )
        )
        
        # Importer et initialiser l'agent original
        from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
        
        agent = ModalLogicAgent(kernel, "TestModalOriginal", service_id)
        agent.setup_agent_components(service_id)
        
        # Test avec un texte qui va générer une erreur de syntaxe TweetyProject
        test_text = "The annihilation of Aryan race is necessary for world peace."
        
        logger.info(f"Test avec: '{test_text}'")
        logger.info("Attente d'un échec SANS retry automatique...")
        
        belief_set, status = await agent.text_to_belief_set(test_text)
        
        if belief_set:
            logger.info(f"SUCCÈS INATTENDU: {status}")
            logger.info(f"Belief Set: {belief_set.content}")
        else:
            logger.warning(f"ÉCHEC ATTENDU: {status}")
            
    except Exception as e:
        logger.error(f"ERREUR dans test original: {e}")
        logger.debug(traceback.format_exc())

async def test_fixed_agent_behavior():
    """Test avec l'agent corrigé (avec retry automatique)."""
    logger.info("=" * 80)
    logger.info("TEST 2: Agent Modal Logic CORRIGÉ (avec retry automatique)")
    logger.info("=" * 80)
    
    try:
        # Initialiser le kernel
        kernel = Kernel()
        
        # Configurer le service LLM (remplacez par votre configuration)
        service_id = "openai"
        kernel.add_service(
            OpenAIChatCompletion(
                service_id=service_id,
                ai_model_id="gpt-4",
                api_key="your-api-key-here"  # Remplacez par votre clé API
            )
        )
        
        # Importer et initialiser l'agent SK Retry
        from argumentation_analysis.agents.core.logic.modal_logic_agent_sk_retry import ModalLogicAgentSKRetry
        
        agent = ModalLogicAgentSKRetry(kernel, "TestModalSKRetry", service_id)
        agent.setup_agent_components(service_id)
        
        # Test avec le même texte problématique
        test_text = "The annihilation of Aryan race is necessary for world peace."
        
        logger.info(f"Test avec: '{test_text}'")
        logger.info("Attente d'un retry automatique et correction...")
        
        belief_set, status = await agent.text_to_belief_set(test_text)
        
        if belief_set:
            logger.info(f"SUCCÈS AVEC RETRY: {status}")
            logger.info(f"Belief Set: {belief_set.content}")
        else:
            logger.warning(f"ÉCHEC MÊME AVEC RETRY: {status}")
            
    except Exception as e:
        logger.error(f"ERREUR dans test corrigé: {e}")
        logger.debug(traceback.format_exc())

async def test_syntax_error_simulation():
    """Test de simulation d'erreur de syntaxe directe."""
    logger.info("=" * 80)
    logger.info("TEST 3: Simulation d'erreur de syntaxe TweetyProject")
    logger.info("=" * 80)
    
    try:
        # Simuler l'erreur exacte du rapport
        original_error = "Error parsing Modal Logic formula 'constant annihilation_of_aryan' for logic 'S4': Predicate 'constantannihilation_of_aryan' has not been declared."
        
        logger.info(f"Erreur originale: {original_error}")
        
        # Importer l'agent SK Retry pour tester l'enrichissement d'erreur
        from argumentation_analysis.agents.core.logic.modal_logic_agent_sk_retry import ModalLogicAgentSKRetry
        from argumentation_analysis.agents.core.logic.tweety_bridge_sk import TweetyBridgeSK
        
        # Créer une instance temporaire pour tester l'enrichissement
        kernel = Kernel()  # Kernel minimal pour test
        agent = ModalLogicAgentSKRetry(kernel, "TestSyntax")
        bridge_sk = TweetyBridgeSK()
        
        # Tester l'enrichissement d'erreur avec BNF
        enriched_error = agent._enrich_error_with_bnf(
            original_error,
            "constant annihilation_of_aryan"
        )
        
        logger.info("Erreur enrichie avec BNF:")
        logger.info(enriched_error)
        
        # Vérifier que la BNF est incluse
        if "BNF Syntaxe TweetyProject" in enriched_error:
            logger.info("✅ SUCCESS: L'erreur contient maintenant la BNF pour aider le retry")
        else:
            logger.error("❌ FAILED: L'erreur n'a pas été enrichie correctement")
            
        # Démontrer la différence avec le nouveau bridge SK
        logger.info("\n" + "="*60)
        logger.info("🔍 DÉMONSTRATION DIFFÉRENCE SK vs CLASSIQUE")
        logger.info("="*60)
        
        problematic_text = "The annihilation of Aryan race is necessary for world peace."
        demo_result = bridge_sk.demonstrate_sk_retry_difference(problematic_text)
        
        logger.info(f"📝 Input problématique: {demo_result['problematic_input']}")
        logger.info(f"\n🔴 ANCIEN MÉCANISME (3 tentatives identiques):")
        logger.info(f"   Méthode: {demo_result['old_approach']['method']}")
        logger.info(f"   Comportement: {demo_result['old_approach']['behavior']}")
        logger.info(f"   Résultat: {demo_result['old_approach']['result']}")
        logger.info(f"   Agent voit: {demo_result['old_approach'].get('agent_sees', 'N/A')}")
        
        logger.info(f"\n🟢 NOUVEAU MÉCANISME SK (erreurs comme résultats):")
        logger.info(f"   Méthode: {demo_result['new_sk_approach']['method']}")
        logger.info(f"   Comportement: {demo_result['new_sk_approach']['behavior']}")
        logger.info(f"   Résultat: {demo_result['new_sk_approach']['result']}")
        logger.info(f"   Agent voit: {demo_result['new_sk_approach'].get('agent_sees', 'N/A')}")
        logger.info(f"   BNF fournie: {demo_result['new_sk_approach'].get('bnf_provided', False)}")
        
        logger.info(f"\n💡 DIFFÉRENCE CLÉ: {demo_result['key_difference']}")
            
    except Exception as e:
        logger.error(f"ERREUR dans simulation: {e}")
        logger.debug(traceback.format_exc())

async def test_retry_settings_configuration():
    """Test de la configuration des settings de retry."""
    logger.info("=" * 80)
    logger.info("TEST 4: Vérification de la configuration du retry automatique")
    logger.info("=" * 80)
    
    try:
        from argumentation_analysis.agents.core.logic.modal_logic_agent_sk_retry import ModalLogicAgentSKRetry
        from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
        
        # Créer une instance pour tester la configuration
        kernel = Kernel()
        agent = ModalLogicAgentSKRetry(kernel, "TestRetryConfig")
        
        # Tester la création des settings de retry
        base_settings = PromptExecutionSettings()
        retry_settings = agent._create_retry_execution_settings(base_settings)
        
        logger.info(f"Settings de base: max_auto_invoke_attempts = {getattr(base_settings, 'max_auto_invoke_attempts', 'Non défini')}")
        logger.info(f"Settings de retry: max_auto_invoke_attempts = {getattr(retry_settings, 'max_auto_invoke_attempts', 'Non défini')}")
        
        if hasattr(retry_settings, 'max_auto_invoke_attempts') and retry_settings.max_auto_invoke_attempts == 3:
            logger.info("✅ SUCCESS: Configuration du retry automatique correcte (max_auto_invoke_attempts=3)")
        else:
            logger.error("❌ FAILED: Configuration du retry automatique incorrecte")
            
        # Tester les capacités de l'agent
        capabilities = agent.get_agent_capabilities()
        features = capabilities.get('features', {})
        
        logger.info("Fonctionnalités de l'agent corrigé:")
        for feature, enabled in features.items():
            status = "✅" if enabled else "❌"
            logger.info(f"  {status} {feature}: {enabled}")
            
    except Exception as e:
        logger.error(f"ERREUR dans test de configuration: {e}")
        logger.debug(traceback.format_exc())

async def main():
    """Fonction principale de test."""
    logger.info("🔍 INVESTIGATION: Mécanisme de retry automatique pour erreurs TweetyProject")
    logger.info("📋 Tests comparatifs entre agent original et agent corrigé")
    
    try:
        # Test 1: Agent original (pour comparaison)
        logger.info("\n" + "🔬 " + "="*50)
        await test_original_agent_behavior()
        
        # Test 2: Agent corrigé
        logger.info("\n" + "🛠️ " + "="*50)
        await test_fixed_agent_behavior()
        
        # Test 3: Simulation d'erreur de syntaxe
        logger.info("\n" + "⚡ " + "="*50)
        await test_syntax_error_simulation()
        
        # Test 4: Configuration du retry
        logger.info("\n" + "⚙️ " + "="*50)
        await test_retry_settings_configuration()
        
        logger.info("\n" + "🏁 " + "="*50)
        logger.info("INVESTIGATION TERMINÉE")
        logger.info("📊 Résultats: Voir les logs ci-dessus pour les détails")
        
    except Exception as e:
        logger.error(f"ERREUR CRITIQUE dans main: {e}")
        logger.debug(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    """Point d'entrée du script de test."""
    print("🚀 Démarrage des tests du mécanisme de retry automatique...")
    
    # Configuration des avertissements pour éviter le spam
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    try:
        # Exécuter les tests async
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("🛑 Tests interrompus par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"🚨 ERREUR FATALE: {e}")
        sys.exit(1)