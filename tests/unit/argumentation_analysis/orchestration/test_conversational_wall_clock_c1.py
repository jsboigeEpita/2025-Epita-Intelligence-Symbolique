# -*- coding: utf-8 -*-
"""Tests for C1 #1500 — wall-clock bounded termination of the conversational mode.

The conversational mode was turn-bounded (CONV-C #1334 ``max_total_turns``)
but WALL-CLOCK-unbounded: on a real (slow) LLM each turn is a round-trip, so
a turn-bounded run could still exceed 600s (the R653 firsthand finding that
motivated Epic #1500). C1 adds an internal ``max_wall_seconds`` budget that,
on exhaustion, exits the phase loop CLEANLY between turns — the partial state
accumulated so far IS the verdict (anti-#1019: a real bounded verdict, not a
``return None`` nor a coroutine killed by an external ``asyncio.wait_for``).

These tests are deterministic and LLM-free:

* ``WallClockBudget`` — pure unit tests of the deadline helper.
* ``run_conversational_analysis`` — param forwarding (mirrors the
  ``test_conversational_llm_budget`` pattern: patches ``_run_conversational_
  analysis_inner`` so no kernel/LLM is built).
* ``_run_phase`` — the per-turn deadline check breaks the round-robin loop
  before the first agent is invoked (AgentGroupChat is forced to raise so the
  fallback path runs — no real SK chat, no LLM).

The harness-side contract (internal bound → real partial verdict) is covered
in ``tests/scripts/test_compare_orchestration_modes_1480.py``.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

# ── WallClockBudget (pure unit) ───────────────────────────────────────────


class TestWallClockBudget:
    """The deadline helper is the crux of C1 — test it in isolation."""

    def test_inactive_when_max_seconds_is_none(self) -> None:
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            WallClockBudget,
        )

        budget = WallClockBudget(max_seconds=None, start=1000.0)
        assert budget.active is False
        assert budget.deadline is None
        # Never exhausted when inactive — the run stays wall-clock-unbounded.
        assert budget.is_exhausted(now=9999.0) is False

    def test_active_when_max_seconds_set(self) -> None:
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            WallClockBudget,
        )

        budget = WallClockBudget(max_seconds=10.0, start=1000.0)
        assert budget.active is True
        assert budget.deadline == 1010.0

    def test_is_exhausted_false_before_deadline(self) -> None:
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            WallClockBudget,
        )

        budget = WallClockBudget(max_seconds=10.0, start=1000.0)
        assert budget.is_exhausted(now=1000.0) is False
        assert budget.is_exhausted(now=1005.0) is False
        assert budget.is_exhausted(now=1009.99) is False

    def test_is_exhausted_true_at_and_after_deadline(self) -> None:
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            WallClockBudget,
        )

        budget = WallClockBudget(max_seconds=10.0, start=1000.0)
        assert budget.is_exhausted(now=1010.0) is True  # boundary: at deadline
        assert budget.is_exhausted(now=1010.001) is True
        assert budget.is_exhausted(now=9999.0) is True


# ── run_conversational_analysis forwards max_wall_seconds ────────────────


class TestRunConversationalForwardsWallClock:
    """The outer wrapper must forward ``max_wall_seconds`` to the inner run."""

    @pytest.mark.asyncio
    async def test_max_wall_seconds_forwarded_to_inner(self) -> None:
        captured: dict = {}

        async def _mock_inner(**kwargs):
            captured.update(kwargs)
            return {
                "state_snapshot": {},
                "conversation_log": [],
                "budget": {"wall_clock_bounded": False},
            }

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._run_conversational_analysis_inner",
            side_effect=_mock_inner,
        ):
            from argumentation_analysis.orchestration.conversational_orchestrator import (
                run_conversational_analysis,
            )

            await run_conversational_analysis("test text", max_wall_seconds=42.0)

        assert captured.get("max_wall_seconds") == 42.0, (
            "C1 regression: run_conversational_analysis did not forward "
            "max_wall_seconds to _run_conversational_analysis_inner."
        )

    @pytest.mark.asyncio
    async def test_max_wall_seconds_defaults_to_none(self) -> None:
        """Default None preserves the prior wall-clock-unbounded behaviour
        (turn-cap only) for callers that do not opt in (anti-pendule)."""
        captured: dict = {}

        async def _mock_inner(**kwargs):
            captured.update(kwargs)
            return {
                "state_snapshot": {},
                "conversation_log": [],
                "budget": {"wall_clock_bounded": False},
            }

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator"
            "._run_conversational_analysis_inner",
            side_effect=_mock_inner,
        ):
            from argumentation_analysis.orchestration.conversational_orchestrator import (
                run_conversational_analysis,
            )

            await run_conversational_analysis("test text")

        assert captured.get("max_wall_seconds") is None


# ── _run_phase per-turn deadline ──────────────────────────────────────────


class TestRunPhaseDeadline:
    """The per-turn deadline check lets a bounded phase exit cleanly between
    turns, preserving the partial conversation as the verdict (anti-#1019)."""

    @pytest.mark.asyncio
    async def test_deadline_in_past_breaks_before_first_turn(self) -> None:
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_phase,
        )

        state = RhetoricalAnalysisState("test text")
        fake_agent = MagicMock()
        fake_agent.name = "FakeAgent"

        # Force the round-robin fallback by making the SK AgentGroupChat raise
        # on construction — no real SK chat, no LLM call.
        with patch(
            "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat",
            side_effect=RuntimeError("force round-robin for test"),
        ):
            # deadline already in the past → must break before turn 1.
            messages = await _run_phase(
                [fake_agent],
                "initial prompt",
                max_turns=5,
                phase_name="Extraction & Detection",
                state=state,
                enable_growth_validation=False,
                deadline=time.time(),
            )

        assert messages == [], (
            "C1 regression: with a past deadline, _run_phase should run ZERO "
            f"turns (clean between-turn exit), got {len(messages)} message(s)."
        )

    @pytest.mark.asyncio
    async def test_no_deadline_runs_as_before(self) -> None:
        """With deadline=None the phase behaves exactly as before C1 — the
        round-robin loop runs at least one turn (anti-pendule: the bound is
        opt-in, not an always-on truncation)."""
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_phase,
        )

        state = RhetoricalAnalysisState("test text")
        fake_agent = MagicMock()
        fake_agent.name = "FakeAgent"

        # Stub invoke() so round-robin yields one fast message, then the
        # max_turns=1 cap ends the loop (deterministic, no LLM).
        async def fake_invoke(chat_history):
            msg = MagicMock()
            msg.content = "stub response"
            yield msg

        fake_agent.invoke = fake_invoke

        with patch(
            "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat",
            side_effect=RuntimeError("force round-robin for test"),
        ):
            messages = await _run_phase(
                [fake_agent],
                "initial prompt",
                max_turns=1,
                phase_name="Extraction & Detection",
                state=state,
                enable_growth_validation=False,
                deadline=None,
            )

        assert len(messages) == 1, (
            "C1 regression: with deadline=None and max_turns=1, _run_phase "
            f"should run exactly 1 turn, got {len(messages)}."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
