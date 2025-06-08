#!/usr/bin/env python3
"""
Démonstration rapide de la correction du retry automatique.
Script minimal pour valider que la solution fonctionne.
"""

import logging
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings

# Configuration basique du logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_retry_configuration():
    """Test rapide de la configuration du retry."""
    logger.info("🔧 Test de la configuration du retry automatique...")
    
    try:
        # Importer l'agent corrigé
        from argumentation_analysis.agents.core.logic.modal_logic_agent_fixed import ModalLogicAgentFixed
        
        # Créer une instance minimale
        kernel = Kernel()
        agent = ModalLogicAgentFixed(kernel, "DemoAgent")
        
        # Tester la création des settings de retry
        base_settings = PromptExecutionSettings()
        retry_settings = agent._create_retry_execution_settings(base_settings)
        
        # Vérifier la configuration
        if hasattr(retry_settings, 'max_auto_invoke_attempts') and retry_settings.max_auto_invoke_attempts == 3:
            logger.info("✅ SUCCESS: Configuration du retry automatique correcte")
            logger.info(f"   max_auto_invoke_attempts = {retry_settings.max_auto_invoke_attempts}")
        else:
            logger.error("❌ FAILED: Configuration du retry incorrecte")
            return False
            
        # Tester l'enrichissement d'erreur
        test_error = "Error parsing Modal Logic formula 'constant test_prop'"
        enriched = agent._enrich_error_with_bnf(test_error, "constant test_prop")
        
        if "BNF Syntaxe TweetyProject" in enriched:
            logger.info("✅ SUCCESS: Enrichissement d'erreur avec BNF fonctionnel")
        else:
            logger.error("❌ FAILED: Enrichissement d'erreur ne fonctionne pas")
            return False
            
        # Vérifier les capacités
        capabilities = agent.get_agent_capabilities()
        features = capabilities.get('features', {})
        
        required_features = ['auto_retry', 'syntax_correction', 'bnf_error_messages']
        for feature in required_features:
            if features.get(feature, False):
                logger.info(f"✅ SUCCESS: Feature '{feature}' activée")
            else:
                logger.error(f"❌ FAILED: Feature '{feature}' non activée")
                return False
        
        logger.info("🎉 TOUTES LES VÉRIFICATIONS PASSÉES !")
        return True
        
    except ImportError as e:
        logger.error(f"❌ ERREUR D'IMPORT: {e}")
        logger.error("Assurez-vous que le fichier modal_logic_agent_fixed.py est accessible")
        return False
    except Exception as e:
        logger.error(f"❌ ERREUR INATTENDUE: {e}")
        return False

def show_bnf_example():
    """Affiche un exemple de BNF enrichie."""
    logger.info("\n📋 Exemple de message d'erreur enrichi avec BNF:")
    
    try:
        from argumentation_analysis.agents.core.logic.modal_logic_agent_fixed import ModalLogicAgentFixed
        
        kernel = Kernel()
        agent = ModalLogicAgentFixed(kernel, "BNFDemo")
        
        # Simuler l'erreur du rapport original
        original_error = "Error parsing Modal Logic formula 'constant annihilation_of_aryan' for logic 'S4': Predicate 'constantannihilation_of_aryan' has not been declared."
        
        enriched = agent._enrich_error_with_bnf(original_error, "constant annihilation_of_aryan")
        
        print("\n" + "="*80)
        print("MESSAGE D'ERREUR ENRICHI:")
        print("="*80)
        print(enriched)
        print("="*80)
        
        logger.info("✅ Exemple de BNF affiché avec succès")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'affichage de l'exemple: {e}")

def main():
    """Fonction principale de démonstration."""
    logger.info("🚀 DÉMONSTRATION: Correction du retry automatique TweetyProject")
    logger.info("📦 Validation de la solution implémentée")
    
    # Test 1: Configuration du retry
    logger.info("\n" + "🔧 " + "="*60)
    success = test_retry_configuration()
    
    if not success:
        logger.error("❌ La démonstration a échoué")
        return 1
    
    # Test 2: Exemple de BNF enrichie
    logger.info("\n" + "📋 " + "="*60)
    show_bnf_example()
    
    # Résumé final
    logger.info("\n" + "🏁 " + "="*60)
    logger.info("DÉMONSTRATION TERMINÉE AVEC SUCCÈS")
    logger.info("✅ Le mécanisme de retry automatique est maintenant opérationnel")
    logger.info("📝 Voir RAPPORT_INVESTIGATION_RETRY_AUTOMATIQUE.md pour les détails")
    
    return 0

if __name__ == "__main__":
    """Point d'entrée du script de démonstration."""
    import sys
    
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n🛑 Démonstration interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n🚨 ERREUR FATALE: {e}")
        sys.exit(1)