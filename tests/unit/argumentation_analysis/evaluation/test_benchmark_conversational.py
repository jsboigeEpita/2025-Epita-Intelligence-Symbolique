"""Tests for conversational mode in benchmark (#208-L).

Verifies list_available_workflows includes conversational and
run_unified_analysis normalizes conversational result format.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestListAvailableWorkflows:
    """Tests for list_available_workflows function."""

    def test_includes_conversational(self):
        """list_available_workflows includes 'conversational'."""
        from argumentation_analysis.evaluation.multi_model_benchmark import (
            list_available_workflows,
        )

        workflows = list_available_workflows()
        assert "conversational" in workflows

    def test_includes_standard_workflows(self):
        """list_available_workflows includes standard pipeline workflows."""
        from argumentation_analysis.evaluation.multi_model_benchmark import (
            list_available_workflows,
        )

        workflows = list_available_workflows()
        assert "light" in workflows
        assert "standard" in workflows

    def test_fallback_includes_conversational(self):
        """Fallback list includes 'conversational' even when import fails."""
        with patch.dict(
            "sys.modules",
            {"argumentation_analysis.orchestration.unified_pipeline": None},
        ):
            # Force re-import to trigger fallback
            import importlib
            import argumentation_analysis.evaluation.multi_model_benchmark as mod

            # The function catches exceptions and returns the fallback list
            try:
                from argumentation_analysis.orchestration.unified_pipeline import (
                    get_workflow_catalog,
                )
            except Exception:
                pass

            from argumentation_analysis.evaluation.multi_model_benchmark import (
                list_available_workflows,
            )

            workflows = list_available_workflows()
            assert "conversational" in workflows


class TestRunUnifiedAnalysisConversational:
    """Tests for conversational mode in run_unified_analysis."""

    async def test_conversational_result_has_summary(self):
        """Conversational result is normalized with summary dict."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        mock_conv_result = {
            "mode": "conversational",
            "phases": ["extraction", "formal", "synthesis"],
            "conversation_log": [{"agent": "PM", "text": "hello"}],
            "total_messages": 1,
            "duration_seconds": 2.5,
            "state_snapshot": {},
            "state_non_empty_fields": 0,
            "unified_state": None,
            "trace_report": {},
            "workflow_name": "conversational",
            "summary": {
                "completed": 3,
                "failed": 0,
                "skipped": 0,
                "total": 3,
                "total_messages": 1,
            },
        }

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.run_conversational_analysis",
            new_callable=AsyncMock,
            return_value=mock_conv_result,
        ):
            result = await run_unified_analysis(
                "test text", workflow_name="conversational"
            )

        assert "summary" in result
        assert result["summary"]["completed"] == 3
        assert result["summary"]["total"] == 3
        assert result["summary"]["failed"] == 0
        assert result["summary"]["total_messages"] == 1
        assert result["workflow_name"] == "conversational"

    async def test_conversational_fallback_on_error(self):
        """Conversational mode falls back to standard on import/runtime error.

        #1591 family-(a): the verdict is the conversational→standard ROUTING.
        ``workflow_name`` in the result comes from ``workflow.name``
        (unified_pipeline.py:324), i.e. from the workflow object the fallback
        selects (``catalog["standard"]`` at line 175) — NOT from executing it.
        The real standard pipeline running end-to-end billed ~94 LLM requests
        (~35-40 % of the gate, measured #1579) while establishing nothing the
        assertion reads: the routing property holds in a single string.

        Hermétisé calqué sur #1578/#1581 (correct the path, add a structural
        bite): the standard workflow's *execution* is short-circuited by
        mocking ``WorkflowExecutor.execute``. The routing verdict is preserved
        (``workflow.name`` is still "standard") AND a structural bite proves
        the fallback drove it: ``execute`` is reached *only* on the fallback
        path — a successful conversational branch returns early
        (unified_pipeline.py:169) and never calls the executor. So if the
        fallback stops triggering, ``mock_exec.assert_awaited_once()`` fails.

        Non-vacuity (leçon #1588, contrôle DoD #1591): the test fails if the
        routing does not happen — remove the ``side_effect=ImportError`` and
        ``run_conversational_analysis`` succeeds, the early-return fires, the
        executor is never awaited → bite fires. Measured: 94 req → 0 req.
        """
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.run_conversational_analysis",
            new_callable=AsyncMock,
            side_effect=ImportError("Module not available"),
        ), patch(
            "argumentation_analysis.orchestration.unified_pipeline.WorkflowExecutor.execute",
            new_callable=AsyncMock,
            return_value={},
        ) as mock_exec:
            # Should fall back to standard workflow without raising
            result = await run_unified_analysis(
                "test text", workflow_name="conversational"
            )

        assert result is not None
        # Verdict preserved: the fallback routed to the standard workflow
        # (workflow_name comes from workflow.name, not from execution).
        assert "standard" in result.get("workflow_name", "").lower()
        # Structural bite (#1578/#1591): the executor is reached ONLY on the
        # fallback path. A successful conversational branch returns early and
        # never calls execute — so this proves the fallback fired. It also
        # proves the standard workflow (not another) was what the fallback
        # selected: execute's first positional arg is the workflow object.
        mock_exec.assert_awaited_once()
        # execute's first positional arg is the workflow object (self is not
        # recorded: the AsyncMock patch replaces the class attribute without a
        # binding descriptor). This pins WHICH workflow the fallback selected.
        # NB: the catalogued "standard" workflow's .name is "standard_analysis"
        # — same substring verdict as the result assertion above ("light" or
        # "full" would not contain "standard", so the bite still discriminates).
        selected_workflow = mock_exec.call_args.args[0]
        assert "standard" in selected_workflow.name.lower()

    async def test_conversational_preserves_original_fields(self):
        """Normalization adds summary but preserves conversation_log etc."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        mock_conv_result = {
            "mode": "conversational",
            "phases": ["phase1"],
            "conversation_log": [{"agent": "A", "text": "msg"}],
            "total_messages": 5,
            "duration_seconds": 1.0,
            "state_snapshot": {"field": "value"},
            "state_non_empty_fields": 1,
            "unified_state": MagicMock(),
            "trace_report": {"convergence": True},
            "summary": {
                "completed": 1,
                "failed": 0,
                "skipped": 0,
                "total": 1,
                "total_messages": 5,
            },
        }

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.run_conversational_analysis",
            new_callable=AsyncMock,
            return_value=mock_conv_result,
        ):
            result = await run_unified_analysis("text", workflow_name="conversational")

        # Original conversational fields preserved
        assert result["mode"] == "conversational"
        assert result["conversation_log"] == [{"agent": "A", "text": "msg"}]
        assert result["trace_report"] == {"convergence": True}
        # Plus normalized summary
        assert result["summary"]["total_messages"] == 5
