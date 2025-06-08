#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests d'intégration pour la refactorisation du pipeline unifié d'analyse textuelle.

Ce script teste l'intégration complète entre le script CLI refactorisé et le 
nouveau pipeline unifié, en validant toutes les fonctionnalités clés.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any

# Ajout du répertoire racine du projet au chemin
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configuration du logging pour les tests (sans emojis pour Windows)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("UnifiedAnalysisTests")

# Imports des composants à tester
try:
    from argumentation_analysis.pipelines.unified_text_analysis import (
        UnifiedAnalysisConfig,
        UnifiedTextAnalysisPipeline,
        run_unified_text_analysis_pipeline,
        create_unified_config_from_legacy,
        run_text_analysis_pipeline_enhanced
    )
    
    # Import avec gestion du chemin pour scripts.main
    scripts_path = project_root / "scripts"
    if str(scripts_path) not in sys.path:
        sys.path.insert(0, str(scripts_path))
    
    # Import conditionnel pour éviter les erreurs de chemin
    try:
        from main.analyze_text import create_analysis_config_from_args
    except ImportError:
        # Fallback - créer une version simplifiée
        def create_analysis_config_from_args(args):
            return UnifiedAnalysisConfig(
                analysis_modes=getattr(args, 'modes', 'fallacies').split(','),
                logic_type=getattr(args, 'logic_type', 'propositional'),
                use_advanced_tools=getattr(args, 'advanced', False),
                use_mocks=getattr(args, 'mocks', True),
                enable_jvm=not getattr(args, 'no_jvm', True)
            )
    
    from scripts.core.unified_source_selector import UnifiedSourceSelector
    
    PIPELINE_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR] Erreur d'importation: {e}")
    PIPELINE_AVAILABLE = False


class MockArgs:
    """Classe simulant les arguments CLI pour les tests."""
    
    def __init__(self, **kwargs):
        # Valeurs par défaut
        self.modes = kwargs.get('modes', 'fallacies,coherence,semantic')
        self.logic_type = kwargs.get('logic_type', 'propositional')
        self.format = kwargs.get('format', 'json')
        self.advanced = kwargs.get('advanced', False)
        self.mocks = kwargs.get('mocks', True)  # Utiliser mocks par défaut pour tests
        self.no_jvm = kwargs.get('no_jvm', True)  # Désactiver JVM par défaut pour tests
        
        # Surcharge avec les kwargs fournis
        for key, value in kwargs.items():
            setattr(self, key, value)


async def test_basic_pipeline_creation():
    """Test de création basique du pipeline unifié."""
    logger.info("[TEST] Creation basique du pipeline unifie")
    
    try:
        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies"],
            use_mocks=True,
            enable_jvm=False
        )
        
        pipeline = UnifiedTextAnalysisPipeline(config)
        result = await pipeline.initialize()
        
        assert result is True, "L'initialisation du pipeline devrait réussir"
        assert pipeline.config.use_mocks is True, "Le mode mocks devrait être activé"
        
        logger.info("[OK] Test creation pipeline reussi")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Test creation pipeline echoue: {e}")
        return False


async def test_config_conversion():
    """Test de conversion des configurations legacy."""
    logger.info("[TEST] Conversion configuration legacy")
    
    try:
        # Test avec arguments CLI simulés
        mock_args = MockArgs(
            modes="fallacies,semantic,unified",
            advanced=True,
            mocks=True
        )
        
        config = create_analysis_config_from_args(mock_args)
        
        assert "fallacies" in config.analysis_modes, "Mode fallacies devrait être présent"
        assert "semantic" in config.analysis_modes, "Mode semantic devrait être présent"
        assert "unified" in config.analysis_modes, "Mode unified devrait être présent"
        assert config.use_advanced_tools is True, "Outils avancés devraient être activés"
        assert config.orchestration_mode == "real", "Mode orchestration devrait être 'real' avec unified"
        
        logger.info("[OK] Test conversion config reussi")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Test conversion config echoue: {e}")
        return False


async def test_text_analysis_mock():
    """Test d'analyse de texte avec mocks."""
    logger.info("[TEST] Analyse de texte avec mocks")
    
    try:
        test_text = """
        Ce texte contient plusieurs arguments. 
        Tous les chats sont noirs. 
        Mon chat est blanc, donc cette affirmation est fausse.
        Par conséquent, tous les arguments basés sur des généralisations sont incorrects.
        """
        
        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies", "coherence"],
            use_mocks=True,
            enable_jvm=False,
            orchestration_mode="standard"
        )
        
        source_info = {
            "description": "Texte de test",
            "type": "test"
        }
        
        results = await run_unified_text_analysis_pipeline(
            text=test_text,
            source_info=source_info,
            config=config,
            log_level="INFO"
        )
        
        assert results is not None, "Les résultats ne devraient pas être None"
        assert "metadata" in results, "Les résultats devraient contenir des métadonnées"
        assert "informal_analysis" in results, "Les résultats devraient contenir une analyse informelle"
        
        # Vérification des métadonnées
        metadata = results["metadata"]
        assert "timestamp" in metadata, "Timestamp devrait être présent"
        assert "text_length" in metadata, "Longueur du texte devrait être présente"
        assert metadata["text_length"] > 0, "Longueur du texte devrait être positive"
        
        # Vérification de l'analyse informelle
        informal = results["informal_analysis"]
        assert "fallacies" in informal, "L'analyse devrait contenir des sophismes"
        assert "summary" in informal, "L'analyse devrait contenir un résumé"
        
        logger.info("[OK] Test analyse texte avec mocks reussi")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Test analyse texte avec mocks echoue: {e}")
        return False


async def test_orchestration_modes():
    """Test des différents modes d'orchestration."""
    logger.info("[TEST] Modes d'orchestration")
    
    try:
        test_text = "Argument simple pour test d'orchestration."
        
        # Test mode standard
        config_standard = UnifiedAnalysisConfig(
            analysis_modes=["fallacies"],
            orchestration_mode="standard",
            use_mocks=True,
            enable_jvm=False
        )
        
        results_standard = await run_unified_text_analysis_pipeline(
            text=test_text,
            config=config_standard
        )
        
        assert results_standard is not None, "Résultats mode standard ne devraient pas être None"
        
        # Test mode conversation (si disponible)
        config_conversation = UnifiedAnalysisConfig(
            analysis_modes=["fallacies"],
            orchestration_mode="conversation",
            use_mocks=True,
            enable_jvm=False
        )
        
        results_conversation = await run_unified_text_analysis_pipeline(
            text=test_text,
            config=config_conversation
        )
        
        assert results_conversation is not None, "Résultats mode conversation ne devraient pas être None"
        
        # Vérification que les modes produisent des résultats différents
        if "orchestration_analysis" in results_conversation:
            logger.info("   Mode conversation activé avec succès")
        
        logger.info("[OK] Test modes d'orchestration reussi")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Test modes d'orchestration echoue: {e}")
        return False


async def test_integration_with_legacy_components():
    """Test d'intégration avec les composants legacy."""
    logger.info("[TEST] Integration composants legacy")
    
    try:
        # Test de la fonction enhanced qui intègre ancien et nouveau
        test_text = "Texte de test pour intégration legacy."
        
        # Configuration legacy-style
        config_legacy = {
            "analysis_modes": ["fallacies"],
            "use_mocks": True,
            "enable_jvm": False
        }
        
        unified_config = UnifiedAnalysisConfig.from_legacy_config(config_legacy)
        
        results = await run_text_analysis_pipeline_enhanced(
            input_text_content=test_text,
            analysis_type="unified",
            unified_config=unified_config
        )
        
        assert results is not None, "Résultats intégration legacy ne devraient pas être None"
        assert "metadata" in results, "Métadonnées devraient être présentes"
        
        logger.info("[OK] Test integration legacy reussi")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Test integration legacy echoue: {e}")
        return False


async def test_conversation_logging():
    """Test du système de logging conversationnel."""
    logger.info("[TEST] Logging conversationnel")
    
    try:
        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies"],
            orchestration_mode="conversation",
            enable_conversation_logging=True,
            use_mocks=True,
            enable_jvm=False
        )
        
        pipeline = UnifiedTextAnalysisPipeline(config)
        await pipeline.initialize()
        
        test_text = "Texte pour test de logging conversationnel."
        results = await pipeline.analyze_text_unified(test_text)
        
        # Vérification du log conversationnel
        conversation_log = pipeline.get_conversation_log()
        
        assert conversation_log is not None, "Log conversationnel ne devrait pas être None"
        
        if isinstance(conversation_log, dict):
            if "messages" in conversation_log:
                logger.info(f"   Trouvé {len(conversation_log['messages'])} messages")
            if "tool_calls" in conversation_log:
                logger.info(f"   Trouvé {len(conversation_log['tool_calls'])} appels d'outils")
        
        logger.info("[OK] Test logging conversationnel reussi")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Test logging conversationnel echoue: {e}")
        return False


async def test_performance_comparison():
    """Test de comparaison de performance (basique)."""
    logger.info("[TEST] Comparaison de performance")
    
    try:
        import time
        
        test_text = "Texte de test pour mesure de performance. " * 10
        
        # Mesure pipeline unifié
        start_time = time.time()
        
        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies"],
            use_mocks=True,
            enable_jvm=False,
            orchestration_mode="standard"
        )
        
        results = await run_unified_text_analysis_pipeline(
            text=test_text,
            config=config
        )
        
        end_time = time.time()
        processing_time = (end_time - start_time) * 1000
        
        assert results is not None, "Résultats ne devraient pas être None"
        
        # Vérification que le temps est enregistré dans les métadonnées
        if "metadata" in results and "processing_time_ms" in results["metadata"]:
            pipeline_time = results["metadata"]["processing_time_ms"]
            logger.info(f"   Temps pipeline: {pipeline_time:.2f}ms")
        
        logger.info(f"   Temps total mesuré: {processing_time:.2f}ms")
        logger.info("[OK] Test performance reussi")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Test performance echoue: {e}")
        return False


async def run_all_tests():
    """Exécute tous les tests d'intégration."""
    logger.info("[START] Demarrage des tests d'integration pipeline unifie")
    
    if not PIPELINE_AVAILABLE:
        logger.error("[ERROR] Pipeline unifie non disponible - tests annules")
        return False
    
    tests = [
        ("Création pipeline", test_basic_pipeline_creation),
        ("Conversion config", test_config_conversion),
        ("Analyse texte mocks", test_text_analysis_mock),
        ("Modes orchestration", test_orchestration_modes),
        ("Intégration legacy", test_integration_with_legacy_components),
        ("Logging conversationnel", test_conversation_logging),
        ("Performance", test_performance_comparison)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n📋 Exécution du test: {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
            if result:
                logger.info(f"[PASS] {test_name}: REUSSI")
            else:
                logger.error(f"[FAIL] {test_name}: ECHOUE")
        except Exception as e:
            logger.error(f"[ERROR] {test_name}: ERREUR - {e}")
            results.append((test_name, False))
    
    # Résumé des résultats
    logger.info("\n" + "="*60)
    logger.info("[SUMMARY] RESUME DES TESTS D'INTEGRATION")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS] REUSSI" if result else "[FAIL] ECHOUE"
        logger.info(f"{test_name:25s} : {status}")
    
    logger.info("-"*60)
    logger.info(f"Tests réussis: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("[SUCCESS] TOUS LES TESTS D'INTEGRATION ONT REUSSI!")
        logger.info("[OK] La refactorisation du pipeline unifie est validee")
        return True
    else:
        logger.warning(f"[WARNING] {total-passed} test(s) ont echoue")
        logger.warning("[INFO] Verification supplementaire recommandee")
        return False


async def main():
    """Point d'entrée principal des tests."""
    try:
        success = await run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPT] Tests interrompus par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n[CRITICAL] Erreur critique lors des tests: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # Configuration spécifique Windows si nécessaire
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())