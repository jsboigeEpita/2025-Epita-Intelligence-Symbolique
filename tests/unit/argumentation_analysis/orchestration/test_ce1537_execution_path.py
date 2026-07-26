# tests/unit/argumentation_analysis/orchestration/test_ce1537_execution_path.py
"""CE #1537 — the conversational mode must surface which execution path ran.

CD #1534 (PR #1536) made ``AgentGroupChat`` construction work, but a silent
round-robin fallback could still occur (construction failure, runtime error,
or SK unavailable), and nothing in the RESULT said which path ran — only a
log line. CE #1537 closes that:

  * ``_run_phase`` records ``execution_path`` AT THE SOURCE (a meta prepended
    to its message list) — never deduced from metrics afterwards.
  * ``run_conversational_analysis`` aggregates the per-phase metas into
    ``result["execution_path"]`` ("agent_group_chat" only if every phase ran
    the SK path; any fallback downgrades to "round_robin_fallback").
  * The comparison harness reads it into ``extra_metrics`` and the trade-off
    table renders a dedicated ``Exec Path`` column — so a fallback line can
    never be read as a genuine ``AgentGroupChat`` run (anti-#1019).

These tests are JVM/LLM-free and deterministic.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# scripts/ is not a package; add it to sys.path so the harness module
# (scripts/compare_orchestration_modes.py) is importable — mirrors the
# test_depth_parity_1500.py setup.
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = str(_PROJECT_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import compare_orchestration_modes as harness  # noqa: E402
from argumentation_analysis.orchestration import (
    conversational_orchestrator as orch,
)  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


def _async_gen(items: List[Any]):
    """Build an async generator that yields the given items (SK invoke() shape)."""

    async def gen():
        for it in items:
            yield it

    return gen()


# ---------------------------------------------------------------------------
# _run_phase records execution_path at the source via the recorder
# (DoD #1 / #2 at the source). The path is NOT stored in `messages` — that
# would break the C1 contract (test_deadline_in_past_breaks_before_first_turn
# counts on the exact message-list length).
# ---------------------------------------------------------------------------


class TestRunPhaseRecordsExecutionPath:
    def test_agent_group_chat_path_records_agent_group_chat(self):
        """DoD #1: a normal AgentGroupChat run records "agent_group_chat"."""
        agent = MagicMock()
        agent.name = "TestAgent"
        response = MagicMock()
        response.name = "TestAgent"
        response.content = "response content"

        mock_chat = MagicMock()
        mock_chat.add_chat_message = AsyncMock()
        mock_chat.invoke = MagicMock(return_value=_async_gen([response]))

        recorder: list = []
        with patch(
            "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat",
            return_value=mock_chat,
        ):
            messages = _run(
                orch._run_phase(
                    [agent],
                    "prompt",
                    max_turns=1,
                    phase_name="Synthesis",
                    state=None,
                    enable_growth_validation=False,
                    execution_path_recorder=recorder,
                )
            )

        assert recorder == ["agent_group_chat"]
        # C1 contract preserved: the message list is NOT polluted.
        assert all(
            not (isinstance(m, dict) and m.get("type") == "execution_path")
            for m in messages
        )

    def test_construction_failure_records_round_robin_fallback(self):
        """DoD #2: a construction failure falls back and records "round_robin_fallback".

        The AgentGroupChat construction is made to raise; _run_phase falls
        through to the round-robin path (one mocked turn) and records the
        fallback path at the source.
        """
        agent = MagicMock()
        agent.name = "TestAgent"
        response = MagicMock()
        response.content = "round-robin content"
        agent.invoke = MagicMock(return_value=_async_gen([response]))

        recorder: list = []
        with patch(
            "semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat",
            side_effect=RuntimeError("construction boom (CE #1537 test)"),
        ):
            messages = _run(
                orch._run_phase(
                    [agent],
                    "prompt",
                    max_turns=1,
                    phase_name="Synthesis",
                    state=None,
                    enable_growth_validation=False,
                    execution_path_recorder=recorder,
                )
            )

        assert recorder == ["round_robin_fallback"]
        assert all(
            not (isinstance(m, dict) and m.get("type") == "execution_path")
            for m in messages
        )


# ---------------------------------------------------------------------------
# Harness propagation: run_conversational_mode -> extra_metrics (DoD #1/#2)
# ---------------------------------------------------------------------------


def _fake_conversational_result(execution_path: str) -> dict:
    return {
        "execution_path": execution_path,
        "budget": {},
        "state_snapshot": {},
        "phases": [],
        "conversation_log": [],
        "total_messages": 0,
        "status": "COMPLETED",
        "duration_seconds": 0.1,
        "extra_metrics": {},
    }


class TestHarnessPropagatesExecutionPath:
    def test_agent_group_chat_propagates_to_extra_metrics(self):
        fake = _fake_conversational_result("agent_group_chat")
        with patch.object(
            orch,
            "run_conversational_analysis",
            new=AsyncMock(return_value=fake),
        ):
            result = _run(
                harness.run_conversational_mode(
                    text="t", corpus_id="corpus_A", max_wall_seconds=10
                )
            )
        assert result.extra_metrics["execution_path"] == "agent_group_chat"

    def test_round_robin_fallback_propagates_to_extra_metrics(self):
        """DoD #2: the harness surfaces the fallback path, not just the log."""
        fake = _fake_conversational_result("round_robin_fallback")
        with patch.object(
            orch,
            "run_conversational_analysis",
            new=AsyncMock(return_value=fake),
        ):
            result = _run(
                harness.run_conversational_mode(
                    text="t", corpus_id="corpus_A", max_wall_seconds=10
                )
            )
        assert result.extra_metrics["execution_path"] == "round_robin_fallback"

    def test_absent_execution_path_defaults_to_fallback_not_agc(self):
        """Defensive: a result without the field must not read as group-chat."""
        fake = _fake_conversational_result("agent_group_chat")
        # Simulate an older orchestrator that does NOT emit the field:
        fake.pop("execution_path")
        with patch.object(
            orch,
            "run_conversational_analysis",
            new=AsyncMock(return_value=fake),
        ):
            result = _run(
                harness.run_conversational_mode(
                    text="t", corpus_id="corpus_A", max_wall_seconds=10
                )
            )
        assert result.extra_metrics["execution_path"] == "round_robin_fallback"


# ---------------------------------------------------------------------------
# generate_report renders the Exec Path column (DoD #2: "the table shows it")
# ---------------------------------------------------------------------------


class TestGenerateReportShowsExecPath:
    def _result(self, corpus_id: str, execution_path: str):
        return harness.ModeResult(
            mode="conversational",
            corpus_id=corpus_id,
            success=True,
            duration_seconds=10.0,
            phases_completed=3,
            phases_total=3,
            scope_of_work="AgentGroupChat 3-phase",
            decides=True,
            extra_metrics={"execution_path": execution_path, "total_messages": 5},
        )

    def test_table_has_exec_path_column_and_distinguishes_paths(self):
        md = harness.generate_report(
            [
                self._result("corpus_A", "agent_group_chat"),
                self._result("corpus_B", "round_robin_fallback"),
            ]
        )
        # The column exists...
        assert "Exec Path" in md
        # ...and the two paths are visually distinct (a fallback line cannot
        # be read as a genuine AgentGroupChat line — anti-#1019):
        assert "AgentGroupChat" in md
        assert "round-robin ⚠" in md

    def test_non_conversational_modes_render_dash(self):
        """Modes that don't record execution_path render '—' (no false signal)."""
        r = harness.ModeResult(
            mode="pipeline",
            corpus_id="corpus_A",
            success=True,
            duration_seconds=5.0,
            phases_completed=15,
            phases_total=15,
            scope_of_work="pipeline DAG",
            decides=True,
            extra_metrics={},  # no execution_path
        )
        md = harness.generate_report([r])
        # pipeline row must NOT claim AgentGroupChat or round-robin:
        assert "AgentGroupChat" not in md
        assert "round-robin ⚠" not in md
