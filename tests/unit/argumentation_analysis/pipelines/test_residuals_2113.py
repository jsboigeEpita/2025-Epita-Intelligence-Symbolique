"""Né-rouge guards for the independently removable #2113 residuals.

Measured on pristine ``b7c42955``:

- ``orchestration/operational`` only contains an empty ``__init__.py`` and a
  stale README since ``direct_executor.py`` and its in-tree test were removed
  by #2140;
- ``pipelines/orchestration/core`` is an unimported wrapper around the live
  root service manager; its exception handler can mask the original error;
- ``ExtendedOrchestrationConfig.use_new_orchestrator`` names no existing
  ``MainOrchestrator`` and has no reader.

The separately arbitrated ``analysis`` directory is not guarded here because
its removal also requires disposing of its orphan consumer ``execution/engine.py``.
"""

import inspect
from pathlib import Path

from argumentation_analysis.pipelines.orchestration.config.base_config import (
    ExtendedOrchestrationConfig,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


def _assert_no_source_surface(relative_dir: str):
    target = REPO_ROOT / relative_dir
    assert not list(target.glob("*.py")), f"Python sources remain under {relative_dir}"
    assert not (
        target / "README.md"
    ).exists(), f"stale README remains under {relative_dir}"


def test_operational_shell_is_removed():
    _assert_no_source_surface("argumentation_analysis/orchestration/operational")


def test_orphan_core_wrapper_is_removed():
    _assert_no_source_surface("argumentation_analysis/pipelines/orchestration/core")


def test_dead_new_orchestrator_flag_is_removed():
    signature = inspect.signature(ExtendedOrchestrationConfig)
    assert "use_new_orchestrator" not in signature.parameters
    assert not hasattr(ExtendedOrchestrationConfig(), "use_new_orchestrator")
