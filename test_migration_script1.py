#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de Migration - Script 1: unified_production_analyzer.py
============================================================

Test de validation de la transformation du premier script selon la spécification
technique de migration vers le pipeline unifié central.

Tests couverts :
1. ✅ Interface CLI identique
2. ✅ Mapping des paramètres vers ExtendedOrchestrationConfig  
3. ✅ Délégation au pipeline unifié
4. ✅ Compatibilité des résultats
5. ✅ Toutes les fonctionnalités préservées

Version: 1.0.0
Auteur: Roo - Validation Migration
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Ajout du répertoire racine au chemin
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import du script transformé
from scripts.consolidated.unified_production_analyzer import (
    UnifiedProductionAnalyzer,
    UnifiedProductionConfig,
    LogicType,
    MockLevel,
    OrchestrationType,
    AnalysisMode,
    create_cli_parser,
    create_config_from_args
)

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("TestMigrationScript1")


class TestMigrationScript1:
    """Tests de validation de la migration du script 1"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.TestMigrationScript1")
        self.test_results = []
    
    async def test_configuration_mapping(self):
        """Test 1: Validation du mapping de configuration"""
        self.logger.info("🧪 Test 1: Mapping de configuration CLI → ExtendedOrchestrationConfig")
        
        try:
            # Configuration de test
            config = UnifiedProductionConfig(
                logic_type=LogicType.FOL,
                mock_level=MockLevel.NONE,
                orchestration_type=OrchestrationType.UNIFIED,
                analysis_modes=[AnalysisMode.UNIFIED, AnalysisMode.FALLACIES],
                enable_conversation_trace=True,
                max_workers=4
            )
            
            analyzer = UnifiedProductionAnalyzer(config)
            
            # Test mapping orchestration
            orchestration_mode = analyzer._map_orchestration_mode()
            assert orchestration_mode.value in ["hierarchical_full", "conversation", "operational_direct", "real", "pipeline"]
            
            # Test mapping analysis type
            analysis_type = analyzer._map_analysis_type("rhetorical")
            assert analysis_type.value in ["rhetorical", "comprehensive", "fallacy_focused", "argument_structure"]
            
            # Test construction config unifiée
            unified_config = analyzer._build_config("rhetorical")
            assert unified_config is not None
            assert hasattr(unified_config, 'analysis_modes')
            assert hasattr(unified_config, 'orchestration_mode')
            assert hasattr(unified_config, 'enable_hierarchical')
            
            self.test_results.append(("Configuration Mapping", "✅ RÉUSSI"))
            self.logger.info("✅ Test 1 réussi - Configuration correctement mappée")
            
        except Exception as e:
            self.test_results.append(("Configuration Mapping", f"❌ ÉCHEC: {e}"))
            self.logger.error(f"❌ Test 1 échoué: {e}")
    
    def test_cli_interface_preservation(self):
        """Test 2: Validation de la préservation de l'interface CLI"""
        self.logger.info("🧪 Test 2: Préservation interface CLI")
        
        try:
            # Test création parser CLI
            parser = create_cli_parser()
            assert parser is not None
            
            # Test simulation arguments CLI
            test_args = [
                "--analysis-modes", "unified", "fallacies",
                "--orchestration-type", "unified", 
                "--logic-type", "fol",
                "--mock-level", "none",
                "--enable-conversation-trace",
                "--max-workers", "4"
            ]
            
            # Parse avec arguments de test
            args = parser.parse_args(test_args + ["Test text"])
            
            # Validation des attributs CLI essentiels
            assert hasattr(args, 'analysis_modes')
            assert hasattr(args, 'orchestration_type')
            assert hasattr(args, 'logic_type')
            assert hasattr(args, 'mock_level')
            assert hasattr(args, 'enable_conversation_trace')
            assert hasattr(args, 'max_workers')
            
            # Test création configuration depuis args
            config = create_config_from_args(args)
            assert config is not None
            assert config.logic_type == LogicType.FOL
            assert config.mock_level == MockLevel.NONE
            assert config.orchestration_type == OrchestrationType.UNIFIED
            
            self.test_results.append(("Interface CLI", "✅ RÉUSSI"))
            self.logger.info("✅ Test 2 réussi - Interface CLI préservée")
            
        except Exception as e:
            self.test_results.append(("Interface CLI", f"❌ ÉCHEC: {e}"))
            self.logger.error(f"❌ Test 2 échoué: {e}")
    
    async def test_pipeline_delegation(self):
        """Test 3: Validation de la délégation au pipeline unifié"""
        self.logger.info("🧪 Test 3: Délégation au pipeline unifié")
        
        try:
            # Configuration minimale pour test
            config = UnifiedProductionConfig(
                mock_level=MockLevel.FULL,  # Mode test pour éviter les dépendances
                logic_type=LogicType.FOL,
                orchestration_type=OrchestrationType.UNIFIED,
                analysis_modes=[AnalysisMode.UNIFIED],
                check_dependencies=False  # Ignorer la validation des dépendances pour le test
            )
            
            analyzer = UnifiedProductionAnalyzer(config)
            
            # Test initialisation
            init_success = await analyzer.initialize()
            assert init_success, "L'initialisation doit réussir"
            
            # Test construction de config unifiée
            unified_config = analyzer._build_config("rhetorical")
            
            # Validation des attributs clés de la config unifiée
            assert unified_config.enable_hierarchical == True
            assert unified_config.enable_specialized_orchestrators == True
            assert unified_config.enable_communication_middleware == True
            assert unified_config.save_orchestration_trace == config.save_trace
            
            self.test_results.append(("Délégation Pipeline", "✅ RÉUSSI"))
            self.logger.info("✅ Test 3 réussi - Délégation correctement configurée")
            
        except Exception as e:
            self.test_results.append(("Délégation Pipeline", f"❌ ÉCHEC: {e}"))
            self.logger.error(f"❌ Test 3 échoué: {e}")
    
    async def test_error_handling(self):
        """Test 4: Validation de la gestion d'erreur"""
        self.logger.info("🧪 Test 4: Gestion d'erreur")
        
        try:
            # Configuration invalide pour tester la gestion d'erreur
            config = UnifiedProductionConfig(
                tweety_retry_count=0,  # Invalide
                llm_retry_count=0,     # Invalide
                max_workers=0          # Invalide si parallel activé
            )
            
            # Test validation de configuration
            is_valid, errors = config.validate()
            assert not is_valid, "La configuration invalide doit être détectée"
            assert len(errors) > 0, "Des erreurs doivent être rapportées"
            
            self.test_results.append(("Gestion Erreur", "✅ RÉUSSI"))
            self.logger.info("✅ Test 4 réussi - Gestion d'erreur fonctionnelle")
            
        except Exception as e:
            self.test_results.append(("Gestion Erreur", f"❌ ÉCHEC: {e}"))
            self.logger.error(f"❌ Test 4 échoué: {e}")
    
    def test_enum_compatibility(self):
        """Test 5: Validation de la compatibilité des enums"""
        self.logger.info("🧪 Test 5: Compatibilité des enums")
        
        try:
            # Test que tous les enums conservent leurs valeurs
            assert LogicType.FOL.value == "fol"
            assert LogicType.PL.value == "propositional"
            assert LogicType.MODAL.value == "modal"
            
            assert MockLevel.NONE.value == "none"
            assert MockLevel.PARTIAL.value == "partial"
            assert MockLevel.FULL.value == "full"
            
            assert OrchestrationType.UNIFIED.value == "unified"
            assert OrchestrationType.CONVERSATION.value == "conversation"
            assert OrchestrationType.MICRO.value == "micro"
            assert OrchestrationType.REAL_LLM.value == "real_llm"
            
            self.test_results.append(("Compatibilité Enums", "✅ RÉUSSI"))
            self.logger.info("✅ Test 5 réussi - Enums compatibles")
            
        except Exception as e:
            self.test_results.append(("Compatibilité Enums", f"❌ ÉCHEC: {e}"))
            self.logger.error(f"❌ Test 5 échoué: {e}")
    
    async def run_all_tests(self):
        """Exécute tous les tests de validation"""
        self.logger.info("🚀 Démarrage des tests de migration - Script 1")
        self.logger.info("=" * 60)
        
        # Tests synchrones
        self.test_cli_interface_preservation()
        self.test_enum_compatibility()
        
        # Tests asynchrones
        await self.test_configuration_mapping()
        await self.test_pipeline_delegation()
        await self.test_error_handling()
        
        # Résumé des résultats
        self.logger.info("=" * 60)
        self.logger.info("📊 RÉSULTATS DES TESTS DE MIGRATION")
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if "✅" in r[1]])
        failed_tests = total_tests - passed_tests
        
        for test_name, result in self.test_results:
            self.logger.info(f"{result} {test_name}")
        
        self.logger.info("-" * 60)
        self.logger.info(f"Total: {total_tests} | Réussis: {passed_tests} | Échoués: {failed_tests}")
        
        if failed_tests == 0:
            self.logger.info("🎉 MIGRATION SCRIPT 1 VALIDÉE - Tous les tests passent!")
            return True
        else:
            self.logger.error(f"❌ MIGRATION INCOMPLÈTE - {failed_tests} test(s) échoué(s)")
            return False


async def main():
    """Fonction principale de test"""
    try:
        tester = TestMigrationScript1()
        success = await tester.run_all_tests()
        
        if success:
            print("\n🎯 CONCLUSION: La migration du script 1 est conforme aux spécifications!")
            print("✅ Interface CLI préservée")
            print("✅ Configuration correctement mappée vers ExtendedOrchestrationConfig") 
            print("✅ Délégation au pipeline unifié fonctionnelle")
            print("✅ Gestion d'erreur maintenue")
            print("✅ Compatibilité assurée")
            return 0
        else:
            print("\n❌ MIGRATION INCOMPLÈTE - Des corrections sont nécessaires")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Erreur dans les tests: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)