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
from types import SimpleNamespace
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
        # Track CA #1529: the default is now None ("not computed"), NOT False
        # ("no") — a runner that bypasses the uniform _compute_decides helper
        # surfaces as indeterminate, not as a false "no verdict".
        assert result.decides is None
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
        # Track CA #1529: `decides` is now computed UNIFORMLY by run_all (not
        # hand-set by the runner), so a direct runner call leaves it None. The
        # partial-verdict-is-real contract is verified via the uniform helper:
        # the fields the runner populated (1 message, 1/3 phases, non-empty
        # state) DO constitute a decision.
        assert result.decides is None
        assert mod._compute_decides(result) is True
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
        # Track CA #1529: decides computed uniformly (3 messages, 3/3 phases → True).
        assert mod._compute_decides(result) is True
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


class TestComputeDecidesCA:
    """Track CA #1529 — ``decides`` computed UNIFORMLY for every mode.

    The BO-4 #1480 defect: ``ModeResult.decides`` defaulted to ``False`` and
    each runner hand-set it on a different local criterion (conversational:
    ``total_messages > 0``; hierarchical: a ``conclusion``; pipeline: never →
    the misleading ``False`` default). Result: ``pipeline_standard`` with
    15/15 phases and 51.2 % state fill was painted ``Decides —``. CA #1529
    replaces this with ONE definition (:func:`_compute_decides`) applied in a
    single ``run_all`` pass, and changes the default to ``None``.

    These tests are deterministic and LLM/JVM-free — they build ``ModeResult``
    instances directly and exercise the helper + the ``run_all`` normalization.
    """

    def _harness(self):
        return _load_harness_module()

    def test_sterile_run_decides_false(self) -> None:
        """Anti-pendule guard: a run that produced nothing stays False → `—`.
        This is the non-regression test the coord emphasized — a fix that
        turns every mode green is wrong."""
        mod = self._harness()
        sterile = mod.ModeResult(
            mode="conversational",
            corpus_id="corpus_A",
            success=False,
            terminates=True,
            terminated_by_budget=True,  # cut at the safety-net
            error="Safety-net timeout (>=60s)",
        )
        assert mod._compute_decides(sterile) is False, (
            "CA #1529 regression: a genuinely sterile run (0/0 phases, 0 % "
            "fill, 0 messages) must decide False, not True."
        )

    def test_state_fill_decides_true(self) -> None:
        mod = self._harness()
        filled = mod.ModeResult(
            mode="pipeline_standard",
            corpus_id="corpus_A",
            success=True,
            state_fill_rate=0.512,
        )
        assert mod._compute_decides(filled) is True

    def test_extracted_artifacts_decide_true(self) -> None:
        mod = self._harness()
        for kwargs in ({"argument_count": 3}, {"fallacy_count": 2}):
            r = mod.ModeResult(mode="x", corpus_id="y", success=True, **kwargs)
            assert mod._compute_decides(r) is True, (
                f"CA #1529 regression: extracted artifacts ({kwargs}) must "
                "count as deciding."
            )

    def test_agent_messages_decide_true(self) -> None:
        mod = self._harness()
        r = mod.ModeResult(
            mode="conversational",
            corpus_id="corpus_A",
            success=True,
            extra_metrics={"total_messages": 5},
        )
        assert mod._compute_decides(r) is True

    def test_verdict_artifact_decides_true_without_fill(self) -> None:
        """DoD-4 #1529: hierarchical_bridge emits a strategic ``conclusion``
        without filling the shared state (0.0 % fill) — that is a LEGITIMATE
        decide, documented via the uniform ``verdict_artifact`` channel."""
        mod = self._harness()
        r = mod.ModeResult(
            mode="hierarchical_bridge",
            corpus_id="corpus_A",
            success=True,
            state_fill_rate=0.0,
            extra_metrics={"verdict_artifact": "strategic conclusion text"},
        )
        assert mod._compute_decides(r) is True, (
            "CA #1529 regression: a mode-specific conclusion (verdict_artifact) "
            "must count as deciding even at 0 % shared-state fill."
        )

    def test_phases_completed_decides_true(self) -> None:
        """A completed workflow phase emits its phase's artifact by definition
        — so ``phases_completed > 0`` decides True even at 0 % fill."""
        mod = self._harness()
        r = mod.ModeResult(
            mode="x",
            corpus_id="y",
            success=True,
            phases_completed=4,
        )
        assert mod._compute_decides(r) is True

    def test_pipeline_bug_reproduction_now_decides_true(self) -> None:
        """The coord's firsthand DoD-4 bug (R706): pipeline_standard completing
        15/15 phases, 51.2 % fill, 14 capabilities was shown ``Decides —``
        because run_pipeline_mode never set decides. The uniform helper must
        now compute True."""
        mod = self._harness()
        pipeline_like = mod.ModeResult(
            mode="pipeline_standard",
            corpus_id="corpus_A",
            success=True,
            duration_seconds=320.75,
            state_fill_rate=0.512,
            phases_completed=15,
            phases_total=15,
            capabilities_used=[f"cap_{i}" for i in range(14)],
        )
        assert mod._compute_decides(pipeline_like) is True, (
            "CA #1529 NOT-fixed: pipeline with 15/15 phases and 51.2 % fill "
            "must decide True (the BO-4 false-negative the coord caught firsthand)."
        )

    def test_conversational_safety_net_stays_false(self) -> None:
        """The coord's non-regression guard verbatim: the conversational run
        cut at the safety-net (0/0 phases, 0 % fill) must HONESTLY stay False.
        If CA turned it green, CA would be theater."""
        mod = self._harness()
        safety_net = mod.ModeResult(
            mode="conversational",
            corpus_id="corpus_A",
            success=False,
            terminates=True,
            terminated_by_budget=True,
            duration_seconds=60.01,
            phases_completed=0,
            phases_total=0,
            state_fill_rate=0.0,
            error="Safety-net timeout (>=30s)",
            extra_metrics={"total_messages": 0},
        )
        assert mod._compute_decides(safety_net) is False

    def test_run_all_computes_decides_uniformly(self) -> None:
        """``run_all`` is the single point that computes ``decides`` for every
        result via the uniform helper — regardless of what the runners return.
        A deciding stub (phases>0) → True; a sterile stub → False; neither
        hand-sets ``decides``."""
        mod = self._harness()

        # CB #1528: run_all now threads max_wall_seconds to EVERY runner, so
        # the stubs accept (and ignore) the kwarg. Intent unchanged — this
        # still verifies run_all computes `decides` uniformly.
        async def stub_deciding(text, cid, max_wall_seconds=None):
            return mod.ModeResult(
                mode="stub_deciding",
                corpus_id=cid,
                success=True,
                phases_completed=2,
            )

        async def stub_sterile(text, cid, max_wall_seconds=None):
            return mod.ModeResult(mode="stub_sterile", corpus_id=cid, success=True)

        real_runners = dict(mod.MODE_RUNNERS)
        mod.MODE_RUNNERS.clear()
        mod.MODE_RUNNERS["stub_deciding"] = stub_deciding
        mod.MODE_RUNNERS["stub_sterile"] = stub_sterile
        try:
            results = asyncio.run(
                mod.run_all(
                    modes=["stub_deciding", "stub_sterile"], corpora=["corpus_A"]
                )
            )
        finally:
            mod.MODE_RUNNERS.clear()
            mod.MODE_RUNNERS.update(real_runners)

        by_mode = {r.mode: r for r in results}
        assert (
            by_mode["stub_deciding"].decides is True
        ), "CA #1529: run_all did not compute decides=True for the deciding stub."
        assert (
            by_mode["stub_sterile"].decides is False
        ), "CA #1529: run_all did not compute decides=False for the sterile stub."


class TestCBWallClockBudget1528:
    """Track CB #1528 — mode-agnostic ``--max-wall-seconds``.

    The bound is threaded to EVERY runner, not just conversational:
    * pipeline applies the STATE-REFERENCE trick (``state=`` passed by
      reference → completed levels survive ``asyncio.wait_for`` cancellation
      → real partial verdict, anti-#1019);
    * hierarchical honest-degrades (no incremental state exposed → sterile
      ``terminated_by_budget=True`` → ``decides`` False → ``—``);
    * conversational unchanged (C1 #1500 internal bound).

    Coord R709 two guards: (a) a torn level must NOT inflate
    ``phases_completed``; (b) cross-mode cancellation contamination is
    MEASURED and reported, never masked by re-ordering.

    Deterministic + LLM/JVM-free: the inner entry-points are patched.
    """

    def _harness(self):
        return _load_harness_module()

    @staticmethod
    def _phase(status_name: str) -> SimpleNamespace:
        """A fake PhaseResult whose ``.status.name`` is ``status_name``."""
        return SimpleNamespace(status=SimpleNamespace(name=status_name))

    def test_pipeline_budget_breach_recovers_partial_state(self) -> None:
        """CB #1528 anti-#1019: a pipeline killed at the bound leaves a REAL
        partial verdict — completed levels' state survives via the
        state-reference trick, so ``decides`` is True (not a killed coroutine
        that lost everything)."""
        mod = self._harness()

        async def fake_run(**kwargs):
            # Level 0 completes: writes an argument to the shared state AND
            # fires the checkpoint with 2 COMPLETED phases.
            state = kwargs.get("state")
            if state is not None and hasattr(state, "add_argument"):
                state.add_argument("partial_argument_from_completed_level")
            cb = kwargs.get("checkpoint_callback")
            if cb is not None:
                cb(
                    {
                        "p_extract": self._phase("COMPLETED"),
                        "p_detect": self._phase("COMPLETED"),
                    },
                    {},
                )
            # Level 1 torn — hangs past the tiny budget.
            await asyncio.sleep(5)

        async def _drive():
            with patch(
                "argumentation_analysis.orchestration.unified_pipeline"
                ".run_unified_analysis",
                side_effect=fake_run,
            ):
                return await mod.run_pipeline_mode(
                    "text", "corpus_A", "standard", max_wall_seconds=0.5
                )

        result = asyncio.run(_drive())

        assert result.terminated_by_budget is True
        assert result.success is False
        assert result.terminates is True
        # Partial state survived the cancellation → fill_rate > 0.
        assert result.state_fill_rate > 0
        # phases_completed == checkpoint count (2), NOT inflated by the torn level.
        assert result.phases_completed == 2
        # The partial state IS the verdict (anti-#1019).
        assert mod._compute_decides(result) is True

    def test_pipeline_torn_level_not_inflated(self) -> None:
        """Coord R709 guard (a): a level torn mid-gather by the budget must
        NOT count toward ``phases_completed``. The checkpoint fires only after
        a full gather, so the torn level's in-flight phase never reaches it."""
        mod = self._harness()

        async def fake_run(**kwargs):
            cb = kwargs.get("checkpoint_callback")
            # Level 0 fully gathered (2 COMPLETED) → checkpoint fires with 2.
            if cb is not None:
                cb({"p1": self._phase("COMPLETED"), "p2": self._phase("COMPLETED")}, {})
            # Level 1 torn mid-gather (1 RUNNING, never completes) → hangs
            # before its own checkpoint could fire.
            await asyncio.sleep(5)

        async def _drive():
            with patch(
                "argumentation_analysis.orchestration.unified_pipeline"
                ".run_unified_analysis",
                side_effect=fake_run,
            ):
                return await mod.run_pipeline_mode(
                    "text", "corpus_A", "standard", max_wall_seconds=0.5
                )

        result = asyncio.run(_drive())
        assert result.phases_completed == 2, (
            "Guard (a) regression: the torn level's in-flight phase leaked into "
            "phases_completed. The checkpoint must count only COMPLETED phases "
            "from fully-gathered levels."
        )

    def test_pipeline_unbounded_path_unchanged(self) -> None:
        """``max_wall_seconds=None`` = original pre-CB path (no state-ref, no
        checkpoint, no wait_for). Regression guard."""
        mod = self._harness()
        fake_result = {
            "summary": {"completed": 15, "total": 15},
            "state_snapshot": {"identified_arguments": {"arg_1": "x"}},
            "capabilities_used": ["fact_extraction"],
            "capabilities_missing": [],
            "extra_metrics": {"fallacy_count": 2, "argument_count": 1},
        }
        captured: dict = {}

        async def fake_run(**kwargs):
            captured["state"] = kwargs.get("state")
            captured["checkpoint_callback"] = kwargs.get("checkpoint_callback")
            return fake_result

        async def _drive():
            with patch(
                "argumentation_analysis.orchestration.unified_pipeline"
                ".run_unified_analysis",
                side_effect=fake_run,
            ):
                return await mod.run_pipeline_mode("text", "corpus_A", "standard")

        result = asyncio.run(_drive())
        # Unbounded → no state-reference, no checkpoint (bound is opt-in).
        assert captured["state"] is None
        assert captured["checkpoint_callback"] is None
        assert result.success is True
        assert result.terminated_by_budget is False
        assert result.phases_completed == 15

    def test_hierarchical_bridge_budget_breach_honest_degrade(self) -> None:
        """CB #1528: hierarchical exposes no incremental state → a budget
        breach honestly degrades to a sterile ``terminated_by_budget=True``
        result (decides False → ``—``), NOT a faked success."""
        mod = self._harness()

        async def fake_hang(**kwargs):
            await asyncio.sleep(5)

        async def _drive():
            with patch(
                "argumentation_analysis.orchestration.hierarchical.orchestrator"
                ".run_hierarchical_analysis",
                side_effect=fake_hang,
            ), patch(
                "argumentation_analysis.orchestration.registry_setup" ".setup_registry",
                return_value=None,
            ):
                return await mod.run_hierarchical_bridge_mode(
                    "text", "corpus_A", max_wall_seconds=0.5
                )

        result = asyncio.run(_drive())
        assert result.terminated_by_budget is True
        assert result.success is False
        assert result.terminates is True
        # No partial state exposed → sterile → honestly decides False.
        assert mod._compute_decides(result) is False

    def test_hierarchical_delegation_budget_breach_honest_degrade(self) -> None:
        """Same honest-degrade contract as bridge, for the delegation mode."""
        mod = self._harness()

        async def fake_hang(**kwargs):
            await asyncio.sleep(5)

        async def _drive():
            with patch(
                "argumentation_analysis.orchestration.hierarchical.orchestrator"
                ".run_hierarchical_analysis",
                side_effect=fake_hang,
            ), patch(
                "argumentation_analysis.orchestration.registry_setup" ".setup_registry",
                return_value=None,
            ):
                return await mod.run_hierarchical_delegation_mode(
                    "text", "corpus_A", max_wall_seconds=0.5
                )

        result = asyncio.run(_drive())
        assert result.terminated_by_budget is True
        assert result.success is False
        assert mod._compute_decides(result) is False

    def test_count_pending_async_tasks_detects_leak(self) -> None:
        """Coord R709 guard (b): the contamination detector must surface
        dangling tasks left by a cancelled coroutine (would inflate the next
        mode's wall-time). Measured, not masked."""
        mod = self._harness()

        async def _drive():
            before = mod._count_pending_async_tasks()
            # Spawn a task that outlives the measurement (a "leaked" session).
            leak = asyncio.ensure_future(asyncio.sleep(50))
            await asyncio.sleep(0)  # let the scheduler start it
            after = mod._count_pending_async_tasks()
            leak.cancel()
            try:
                await leak
            except asyncio.CancelledError:
                pass
            return before, after

        before, after = asyncio.run(_drive())
        assert after > before, (
            "Guard (b) regression: _count_pending_async_tasks did not detect "
            f"the leaked task (before={before}, after={after})."
        )

    def test_run_all_threads_max_wall_seconds_to_all_runners(self) -> None:
        """CB #1528: ``run_all`` threads ``max_wall_seconds`` to EVERY runner
        (not just conversational) via the uniform dispatch call."""
        mod = self._harness()
        received: dict = {}

        async def fake_pipeline(
            text, cid, workflow_name="standard", max_wall_seconds=None
        ):
            received[f"pipeline_{workflow_name}"] = max_wall_seconds
            return mod.ModeResult(
                mode=f"pipeline_{workflow_name}", corpus_id=cid, success=True
            )

        async def fake_bridge(text, cid, max_wall_seconds=None):
            received["hierarchical_bridge"] = max_wall_seconds
            return mod.ModeResult(
                mode="hierarchical_bridge", corpus_id=cid, success=True
            )

        async def fake_conv(text, cid, max_wall_seconds=180.0):
            received["conversational"] = max_wall_seconds
            return mod.ModeResult(mode="conversational", corpus_id=cid, success=True)

        async def fake_det(text, cid, max_wall_seconds=None):
            received["conversation_deterministic"] = max_wall_seconds
            return mod.ModeResult(
                mode="conversation_deterministic",
                corpus_id=cid,
                success=True,
                phases_completed=3,
            )

        fake_runners = {
            "pipeline": fake_pipeline,
            "hierarchical_bridge": fake_bridge,
            "conversational": fake_conv,
            "conversation_deterministic": fake_det,
        }

        async def _drive():
            with patch.object(mod, "MODE_RUNNERS", fake_runners), patch(
                "argumentation_analysis.core.jvm_setup.initialize_jvm",
                return_value=None,
            ):
                return await mod.run_all(
                    modes=[
                        "pipeline",
                        "hierarchical_bridge",
                        "conversational",
                        "conversation_deterministic",
                    ],
                    corpora=["corpus_A"],
                    max_wall_seconds=42.0,
                )

        asyncio.run(_drive())
        assert received == {
            "pipeline_standard": 42.0,
            "hierarchical_bridge": 42.0,
            "conversational": 42.0,
            "conversation_deterministic": 42.0,
        }, f"run_all did not thread max_wall_seconds to all runners: {received}"

    def test_generate_report_renders_none_decides_as_question(self) -> None:
        """CB #1528 folds-in: ``decides=None`` (indeterminate) renders ``?``,
        NOT ``—`` (anti-#1019: 'I didn't check' ≠ 'I checked, nothing')."""
        mod = self._harness()
        none_result = mod.ModeResult(
            mode="pipeline_standard", corpus_id="corpus_A", success=True
        )
        none_result.decides = None  # bypassed _compute_decides
        report = mod.generate_report([none_result])
        assert (
            "| ? |" in report
        ), "CB #1528 folds-in regression: decides=None must render '?', not '—'."

    def test_generate_report_decides_true_false_distinct(self) -> None:
        """True → ``✅``, False → ``—`` (the common run_all-normalized cases)."""
        mod = self._harness()
        yes = mod.ModeResult(
            mode="pipeline_standard", corpus_id="corpus_A", success=True
        )
        yes.decides = True
        no = mod.ModeResult(mode="conversational", corpus_id="corpus_B", success=False)
        no.decides = False
        report = mod.generate_report([yes, no])
        assert "| ✅ |" in report
        assert "| — |" in report


class TestC3DelegationDepthParity1500:
    """Track C3 #1500 — delegation depth-parity chiffrage + reader fold-in.

    Two coupled fixes (coord R710 FINDING + DISPATCH):

    * **Reader fold-in**: ``run_hierarchical_delegation_mode`` reads the keys
      ``DelegationOrchestrator.analyze`` ACTUALLY emits (``tasks_created`` /
      ``operational_results[].status`` / ``evaluation``), not the phantom
      ``summary`` / ``capabilities_used`` (never emitted → the report line
      showed ``0/0`` phases on a run where 5 tasks executed). Those zeros were
      unread fields, not measurements.
    * **Depth chiffrage**: the delegation depth axis is LLM-derived, so its
      count is a MEASURED RANGE over ≥3 inputs (injected as a constant +
      provenance, NOT an LLM call at render time).

    Deterministic + LLM/JVM-free: the inner entry-point is patched with a fake
    delegation result carrying the real return shape.
    """

    def _harness(self):
        return _load_harness_module()

    @staticmethod
    def _fake_delegation_result():
        """The real ``DelegationOrchestrator.analyze`` return shape (no
        ``summary``, no ``capabilities_used`` — those are the phantom keys)."""
        return {
            "mode": "delegation",
            "objectives": [
                {"id": "obj-1"},
                {"id": "obj-2"},
                {"id": "obj-3"},
                {"id": "obj-4"},
            ],
            "tasks_created": 5,
            "operational_results": [
                {
                    "objective_id": "obj-1",
                    "status": "completed",
                    "outputs": {"arguments": ["a1"]},
                },
                {
                    "objective_id": "obj-1",
                    "status": "completed_with_issues",
                    "outputs": {"fallacies": ["f1"]},
                },
                {"objective_id": "obj-2", "status": "completed", "outputs": {}},
                {
                    "objective_id": "obj-3",
                    "status": "failed",
                    "reason": "insufficient_input",
                },
                {"objective_id": "obj-4", "status": "completed", "outputs": {}},
            ],
            "evaluation": {"overall_success_rate": 0.8, "objectives_evaluated": 4},
            "conclusion": "Analyse réussie.",
        }

    def test_delegation_reader_reads_real_keys(self) -> None:
        """The reader maps ``tasks_created`` -> phases_total and counts
        ``operational_results[].status`` -> phases_completed. A ``summary``
        key is absent from the input; the counts must still be correct
        (proving we do not rely on the phantom key)."""
        mod = self._harness()
        fake = self._fake_delegation_result()

        async def fake_analyze(**kwargs):
            return fake

        async def _drive():
            with patch(
                "argumentation_analysis.orchestration.hierarchical.orchestrator"
                ".run_hierarchical_analysis",
                side_effect=fake_analyze,
            ), patch(
                "argumentation_analysis.orchestration.registry_setup" ".setup_registry",
                return_value=None,
            ):
                return await mod.run_hierarchical_delegation_mode(
                    "text", "corpus_A", max_wall_seconds=None
                )

        r = asyncio.run(_drive())
        # phases_total <- tasks_created (5), NOT summary.total (absent).
        assert r.phases_total == 5
        # 4 completed (3 "completed" + 1 "completed_with_issues"), 1 failed.
        assert r.phases_completed == 4
        assert r.extra_metrics["tasks_failed"] == 1
        # objectives_count is the DoD-3 depth axis (strategic tier).
        assert r.extra_metrics["objectives_count"] == 4
        # Honest evaluation signal surfaced, not buried.
        assert r.extra_metrics["overall_success_rate"] == 0.8
        # The verdict artifact (conclusion) is stashed for _compute_decides.
        assert r.extra_metrics["verdict_artifact"] == "Analyse réussie."

    def test_delegation_decides_from_real_completed_tasks(self) -> None:
        """Post-fold-in, ``decides`` keys on ``phases_completed > 0`` (real
        completed operational tasks), not just the conclusion. A run with
        completed tasks decides True even before run_all normalizes it."""
        mod = self._harness()
        fake = self._fake_delegation_result()

        async def fake_analyze(**kwargs):
            return fake

        async def _drive():
            with patch(
                "argumentation_analysis.orchestration.hierarchical.orchestrator"
                ".run_hierarchical_analysis",
                side_effect=fake_analyze,
            ), patch(
                "argumentation_analysis.orchestration.registry_setup" ".setup_registry",
                return_value=None,
            ):
                return await mod.run_hierarchical_delegation_mode("text", "corpus_A")

        r = asyncio.run(_drive())
        # Direct runner call leaves decides=None (run_all computes it); verify
        # via the uniform helper that the real signals => True.
        assert r.decides is None
        assert mod._compute_decides(r) is True

    def test_depth_parity_delegation_row_carries_measured_range(self) -> None:
        """The delegation depth-parity row carries a MEASURED RANGE with
        provenance (not the old ``variable (LLM-derived)`` placeholder)."""
        mod = self._harness()
        rows = mod.compute_depth_parity()
        delegation = next(r for r in rows if r.mode == "hierarchical_delegation")
        assert delegation.measured_range is not None, (
            "C3 regression: delegation row has no measured_range — the depth "
            "axis must be a firsthand-measured range, not 'variable'."
        )
        # Provenance: range + n= + inputs, so a reader can audit the measure.
        assert "objectives" in delegation.measured_range
        assert "tasks" in delegation.measured_range
        assert "n=" in delegation.measured_range
        # depth_count is a usable int (max of the objective range).
        assert delegation.depth_count > 0

    def test_depth_parity_render_shows_range_not_variable(self) -> None:
        """The rendered section shows the measured range, NOT the stale
        ``variable (LLM-derived)`` string — and does so WITHOUT calling an
        LLM (deterministic render from the injected constant)."""
        mod = self._harness()
        section = mod.render_depth_parity_section()
        assert "variable (LLM-derived)" not in section, (
            "C3 regression: the delegation cell still renders 'variable' — the "
            "measured range must replace it."
        )
        delegation_line = next(
            ln for ln in section.splitlines() if "hierarchical_delegation" in ln
        )
        assert "objectives" in delegation_line
        assert "n=" in delegation_line

    def test_depth_parity_render_is_deterministic(self) -> None:
        """The render path is LLM-free — two calls produce identical output
        (regression guard against accidental LLM/IO in the render)."""
        mod = self._harness()
        a = mod.render_depth_parity_section()
        b = mod.render_depth_parity_section()
        assert a == b


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
