# Make submodules available to the parent package — lazily (PEP 562).

import importlib
from typing import Any

# The eager ``from . import <sibling>`` chain this file used to run was pure
# import-time waste on the ``api.main`` path: ``agents.core.informal`` imports
# only ``taxonomy_loader``, yet every sibling body ran — ``reporting_utils ->
# visualization_generator`` reached seaborn and 75 ``scipy.stats`` modules,
# 719 ms warm for a package touch that needed none of it (#2855).
# ``__getattr__`` imports a sibling on first attribute access and caches it, so
# ``from argumentation_analysis.utils import version_validator`` (and any other
# ``from <package> import <sibling>``) keeps working unchanged.
#
# `unified_pipeline` is an archived shim (deprecated 2026-03-24, #217). It is
# still importable via its explicit path for back-compat, and it is
# deliberately NOT in ``__all__`` — auto-importing it fired DeprecationWarning
# on every `argumentation_analysis.utils` import. Direct callers were migrated
# to `analysis_config` — see commit f0b8e91d.
__all__ = [
    "analysis_comparison",
    "async_manager",
    "cleanup_sensitive_files",
    "config_utils",
    "config_validation",
    "correction_utils",
    "crypto_workflow",
    "data_generation",
    "data_loader",
    "data_processing_utils",
    "debug_utils",
    "error_estimation",
    "metrics_aggregation",
    "metrics_calculator",
    "metrics_extraction",
    "performance_monitoring",
    "report_generator",
    "reporting_utils",
    "restore_config",
    "run_extract_editor",
    "run_verify_extracts_with_llm",
    "system_utils",
    "taxonomy_loader",
    "text_processing",
    "tweety_error_analyzer",
    "update_encrypted_config",
    "version_validator",
    "visualization_generator",
    "dev_tools",
    "extract_repair",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        module = importlib.import_module(f".{name}", __name__)
        globals()[name] = module  # cached; later accesses skip this hook
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list:
    # PEP 562's companion: without it, dir() would stop listing the siblings
    # that are no longer imported eagerly.
    return sorted(set(globals()) | set(__all__))
