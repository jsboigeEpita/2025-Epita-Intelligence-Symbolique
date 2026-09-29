# Initializer for the core_utils package — submodules re-exported lazily
# (PEP 562).

import importlib
from typing import Any

# Same repair as ``argumentation_analysis.utils`` (#2855): the eager chain ran
# all 17 module bodies on any touch of this package, and
# ``visualization_utils`` imports matplotlib.pyplot and pandas at module level
# (~1 s warm) — paid by callers of ``file_loaders`` / ``network_utils`` /
# ``crypto_utils`` (all on the ``api.main`` path) that need neither.
# ``__getattr__`` imports a sibling on first attribute access and caches it.
__all__ = [
    "cli_utils",
    "crypto_utils",
    "file_loaders",
    "file_savers",
    "file_utils",
    "file_validation_utils",
    "filesystem_utils",
    "logging_utils",
    "markdown_utils",
    "network_utils",
    "parsing_utils",
    "path_operations",
    "reporting_utils",
    "shell_utils",
    "string_utils",
    "text_utils",
    "visualization_utils",
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
