# tests/unit/argumentation_analysis/orchestration/test_main_orchestrator_import.py
"""Regression tests for the main_orchestrator entry point import path.

Background
----------
The top-level orchestrator script (`argumentation_analysis/main_orchestrator.py`)
used to import `from argumentation_analysis.orchestration.analysis_runner import
AnalysisRunner`. The legacy `analysis_runner` module was removed, leaving a
broken import that was silently swallowed by a `try/except ImportError`. This
masked a real entry-point failure: launching the CLI without `--mock-llm` and
without an upstream service would reach L210 and never actually execute the
analysis pipeline.

These tests guard against regression to the legacy path AND verify the V2
substitute (`AnalysisRunnerV2`) is reachable and exposes the async `run_analysis`
method with the kwargs the orchestrator passes.
"""

from __future__ import annotations

import inspect
import importlib

import pytest


# The legacy module must stay gone — guard against resurrection.
def test_legacy_analysis_runner_module_remains_absent() -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("argumentation_analysis.orchestration.analysis_runner")


# The canonical V2 entry point must be importable from the path the
# orchestrator now uses.
def test_analysis_runner_v2_importable() -> None:
    mod = importlib.import_module(
        "argumentation_analysis.orchestration.analysis_runner_v2"
    )
    assert hasattr(mod, "AnalysisRunnerV2"), (
        "AnalysisRunnerV2 must be importable from analysis_runner_v2"
    )


# The orchestrator's call site uses `await runner.run_analysis(...)` with
# kwargs text_content + llm_service. Verify the signature matches — if the
# V2 contract drifts again, this test catches it before runtime.
def test_analysis_runner_v2_run_analysis_signature() -> None:
    from argumentation_analysis.orchestration.analysis_runner_v2 import (
        AnalysisRunnerV2,
    )

    method = getattr(AnalysisRunnerV2, "run_analysis", None)
    assert method is not None, "AnalysisRunnerV2.run_analysis must exist"
    sig = inspect.signature(method)
    params = sig.parameters
    assert "text_content" in params, (
        "run_analysis must accept 'text_content' kwarg (see main_orchestrator.py L221)"
    )
    assert "llm_service" in params, (
        "run_analysis must accept 'llm_service' kwarg"
    )
    assert inspect.iscoroutinefunction(method), (
        "run_analysis must be async — main_orchestrator awaits it"
    )


# The orchestrator module itself must be importable. This catches any
# top-level syntax/import regression in the main_orchestrator.py module.
def test_main_orchestrator_module_importable() -> None:
    # Use a spec import to avoid running the module's top-level side effects.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "argumentation_analysis.main_orchestrator",
        "argumentation_analysis/main_orchestrator.py",
    )
    assert spec is not None, "main_orchestrator.py must have a valid module spec"

    # Static AST scan: the legacy import path must NOT appear in source.
    import ast

    with open("argumentation_analysis/main_orchestrator.py", "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename="main_orchestrator.py")

    legacy_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                full = f"{module}.{alias.name}" if module else alias.name
                if "analysis_runner" in module and "v2" not in module:
                    legacy_imports.append(full)

    assert not legacy_imports, (
        f"Legacy non-v2 analysis_runner import(s) still present: {legacy_imports}. "
        "Use 'analysis_runner_v2.AnalysisRunnerV2' instead."
    )