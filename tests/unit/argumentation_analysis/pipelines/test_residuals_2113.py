"""Né-rouge guards for the #2113 residual withdrawals.

Measured on pristine ``b7c42955``:

- ``orchestration/operational`` only contains an empty ``__init__.py`` and a
  stale README since ``direct_executor.py`` and its in-tree test were removed
  by #2140;
- ``pipelines/orchestration/core`` is an unimported wrapper around the live
  root service manager; its exception handler can mask the original error;
- ``ExtendedOrchestrationConfig.use_new_orchestrator`` names no existing
  ``MainOrchestrator`` and has no reader;
- ``pipelines/orchestration/analysis`` is consumed only by its parent re-export,
  tests, and the orphan ``execution/engine.py``; coordinator ruling A removes
  that complete dead chain while preserving ``execution/strategies.py``.
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


def test_orphan_analysis_helpers_are_removed():
    _assert_no_source_surface("argumentation_analysis/pipelines/orchestration/analysis")


def test_orphan_execution_engine_is_removed_but_strategies_remain():
    execution = REPO_ROOT / "argumentation_analysis/pipelines/orchestration/execution"
    assert not (execution / "engine.py").exists()
    assert (execution / "strategies.py").exists()


def test_dead_chain_is_not_reexported():
    from argumentation_analysis.pipelines import orchestration

    dead_exports = {
        "Engine",
        "execute_operational_tasks",
        "synthesize_hierarchical_results",
        "post_process_orchestration_results",
        "save_orchestration_trace",
    }
    assert dead_exports.isdisjoint(vars(orchestration))
