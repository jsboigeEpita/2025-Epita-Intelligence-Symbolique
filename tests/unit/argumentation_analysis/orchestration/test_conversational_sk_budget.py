"""Tests for conversational-path LLM-budget coverage (#1029 / FB-5).

Verifies that SK-native agent calls (AgentGroupChat.invoke / ChatCompletionAgent.invoke)
increment the shared _LLMBudget counter, so the runaway circuit-breaker fires on the
conversational path too (incident #708 — 8h / 12.4K calls).
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import contextmanager


# ---------------------------------------------------------------------------
# 1. _bump_sk_budget — unit tests on the shared counter mechanism
# ---------------------------------------------------------------------------


class TestBumpSKBudget:
    """Verify _bump_sk_budget increments and enforces ceiling."""

    def test_noop_without_active_budget(self):
        """When no budget scope is active, _bump_sk_budget is a no-op."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _bump_sk_budget,
        )

        # Should not raise
        _bump_sk_budget()

    def test_increments_counter(self):
        """When budget scope is active, counter increments."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _bump_sk_budget,
            llm_budget_scope,
        )

        with llm_budget_scope(ceiling=100) as budget:
            assert budget.count == 0
            _bump_sk_budget()
            assert budget.count == 1
            _bump_sk_budget(n=5)
            assert budget.count == 6

    def test_raises_on_ceiling_exceeded(self):
        """When budget ceiling is exceeded, LLMBudgetExceeded is raised."""
        from argumentation_analysis.orchestration.invoke_callables import (
            LLMBudgetExceeded,
            _bump_sk_budget,
            llm_budget_scope,
        )

        with llm_budget_scope(ceiling=3) as budget:
            _bump_sk_budget()  # count=1
            _bump_sk_budget()  # count=2
            _bump_sk_budget()  # count=3

            with pytest.raises(LLMBudgetExceeded, match="budget exceeded"):
                _bump_sk_budget()  # count=4 > 3

    def test_budget_shared_with_guarded_completion(self):
        """SK budget bumps and _guarded_chat_completion share the same counter."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _bump_sk_budget,
            _llm_budget,
            llm_budget_scope,
        )

        with llm_budget_scope(ceiling=100) as budget:
            _bump_sk_budget(n=10)
            # Read the counter directly via ContextVar
            active = _llm_budget.get()
            assert active.count == 10

    def test_importable_from_conversational_orchestrator(self):
        """_bump_sk_budget is re-exported via conversational_orchestrator."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _bump_sk_budget,
        )

        assert callable(_bump_sk_budget)

    def test_importable_from_conversational_executor(self):
        """_bump_sk_budget is re-exported via conversational_executor."""
        from argumentation_analysis.orchestration.conversational_executor import (
            _bump_sk_budget,
        )

        assert callable(_bump_sk_budget)


# ---------------------------------------------------------------------------
# 2. _run_phase integration — budget bumps once per agent turn (per-call)
# ---------------------------------------------------------------------------


class TestRunPhaseBudgetIntegration:
    """Verify _run_phase bumps budget once per agent turn, not per streaming chunk."""

    @pytest.mark.asyncio
    async def test_round_robin_path_bumps_per_call(self):
        """Each agent.invoke() call bumps budget exactly once, regardless of chunks.

        The bump is placed BEFORE the async-for loop (NanoClaw concern #1):
        one LLM API call = one budget tick, not one per streaming chunk.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_phase,
        )
        from argumentation_analysis.orchestration.invoke_callables import (
            llm_budget_scope,
        )

        # Create mock agent that yields 5 chunks per invoke (simulates streaming)
        mock_agent = MagicMock()
        mock_agent.name = "TestAgent"

        async def _mock_invoke(history):
            for i in range(5):
                yield MagicMock(content=f"chunk {i}", name="TestAgent")

        mock_agent.invoke = _mock_invoke

        # Force ImportError for AgentGroupChat (triggers round-robin fallback)
        with patch(
            "semantic_kernel.agents.AgentGroupChat",
            side_effect=ImportError("SK not available"),
            create=True,
        ):
            with llm_budget_scope(ceiling=100) as budget:
                messages = await _run_phase(
                    agents=[mock_agent],
                    initial_prompt="test",
                    max_turns=3,
                    phase_name="test_phase",
                    state=MagicMock(),
                    enable_growth_validation=False,
                )

                # Budget should be bumped exactly 3 times (1 per turn, not 5 per chunk)
                assert budget.count == 3, (
                    f"Expected budget=3 (per-call), got {budget.count}. "
                    f"Per-chunk bumping would give 15 (3×5)."
                )

    @pytest.mark.asyncio
    async def test_budget_cap_stops_phase(self):
        """LLMBudgetExceeded propagates out of _run_phase (anti-theater #1019).

        The per-turn try/except re-raises LLMBudgetExceeded so the budget
        guard stops the pipeline instead of just logging.
        """
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_phase,
        )
        from argumentation_analysis.orchestration.invoke_callables import (
            LLMBudgetExceeded,
            llm_budget_scope,
        )

        mock_agent = MagicMock()
        mock_agent.name = "RunawayAgent"

        # Each invoke yields 1 chunk — bump is per-call
        async def _mock_invoke(history):
            yield MagicMock(content="response", name="RunawayAgent")

        mock_agent.invoke = _mock_invoke

        with patch(
            "semantic_kernel.agents.AgentGroupChat",
            side_effect=ImportError("SK not available"),
            create=True,
        ):
            with llm_budget_scope(ceiling=2) as budget:
                with pytest.raises(LLMBudgetExceeded, match="budget exceeded"):
                    await _run_phase(
                        agents=[mock_agent],
                        initial_prompt="test",
                        max_turns=10,
                        phase_name="runaway_test",
                        state=MagicMock(),
                        enable_growth_validation=False,
                    )

                # Counter should be at ceiling + 1 (the bump that triggered)
                assert budget.count > budget.ceiling, (
                    f"Budget counter ({budget.count}) should exceed ceiling ({budget.ceiling})."
                )


# ---------------------------------------------------------------------------
# 3. Non-regression — budget scope is entered on conversational path
# ---------------------------------------------------------------------------


class TestConversationalBudgetScopeEntered:
    """Non-regression: budget scope is entered on the conversational path."""

    def test_budget_scope_entered_in_run_conversational(self):
        """run_conversational_analysis enters llm_budget_scope."""
        # This is verified by the existing test_conversational_llm_budget.py
        # Here we just confirm the import chain works
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        assert callable(run_conversational_analysis)
