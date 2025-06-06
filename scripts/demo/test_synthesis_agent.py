#!/usr/bin/env python3
"""
Script de test et démonstration pour l'Agent de Synthèse Unifié - Phase 1

Ce script valide l'implémentation du SynthesisAgent Core et démontre
ses capacités de coordination des analyses formelles et informelles.

Usage: python scripts/demo/test_synthesis_agent.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

import logging
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatCompletion

from argumentation_analysis.agents.core.synthesis import SynthesisAgent
# Configuration des logs directe
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SynthesisAgentTester:
    """
    Classe de test pour le SynthesisAgent.
    
    Valide les fonctionnalités principales:
    - Initialisation correcte
    - Orchestration des analyses
    - Unification des résultats  
    - Génération de rapports
    """
    
    def __init__(self):
        self.kernel = None
        self.synthesis_agent = None
        
    async def setup_kernel(self):
        """Configure le kernel Semantic Kernel."""
        logger.info("Configuration du kernel Semantic Kernel")
        
        self.kernel = Kernel()
        
        # Configuration du service LLM (à adapter selon votre environnement)
        try:
            # Tentative avec Azure OpenAI
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://your-endpoint.openai.azure.com/")
            deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4")
            
            if api_key and endpoint:
                chat_service = AzureChatCompletion(
                    service_id="azure_chat_completion",
                    deployment_name=deployment_name,
                    endpoint=endpoint,
                    api_key=api_key,
                )
                self.kernel.add_service(chat_service)
                logger.info("Service Azure OpenAI configuré")
            else:
                # Fallback vers OpenAI standard
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if openai_api_key:
                    chat_service = OpenAIChatCompletion(
                        service_id="openai_chat_completion",
                        ai_model_id="gpt-4o-mini",
                        api_key=openai_api_key,
                    )
                    self.kernel.add_service(chat_service)
                    logger.info("Service OpenAI configuré")
                else:
                    logger.warning("Aucune clé API trouvée - mode simulation")
                    
        except Exception as e:
            logger.error(f"Erreur configuration LLM: {e}")
            logger.info("Poursuite en mode simulation")
    
    async def test_agent_initialization(self):
        """Test l'initialisation du SynthesisAgent."""
        logger.info("=== TEST: Initialisation du SynthesisAgent ===")
        
        try:
            # Test en mode simple (Phase 1)
            self.synthesis_agent = SynthesisAgent(
                kernel=self.kernel,
                agent_name="TestSynthesisAgent",
                enable_advanced_features=False
            )
            
            # Configuration des composants
            self.synthesis_agent.setup_agent_components("azure_chat_completion")
            
            # Vérification des capacités
            capabilities = self.synthesis_agent.get_agent_capabilities()
            logger.info(f"Capacités de l'agent: {capabilities}")
            
            assert capabilities["synthesis_coordination"] == True
            assert capabilities["phase"] == 1
            assert capabilities["advanced_features_enabled"] == False
            
            logger.info("✓ Initialisation réussie")
            return True
            
        except Exception as e:
            logger.error(f"✗ Échec initialisation: {e}")
            return False
    
    async def test_simple_synthesis(self):
        """Test la synthèse simple (Phase 1)."""
        logger.info("=== TEST: Synthèse simple (Phase 1) ===")
        
        # Texte de test avec contenu argumentatif
        test_text = """
        Tous les oiseaux volent. Tweety est un oiseau. 
        Donc Tweety vole. Cependant, il est évident que 
        cette conclusion est absolument certaine car tout 
        le monde sait que c'est vrai. De plus, quiconque 
        conteste cela est clairement dans l'erreur.
        """
        
        try:
            logger.info(f"Analyse du texte: {test_text.strip()}")
            
            # Exécution de la synthèse
            unified_report = await self.synthesis_agent.synthesize_analysis(test_text)
            
            # Vérifications
            assert unified_report is not None
            assert unified_report.original_text == test_text
            assert unified_report.logic_analysis is not None
            assert unified_report.informal_analysis is not None
            assert unified_report.executive_summary != ""
            
            logger.info("✓ Synthèse simple réussie")
            logger.info(f"Résumé: {unified_report.executive_summary}")
            
            # Affichage des statistiques
            stats = unified_report.get_summary_statistics()
            logger.info(f"Statistiques: {stats}")
            
            return True, unified_report
            
        except Exception as e:
            logger.error(f"✗ Échec synthèse simple: {e}", exc_info=True)
            return False, None
    
    async def test_orchestration(self):
        """Test l'orchestration des analyses."""
        logger.info("=== TEST: Orchestration des analyses ===")
        
        test_text = "Si P alors Q. P. Donc Q. Cette logique est parfaite et irréfutable."
        
        try:
            # Test de l'orchestration directe
            logic_result, informal_result = await self.synthesis_agent.orchestrate_analysis(test_text)
            
            # Vérifications
            assert logic_result is not None
            assert informal_result is not None
            assert hasattr(logic_result, 'analysis_timestamp')
            assert hasattr(informal_result, 'analysis_timestamp')
            
            logger.info("✓ Orchestration réussie")
            logger.info(f"Résultat logique: {logic_result.to_dict()}")
            logger.info(f"Résultat informel: {informal_result.to_dict()}")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Échec orchestration: {e}")
            return False
    
    async def test_report_generation(self, unified_report):
        """Test la génération de rapport textuel."""
        logger.info("=== TEST: Génération de rapport ===")
        
        try:
            if unified_report is None:
                logger.warning("Aucun rapport à tester")
                return False
            
            # Génération du rapport textuel
            text_report = await self.synthesis_agent.generate_report(unified_report)
            
            # Vérifications
            assert text_report is not None
            assert len(text_report) > 0
            assert "RAPPORT DE SYNTHÈSE UNIFIÉ" in text_report
            assert "RÉSUMÉ EXÉCUTIF" in text_report
            
            logger.info("✓ Génération de rapport réussie")
            logger.info("Aperçu du rapport:")
            print("\n" + "="*60)
            print(text_report[:500] + "..." if len(text_report) > 500 else text_report)
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Échec génération rapport: {e}")
            return False
    
    async def test_data_models(self):
        """Test les modèles de données."""
        logger.info("=== TEST: Modèles de données ===")
        
        try:
            from argumentation_analysis.agents.core.synthesis.data_models import (
                LogicAnalysisResult, 
                InformalAnalysisResult, 
                UnifiedReport
            )
            
            # Test LogicAnalysisResult
            logic_result = LogicAnalysisResult(
                propositional_result="Valide",
                logical_validity=True,
                formulas_extracted=["P → Q", "P", "Q"]
            )
            logic_dict = logic_result.to_dict()
            assert "propositional_result" in logic_dict
            
            # Test InformalAnalysisResult
            informal_result = InformalAnalysisResult(
                fallacies_detected=[{"type": "ad_hominem", "confidence": 0.8}],
                argument_strength=0.7
            )
            informal_dict = informal_result.to_dict()
            assert "fallacies_detected" in informal_dict
            
            # Test UnifiedReport
            unified = UnifiedReport(
                original_text="Test",
                logic_analysis=logic_result,
                informal_analysis=informal_result,
                executive_summary="Test summary"
            )
            unified_json = unified.to_json()
            assert "original_text" in unified_json
            
            stats = unified.get_summary_statistics()
            assert "text_length" in stats
            
            logger.info("✓ Modèles de données valides")
            return True
            
        except Exception as e:
            logger.error(f"✗ Échec modèles de données: {e}")
            return False
    
    async def test_edge_cases(self):
        """Test les cas limites."""
        logger.info("=== TEST: Cas limites ===")
        
        test_cases = [
            "",  # Texte vide
            "A",  # Texte minimal
            "Non-sense gibberish random words",  # Texte sans structure
            "P et non-P",  # Contradiction logique
        ]
        
        success_count = 0
        
        for i, test_text in enumerate(test_cases):
            try:
                logger.info(f"Test cas limite {i+1}: '{test_text}'")
                result = await self.synthesis_agent.synthesize_analysis(test_text)
                
                # Vérifications basiques
                assert result is not None
                assert result.original_text == test_text
                
                success_count += 1
                logger.info(f"✓ Cas limite {i+1} géré")
                
            except Exception as e:
                logger.warning(f"⚠ Cas limite {i+1} échoué: {e}")
        
        logger.info(f"Cas limites réussis: {success_count}/{len(test_cases)}")
        return success_count > 0
    
    async def run_all_tests(self):
        """Exécute tous les tests."""
        logger.info("🚀 DÉMARRAGE DES TESTS SYNTHESIS AGENT - PHASE 1")
        logger.info("="*60)
        
        await self.setup_kernel()
        
        tests = [
            ("Modèles de données", self.test_data_models),
            ("Initialisation agent", self.test_agent_initialization),
            ("Orchestration", self.test_orchestration),
            ("Synthèse simple", self.test_simple_synthesis),
            ("Cas limites", self.test_edge_cases),
        ]
        
        results = []
        unified_report = None
        
        for test_name, test_func in tests:
            try:
                if test_name == "Synthèse simple":
                    success, unified_report = await test_func()
                else:
                    success = await test_func()
                
                results.append((test_name, success))
                
            except Exception as e:
                logger.error(f"Erreur dans le test '{test_name}': {e}")
                results.append((test_name, False))
        
        # Test séparé de génération de rapport (dépend de la synthèse)
        if unified_report:
            try:
                report_success = await self.test_report_generation(unified_report)
                results.append(("Génération rapport", report_success))
            except Exception as e:
                logger.error(f"Erreur génération rapport: {e}")
                results.append(("Génération rapport", False))
        
        # Résumé des résultats
        logger.info("\n" + "="*60)
        logger.info("📊 RÉSULTATS DES TESTS")
        logger.info("="*60)
        
        passed = 0
        for test_name, success in results:
            status = "✓ RÉUSSI" if success else "✗ ÉCHOUÉ"
            logger.info(f"{test_name:25} : {status}")
            if success:
                passed += 1
        
        total = len(results)
        logger.info("="*60)
        logger.info(f"BILAN: {passed}/{total} tests réussis ({passed/total*100:.1f}%)")
        
        if passed == total:
            logger.info("🎉 TOUS LES TESTS SONT PASSÉS - PHASE 1 VALIDÉE")
            return True
        else:
            logger.warning("⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
            return False


async def main():
    """Point d'entrée principal."""
    print("🔬 TEST SYNTHESIS AGENT - PHASE 1")
    print("Architecture progressive - Mode simple")
    print("-" * 50)
    
    tester = SynthesisAgentTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\n✨ IMPLÉMENTATION PHASE 1 VALIDÉE")
        print("Le SynthesisAgent Core est fonctionnel et prêt pour les extensions futures.")
    else:
        print("\n❌ VALIDATION PARTIELLE")
        print("Vérifier les logs pour identifier les problèmes.")
    
    return 0 if success else 1


if __name__ == "__main__":
    # Exécution avec gestion d'erreur
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️ Test interrompu par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)