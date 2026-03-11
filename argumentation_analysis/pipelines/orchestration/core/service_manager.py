#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Service Manager Core Module for the Orchestration Pipeline.

This module centralizes the logic for initializing and using the
OrchestrationServiceManager.
"""

import logging
from typing import Dict, Any, Optional

from argumentation_analysis.pipelines.orchestration.config.base_config import (
    ExtendedOrchestrationConfig,
)
from argumentation_analysis.paths import RESULTS_DIR, DATA_DIR

# This import might be circular depending on the final structure, needs review.
# For now, we assume OrchestrationServiceManager is in the said location.
try:
    from argumentation_analysis.orchestration.service_manager import (
        OrchestrationServiceManager,
    )
except ImportError as e:
    logging.getLogger(__name__).warning(
        f"Could not import OrchestrationServiceManager: {e}"
    )
    OrchestrationServiceManager = None

logger = logging.getLogger(__name__)


async def initialize_service_manager(
    config: ExtendedOrchestrationConfig,
) -> Optional[OrchestrationServiceManager]:
    """
    Initializes the centralized service manager.

    Args:
        config: The extended orchestration configuration.

    Returns:
        An initialized OrchestrationServiceManager instance, or None on failure.
    """
    if not OrchestrationServiceManager:
        logger.warning(
            "[SERVICE_MANAGER] OrchestrationServiceManager class not available."
        )
        return None

    logger.info("[SERVICE_MANAGER] Initializing centralized service manager...")

    service_config = {
        "enable_hierarchical": config.enable_hierarchical,
        "enable_specialized_orchestrators": config.enable_specialized_orchestrators,
        "enable_communication_middleware": config.enable_communication_middleware,
        "max_concurrent_analyses": config.max_concurrent_analyses,
        "analysis_timeout": config.analysis_timeout,
        "auto_cleanup": True,
        "save_results": True,
        "results_dir": str(RESULTS_DIR),
        "data_dir": str(DATA_DIR),
    }
    service_config.update(config.middleware_config)

    service_manager = OrchestrationServiceManager(
        config=service_config, enable_logging=True, log_level=logging.INFO
    )

    # Initialize the service manager
    success = await service_manager.initialize()
    if success:
        logger.info(
            "[SERVICE_MANAGER] Centralized service manager initialized successfully."
        )
        return service_manager
    else:
        logger.warning("[SERVICE_MANAGER] Failed to initialize service manager.")
        return None


async def execute_service_manager_orchestration(
    service_manager: OrchestrationServiceManager,
    text: str,
    config: ExtendedOrchestrationConfig,
    results: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Executes orchestration via the centralized service manager.

    Args:
        service_manager: The initialized service manager instance.
        text: The text to analyze.
        config: The orchestration configuration.
        results: The results dictionary to populate.

    Returns:
        The updated results dictionary.
    """
    logger.info("[SERVICE_MANAGER] Executing via centralized service manager...")

    try:
        if service_manager and service_manager._initialized:
            # Prepare analysis options
            analysis_options = {
                "analysis_type": config.analysis_type.value,
                "orchestration_mode": config.orchestration_mode_enum.value,
                "use_hierarchical": config.enable_hierarchical,
                "enable_specialized": config.enable_specialized_orchestrators,
            }

            # Run analysis via the service manager
            service_results = await service_manager.analyze_text(
                text=text,
                analysis_type=config.analysis_type.value,
                options=analysis_options,
            )

            results["service_manager_results"] = service_results

            # Note: Tracing should be handled by the main pipeline
            # self._trace_orchestration("service_manager_orchestration_completed", ...)
        else:
            results["service_manager_results"] = {
                "status": "unavailable",
                "message": "Service manager not available or not initialized",
            }

    except Exception as e:
        logger.error(f"[SERVICE_MANAGER] Error in service manager orchestration: {e}")
        results["service_manager_results"]["error"] = str(e)

    return results
