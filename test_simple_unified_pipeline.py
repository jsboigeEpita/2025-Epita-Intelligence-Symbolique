#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test simple du pipeline unifié d'analyse textuelle.

Test direct des fonctionnalités principales sans dépendances complexes.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ajout du répertoire racine du projet au chemin
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configuration du logging simple
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("SimpleUnifiedTest")

# Test d'import du pipeline unifié
try:
    from argumentation_analysis.pipelines.unified_text_analysis import (
        UnifiedAnalysisConfig,
        UnifiedTextAnalysisPipeline,
        run_unified_text_analysis_pipeline
    )
    PIPELINE_AVAILABLE = True
    logger.info("[OK] Pipeline unifie importe avec succes")
except ImportError as e:
    print(f"[ERROR] Impossible d'importer le pipeline unifie: {e}")
    PIPELINE_AVAILABLE = False


async def test_basic_config_creation():
    """Test de création de configuration basique."""
    logger.info("[TEST] Creation configuration basique")
    
    try:
        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies"],
            use_mocks=True,
            enable_jvm=False,
            orchestration_mode="standard"
        )
        
        config_dict = config.to_dict()
        
        assert "analysis_modes" in config_dict
        assert "fallacies" in config_dict["analysis_modes"]
        assert config_dict["use_mocks"] is True
        assert config_dict["enable_jvm"] is False
        
        logger.info("[PASS] Configuration creee et validee")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Erreur creation config: {e}")
        return False


async def test_pipeline_initialization():
    """Test d'initialisation du pipeline."""
    logger.info("[TEST] Initialisation pipeline")
    
    try:
        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies"],
            use_mocks=True,
            enable_jvm=False,
            orchestration_mode="standard"
        )
        
        pipeline = UnifiedTextAnalysisPipeline(config)
        success = await pipeline.initialize()
        
        assert success is True
        assert pipeline.config.use_mocks is True
        
        logger.info("[PASS] Pipeline initialise avec succes")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Erreur initialisation pipeline: {e}")
        return False


async def test_text_analysis():
    """Test d'analyse de texte simple."""
    logger.info("[TEST] Analyse de texte simple")
    
    try:
        test_text = """
        Voici un argument simple. 
        Tous les politiciens mentent.
        Jean est politicien.
        Donc Jean ment.
        """
        
        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies"],
            use_mocks=True,
            enable_jvm=False,
            orchestration_mode="standard",
            enable_conversation_logging=False
        )
        
        results = await run_unified_text_analysis_pipeline(
            text=test_text,
            config=config,
            log_level="INFO"
        )
        
        assert results is not None
        assert "metadata" in results
        assert "informal_analysis" in results
        
        # Validation des métadonnées
        metadata = results["metadata"]
        assert "timestamp" in metadata
        assert "text_length" in metadata
        assert metadata["text_length"] > 0
        assert "pipeline_version" in metadata
        
        # Validation de l'analyse informelle
        informal = results["informal_analysis"]
        assert "fallacies" in informal
        assert "summary" in informal
        
        logger.info("[PASS] Analyse de texte completee avec succes")
        logger.info(f"   Longueur texte: {metadata['text_length']} caracteres")
        logger.info(f"   Sophismes detectes: {len(informal.get('fallacies', []))}")
        
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Erreur analyse texte: {e}")
        return False


async def test_multiple_analysis_modes():
    """Test avec plusieurs modes d'analyse."""
    logger.info("[TEST] Modes d'analyse multiples")
    
    try:
        test_text = "Argument pour test multi-modes."
        
        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies", "coherence", "semantic"],
            use_mocks=True,
            enable_jvm=False,
            orchestration_mode="standard"
        )
        
        results = await run_unified_text_analysis_pipeline(
            text=test_text,
            config=config
        )
        
        assert results is not None
        assert "informal_analysis" in results
        
        # Vérification que l'analyse informelle contient les sections attendues
        informal = results["informal_analysis"]
        assert "fallacies" in informal
        assert "summary" in informal
        
        logger.info("[PASS] Modes multiples executes avec succes")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Erreur modes multiples: {e}")
        return False


async def test_orchestration_mode():
    """Test du mode d'orchestration."""
    logger.info("[TEST] Mode d'orchestration")
    
    try:
        test_text = "Test orchestration."
        
        config = UnifiedAnalysisConfig(
            analysis_modes=["fallacies"],
            use_mocks=True,
            enable_jvm=False,
            orchestration_mode="conversation",
            enable_conversation_logging=True
        )
        
        results = await run_unified_text_analysis_pipeline(
            text=test_text,
            config=config
        )
        
        assert results is not None
        
        # Vérification qu'il y a une section orchestration
        if "orchestration_analysis" in results:
            logger.info("   Mode orchestration active avec succes")
        
        logger.info("[PASS] Mode orchestration teste")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Erreur mode orchestration: {e}")
        return False


async def test_performance_measurement():
    """Test de mesure de performance."""
    logger.info("[TEST] Mesure de performance")
    
    try:
        import time
        
        test_text = "Test performance. " * 20
        
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
        total_time = (end_time - start_time) * 1000
        
        assert results is not None
        
        if "metadata" in results and "processing_time_ms" in results["metadata"]:
            pipeline_time = results["metadata"]["processing_time_ms"]
            logger.info(f"   Temps pipeline: {pipeline_time:.2f}ms")
        
        logger.info(f"   Temps total: {total_time:.2f}ms")
        logger.info("[PASS] Performance mesuree")
        return True
        
    except Exception as e:
        logger.error(f"[FAIL] Erreur mesure performance: {e}")
        return False


async def run_simple_tests():
    """Exécute tous les tests simples."""
    logger.info("[START] Tests simples du pipeline unifie")
    
    if not PIPELINE_AVAILABLE:
        logger.error("[ERROR] Pipeline non disponible - tests annules")
        return False
    
    tests = [
        ("Configuration basique", test_basic_config_creation),
        ("Initialisation pipeline", test_pipeline_initialization),
        ("Analyse texte simple", test_text_analysis),
        ("Modes multiples", test_multiple_analysis_modes),
        ("Mode orchestration", test_orchestration_mode),
        ("Mesure performance", test_performance_measurement)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        logger.info(f"\n[RUN] {test_name}")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"[ERROR] {test_name}: {e}")
            results.append((test_name, False))
    
    # Résumé
    logger.info("\n" + "="*50)
    logger.info("[SUMMARY] RESUME DES TESTS")
    logger.info("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        logger.info(f"{test_name:25s} : {status}")
    
    logger.info("-"*50)
    logger.info(f"Tests reussis: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        logger.info("[SUCCESS] Tous les tests ont reussi!")
        logger.info("[OK] Pipeline unifie valide")
        return True
    else:
        logger.warning(f"[WARNING] {total-passed} test(s) ont echoue")
        return False


async def main():
    """Point d'entrée principal."""
    try:
        success = await run_simple_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n[INTERRUPT] Tests interrompus")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n[CRITICAL] Erreur critique: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())