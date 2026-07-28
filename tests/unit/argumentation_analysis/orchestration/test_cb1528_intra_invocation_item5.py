# -*- coding: utf-8 -*-
"""Tests for CB #1528 item 5 — the intra-invocation wall-clock bound.

Firsthand measurement recorded on #1528 (R716/R717, published by the
coordinator): the live (CD #1534) AgentGroupChat path's first ``chat.invoke()``
drives a function-calling agent that chains ~12 LLM round-trips before yielding
a single response. Every inter-turn deadline guard (item 3 #1544 / item 4 #1546)
checks BETWEEN turns — none can fire inside a turn that never ends. So a tight
wall-clock budget was blown by ONE invocation and the external net caught it,
throwing away a populated state (arguments written seconds before the cut).

Item 5 closes that path: ``_bounded_invoke`` wraps the invocation generator and
bounds EACH ``__anext__`` to the remaining budget. On timeout the in-flight
response is lost, but the shared ``state`` is NOT — plugins wrote to it during
the invocation, and the ``CancelledError`` raised at the await point leaves
those writes intact. The partial state becomes the honest partial verdict.

These tests are LLM-free and deterministic. They exercise the REAL ``_run_phase``
with a mocked ``AgentGroupChat`` whose ``invoke()`` simulates the stuck turn
(an ``asyncio.sleep`` that never yields within the budget) — the exact shape
the measurement diagnosed. The first test is mutation-verified: remove the
``_bounded_invoke`` wrap at the call site and it hangs (timeout → red).

Anti-pendule (from the dispatch): a SINGLE mechanism, derived from the existing
``deadline`` (no second budget); when ``deadline`` is None the generator is
yielded unchanged (no-op for unbounded runs).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import List
from unittest.mock import MagicMock, patch

import pytest

_AGENT_GROUP_CHAT = "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat"


class _FakeMsg:
    """Minimal stand-in for an SK ``ChatMessageContent``-like response."""

    def __init__(self, name: str, content: str = "ok") -> None:
        self.name = name
        self.content = content


class _StuckInvokeChat:
    """A fake ``AgentGroupChat`` whose first ``invoke().__anext__`` never
    returns within the budget.

    Mirrors the measured shape: the agent chains many LLM round-trips inside a
    single ``__anext__`` before yielding. ``state_writer`` (if provided) is
    called BEFORE the long sleep — simulating plugins writing to the shared
    ``state`` DURING the invocation, which must survive the cut.
    """

    def __init__(self, state_writer=None, stuck_seconds: float = 10.0) -> None:
        self._state_writer = state_writer
        self._stuck_seconds = stuck_seconds

    async def add_chat_message(self, _msg) -> None:  # noqa: ANN001 — SK signature
        return None

    def invoke(self):
        return self._gen()

    async def _gen(self):
        if self._state_writer is not None:
            self._state_writer()
        # The ~12 LLM round-trips that never yield control back to the loop.
        await asyncio.sleep(self._stuck_seconds)
        yield _FakeMsg("unreachable")  # pragma: no cover — the bound cuts first


class _QuickYieldChat:
    """A fake ``AgentGroupChat`` that yields promptly — the unbounded (no
    deadline) path must iterate it unchanged."""

    def __init__(self, names: List[str]) -> None:
        self._names = names

    async def add_chat_message(self, _msg) -> None:  # noqa: ANN001
        return None

    def invoke(self):
        return self._gen()

    async def _gen(self):
        for name in self._names:
            await asyncio.sleep(0)  # yield control to the loop between turns
            yield _FakeMsg(name)


def _run_phase_import():
    from argumentation_analysis.orchestration.conversational_orchestrator import (
        _run_phase,
    )

    return _run_phase


# ── Behavioural: the bound cuts a stuck first turn ─────────────────────────


class TestIntraInvocationBoundCutsStuckTurn:
    """The bound fires INSIDE a single ``chat.invoke()`` that never yields."""

    @pytest.mark.asyncio
    async def test_stuck_first_turn_is_cut_within_budget(self) -> None:
        """A first ``__anext__`` that never returns is cut by the bound.

        Mutation-verified: remove the ``_bounded_invoke`` wrap at the group-chat
        call site and this test hangs on the ``asyncio.sleep(10)`` until the
        pytest per-test timeout kills it (red). With the wrap, ``wait_for``
        raises ``TimeoutError`` at ``deadline - now`` (~0.05 s here) and the
        phase returns with zero messages — the response in flight was lost, but
        the run did not hang and the populated ``state`` is preserved (next
        test).
        """
        _run_phase = _run_phase_import()
        from argumentation_analysis.core.shared_state import (
            RhetoricalAnalysisState,
        )

        state = RhetoricalAnalysisState("test text")
        fake_agent = MagicMock()
        fake_agent.name = "FakeAgent"

        chat = _StuckInvokeChat()
        chat_cls = MagicMock(return_value=chat)

        tight_deadline = time.time() + 0.05
        start = time.time()
        with patch(_AGENT_GROUP_CHAT, chat_cls):
            messages = await _run_phase(
                [fake_agent],
                "initial prompt",
                max_turns=5,
                phase_name="Extraction & Detection",
                state=state,
                enable_growth_validation=False,
                deadline=tight_deadline,
            )
        elapsed = time.time() - start

        assert elapsed < 2.0, (
            f"CB #1528 item 5 regression: the intra-invocation bound did NOT "
            f"fire — _run_phase took {elapsed:.2f}s (stuck turn hung). Remove "
            f"the _bounded_invoke wrap and this hangs until the test timeout."
        )
        assert messages == [], (
            f"the stuck first __anext__ must be cut before ANY message is "
            f"yielded; got {len(messages)} message(s)."
        )

    @pytest.mark.asyncio
    async def test_stuck_turn_state_survives_the_cut(self) -> None:
        """The shared ``state`` written DURING the stuck invocation survives.

        This is the non-trivial point of item 5: the in-flight response is lost,
        but plugins have already written to ``state`` before the cut. Those
        writes are the honest partial verdict — NOT a hole. A ``CancelledError``
        at the await point does not unwind mutations made to the shared mutable
        ``state`` object.
        """
        _run_phase = _run_phase_import()
        from argumentation_analysis.core.shared_state import (
            RhetoricalAnalysisState,
        )

        state = RhetoricalAnalysisState("test text")

        def _plugin_write():
            # Plugins mutate the shared state DURING the invocation.
            state._intra_invocation_marker = "written-before-cut"

        chat = _StuckInvokeChat(state_writer=_plugin_write)
        chat_cls = MagicMock(return_value=chat)

        with patch(_AGENT_GROUP_CHAT, chat_cls):
            await _run_phase(
                [MagicMock(name="FakeAgent")],
                "initial prompt",
                max_turns=5,
                phase_name="Extraction & Detection",
                state=state,
                enable_growth_validation=False,
                deadline=time.time() + 0.05,
            )

        assert getattr(state, "_intra_invocation_marker", None) == (
            "written-before-cut"
        ), (
            "CB #1528 item 5: the partial state written during the stuck "
            "invocation was lost at the cut — the verdict partial must be REAL."
        )

    @pytest.mark.asyncio
    async def test_stuck_turn_cut_is_logged_loud(self, caplog) -> None:
        """The cut is a NAMED log, not a drowned INFO (DoD #2).

        Uses the named-logger capture validated in R713/R720 (the project
        re-installs root handlers mid-import, evicting a plain ``caplog``
        handler; pinning the level on the named logger survives that).
        """
        _run_phase = _run_phase_import()
        from argumentation_analysis.core.shared_state import (
            RhetoricalAnalysisState,
        )

        state = RhetoricalAnalysisState("test text")
        chat = _StuckInvokeChat()
        chat_cls = MagicMock(return_value=chat)

        with caplog.at_level(logging.INFO, logger="ConversationalOrchestrator"), patch(
            _AGENT_GROUP_CHAT, chat_cls
        ):
            await _run_phase(
                [MagicMock(name="FakeAgent")],
                "initial prompt",
                max_turns=5,
                phase_name="Extraction & Detection",
                state=state,
                enable_growth_validation=False,
                deadline=time.time() + 0.05,
            )

        assert any(
            "borne intra-invocation" in rec.getMessage()
            and "CB #1528 item 5" in rec.getMessage()
            for rec in caplog.records
        ), (
            f"the intra-invocation cut must be a NAMED log mentioning "
            f"'borne intra-invocation CB #1528 item 5'; got records: "
            f"{[r.getMessage() for r in caplog.records]}"
        )

    @pytest.mark.asyncio
    async def test_mutation_without_the_bound_the_turn_is_not_cut(self) -> None:
        """DoD mutation check, automated so it cannot rot: with ``_bounded_invoke``
        neutralized to identity at the module reference, the stuck first turn is
        NOT cut — it hangs for the full ``stuck_seconds``. This is the explicit
        counterpart to ``test_stuck_first_turn_is_cut_within_budget``: together
        they prove the bound is the thing cutting the turn, and that removing it
        re-opens the defect.

        ``stuck_seconds`` is kept short (1.5 s) to bound CI cost while staying
        comfortably above the 0.05 s budget the cut test uses.
        """
        _run_phase = _run_phase_import()
        from argumentation_analysis.core.shared_state import (
            RhetoricalAnalysisState,
        )

        async def _identity_invoke(async_gen, _deadline, _phase, _path):
            async for r in async_gen:
                yield r

        state = RhetoricalAnalysisState("test text")
        chat = _StuckInvokeChat(stuck_seconds=1.5)
        chat_cls = MagicMock(return_value=chat)

        start = time.time()
        with patch(_AGENT_GROUP_CHAT, chat_cls), patch(
            "argumentation_analysis.orchestration.conversational_orchestrator."
            "_bounded_invoke",
            _identity_invoke,
        ):
            messages = await _run_phase(
                [MagicMock(name="FakeAgent")],
                "initial prompt",
                max_turns=5,
                phase_name="Extraction & Detection",
                state=state,
                enable_growth_validation=False,
                deadline=time.time() + 0.05,
            )
        elapsed = time.time() - start

        assert elapsed >= 1.2, (
            f"Mutation check: with _bounded_invoke neutralized, the stuck turn "
            f"should hang for the full stuck_seconds (~1.5s); elapsed={elapsed:.2f}s "
            f"means something ELSE cut the turn — the bound is no longer load-bearing."
        )
        # With the bound removed, the stuck generator eventually completes and
        # yields its single response — i.e. the turn was NOT cut at the budget
        # (0.05 s) but ran to completion (~1.5 s). That is exactly the
        # pre-item-5 defect the bound closes.
        assert len(messages) == 1, (
            f"with the bound removed the stuck turn completes and yields once; "
            f"got {len(messages)} message(s)."
        )


# ── Non-regression: the unbounded path is unchanged ────────────────────────


class TestUnboundedPathUnchanged:
    """When ``deadline`` is None the bound is a no-op — the generator yields
    normally. Anti-pendule: item 5 must not change the unbounded run."""

    @pytest.mark.asyncio
    async def test_no_deadline_iterates_normally(self) -> None:
        _run_phase = _run_phase_import()
        from argumentation_analysis.core.shared_state import (
            RhetoricalAnalysisState,
        )

        state = RhetoricalAnalysisState("test text")
        chat = _QuickYieldChat(["Agent-A", "Agent-B"])
        chat_cls = MagicMock(return_value=chat)

        with patch(_AGENT_GROUP_CHAT, chat_cls):
            messages = await _run_phase(
                [MagicMock(name="FakeAgent")],
                "initial prompt",
                max_turns=2,
                phase_name="Extraction & Detection",
                state=state,
                enable_growth_validation=False,
                deadline=None,  # unbounded — the bound must be a no-op
            )

        assert len(messages) == 2, (
            f"with no deadline the generator must yield normally (2 turns); "
            f"got {len(messages)}. The _bounded_invoke no-op path regressed."
        )


# ── Unit: _bounded_invoke in isolation ─────────────────────────────────────


class TestBoundedInvokeUnit:
    """Direct unit tests on the helper, isolating the mechanism from
    ``_run_phase`` wiring."""

    @pytest.mark.asyncio
    async def test_timeout_stops_generator_and_preserves_writes(self) -> None:
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _bounded_invoke,
        )

        written = {}

        async def stuck_gen():
            written["before_sleep"] = True
            await asyncio.sleep(10)
            yield "unreachable"  # pragma: no cover

        deadline = time.time() + 0.05
        out = []
        async for r in _bounded_invoke(stuck_gen(), deadline, "X", "unit"):
            out.append(r)

        assert out == [], "the stuck __anext__ must be cut before any yield"
        assert (
            written.get("before_sleep") is True
        ), "the write made before the stuck await must survive the cut"

    @pytest.mark.asyncio
    async def test_no_deadline_is_identity(self) -> None:
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _bounded_invoke,
        )

        async def quick_gen():
            for v in ("a", "b", "c"):
                await asyncio.sleep(0)
                yield v

        out = []
        async for r in _bounded_invoke(quick_gen(), None, "X", "unit"):
            out.append(r)

        assert out == [
            "a",
            "b",
            "c",
        ], f"with deadline=None the wrapper must be identity; got {out}"
