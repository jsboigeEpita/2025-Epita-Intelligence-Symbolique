"""Core package for the project.

This package contains the functional core of the application,
including utilities, pipelines, and other essential modules.
It serves as the primary entry point for accessing the project's
core functionalities.
"""

import importlib
from typing import Any

# from .bootstrap import * # COMMENTÉ - L'initialisation doit être explicite

# Exports principaux, servis paresseusement (PEP 562).
# L'import eager de ``llm_service`` faisait payer ``semantic_kernel`` (2.24 s à
# chaud) à tout contact de ce paquet sur le chemin ``api.main`` (#2855).
# ``shared_state`` est bon marché mais reçoit le même traitement : un contact
# de paquet n'exécute plus aucun corps de sous-module.
__all__ = ["RhetoricalAnalysisState", "create_llm_service"]

_LAZY_EXPORTS = {
    "RhetoricalAnalysisState": (".shared_state", "RhetoricalAnalysisState"),
    "create_llm_service": (".llm_service", "create_llm_service"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module_name, attribute = _LAZY_EXPORTS[name]
        value = getattr(importlib.import_module(module_name, __name__), attribute)
        globals()[name] = value  # cached; later accesses skip this hook
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    # PEP 562's companion: without it, dir() would stop listing the lazy names.
    return sorted(set(globals()) | set(__all__))


# Import conditionnel pour éviter la dépendance circulaire
def get_argumentation_analyzer():
    """Importe et retourne ArgumentationAnalyzer de manière lazy."""
    from .argumentation_analyzer import ArgumentationAnalyzer

    return ArgumentationAnalyzer


def get_analyzer():
    """Importe et retourne Analyzer de manière lazy."""
    from .argumentation_analyzer import Analyzer

    return Analyzer
