"""Tests for JPype synchronous warmup before DAG execution (#529).

Validates that run_unified_analysis eagerly initialises JVM + Tweety
before parallel DAG phases start, eliminating the race condition that
caused ~20% timeout rates.
"""

import ast
import inspect
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


class TestJpypeWarmup:
    """Verify synchronous JPype warmup in unified_pipeline.py."""

    def test_warmup_code_exists_in_run_unified_analysis(self):
        """run_unified_analysis must contain JPype warmup block."""
        from argumentation_analysis.orchestration import unified_pipeline

        source = inspect.getsource(unified_pipeline.run_unified_analysis)
        assert "TweetyInitializer" in source, (
            "run_unified_analysis should reference TweetyInitializer for warmup"
        )
        assert "ensure_jvm_and_components_are_ready" in source, (
            "run_unified_analysis should call ensure_jvm_and_components_are_ready() "
            "for synchronous JPype warmup"
        )

    def test_warmup_guarded_by_spectacular_check(self):
        """Warmup should only trigger for spectacular workflows."""
        from argumentation_analysis.orchestration import unified_pipeline

        source = inspect.getsource(unified_pipeline.run_unified_analysis)
        assert 'workflow_name == "spectacular"' in source, (
            "Warmup should be guarded by workflow_name == 'spectacular' check"
        )

    def test_warmup_failure_is_non_fatal(self):
        """Warmup failure should log warning, not crash."""
        from argumentation_analysis.orchestration import unified_pipeline

        source = inspect.getsource(unified_pipeline.run_unified_analysis)
        # Find the try/except around warmup
        assert "JPype warmup failed" in source, (
            "Warmup should catch exceptions and log a warning, not propagate"
        )

    @pytest.mark.asyncio
    async def test_warmup_called_before_executor(self):
        """Warmup must execute before WorkflowExecutor.execute()."""
        from argumentation_analysis.orchestration.unified_pipeline import run_unified_analysis

        # Parse the function source to verify ordering
        source = inspect.getsource(run_unified_analysis)
        tree = ast.parse(source)

        func_def = None
        for node in ast.walk(tree):
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "run_unified_analysis":
                func_def = node
                break

        assert func_def is not None

        # Find line numbers for warmup and executor
        warmup_line = None
        executor_line = None
        for node in ast.walk(func_def):
            if isinstance(node, ast.Try):
                # The warmup try block
                for handler in node.handlers:
                    if isinstance(handler.body, list):
                        for stmt in handler.body:
                            if isinstance(stmt, ast.Expr) and isinstance(
                                stmt.value, ast.Call
                            ):
                                if hasattr(stmt.value, "func"):
                                    func = stmt.value.func
                                    if (
                                        isinstance(func, ast.Attribute)
                                        and func.attr == "warning"
                                    ):
                                        warmup_line = stmt.lineno
                                        break
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and (
                    node.func.attr == "execute"
                ):
                    executor_line = node.lineno

        # Warmup (the warning line is in the except, after the try block)
        # The TweetyInitializer call is in the try block
        # Just verify the text ordering in source
        warmup_pos = source.find("TweetyInitializer")
        executor_pos = source.find("executor.execute")
        assert warmup_pos > 0, "TweetyInitializer not found in source"
        assert executor_pos > 0, "executor.execute not found in source"
        assert warmup_pos < executor_pos, (
            "JPype warmup (TweetyInitializer) must appear before executor.execute()"
        )

    def test_jpype_phase_set_covers_all_required_phases(self):
        """The _jpype_phases set should include all phases that use JPype."""
        from argumentation_analysis.orchestration import unified_pipeline

        source = inspect.getsource(unified_pipeline.run_unified_analysis)
        required_phases = [
            "pl", "fol", "modal", "dung_extensions",
            "aspic_analysis", "fol_solver", "modal_solver",
        ]
        for phase in required_phases:
            assert f'"{phase}"' in source, (
                f"_jpype_phases should include '{phase}'"
            )
