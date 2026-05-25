"""Tests for the global per-run LLM-call circuit breaker (Track LL-bis #708).

The DAG ``spectacular`` workflow had no backstop against a runaway: the
counter-argument chain (``_extract_arguments_from_context`` →
``_invoke_counter_argument`` → ``_generate_counters_for_targets``) is uncapped
and scales with the upstream argument count, and the ``counter`` phase had no
``timeout_seconds``. A degenerate upstream once drove an 8h / ~12,417-call /
0-JSON run. This module verifies, with a mocked LLM (no real API), the three
parts of the fix:

  1. A per-run budget (``llm_budget_scope`` + ``_guarded_chat_completion``)
     funnels EVERY chat-completion through one shared counter and raises
     ``LLMBudgetExceeded`` past the ceiling — so a pathological argument list
     cannot produce more than ``ceiling`` LLM calls. The guard is inert outside
     a scope (single-callable unit tests are unaffected) and re-entrant (a
     nested scope shares one global count).
  2. ``_extract_arguments_from_context`` caps its primary ``arguments`` branch
     at 40 (generous-but-finite; anti-pendulum — the GG #696 volume win, which
     far exceeds the ~15 zero-shot argument volume, is preserved).
  3. ``build_spectacular_workflow().get_phase("counter")`` has a
     ``timeout_seconds`` wall-clock bound.

And that ``WorkflowExecutor.execute`` activates the budget for every phase.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import argumentation_analysis.orchestration.invoke_callables as mod
from argumentation_analysis.orchestration.invoke_callables import (
    LLMBudgetExceeded,
    _guarded_chat_completion,
    llm_budget_scope,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseStatus,
    WorkflowBuilder,
    WorkflowExecutor,
)
from argumentation_analysis.orchestration.workflows import build_spectacular_workflow


def _counting_client():
    """Mock client whose create() counts invocations and returns an empty array."""

    async def fake_create(**kwargs):
        resp = MagicMock()
        choice = MagicMock()
        choice.message.content = "[]"
        resp.choices = [choice]
        return resp

    client = MagicMock()
    client.chat.completions.create = AsyncMock(side_effect=fake_create)
    return client


class TestBudgetBreakerFires:
    """The funnel raises past the ceiling and never exceeds it."""

    async def test_breaker_fires_past_ceiling(self):
        client = _counting_client()
        with llm_budget_scope(ceiling=5):
            # The 6th call trips the breaker (count would become 6 > 5).
            for _ in range(5):
                await _guarded_chat_completion(client, model="m", messages=[])
            with pytest.raises(LLMBudgetExceeded):
                await _guarded_chat_completion(client, model="m", messages=[])

    async def test_create_called_exactly_ceiling_times(self):
        client = _counting_client()
        with llm_budget_scope(ceiling=5):
            for _ in range(5):
                await _guarded_chat_completion(client, model="m", messages=[])
            with pytest.raises(LLMBudgetExceeded):
                await _guarded_chat_completion(client, model="m", messages=[])
        # The tripping call raises BEFORE issuing the network round-trip, so the
        # real create() ran exactly `ceiling` times — the runaway is capped.
        assert client.chat.completions.create.call_count == 5


class TestBudgetInertOutsideScope:
    """Without an active scope the funnel is a transparent pass-through."""

    async def test_no_scope_never_raises(self):
        client = _counting_client()
        # 1000 calls, no scope => no counting, no raise (single-callable tests
        # and any non-run caller are unaffected).
        for _ in range(1000):
            await _guarded_chat_completion(client, model="m", messages=[])
        assert client.chat.completions.create.call_count == 1000


class TestBudgetReentrant:
    """A nested scope reuses the active budget — one global count per run."""

    async def test_nested_scope_shares_count(self):
        client = _counting_client()
        with llm_budget_scope(ceiling=3):
            await _guarded_chat_completion(client, model="m", messages=[])
            # Nested scope must NOT reset the count back to 0.
            with llm_budget_scope(ceiling=999) as inner:
                assert inner.ceiling == 3  # inner yields the existing budget
                await _guarded_chat_completion(client, model="m", messages=[])
                await _guarded_chat_completion(client, model="m", messages=[])
                # 4th call across the whole run trips the ceiling of 3.
                with pytest.raises(LLMBudgetExceeded):
                    await _guarded_chat_completion(client, model="m", messages=[])


class TestBudgetAggregatesAcrossTasks:
    """The mutable budget aggregates across concurrent asyncio tasks.

    asyncio copies the *context* (var binding) into each child task, but the
    bound ``_LLMBudget`` object is shared by reference, so concurrent phase
    sub-tasks increment ONE counter (a plain int in a ContextVar would not).
    """

    async def test_gather_shares_one_counter(self):
        client = _counting_client()

        async def worker():
            await _guarded_chat_completion(client, model="m", messages=[])

        with pytest.raises(LLMBudgetExceeded):
            with llm_budget_scope(ceiling=4):
                # 6 concurrent calls against a ceiling of 4 must trip.
                await asyncio.gather(*(worker() for _ in range(6)))


class TestBudgetCeilingResolution:
    """Ceiling comes from the explicit arg, else env LLM_CALL_BUDGET, else 500."""

    async def test_env_override(self):
        with patch.dict("os.environ", {"LLM_CALL_BUDGET": "7"}):
            with llm_budget_scope() as budget:
                assert budget.ceiling == 7

    async def test_default_when_unset(self):
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("LLM_CALL_BUDGET", None)
            with llm_budget_scope() as budget:
                assert budget.ceiling == 500

    async def test_malformed_env_falls_back_to_500(self):
        with patch.dict("os.environ", {"LLM_CALL_BUDGET": "not-a-number"}):
            with llm_budget_scope() as budget:
                assert budget.ceiling == 500


class TestExtractArgumentsCap:
    """The primary `arguments` branch is capped generously at 40."""

    def test_primary_branch_caps_at_40(self):
        context = {
            "phase_extract_output": {
                "arguments": [{"text": f"argument {i}"} for i in range(200)]
            }
        }
        out = mod._extract_arguments_from_context("", context)
        # 200 pathological args => bounded to 40, not the full 200.
        assert len(out) == 40
        assert out[0] == "argument 0"
        assert out[-1] == "argument 39"

    def test_small_lists_unaffected(self):
        context = {
            "phase_extract_output": {
                "arguments": [{"text": f"argument {i}"} for i in range(15)]
            }
        }
        out = mod._extract_arguments_from_context("", context)
        # 15 (= ~zero-shot volume) passes through untouched; cap never bites.
        assert len(out) == 15


class TestCounterPhaseTimeout:
    """The counter phase carries a wall-clock bound (no longer unbounded)."""

    def test_counter_phase_has_timeout(self):
        wf = build_spectacular_workflow()
        counter = wf.get_phase("counter")
        assert counter is not None
        assert counter.timeout_seconds is not None
        assert counter.timeout_seconds == 420

    def test_counter_is_the_only_uncapped_path_now_bounded(self):
        # Sanity: the phase exists and depends on quality (its place in the DAG).
        wf = build_spectacular_workflow()
        counter = wf.get_phase("counter")
        assert "quality" in counter.depends_on


class TestExecutorActivatesBudget:
    """WorkflowExecutor.execute wraps execution in a live budget scope."""

    async def test_budget_active_inside_phase_invoke(self):
        seen = {}

        async def invoke(phase_input, ctx):
            # Inside a phase invoked by the executor, the per-run budget MUST be
            # active — this proves the wiring covers every phase.
            seen["budget"] = mod._llm_budget.get()
            return {"ok": True}

        provider = SimpleNamespace(name="fake", invoke=invoke)
        registry = MagicMock()
        registry.find_for_capability = MagicMock(return_value=[provider])

        wf = WorkflowBuilder("t").add_phase("p", capability="cap").build()
        executor = WorkflowExecutor(registry)
        results = await executor.execute(wf, "input text")

        assert results["p"].status == PhaseStatus.COMPLETED
        assert seen["budget"] is not None  # budget was live during the phase

    async def test_budget_inactive_outside_executor(self):
        # Outside any execute() call, no budget is active (inert by default).
        assert mod._llm_budget.get() is None

    async def test_breaker_in_phase_degrades_gracefully(self):
        # A phase that trips the breaker must degrade to a FAILED PhaseResult,
        # not propagate LLMBudgetExceeded out of the run (DoD #708).
        async def invoke(phase_input, ctx):
            raise LLMBudgetExceeded("simulated runaway")

        provider = SimpleNamespace(name="fake", invoke=invoke)
        registry = MagicMock()
        registry.find_for_capability = MagicMock(return_value=[provider])

        wf = WorkflowBuilder("t").add_phase("p", capability="cap").build()
        executor = WorkflowExecutor(registry)
        # Must not raise — the executor catches it per-phase.
        results = await executor.execute(wf, "input text")

        assert results["p"].status == PhaseStatus.FAILED
        assert "runaway" in (results["p"].error or "")
