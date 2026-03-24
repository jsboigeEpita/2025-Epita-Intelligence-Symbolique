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
        with patch.dict("sys.modules", {"argumentation_analysis.orchestration.unified_pipeline": None}):
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
        }

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.run_conversational_analysis",
            new_callable=AsyncMock,
            return_value=mock_conv_result,
        ):
            result = await run_unified_analysis("test text", workflow_name="conversational")

        assert "summary" in result
        assert result["summary"]["completed"] == 3
        assert result["summary"]["total"] == 3
        assert result["summary"]["failed"] == 0
        assert result["summary"]["total_messages"] == 1
        assert result["workflow_name"] == "conversational"

    async def test_conversational_fallback_on_error(self):
        """Conversational mode falls back to standard on import/runtime error."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            run_unified_analysis,
        )

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.run_conversational_analysis",
            new_callable=AsyncMock,
            side_effect=ImportError("Module not available"),
        ):
            # Should fall back to standard workflow without raising
            result = await run_unified_analysis("test text", workflow_name="conversational")

        assert result is not None
        # Fell back to standard pipeline, workflow name from catalog
        assert "standard" in result.get("workflow_name", "").lower()

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
