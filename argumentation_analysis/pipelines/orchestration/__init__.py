# argumentation_analysis/pipelines/orchestration/__init__.py

"""Residual configuration and service aliases for pipeline orchestration."""

# 1. Configuration Essentielle
from .config.base_config import ExtendedOrchestrationConfig
from .config.enums import OrchestrationMode, AnalysisType

# 2. Composants Core du Système
try:
    from argumentation_analysis.core.communication import (
        MessageMiddleware as Middleware,
    )
except ImportError:
    Middleware = None

try:
    from argumentation_analysis.orchestration.service_manager import (
        OrchestrationServiceManager as ServiceManager,
    )
except ImportError:
    ServiceManager = None

# 3. Orchestrateurs Spécialisés (Wrappers) — withdrawn (#2111): the two
# wrappers had zero instantiation in production and tests; the shell
# orchestrators/ directory went with them.

__all__ = [
    # Config
    "ExtendedOrchestrationConfig",
    "OrchestrationMode",
    "AnalysisType",
    # Core
    "Middleware",
    "ServiceManager",
]
