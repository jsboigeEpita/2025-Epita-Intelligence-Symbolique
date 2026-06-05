"""Tests for conversational path LLM budget coverage (#950).

Verifies that the conversational orchestrator runs under the LLM budget
circuit breaker, mirroring the sequential path (workflow_dsl.py:334).

Epic #947 Phase 2 — FB-5.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestConversationalLLMBudget:
    """Verify run_conversational_analysis enters llm_budget_scope."""

    def test_llm_budget_scope_importable(self):
        """llm_budget_scope can be imported from invoke_callables."""
        from argumentation_analysis.orchestration.invoke_callables import (
            llm_budget_scope,
        )

        assert callable(llm_budget_scope)

    @pytest.mark.asyncio
    async def test_conversational_enters_budget_scope(self):
        """run_conversational_analysis must enter llm_budget_scope."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _llm_budget,
        )

        # Mock _run_conversational_analysis_inner to check if budget is active
        budget_active = False

        async def _mock_inner(**kwargs):
            nonlocal budget_active
            budget_active = _llm_budget.get() is not None
            return {"state_snapshot": {}, "conversation_log": [], "metrics": {}}

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._run_conversational_analysis_inner",
            side_effect=_mock_inner,
        ):
            from argumentation_analysis.orchestration.conversational_orchestrator import (
                run_conversational_analysis,
            )

            result = await run_conversational_analysis("Test text")

        assert budget_active, (
            "run_conversational_analysis did NOT enter llm_budget_scope — "
            "conversational LLM calls are uncapped (runaway risk from #708)"
        )

    @pytest.mark.asyncio
    async def test_budget_scope_exits_after_run(self):
        """Budget scope must be cleaned up after run_conversational_analysis."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _llm_budget,
        )

        async def _mock_inner(**kwargs):
            return {"state_snapshot": {}, "conversation_log": [], "metrics": {}}

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._run_conversational_analysis_inner",
            side_effect=_mock_inner,
        ):
            from argumentation_analysis.orchestration.conversational_orchestrator import (
                run_conversational_analysis,
            )

            await run_conversational_analysis("Test text")

        # After the run, budget should be cleared
        assert _llm_budget.get() is None, "Budget scope leaked after run"

    @pytest.mark.asyncio
    async def test_budget_exceeded_stops_conversational(self):
        """LLMBudgetExceeded from inner run propagates (budget enforcement works)."""
        from argumentation_analysis.orchestration.invoke_callables import (
            LLMBudgetExceeded,
        )

        async def _mock_inner(**kwargs):
            raise LLMBudgetExceeded("Simulated budget exceeded")

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._run_conversational_analysis_inner",
            side_effect=_mock_inner,
        ):
            from argumentation_analysis.orchestration.conversational_orchestrator import (
                run_conversational_analysis,
            )

            with pytest.raises(LLMBudgetExceeded, match="Simulated budget exceeded"):
                await run_conversational_analysis("Test text")
