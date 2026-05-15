"""DLL load order guard for Windows.

On Windows, importing jpype before torch/transformers causes
``OSError: [WinError 182]`` due to DLL conflicts (fbgemm.dll).
This module must be imported BEFORE any jpype import in production
entry points.

Usage (at the top of any entry point)::

    import argumentation_analysis.core.dll_guard  # noqa: F401

The import is side-effect only — it ensures torch/transformers are
loaded into the process before jpype gets a chance to trigger the
conflict.  It is idempotent (safe to call multiple times).

Currently guarded entry points:
- ``api/main.py`` (FastAPI startup)
- ``argumentation_analysis/run_orchestration.py`` (CLI)
- ``argumentation_analysis/core/bootstrap.py`` (shared init)
"""

import logging
import sys

_guard_applied = False
_logger = logging.getLogger(__name__)


def apply_dll_guard() -> None:
    """Pre-load heavy native libs to avoid WinError 182 on Windows.

    On non-Windows platforms this is a no-op.
    """
    global _guard_applied
    if _guard_applied:
        return
    _guard_applied = True

    if sys.platform != "win32":
        return

    for mod_name in ("torch", "transformers"):
        try:
            __import__(mod_name)
            _logger.debug("DLL guard: pre-loaded %s", mod_name)
        except (ImportError, OSError, RuntimeError):
            _logger.debug("DLL guard: %s not available, skipping", mod_name)


# Apply on import
apply_dll_guard()
