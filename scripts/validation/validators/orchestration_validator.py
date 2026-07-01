#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argumentation_analysis.core.environment
"""
Validator for unified orchestrators.
"""

import time
import logging
import traceback
from typing import Dict, Any, List

# Ajout du chemin pour les imports si nécessaire
# from pathlib import Path
# PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
# sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


async def validate_orchestration(
    report_errors_list: list,
    available_components: Dict[str, bool],
    test_texts: List[str],
) -> Dict[str, Any]:
    """Validates unified orchestrators."""
    logger.info("🎭 Validation des orchestrateurs unifiés...")

    orchestration_results = {
        "conversation_orchestrator": {},
        "unified_pipeline": {},
        "integration_tests": {},  # Peut-être à déplacer dans integration_validator
        "performance_metrics": {},  # Peut-être à déplacer dans performance_validator
        "errors": [],
    }

    try:
        # Test ConversationOrchestrator
        if available_components.get("conversation_orchestrator", False):
            orchestration_results["conversation_orchestrator"] = (
                await _test_conversation_orchestrator(test_texts)
            )
        else:
            orchestration_results["conversation_orchestrator"] = {
                "status": "unavailable",
                "reason": "Module ConversationOrchestrator non disponible",
            }

        # Test UnifiedPipeline
        if available_components.get("unified_pipeline", False):
            orchestration_results["unified_pipeline"] = (
                await _test_unified_pipeline(test_texts)
            )
        else:
            orchestration_results["unified_pipeline"] = {
                "status": "unavailable",
                "reason": "Module unified_pipeline non disponible",
            }

    except Exception as e:
        error_details = {
            "context": "orchestration_validation",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }
        orchestration_results["errors"].append(error_details)
        report_errors_list.append(error_details)

    return orchestration_results


async def _test_conversation_orchestrator(test_texts: List[str]) -> Dict[str, Any]:
    """Tests the ConversationOrchestrator."""
    results = {"status": "unknown", "modes_tested": [], "performance": {}, "errors": []}

    try:
        from argumentation_analysis.orchestration.conversation_orchestrator import (
            ConversationOrchestrator,
        )

        modes = ["micro", "demo", "trace", "enhanced"]

        for mode in modes:
            logger.info(f"  Test ConversationOrchestrator mode: {mode}")
            start_time = time.time()

            try:
                orchestrator = ConversationOrchestrator(mode=mode)
                # Utilise le premier texte de test fourni
                result = orchestrator.run_orchestration(
                    test_texts[0] if test_texts else "Default test text"
                )

                elapsed = time.time() - start_time

                if isinstance(result, str) and len(result) > 0:
                    results["modes_tested"].append(mode)
                    results["performance"][mode] = elapsed
                    logger.info(f"    ✓ Mode {mode}: {elapsed:.2f}s")
                else:
                    raise ValueError(f"Résultat invalide pour mode {mode}: {result}")

            except Exception as e:
                error_msg = f"Erreur mode {mode}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(f"    ✗ {error_msg}", exc_info=True)

        if len(results["modes_tested"]) > 0:
            results["status"] = "success" if len(results["errors"]) == 0 else "partial"
        else:
            results["status"] = "failed"

    except ImportError:
        results["status"] = "failed"
        results["errors"].append("Impossible d'importer ConversationOrchestrator")
        logger.error("✗ Erreur Import ConversationOrchestrator")
    except Exception as e:
        results["status"] = "failed"
        results["errors"].append(f"Erreur générale ConversationOrchestrator: {str(e)}")
        logger.error(f"✗ Erreur générale ConversationOrchestrator: {e}", exc_info=True)

    return results


async def _test_unified_pipeline(test_texts: List[str]) -> Dict[str, Any]:
    """Tests the UnifiedPipeline (run_unified_analysis)."""
    results = {
        "status": "unknown",
        "initialization": False,
        "orchestration": False,
        "performance": {},
        "errors": [],
    }

    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        logger.info("  Test UnifiedPipeline (run_unified_analysis)...")
        start_time = time.time()

        # Test d'import — l'initialisation est automatique dans run_unified_analysis
        results["initialization"] = callable(run_unified_analysis)

        init_time = time.time() - start_time
        results["performance"]["initialization"] = init_time

        if results["initialization"]:
            logger.info(f"    ✓ Import: {init_time:.2f}s")

            logger.info("  Test UnifiedPipeline orchestration...")
            start_time = time.time()

            # Utilise le deuxième texte de test fourni, ou un texte par défaut
            test_input = (
                test_texts[1]
                if len(test_texts) > 1
                else "Default test text for UnifiedPipeline"
            )
            result = await run_unified_analysis(test_input, workflow_name="standard")

            orch_time = time.time() - start_time
            results["performance"]["orchestration"] = orch_time

            if isinstance(result, dict) and "summary" in result:
                results["orchestration"] = True
                logger.info(f"    ✓ Orchestration: {orch_time:.2f}s")
            else:
                raise ValueError(f"Résultat d'orchestration invalide: {result}")
        else:
            logger.error("    ✗ Échec import UnifiedPipeline")

        if results["initialization"] and results["orchestration"]:
            results["status"] = "success"
        else:
            results["status"] = "failed"

    except ImportError:
        results["status"] = "failed"
        results["errors"].append("Impossible d'importer run_unified_analysis")
        logger.error("✗ Erreur Import UnifiedPipeline")
    except Exception as e:
        results["status"] = "failed"
        results["errors"].append(f"Erreur générale UnifiedPipeline: {str(e)}")
        logger.error(f"✗ Erreur générale UnifiedPipeline: {e}", exc_info=True)

    return results
