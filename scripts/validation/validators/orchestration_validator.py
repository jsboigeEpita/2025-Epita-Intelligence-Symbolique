import argumentation_analysis.core.environment

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
        "real_llm_orchestrator": {},
        "integration_tests": {},  # Peut-être à déplacer dans integration_validator
        "performance_metrics": {},  # Peut-être à déplacer dans performance_validator
        "errors": [],
    }

    try:
        # Test ConversationOrchestrator
        if available_components.get("conversation_orchestrator", False):
            orchestration_results[
                "conversation_orchestrator"
            ] = await _test_conversation_orchestrator(test_texts)
        else:
            orchestration_results["conversation_orchestrator"] = {
                "status": "unavailable",
                "reason": "Module ConversationOrchestrator non disponible",
            }

        # Test RealLLMOrchestrator
        if available_components.get("real_llm_orchestrator", False):
            orchestration_results[
                "real_llm_orchestrator"
            ] = await _test_real_llm_orchestrator(test_texts)
        else:
            orchestration_results["real_llm_orchestrator"] = {
                "status": "unavailable",
                "reason": "Module RealLLMOrchestrator non disponible",
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


async def _test_real_llm_orchestrator(test_texts: List[str]) -> Dict[str, Any]:
    """Tests the RealLLMOrchestrator."""
    results = {
        "status": "unknown",
        "initialization": False,
        "orchestration": False,
        "performance": {},
        "errors": [],
    }

    try:
        from argumentation_analysis.orchestration.real_llm_orchestrator import (
            RealLLMOrchestrator,
        )

        orchestrator = RealLLMOrchestrator(
            mode="real"
        )  # Mode est souvent 'real' ou similaire

        logger.info("  Test RealLLMOrchestrator initialisation...")
        start_time = time.time()

        if hasattr(orchestrator, "initialize"):
            init_success = (
                await orchestrator.initialize()
            )  # Assurez-vous que c'est une coroutine si await est utilisé
            results["initialization"] = init_success
        else:
            results["initialization"] = True  # Pas d'initialisation explicite requise

        init_time = time.time() - start_time
        results["performance"]["initialization"] = init_time

        if results["initialization"]:
            logger.info(f"    ✓ Initialisation: {init_time:.2f}s")

            logger.info("  Test RealLLMOrchestrator orchestration...")
            start_time = time.time()

            # Utilise le deuxième texte de test fourni, ou un texte par défaut
            test_input = (
                test_texts[1]
                if len(test_texts) > 1
                else "Default test text for RealLLM"
            )
            result = await orchestrator.run_real_llm_orchestration(test_input)

            orch_time = time.time() - start_time
            results["performance"]["orchestration"] = orch_time

            if isinstance(result, dict) and (
                "status" in result or "analysis" in result
            ):
                results["orchestration"] = True
                logger.info(f"    ✓ Orchestration: {orch_time:.2f}s")
            else:
                raise ValueError(f"Résultat d'orchestration invalide: {result}")
        else:
            logger.error("    ✗ Échec initialisation RealLLMOrchestrator")

        if results["initialization"] and results["orchestration"]:
            results["status"] = "success"
        else:
            results["status"] = "failed"

    except ImportError:
        results["status"] = "failed"
        results["errors"].append("Impossible d'importer RealLLMOrchestrator")
        logger.error("✗ Erreur Import RealLLMOrchestrator")
    except Exception as e:
        results["status"] = "failed"
        results["errors"].append(f"Erreur générale RealLLMOrchestrator: {str(e)}")
        logger.error(f"✗ Erreur générale RealLLMOrchestrator: {e}", exc_info=True)

    return results
