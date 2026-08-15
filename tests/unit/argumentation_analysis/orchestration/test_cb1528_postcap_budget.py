# -*- coding: utf-8 -*-
"""Tests for CB #1528 item 3 — the wall-clock cap must CANCEL, not just schedule.

Firsthand measurement recorded on #1528 (R715/R716): ``wall_clock_bounded`` was
set at the breach and then read ONLY to build the result dict — no ``if`` ever
consulted it. So the cap decided "do not start the next PHASE" and the run kept
going: a whole conditional Re-Analysis phase (4 agents, guarded by the distinct
TURN-COUNT flag) plus five ``spectacular`` LLM stages, ~16 round-trips past the
deadline, until an external safety-net cut the coroutine and discarded the state
it had just populated (arguments and counter-arguments written seconds before
the cut, reported as an empty row).

Two defects, two kinds of test here:

* **Behavioural** — ``_run_phase`` entered with an already-expired deadline used
  to burn one full multi-agent turn on the ``AgentGroupChat`` path, because that
  path invoked ``chat.invoke()`` unconditionally and only checked the deadline
  *after* the first response. The round-robin path had the check; the group-chat
  path did not. The pre-existing regression test
  (``test_deadline_in_past_breaks_before_first_turn``) injects a raising
  ``AgentGroupChat`` precisely to force the round-robin fallback, so it does NOT
  cover the path that has been live since CD #1534. These tests do.

* **Structural** — the post-loop stages are now gated by one shared
  ``_budget_allows`` predicate. That gating is not reachable without a real LLM
  run, so it is pinned as a WIRING GUARD (same family as
  ``test_external_provers_wired.py``): the guard proves the call sites are still
  attached to the budget, and the behaviour they protect is measured firsthand
  in the bounded run recorded on #1528. A new post-loop stage added without the
  predicate re-opens the exact defect this item closed, silently.

Anti-pendule: none of these stages is removed — they carry the analytical value
of the mode. They are SKIPPED once the budget is spent, which is what "verdict
partiel honnête" already means everywhere else in this module.

All tests are deterministic and LLM-free.
"""

from __future__ import annotations

import ast
import time
from pathlib import Path
from typing import List, Optional
from unittest.mock import MagicMock, patch

import pytest

ORCHESTRATOR_PATH = (
    Path(__file__).resolve().parents[4]
    / "argumentation_analysis"
    / "orchestration"
    / "conversational_orchestrator.py"
)


# ── Behavioural: the group-chat path checks the deadline BEFORE turn 1 ────


class TestGroupChatPreFirstTurnDeadline:
    """A phase entered past its deadline must run ZERO turns on BOTH paths."""

    @pytest.mark.asyncio
    async def test_past_deadline_never_constructs_group_chat(self) -> None:
        """The live (CD #1534) path: AgentGroupChat must not even be built.

        Asserting on the mock rather than on the message list is the point —
        an empty list would also be produced by a chat that ran and returned
        nothing. Here we assert the LLM path was never entered at all.
        """
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_phase,
        )

        state = RhetoricalAnalysisState("test text")
        fake_agent = MagicMock()
        fake_agent.name = "FakeAgent"

        # NOT raising: unlike the pre-existing C1 test, we let the group-chat
        # path be available so that reaching it would be observable.
        chat_cls = MagicMock(name="AgentGroupChat")

        with patch(
            "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat",
            chat_cls,
        ):
            messages = await _run_phase(
                [fake_agent],
                "initial prompt",
                max_turns=5,
                phase_name="Extraction & Detection",
                state=state,
                enable_growth_validation=False,
                deadline=time.time() - 1.0,
            )

        assert chat_cls.call_count == 0, (
            "CB #1528 item 3 regression: _run_phase entered with an expired "
            "deadline constructed an AgentGroupChat — the group-chat path used "
            "to burn one full multi-agent turn before checking the deadline."
        )
        assert messages == [], (
            f"Expected zero turns past the deadline, got {len(messages)} " "message(s)."
        )

    @pytest.mark.asyncio
    async def test_past_deadline_records_no_execution_path(self) -> None:
        """Nothing ran, so no execution path may be claimed (CE #1537).

        Recording a path here would re-introduce the CE defect: a value
        asserted for a branch that never executed.
        """
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_phase,
        )

        state = RhetoricalAnalysisState("test text")
        fake_agent = MagicMock()
        fake_agent.name = "FakeAgent"
        recorder: List[str] = []

        with patch(
            "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat",
            MagicMock(name="AgentGroupChat"),
        ):
            await _run_phase(
                [fake_agent],
                "initial prompt",
                max_turns=5,
                phase_name="Extraction & Detection",
                state=state,
                enable_growth_validation=False,
                deadline=time.time() - 1.0,
                execution_path_recorder=recorder,
            )

        assert recorder == [], (
            "CB #1528 item 3: no execution path may be recorded when the "
            f"deadline aborted the phase before any turn — got {recorder}."
        )

    @pytest.mark.asyncio
    async def test_future_deadline_still_runs_a_turn(self) -> None:
        """Anti-pendule: the pre-entry check is a BOUND, not a truncation.

        With a deadline comfortably ahead, the phase must behave exactly as
        before — one turn under ``max_turns=1``.
        """
        from argumentation_analysis.core.shared_state import RhetoricalAnalysisState
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _run_phase,
        )

        state = RhetoricalAnalysisState("test text")
        fake_agent = MagicMock()
        fake_agent.name = "FakeAgent"

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
                deadline=time.time() + 3600.0,
            )

        assert len(messages) == 1, (
            "Anti-pendule regression: a deadline in the future must not "
            f"suppress the phase — expected 1 turn, got {len(messages)}."
        )


# ── Structural wiring guard: post-loop stages consult the budget ─────────


def _module_ast() -> ast.Module:
    return ast.parse(ORCHESTRATOR_PATH.read_text(encoding="utf-8"))


def _guard_test_source_for_call(callee: str) -> Optional[str]:
    """Source of the ``if`` test whose body calls ``callee``.

    ``ast.walk`` is breadth-first, so the first matching ``If`` is the
    outermost one containing the call — which for these top-level post-loop
    stages is exactly their guard.
    """
    for node in ast.walk(_module_ast()):
        if not isinstance(node, ast.If):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and getattr(sub.func, "id", None) == callee:
                return ast.unparse(node.test)
    return None


class TestPostLoopStagesAreBudgetGated:
    """Every post-loop LLM stage must be attached to the ONE shared predicate."""

    # The five ``spectacular`` stages measured on #1528 as running past the cap.
    POST_LOOP_LLM_STAGES = [
        "_generate_counter_arguments_from_state",
        "_run_formal_logic_from_state",
        "_run_quality_sweep_from_state",
        "_invoke_stakes_extractor",
        "_invoke_deep_synthesis",
    ]

    @pytest.mark.parametrize("callee", POST_LOOP_LLM_STAGES)
    def test_stage_guard_consults_budget(self, callee: str) -> None:
        guard = _guard_test_source_for_call(callee)
        assert guard is not None, (
            f"{callee} is no longer called from an `if` in the orchestrator — "
            "update this guard so the budget wiring stays checked."
        )
        assert "_budget_allows" in guard, (
            f"CB #1528 item 3 regression: the post-loop stage `{callee}` runs "
            f"under `if {guard}` — it does not consult the wall-clock budget. "
            "Past the cap this stage issues LLM round-trips that the external "
            "safety-net then cuts, discarding the state just populated."
        )

    def test_reanalysis_phase_consults_wall_clock_not_only_turn_count(self) -> None:
        """The conditional Re-Analysis phase is a WHOLE extra 4-agent phase.

        It was guarded by ``budget_exhausted`` — the turn-count flag from
        CONV-C #1334 — which is a different budget from the wall clock.
        """
        guard = _guard_test_source_for_call("_should_add_reanalysis_phase")
        assert guard is not None, (
            "Re-Analysis is no longer gated by an `if` calling "
            "_should_add_reanalysis_phase — update this guard."
        )
        assert "_budget_allows" in guard, (
            f"CB #1528 item 3 regression: Re-Analysis runs under `if {guard}` "
            "— the turn-count flag alone let a wall-clock-stopped run start a "
            "whole extra 4-agent phase."
        )

    def test_budget_predicate_is_defined_once_in_the_inner_run(self) -> None:
        """One predicate, not five copies, and not a second budget mechanism."""
        definitions = [
            node
            for node in ast.walk(_module_ast())
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_budget_allows"
        ]
        assert len(definitions) == 1, (
            f"Expected exactly one `_budget_allows` definition, found "
            f"{len(definitions)} — the item asked for ONE shared predicate."
        )

    def test_predicate_asks_the_budget_not_the_reporting_flag(self) -> None:
        """``wall_clock_bounded`` is a REPORTING flag; ``wall`` is the authority.

        The original defect was a flag that gated nothing. Re-implementing the
        gate on that same flag would rebuild the defect with an `if` in front
        of it, so the predicate must ask ``wall.is_exhausted``.
        """
        definition = next(
            node
            for node in ast.walk(_module_ast())
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_budget_allows"
        )
        body = ast.unparse(definition)
        assert "wall.is_exhausted" in body, (
            "`_budget_allows` must consult the WallClockBudget itself, not the "
            "`wall_clock_bounded` reporting flag."
        )


class TestSynchronousStagesStayExemptForTheStatedReason:
    """Four post-loop stages are ungated *because* they spend no wall clock.

    Dung / modal / ASPIC / belief-revision re-read state the conversation has
    already populated. Gating them would strip content from an honest partial
    verdict and save no time. That exemption is only sound while they stay
    synchronous — so pin the reason, not the decision: if one of them ever
    becomes awaited (or starts calling a kernel/agent/LLM), this fails and the
    gating question has to be answered again rather than silently inherited.
    """

    SYNC_STAGES = [
        "_build_dung_framework_from_state",
        "_detect_and_run_modal_analysis",
        "_run_belief_revision_from_state",
    ]

    _LLM_HINTS = ("openai", "completion", "kernel", "llm", "asyncio")

    @pytest.mark.parametrize("name", SYNC_STAGES)
    def test_stage_spends_no_wall_clock(self, name: str) -> None:
        definition = next(
            (
                node
                for node in ast.walk(_module_ast())
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name == name
            ),
            None,
        )
        assert definition is not None, f"{name} disappeared — update this guard."

        assert not isinstance(definition, ast.AsyncFunctionDef), (
            f"`{name}` became async. It is one of the four post-loop stages left "
            "ungated by `_budget_allows` on the grounds that it spends no wall "
            "clock — re-examine whether it now needs the budget guard."
        )

        awaits = [n for n in ast.walk(definition) if isinstance(n, ast.Await)]
        assert not awaits, f"`{name}` now awaits — see the message above."

        calls = {
            ast.unparse(n.func).lower()
            for n in ast.walk(definition)
            if isinstance(n, ast.Call)
        }
        suspicious = sorted(
            c for c in calls if any(hint in c for hint in self._LLM_HINTS)
        )
        assert not suspicious, (
            f"`{name}` now calls {suspicious} — it may issue LLM round-trips, "
            "which would invalidate its exemption from the budget guard."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
