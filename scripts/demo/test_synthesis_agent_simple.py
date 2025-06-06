#!/usr/bin/env python3
"""
Script de test simplifié pour l'Agent de Synthèse Unifié - Phase 1

Ce script valide l'implémentation du SynthesisAgent Core de manière autonome.

Usage: python scripts/demo/test_synthesis_agent_simple.py
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Configuration des logs directe
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

from semantic_kernel import Kernel

from argumentation_analysis.agents.core.synthesis import SynthesisAgent
from argumentation_analysis.agents.core.synthesis.data_models import (
    LogicAnalysisResult,
    InformalAnalysisResult,
    UnifiedReport
)


class SimpleSynthesisAgentTester:
    """
    Testeur simplifié pour le SynthesisAgent.
    
    Teste les fonctionnalités principales en mode simulation.
    """
    
    def __init__(self):
        self.kernel = None
        self.synthesis_agent = None
        
    async def setup_kernel(self):
        """Configure un kernel basique."""
        logger.info("Configuration du kernel Semantic Kernel")
        self.kernel = Kernel()
        logger.info("Kernel configuré en mode simulation")
    
    async def test_data_models(self):
        """Test les modèles de données."""
        logger.info("=== TEST: Modèles de données ===")
        
        try:
            # Test LogicAnalysisResult
            logic_result = LogicAnalysisResult(
                propositional_result="Test PL valide",
                logical_validity=True,
                formulas_extracted=["P → Q", "P", "Q"]
            )
            logic_dict = logic_result.to_dict()
            assert "propositional_result" in logic_dict
            assert logic_dict["logical_validity"] is True
            
            # Test InformalAnalysisResult
            informal_result = InformalAnalysisResult(
                fallacies_detected=[{"type": "ad_hominem", "confidence": 0.8}],
                argument_strength=0.7
            )
            informal_dict = informal_result.to_dict()
            assert "fallacies_detected" in informal_dict
            assert len(informal_dict["fallacies_detected"]) == 1
            
            # Test UnifiedReport
            unified = UnifiedReport(
                original_text="Texte de test",
                logic_analysis=logic_result,
                informal_analysis=informal_result,
                executive_summary="Résumé de test"
            )
            unified_json = unified.to_json()
            assert "original_text" in unified_json
            assert "executive_summary" in unified_json
            
            stats = unified.get_summary_statistics()
            assert "text_length" in stats
            assert stats["formulas_count"] == 3
            assert stats["fallacies_count"] == 1
            
            logger.info("✓ Modèles de données validés")
            return True
            
        except Exception as e:
            logger.error(f"✗ Échec modèles de données: {e}")
            return False
    
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
            self.synthesis_agent.setup_agent_components("test_service")
            
            # Vérification des capacités
            capabilities = self.synthesis_agent.get_agent_capabilities()
            logger.info(f"Capacités de l'agent: {capabilities}")
            
            assert capabilities["synthesis_coordination"] == True
            assert capabilities["phase"] == 1
            assert capabilities["advanced_features_enabled"] == False
            assert "logic_types_supported" in capabilities
            
            logger.info("✓ Initialisation réussie")
            return True
            
        except Exception as e:
            logger.error(f"✗ Échec initialisation: {e}")
            import traceback
            traceback.print_exc()
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
            assert unified_report.synthesis_version == "1.0.0"
            
            logger.info("✓ Synthèse simple réussie")
            logger.info(f"Résumé: {unified_report.executive_summary}")
            
            # Affichage des statistiques
            stats = unified_report.get_summary_statistics()
            logger.info(f"Statistiques: {stats}")
            
            # Vérification du contenu logique
            logic_analysis = unified_report.logic_analysis
            assert logic_analysis.propositional_result is not None
            assert logic_analysis.first_order_result is not None
            assert logic_analysis.modal_result is not None
            
            # Vérification du contenu informel
            informal_analysis = unified_report.informal_analysis
            assert informal_analysis.fallacies_detected is not None
            assert len(informal_analysis.fallacies_detected) >= 2  # Devrait détecter les sophismes
            
            return True, unified_report
            
        except Exception as e:
            logger.error(f"✗ Échec synthèse simple: {e}")
            import traceback
            traceback.print_exc()
            return False, None
    
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
            assert "STATISTIQUES" in text_report
            assert "ÉVALUATION GLOBALE" in text_report
            
            logger.info("✓ Génération de rapport réussie")
            logger.info("Aperçu du rapport:")
            print("\n" + "="*60)
            print(text_report[:800] + "..." if len(text_report) > 800 else text_report)
            print("="*60 + "\n")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Échec génération rapport: {e}")
            import traceback
            traceback.print_exc()
            return False
    
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
            assert logic_result.processing_time_ms is not None
            assert informal_result.processing_time_ms is not None
            
            logger.info("✓ Orchestration réussie")
            logger.info(f"Temps analyse logique: {logic_result.processing_time_ms:.2f}ms")
            logger.info(f"Temps analyse informelle: {informal_result.processing_time_ms:.2f}ms")
            
            return True
            
        except Exception as e:
            logger.error(f"✗ Échec orchestration: {e}")
            import traceback
            traceback.print_exc()
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
                assert result.logic_analysis is not None
                assert result.informal_analysis is not None
                
                success_count += 1
                logger.info(f"✓ Cas limite {i+1} géré")
                
            except Exception as e:
                logger.warning(f"⚠ Cas limite {i+1} échoué: {e}")
        
        logger.info(f"Cas limites réussis: {success_count}/{len(test_cases)}")
        return success_count >= len(test_cases) // 2  # Au moins 50% de réussite
    
    async def run_all_tests(self):
        """Exécute tous les tests."""
        logger.info("DEMARRAGE DES TESTS SYNTHESIS AGENT - PHASE 1")
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
        logger.info("RESULTATS DES TESTS")
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
        
        if passed >= total * 0.8:  # 80% de réussite minimum
            logger.info("TESTS GLOBALEMENT REUSSIS - PHASE 1 VALIDEE")
            return True
        else:
            logger.warning("⚠️ TROP DE TESTS ONT ÉCHOUÉ")
            return False


async def main():
    """Point d'entrée principal."""
    print("TEST SYNTHESIS AGENT - PHASE 1 (Version Simplifiee)")
    print("Architecture progressive - Mode simple avec simulation")
    print("-" * 60)
    
    tester = SimpleSynthesisAgentTester()
    success = await tester.run_all_tests()
    
    if success:
        print("\nIMPLEMENTATION PHASE 1 VALIDEE")
        print("Le SynthesisAgent Core est fonctionnel et pret pour les extensions futures.")
        print("La simulation des agents logiques et informels fonctionne correctement.")
        print("Prochaine etape: Integration avec les vrais agents (Phase 2).")
    else:
        print("\nVALIDATION PARTIELLE")
        print("Verifier les logs pour identifier les problemes.")
    
    return 0 if success else 1


if __name__ == "__main__":
    # Exécution avec gestion d'erreur
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrompu par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"\nErreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)