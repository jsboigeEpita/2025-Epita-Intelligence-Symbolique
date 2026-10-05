"""DLL load order guard for Windows.

On Windows, importing jpype before torch causes
``OSError: [WinError 182]`` due to DLL conflicts (fbgemm.dll).
This module must be imported BEFORE any jpype import in production
entry points.

Usage (at the top of any entry point)::

    import argumentation_analysis.core.dll_guard  # noqa: F401

The import is side-effect only — it ensures torch is loaded into the
process before jpype gets a chance to trigger the conflict.  It is
idempotent (safe to call multiple times).

#2946: the preload is torch-only. The original pair (#512) also
pre-loaded transformers, whose only role in the fbgemm/libiomp conflict
was to pull torch transitively — torch is pre-loaded directly here.
transformers 4.x drags sklearn, hence pandas, at its own import time
(``sklearn.utils.fixes``), and this guard sits on the ``api.main``
import path, which must stay pandas-free (#2867, measured 13.4 s ->
11.5 s warm). transformers loads on first use instead, when torch is
already in ``sys.modules``.

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

    try:
        __import__("torch")
        _logger.debug("DLL guard: pre-loaded torch")
    except (ImportError, OSError, RuntimeError):
        _logger.debug("DLL guard: torch not available, skipping")


# Apply on import
apply_dll_guard()
