#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Communication Middleware Core Module for the Orchestration Pipeline.

This module centralizes the logic for creating and managing the 
communication middleware used between different components of the
hierarchical architecture.
"""

import logging
from typing import Optional

# Attempt to import the real MessageMiddleware and ServiceManager
try:
    from argumentation_analysis.core.communication import MessageMiddleware
    from argumentation_analysis.orchestration.service_manager import OrchestrationServiceManager
except ImportError as e:
    logging.getLogger(__name__).warning(f"Could not import core communication components: {e}")
    MessageMiddleware = None
    OrchestrationServiceManager = None

logger = logging.getLogger(__name__)


def initialize_communication_middleware(
    service_manager: Optional[OrchestrationServiceManager] = None,
    enable_communication: bool = False
) -> Optional[MessageMiddleware]:
    """
    Initializes or retrieves the communication middleware.

    This function prioritizes retrieving the middleware from an existing
    ServiceManager instance to ensure a single, unified communication bus.
    If no service manager is provided, it creates a new middleware instance.

    Args:
        service_manager: An optional initialized OrchestrationServiceManager instance.
        enable_communication: Flag to enable the creation of a new middleware
                              if no service_manager is available.

    Returns:
        An initialized MessageMiddleware instance, or None if unavailable/disabled.
    """
    if not MessageMiddleware:
        logger.warning("[COMMUNICATION] MessageMiddleware class not available.")
        return None

    # Prioritize the middleware from the ServiceManager to ensure a single bus
    if service_manager and hasattr(service_manager, 'middleware') and service_manager.middleware:
        logger.info("[COMMUNICATION] Communication middleware linked from ServiceManager.")
        return service_manager.middleware
    
    # Fallback to creating a new instance if enabled
    if enable_communication:
        logger.warning("[COMMUNICATION] Creating a new, isolated middleware instance. "
                       "This may lead to unsynchronized communication if a ServiceManager is used elsewhere.")
        return MessageMiddleware()

    logger.info("[COMMUNICATION] Middleware not initialized (not enabled or no source available).")
    return None