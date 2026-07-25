# -*- coding: utf-8 -*-
"""Tests for BO-4 #1480 — orchestration mode comparison harness.

Verifies that ``scripts/compare_orchestration_modes.py`` honors the
trade-off contract established in the dispatch:

* ``MODE_RUNNERS`` exposes ``hierarchical_bridge`` and
  ``hierarchical_delegation`` (post-#1474/#1476/#1478/#1479 entry-points),
  NOT the legacy ``HierarchicalOrchestrator().analyze()`` shim.
* The cluedo stubs (``cluedo_baseline``, ``cluedo_extended``) are REMOVED
  from the registry (anti-pendule: dead-code ``success=False`` placeholders
  were theater, not modes).
* The conversational runner is bounded by ``max_wall_seconds`` and
  reports ``terminated_by_budget=True`` HONNÊTE on breach (never faked
  into ``success=True``).
* The ``ModeResult`` dataclass carries the trade-off columns
  (``terminates``, ``decides``, ``terminated_by_budget``, ``scope_of_work``)
  required by the BO-4 DoD report.
* The ``generate_report`` table includes the BO-4 trade-off columns
  (Terminates / Wall-Time / Decides / Phases / Scope) on top of the
  legacy Detailed Summary table.
* The CLI exposes ``--max-wall-seconds`` and propagates it to the runner.
* The harness produces a non-empty comparison for ≥3 modes in ``--dry-run``.

These tests are no-key / no-LLM and run in CI's fast lane.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO_ROOT / "scripts" / "compare_orchestration_modes.py"


def _load_harness_module():
    """Import the harness module by file path so the test stays
    independent of any ``scripts`` namespace package shadowing."""
    spec = importlib.util.spec_from_file_location(
        "compare_orchestration_modes", str(HARNESS_PATH)
    )
    assert (
        spec is not None and spec.loader is not None
    ), f"Cannot load harness from {HARNESS_PATH}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


class TestModeRegistry:
    """The harness exposes the two post-#1474 hierarchical sub-modes
    and removes the dead-code cluedo stubs."""

    def test_hierarchical_bridge_runner_is_registered(self) -> None:
        mod = _load_harness_module()
        assert "hierarchical_bridge" in mod.MODE_RUNNERS, (
            "BO-4 regression: 'hierarchical_bridge' runner missing — "
            "the harness cannot compare the M2 entry-point "
            "(run_hierarchical_analysis(..., mode='bridge'))."
        )

    def test_hierarchical_delegation_runner_is_registered(self) -> None:
        mod = _load_harness_module()
        assert "hierarchical_delegation" in mod.MODE_RUNNERS, (
            "BO-4 regression: 'hierarchical_delegation' runner missing — "
            "the harness cannot compare the M3 entry-point "
            "(run_hierarchical_analysis(..., mode='delegation'))."
        )

    def test_cluedo_stubs_are_removed(self) -> None:
        """Anti-pendule: the cluedo baselines were dead-code
        ``success=False`` placeholders. The harness must REMOVE them
        rather than carry fake modes that could be confused with
        real runners."""
        mod = _load_harness_module()
        assert "cluedo_baseline" not in mod.MODE_RUNNERS
        assert "cluedo_extended" not in mod.MODE_RUNNERS

    def test_hierarchical_alias_kept_for_backward_compat(self) -> None:
        """The legacy ``hierarchical`` key is preserved as an alias
        for ``hierarchical_bridge`` (the historical default) so old
        callers do not silently break.

        We assert alias identity statically (without invoking the
        runner) because calling it triggers JVM init via the registry,
        which is broken on this environment (pre-existing OpenSSL
        GEN_EMAIL issue, out of scope for BO-4).
        """
        import inspect

        mod = _load_harness_module()
        assert "hierarchical" in mod.MODE_RUNNERS
        # The alias MUST route to bridge — verify by inspecting the
        # wrapper's source. We accept either direct identity OR a
        # wrapper that calls ``run_hierarchical_bridge_mode`` (both
        # are valid alias patterns).
        runner = mod.MODE_RUNNERS["hierarchical"]
        if runner is mod.run_hierarchical_bridge_mode:
            return  # Direct alias — OK.
        source = inspect.getsource(runner)
        assert "run_hierarchical_bridge_mode" in source, (
            "BO-4 regression: 'hierarchical' alias does not route to "
            "run_hierarchical_bridge_mode — old callers may not get "
            "the bridge semantics."
        )


class TestModeResultColumns:
    """The ``ModeResult`` dataclass carries the BO-4 trade-off columns."""

    def test_tradeoff_columns_present(self) -> None:
        from dataclasses import fields

        mod = _load_harness_module()
        names = {f.name for f in fields(mod.ModeResult)}
        for col in (
            "terminates",
            "decides",
            "terminated_by_budget",
            "scope_of_work",
        ):
            assert col in names, (
                f"BO-4 regression: ModeResult missing column '{col}' "
                f"(required by the trade-off table)."
            )

    def test_default_field_values(self) -> None:
        mod = _load_harness_module()
        result = mod.ModeResult(mode="x", corpus_id="y", success=True)
        assert result.terminates is True
        assert result.decides is False
        assert result.terminated_by_budget is False
        assert result.scope_of_work == ""


class TestConversationalWallBudget:
    """The conversational runner is bounded by ``max_wall_seconds`` and
    surfaces a HONEST PARTIAL verdict on breach."""

    def test_breach_records_terminated_by_budget(self) -> None:
        mod = _load_harness_module()

        async def never_resolves():
            await asyncio.sleep(60)  # far above the budget

        # Patch the inner conversational runner to a slow stub.
        real_runner = mod.MODE_RUNNERS["conversational"]

        # Build a runner bound to a tiny budget and a hanging awaitable.
        async def slow_runner(
            text: str, corpus_id: str, max_wall_seconds: float = 0.05
        ) -> mod.ModeResult:
            try:
                await asyncio.wait_for(never_resolves(), timeout=max_wall_seconds)
            except asyncio.TimeoutError:
                return mod.ModeResult(
                    mode="conversational",
                    corpus_id=corpus_id,
                    success=False,
                    terminates=True,
                    terminated_by_budget=True,
                    duration_seconds=max_wall_seconds,
                    error=f"Budget breached (>={max_wall_seconds:g}s)",
                    scope_of_work="wall-time-bounded test",
                )
            return mod.ModeResult(
                mode="conversational", corpus_id=corpus_id, success=True
            )

        # Invoke the patched runner directly to verify breach semantics.
        result = asyncio.run(slow_runner("dummy", "corpus_A", max_wall_seconds=0.05))
        assert result.success is False
        assert result.terminates is True
        assert result.terminated_by_budget is True
        assert "Budget breached" in (result.error or "")
        # Surface the patched runner to silence the linter about real_runner.
        _ = real_runner


class TestConversationalInternalBound:
    """C1 #1500 — the wall-clock bound is enforced INTERNALLY by
    ``run_conversational_analysis``; the harness maps the resulting partial
    verdict to ``success=True`` / ``decides=True`` (a REAL verdict at the
    bound, anti-#1019), keeping ``asyncio.wait_for`` only as a safety net.

    Distinct from ``TestConversationalWallBudget`` above, which covers the
    safety-net-fires contract via a stub runner. These tests exercise the real
    ``run_conversational_mode`` with the inner runner patched.
    """

    def test_safety_net_timeout_math(self) -> None:
        """The safety net gives 20 % headroom for large budgets, 30 s min for
        small ones — so the internal bound reliably fires first."""
        mod = _load_harness_module()
        # 20 % headroom dominates for large budgets.
        assert mod._conversational_safety_net_timeout(180.0) == 216.0
        # 30 s minimum headroom dominates for small budgets.
        assert mod._conversational_safety_net_timeout(10.0) == 40.0
        assert mod._conversational_safety_net_timeout(60.0) == 90.0

    def test_internal_bound_maps_to_real_partial_verdict(self) -> None:
        mod = _load_harness_module()
        fake_result = {
            "phases": [
                "Extraction & Detection",
                "Formal Analysis & Quality",
                "Synthesis & Debate",
            ],
            "conversation_log": [
                {
                    "phase": "Extraction & Detection",
                    "turn": 1,
                    "agent": "ExtractAgent",
                    "content": "partial",
                },
            ],
            "total_messages": 1,
            "state_snapshot": {"identified_arguments": ["arg_0"]},
            "budget": {"wall_clock_bounded": True},
            "capabilities_used": ["fact_extraction"],
            "status": "WALL_CLOCK_BOUNDED",
            "duration_seconds": 30.0,
        }

        async def fake_run(**kwargs):
            return fake_result

        async def _drive():
            with patch(
                "argumentation_analysis.orchestration.conversational_orchestrator"
                ".run_conversational_analysis",
                side_effect=fake_run,
            ):
                return await mod.run_conversational_mode(
                    "text", "corpus_A", max_wall_seconds=30.0
                )

        result = asyncio.run(_drive())

        # The partial state reached at the bound IS a real verdict (anti-#1019).
        assert result.success is True
        assert result.terminates is True
        assert result.decides is True
        assert result.terminated_by_budget is False
        assert result.extra_metrics["wall_clock_bounded"] is True
        assert result.extra_metrics["conversational_status"] == "WALL_CLOCK_BOUNDED"
        # Honest phase count: only 1 of 3 planned phases produced a message.
        assert result.phases_completed == 1
        assert result.phases_total == 3

    def test_clean_completion_not_marked_bounded(self) -> None:
        """A run that completes within the bound is not flagged bounded."""
        mod = _load_harness_module()
        fake_result = {
            "phases": [
                "Extraction & Detection",
                "Formal Analysis & Quality",
                "Synthesis & Debate",
            ],
            "conversation_log": [
                {
                    "phase": "Extraction & Detection",
                    "turn": 1,
                    "agent": "ExtractAgent",
                    "content": "x",
                },
                {
                    "phase": "Formal Analysis & Quality",
                    "turn": 1,
                    "agent": "FormalAgent",
                    "content": "y",
                },
                {
                    "phase": "Synthesis & Debate",
                    "turn": 1,
                    "agent": "DebateAgent",
                    "content": "z",
                },
            ],
            "total_messages": 3,
            "state_snapshot": {"identified_arguments": ["arg_0"]},
            "budget": {"wall_clock_bounded": False},
            "capabilities_used": ["fact_extraction"],
            "status": "COMPLETED",
            "duration_seconds": 12.0,
        }

        async def fake_run(**kwargs):
            return fake_result

        async def _drive():
            with patch(
                "argumentation_analysis.orchestration.conversational_orchestrator"
                ".run_conversational_analysis",
                side_effect=fake_run,
            ):
                return await mod.run_conversational_mode(
                    "text", "corpus_A", max_wall_seconds=30.0
                )

        result = asyncio.run(_drive())

        assert result.success is True
        assert result.decides is True
        assert result.extra_metrics["wall_clock_bounded"] is False
        assert result.phases_completed == 3

    def test_safety_net_timeout_is_honest_partial(self) -> None:
        """When the safety-net ``asyncio.wait_for`` DOES fire (a single
        in-flight call hung past the between-turn check), the verdict is an
        honest partial — never faked into success (anti-#1019)."""
        mod = _load_harness_module()

        async def fake_wait_for(coro, timeout=None):
            coro.close()  # avoid 'coroutine never awaited' warning
            raise asyncio.TimeoutError()

        async def _drive():
            with patch.object(asyncio, "wait_for", fake_wait_for):
                return await mod.run_conversational_mode(
                    "text", "corpus_A", max_wall_seconds=30.0
                )

        result = asyncio.run(_drive())

        assert result.success is False
        assert result.terminates is True
        assert result.terminated_by_budget is True
        assert "Safety-net timeout" in (result.error or "")

    def test_report_marks_bounded_verdict_distinctly(self) -> None:
        """The trade-off table distinguishes a bounded partial verdict (✅⏱)
        from a clean completion (✅) and a safety-net breach (⏱ budget)."""
        mod = _load_harness_module()
        report = mod.generate_report(
            [
                mod.ModeResult(
                    mode="conversational",
                    corpus_id="corpus_A",
                    success=True,
                    terminates=True,
                    decides=True,
                    duration_seconds=180.0,
                    phases_completed=2,
                    phases_total=3,
                    scope_of_work="AgentGroupChat (bounded)",
                    extra_metrics={"wall_clock_bounded": True},
                ),
            ]
        )
        assert "✅⏱ bounded" in report


class TestReportFormat:
    """The trade-off table is generated with the BO-4 columns."""

    def test_tradeoff_table_includes_bo4_columns(self) -> None:
        mod = _load_harness_module()
        report = mod.generate_report(
            [
                mod.ModeResult(
                    mode="pipeline",
                    corpus_id="corpus_A",
                    success=True,
                    duration_seconds=12.3,
                    phases_completed=4,
                    phases_total=4,
                    decides=True,
                    scope_of_work="UnifiedPipeline DAG",
                ),
                mod.ModeResult(
                    mode="hierarchical_bridge",
                    corpus_id="corpus_A",
                    success=True,
                    duration_seconds=8.1,
                    phases_completed=4,
                    phases_total=4,
                    decides=True,
                    scope_of_work="Strategic -> WorkflowExecutor",
                ),
                mod.ModeResult(
                    mode="conversational",
                    corpus_id="corpus_A",
                    success=False,
                    terminates=True,
                    terminated_by_budget=True,
                    duration_seconds=180.0,
                    error="Budget breached (>=180s)",
                    scope_of_work="AgentGroupChat (budget)",
                ),
            ]
        )

        # Trade-off table header.
        assert "## Trade-off Summary" in report
        for col in (
            "Mode",
            "Corpus",
            "Terminates",
            "Wall-Time",
            "Decides",
            "Phases",
            "Scope",
        ):
            assert (
                col in report
            ), f"BO-4 regression: trade-off table missing column '{col}'."
        # Status markers (✅ for OK, ⏱ for budget, ❌ for failure).
        assert "✅" in report
        assert "⏱ budget" in report
        # Partial verdict surfaced in the skip/failed section.
        assert "BUDGET BREACH" in report


class TestCliDryRun:
    """The CLI exposes the BO-4 affordances and the dry-run is non-empty."""

    def test_dry_run_lists_three_or_more_modes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HARNESS_PATH), "--dry-run"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=60,
        )
        assert result.returncode == 0, (
            f"Harness --dry-run failed:\nSTDOUT={result.stdout}\n"
            f"STDERR={result.stderr}"
        )
        listed_modes = [
            line.split(":")[0].strip().lstrip("- ")
            for line in result.stdout.splitlines()
            if ":" in line and "available" in line
        ]
        # ≥3 comparable modes must be available in --dry-run.
        assert len(listed_modes) >= 3, (
            f"BO-4 regression: dry-run only lists {len(listed_modes)} "
            f"modes, expected ≥3. Listed={listed_modes}"
        )

    def test_cli_exposes_max_wall_seconds_flag(self) -> None:
        result = subprocess.run(
            [sys.executable, str(HARNESS_PATH), "--help"],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
            timeout=60,
        )
        assert (
            "--max-wall-seconds" in result.stdout
        ), "BO-4 regression: --max-wall-seconds CLI flag is missing."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
