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


class TestCB1528CountsComeFromTheSnapshot:
    """CB #1528 item 3 — the Args/Fallacies columns must be MEASURED.

    The runner read ``result["extra_metrics"]["fallacy_count"]``, a key the
    conversational orchestrator never emits, so the default ``0`` was a
    fabricated zero indistinguishable from an observed one (leçon #1531);
    ``argument_count`` was not read at all, so a populated state rendered
    ``—``. Both are measured from the state snapshot, which this runner
    receives NON-summarized: raw attribute names (``identified_arguments``),
    not the summarized ``*_count`` shape — the same shape the pre-existing
    ``test_internal_bound_maps_to_real_partial_verdict`` fixture uses.
    """

    @staticmethod
    def _fake_result(**snapshot_extra):
        snapshot = {
            "identified_arguments": {"arg_0": "a", "arg_1": "b", "arg_2": "c"},
            "identified_fallacies": {"f_0": "x", "f_1": "y"},
        }
        snapshot.update(snapshot_extra)
        return {
            "phases": ["Extraction & Detection"],
            "conversation_log": [
                {"phase": "Extraction & Detection", "turn": 1, "content": "x"}
            ],
            "total_messages": 1,
            "state_snapshot": snapshot,
            "budget": {"wall_clock_bounded": True},
            "status": "WALL_CLOCK_BOUNDED",
            "duration_seconds": 30.0,
        }

    def _run(self, fake_result):
        mod = _load_harness_module()

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

        return asyncio.run(_drive())

    def test_counts_are_read_from_the_state_snapshot(self) -> None:
        result = self._run(self._fake_result())
        assert result.argument_count == 3, (
            "CB #1528 item 3 regression: argument_count is not read from the "
            f"state snapshot (got {result.argument_count!r}) — a populated "
            "state renders '—' in the Args column."
        )
        assert result.fallacy_count == 2, (
            "CB #1528 item 3 regression: fallacy_count is not read from the "
            f"state snapshot (got {result.fallacy_count!r})."
        )

    def test_absent_counts_stay_none_never_a_fabricated_zero(self) -> None:
        """Track CG #1540: absent ≠ measured. A snapshot without the keys must
        leave the columns unwritten (``None`` → ``—``), not report ``0``."""
        fake = self._fake_result()
        fake["state_snapshot"] = {"some_other_field": 1}
        result = self._run(fake)
        assert result.argument_count is None
        assert result.fallacy_count is None, (
            "A snapshot with no fallacy_count must render '—', not a 0 that "
            "reads as 'measured, none found'."
        )

    def test_measured_zero_stays_zero(self) -> None:
        """Anti-pendule: a real 0 must survive as 0, not be turned into ``—``."""
        fake = self._fake_result(identified_arguments={}, identified_fallacies={})
        result = self._run(fake)
        assert result.argument_count == 0
        assert result.fallacy_count == 0


class Test1560PipelineCountsComeFromTheSnapshot:
    """#1560 — the SAME phantom-key defect, in the pipeline runner.

    ``run_pipeline_mode`` read ``result["extra_metrics"]["fallacy_count"]``.
    ``extra_metrics`` has no producer anywhere in the package, so the call
    returned its literal default ``0`` on every run — a fabricated zero
    indistinguishable from an observed one (leçon #1531). It went unnoticed
    because the twin call-site was fixed (CB #1528 item 3, class above)
    WITHOUT grepping the pattern: a phantom key copied between sibling
    runners is a motif, not an accident.

    ⚠ INVERSE polarity from the conversational fix. ``unified_pipeline``
    returns ``get_state_snapshot(summarize=True)``, whose shape carries
    ``fallacy_count`` / ``argument_count`` FLAT at top level — NOT the raw
    ``identified_*`` collections the conversational runner reads. Copying
    that fix verbatim yields ``None`` everywhere while looking correct;
    ``test_counts_are_read_from_the_summarized_snapshot`` is what catches it.
    """

    @staticmethod
    def _fake_result(snapshot=None, **extra):
        result = {
            "summary": {"completed": 15, "total": 15},
            "state_snapshot": (
                {"fallacy_count": 2, "argument_count": 3}
                if snapshot is None
                else snapshot
            ),
            "capabilities_used": ["fact_extraction"],
            "capabilities_missing": [],
        }
        result.update(extra)
        return result

    def _run(self, fake_result):
        mod = _load_harness_module()

        async def fake_run(**kwargs):
            return fake_result

        async def _drive():
            with patch(
                "argumentation_analysis.orchestration.unified_pipeline"
                ".run_unified_analysis",
                side_effect=fake_run,
            ):
                return await mod.run_pipeline_mode("text", "corpus_A", "standard")

        return asyncio.run(_drive())

    def test_counts_are_read_from_the_summarized_snapshot(self) -> None:
        result = self._run(self._fake_result())
        assert result.fallacy_count == 2, (
            "#1560 regression: fallacy_count is not read from the summarized "
            f"state snapshot (got {result.fallacy_count!r}). Reading the raw "
            "``identified_*`` keys instead — the conversational shape — yields "
            "None here."
        )
        assert result.argument_count == 3

    def test_phantom_extra_metrics_is_never_consulted(self) -> None:
        """The exact defect: a key with no producer must not drive the column.

        If the reader still consults ``extra_metrics``, this returns 99 (or the
        old fabricated 0). Only reading the snapshot gives ``None`` here.
        """
        fake = self._fake_result(
            snapshot={"some_other_field": 1},
            extra_metrics={"fallacy_count": 99, "argument_count": 99},
        )
        result = self._run(fake)
        assert result.fallacy_count is None, (
            "#1560 regression: the runner is still reading the phantom "
            f"``extra_metrics`` key (got {result.fallacy_count!r})."
        )
        assert result.argument_count is None

    def test_absent_counts_stay_none_never_a_fabricated_zero(self) -> None:
        """Track CG #1540: absent ≠ measured. Unwritten renders ``—``, not 0."""
        result = self._run(self._fake_result(snapshot={"some_other_field": 1}))
        assert result.fallacy_count is None, (
            "A snapshot with no fallacy_count must render '—', not a 0 that "
            "reads as 'measured, none found'."
        )
        assert result.argument_count is None

    def test_measured_zero_stays_zero(self) -> None:
        """Anti-pendule: a real 0 must survive as 0, not be turned into ``—``."""
        result = self._run(
            self._fake_result(snapshot={"fallacy_count": 0, "argument_count": 0})
        )
        assert result.fallacy_count == 0
        assert result.argument_count == 0

    def test_null_snapshot_does_not_crash(self) -> None:
        """``unified_pipeline`` sets ``state_snapshot = None`` when state
        tracking is off — the key is PRESENT with a null value, so ``.get(...,
        {})`` returns None, not the default. The reader must survive that."""
        fake = self._fake_result()
        fake["state_snapshot"] = None
        result = self._run(fake)
        assert result.fallacy_count is None
        assert result.argument_count is None

    def test_summarized_snapshot_really_carries_these_keys(self) -> None:
        """Pin the CONSUMER-side contract this reader depends on.

        The reader is correct only as long as ``get_state_snapshot(summarize=
        True)`` exposes these two names at top level. If ``shared_state`` drifts,
        the reader silently returns ``None`` and the columns go back to being
        uninformative — so assert the contract rather than trust it.
        """
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        snapshot = UnifiedAnalysisState("x").get_state_snapshot(summarize=True)
        assert "fallacy_count" in snapshot
        assert "argument_count" in snapshot


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
            # #1560: the pipeline's snapshot is the SUMMARIZED shape. This
            # fixture used to also carry an ``extra_metrics`` key — which no
            # orchestrator emits — encoding the phantom key as if it were real.
            "state_snapshot": {"argument_count": 1, "fallacy_count": 2},
            "capabilities_used": ["fact_extraction"],
            "capabilities_missing": [],
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
        """CB #1528 item 2 anti-pendule: a breach that recovered NOTHING must
        stay sterile.

        The fake hangs before any checkpoint fires, so no phase completed and
        the state is measured empty. Post-item-2 the runner instruments the
        run — but instrumenting is not producing: ``decides`` must remain
        False → ``—``. This is the guard against "relabel every budget cut as
        bounded", which would destroy the column's discriminating power."""
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
        assert result.phases_completed == 0
        # Nothing recovered → sterile → honestly decides False.
        assert mod._compute_decides(result) is False

    def test_hierarchical_delegation_budget_breach_honest_degrade(self) -> None:
        """Same anti-pendule guard for the delegation mode: no task finished
        before the cut ⇒ nothing to recover ⇒ still ``—``."""
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
        assert result.phases_completed == 0
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

        async def fake_conv(
            text, cid, max_wall_seconds=180.0, room_policy="phase_casting"
        ):
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


class TestCC1531DegradedDelegationScoresDash:
    """CC #1531 item 1 — un verdict dégradé ne compte pas comme une décision.

    Sonde R718 : deux tâches ``completed``, dont une se déclarant
    ``degraded: true``, remontaient ``overall_rate: 1.0`` puis « Analyse
    réussie avec une performance globale élevée », et la ligne du tableau
    affichait ``Decides ✅``.

    Anti-pendule du ticket : ``_compute_decides`` n'est PAS touché — la
    définition uniforme (CA #1529) est correcte, c'est son ENTRÉE qui mentait.
    Ces tests vérifient donc l'entrée : ``verdict_artifact`` et
    ``phases_completed``.
    """

    @staticmethod
    def _harness():
        return _load_harness_module()

    @staticmethod
    def _degraded_result():
        """Forme réellement émise par ``DelegationOrchestrator.analyze`` quand
        aucune tâche opérationnelle n'a produit (delegation_orchestrator.py)."""
        return {
            "mode": "delegation",
            "objectives": [{"id": "obj-1"}, {"id": "obj-2"}],
            "tasks_created": 2,
            "operational_results": [
                {
                    "objective_id": "obj-1",
                    "status": "completed",
                    "degraded": True,
                    "degradation_reasons": ["fallacy_detection: degraded"],
                    "outputs": {"degraded": True, "total_fallacies": 0},
                },
                {
                    "objective_id": "obj-2",
                    "status": "completed",
                    "degraded": True,
                    "degradation_reasons": ["fact_extraction: status=unavailable"],
                    "outputs": {"status": "unavailable"},
                },
            ],
            "evaluation": {"overall_success_rate": 0.0, "objectives_evaluated": 2},
            "conclusion": "Analyse dégradée : aucune des 2 tâche(s) ...",
            "degraded": True,
            "degradation_reasons": ["fallacy_detection: degraded"],
        }

    def _drive(self, mod, fake):
        async def fake_analyze(**kwargs):
            return fake

        async def _run():
            with patch(
                "argumentation_analysis.orchestration.hierarchical.orchestrator"
                ".run_hierarchical_analysis",
                side_effect=fake_analyze,
            ), patch(
                "argumentation_analysis.orchestration.registry_setup" ".setup_registry",
                return_value=None,
            ):
                return await mod.run_hierarchical_delegation_mode("text", "corpus_A")

        return asyncio.run(_run())

    def test_degraded_run_scores_decides_false(self) -> None:
        """Le run dégradé tombe à ``—``, via son entrée et non via le helper."""
        mod = self._harness()
        r = self._drive(mod, self._degraded_result())

        assert r.extra_metrics["degraded"] is True
        assert r.extra_metrics["tasks_degraded"] == 2
        assert r.extra_metrics["verdict_artifact"] is None, (
            "un rapport de dégradation a été offert comme verdict sur "
            "l'argumentation"
        )
        assert r.phases_completed == 0, (
            "des tâches qui n'ont rien produit comptent encore comme des "
            "phases complétées — c'est ce qui alimentait le ✅"
        )
        assert mod._compute_decides(r) is False

    def test_degraded_conclusion_is_still_emitted_by_the_mode(self) -> None:
        """Anti-pendule : la conclusion EXISTE toujours côté orchestrateur.

        Le harness ne la compte pas comme un verdict, mais ne la supprime pas :
        un mode qui n'émettrait plus rien mentirait dans l'autre sens.
        """
        fake = self._degraded_result()
        assert fake["conclusion"], "le scénario de test doit garder la conclusion"
        assert "dégradée" in fake["conclusion"].lower()

    def test_healthy_run_still_decides_true(self) -> None:
        """GARDE-FOU : le chemin sain n'est pas affecté.

        Si ce test rougit, le fix a débordé de « ne pas compter une
        non-analyse » vers « ne plus rien compter ».
        """
        mod = self._harness()
        healthy = TestC3DelegationDepthParity1500._fake_delegation_result()
        r = self._drive(mod, healthy)

        assert r.extra_metrics["degraded"] is False
        assert r.extra_metrics["tasks_degraded"] == 0
        assert r.extra_metrics["verdict_artifact"] == "Analyse réussie."
        assert r.phases_completed == 4
        assert mod._compute_decides(r) is True


class TestCB1528Item2HierarchicalPartialVerdict:
    """CB #1528 item 2 — a wall-clock breach on a HIERARCHICAL mode must
    produce a REAL partial verdict, not a sterile hole.

    Measured gap that motivated this (coord R723/R724, firsthand): at N=45 s
    the two hierarchical modes were cut at ~45 % of their ~100-160 s
    trajectory and rendered ``decides —`` / ``0/0``, while the pipeline —
    cut at ~10 % of its trajectory, four times earlier in proportion — still
    rendered a verdict with 5.9 % fill. Coupé deux fois plus loin, on rendait
    quatre fois moins: the work was done and then thrown away by the
    ``asyncio.wait_for`` that killed the coroutine.

    The fix reuses the pipeline's mechanism rather than reimplementing it
    (issue périmètre point 2): a state reference + a recording checkpoint for
    the bridge (its DAG is a strictly sequential chain, so both fire once per
    completed phase), checkpointed task results for delegation (its T→O loop
    is sequential too).

    Anti-pendule guards live next to the recovery tests, not apart from them:
    a cut that recovered nothing stays sterile, and the unbounded path keeps
    passing no state / no callback at all.

    LLM-free and deterministic: the inner entry-points are patched.
    """

    def _harness(self):
        return _load_harness_module()

    @staticmethod
    def _phase(status_name: str) -> SimpleNamespace:
        return SimpleNamespace(status=SimpleNamespace(name=status_name))

    @staticmethod
    def _drive_bridge(mod, fake, **kwargs):
        async def _run():
            with patch(
                "argumentation_analysis.orchestration.hierarchical.orchestrator"
                ".run_hierarchical_analysis",
                side_effect=fake,
            ), patch(
                "argumentation_analysis.orchestration.registry_setup.setup_registry",
                return_value=None,
            ):
                return await mod.run_hierarchical_bridge_mode(
                    "text", "corpus_A", **kwargs
                )

        return asyncio.run(_run())

    @staticmethod
    def _drive_delegation(mod, fake, **kwargs):
        async def _run():
            with patch(
                "argumentation_analysis.orchestration.hierarchical.orchestrator"
                ".run_hierarchical_analysis",
                side_effect=fake,
            ), patch(
                "argumentation_analysis.orchestration.registry_setup.setup_registry",
                return_value=None,
            ):
                return await mod.run_hierarchical_delegation_mode(
                    "text", "corpus_A", **kwargs
                )

        return asyncio.run(_run())

    # ------------------------------------------------------------------
    # Bridge
    # ------------------------------------------------------------------

    def test_bridge_breach_recovers_completed_phases_and_state(self) -> None:
        """THE defect this item closes: work finished before the cut is
        reported instead of dying with the cancelled coroutine."""
        mod = self._harness()

        async def fake(**kwargs):
            state = kwargs.get("state")
            if state is not None and hasattr(state, "add_argument"):
                state.add_argument("argument_from_a_completed_phase")
            cb = kwargs.get("checkpoint_callback")
            if cb is not None:
                cb(
                    {"p1": self._phase("COMPLETED"), "p2": self._phase("COMPLETED")},
                    {"hierarchical_planned_phases": 6},
                )
            await asyncio.sleep(5)  # next phase torn by the budget

        result = self._drive_bridge(mod, fake, max_wall_seconds=0.5)

        assert result.terminated_by_budget is True
        assert result.success is False
        assert result.phases_completed == 2
        # Planned denominator read off the real WorkflowDefinition, so the
        # Phases column reads 2/6 — not the nonsensical N/0 (coord R710 wart).
        assert result.phases_total == 6
        assert result.state_fill_rate is not None and result.state_fill_rate > 0
        # The accumulated work IS the verdict (anti-#1019).
        assert mod._compute_decides(result) is True

    def test_bridge_breach_passes_the_recovery_seam(self) -> None:
        """Mutation guard: if the runner ever stops passing state / writers /
        checkpoint, recovery degrades SILENTLY back to the sterile result —
        the row would just read ``—`` again with nothing to explain it."""
        mod = self._harness()
        seen = {}

        async def fake(**kwargs):
            seen.update(kwargs)
            await asyncio.sleep(5)

        self._drive_bridge(mod, fake, max_wall_seconds=0.5)

        assert seen.get("state") is not None, "no state reference → nothing survives"
        assert seen.get("checkpoint_callback") is not None
        writers = seen.get("state_writers")
        assert writers, "no writers → the state stays empty however far the run got"
        from argumentation_analysis.orchestration.state_writers import (
            CAPABILITY_STATE_WRITERS,
        )

        assert writers is CAPABILITY_STATE_WRITERS, (
            "the harness must reuse the canonical writers, not a private copy "
            "(a second mapping is how call-sites drift apart — #1560)."
        )

    def test_bridge_torn_phase_is_not_counted(self) -> None:
        """A phase still running when the budget fires must not inflate the
        count. Only COMPLETED statuses are summed."""
        mod = self._harness()

        async def fake(**kwargs):
            cb = kwargs.get("checkpoint_callback")
            if cb is not None:
                cb(
                    {"p1": self._phase("COMPLETED"), "p2": self._phase("RUNNING")},
                    {"hierarchical_planned_phases": 4},
                )
            await asyncio.sleep(5)

        result = self._drive_bridge(mod, fake, max_wall_seconds=0.5)
        assert result.phases_completed == 1

    def test_bridge_unbounded_path_passes_no_instrumentation(self) -> None:
        """``max_wall_seconds=None`` = the original free-running path.
        Bounding is opt-in; it must not change how an unbounded run executes."""
        mod = self._harness()
        seen = {}

        async def fake(**kwargs):
            seen.update(kwargs)
            return {"summary": {"completed": 4, "total": 4}, "conclusion": "ok"}

        result = self._drive_bridge(mod, fake)
        assert result.success is True
        assert seen.get("state") is None
        assert seen.get("state_writers") is None
        assert seen.get("checkpoint_callback") is None

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------

    def test_delegation_breach_recovers_finished_tasks(self) -> None:
        mod = self._harness()

        async def fake(**kwargs):
            cb = kwargs.get("checkpoint_callback")
            if cb is not None:
                cb(
                    [
                        {"status": "completed", "capability": "c1"},
                        {"status": "completed_with_issues", "capability": "c2"},
                    ],
                    {"planned_tasks": 5},
                )
            await asyncio.sleep(5)

        result = self._drive_delegation(mod, fake, max_wall_seconds=0.5)

        assert result.terminated_by_budget is True
        # ``completed_with_issues`` produced output → counts (anti-punitive).
        assert result.phases_completed == 2
        assert result.phases_total == 5
        assert result.extra_metrics["tasks_finished_before_breach"] == 2
        assert mod._compute_decides(result) is True

    def test_delegation_breach_uses_the_same_counting_rules(self) -> None:
        """CC #1531 item 1 must hold at breach exactly as it holds on the
        completion path: a task that ran but self-declared it produced
        nothing is NOT a completed phase. One predicate, both paths — the
        twin-call-site drift of #1560 is what this pins."""
        mod = self._harness()

        async def fake(**kwargs):
            cb = kwargs.get("checkpoint_callback")
            if cb is not None:
                cb(
                    [
                        {"status": "completed", "capability": "c1"},
                        {"status": "completed", "capability": "c2", "degraded": True},
                        {"status": "failed", "capability": "c3"},
                    ],
                    {"planned_tasks": 5},
                )
            await asyncio.sleep(5)

        result = self._drive_delegation(mod, fake, max_wall_seconds=0.5)

        assert result.phases_completed == 1, "the degraded task must be subtracted"
        assert result.extra_metrics["tasks_degraded"] == 1
        assert result.extra_metrics["tasks_failed"] == 1

    def test_delegation_breach_with_only_degraded_tasks_stays_sterile(self) -> None:
        """The pendulum in the other direction: recovering *something* is not
        the same as producing something. Three tasks that all self-declared
        non-analysis leave no verdict."""
        mod = self._harness()

        async def fake(**kwargs):
            cb = kwargs.get("checkpoint_callback")
            if cb is not None:
                cb(
                    [{"status": "completed", "degraded": True} for _ in range(3)],
                    {"planned_tasks": 5},
                )
            await asyncio.sleep(5)

        result = self._drive_delegation(mod, fake, max_wall_seconds=0.5)
        assert result.phases_completed == 0
        assert mod._compute_decides(result) is False

    def test_delegation_unbounded_path_passes_no_callback(self) -> None:
        mod = self._harness()
        seen = {}

        async def fake(**kwargs):
            seen.update(kwargs)
            return {
                "mode": "delegation",
                "objectives": [{"id": "o1"}],
                "tasks_created": 1,
                "operational_results": [{"status": "completed"}],
                "evaluation": {},
                "conclusion": "ok",
            }

        result = self._drive_delegation(mod, fake)
        assert result.success is True
        assert seen.get("checkpoint_callback") is None

    # ------------------------------------------------------------------
    # Report marker (coord R723 "écart de rapport")
    # ------------------------------------------------------------------

    def test_recovered_budget_cut_renders_bounded(self) -> None:
        """A budget cut that produced a verdict must not carry the marker
        whose legend says "no verdict produced"."""
        mod = self._harness()
        r = mod.ModeResult(
            mode="hierarchical_bridge",
            corpus_id="corpus_A",
            success=False,
            terminates=True,
            terminated_by_budget=True,
            phases_completed=2,
            phases_total=6,
            decides=True,
        )
        row = [
            ln
            for ln in mod.generate_report([r]).splitlines()
            if ln.startswith("| hierarchical_bridge |")
        ]
        assert row and "✅⏱ bounded" in row[0], row

    def test_sterile_budget_cut_keeps_the_plain_marker(self) -> None:
        """Anti-théâtre: the marker tracks measured output, not the mere fact
        of having been bounded."""
        mod = self._harness()
        r = mod.ModeResult(
            mode="hierarchical_bridge",
            corpus_id="corpus_A",
            success=False,
            terminates=True,
            terminated_by_budget=True,
            decides=False,
        )
        row = [
            ln
            for ln in mod.generate_report([r]).splitlines()
            if ln.startswith("| hierarchical_bridge |")
        ]
        assert row and "✅⏱ bounded" not in row[0] and "⏱ budget" in row[0], row


class TestFillRateExcludesConstructionBaseline:
    """The fill rate must measure what the RUN produced, not the constructor.

    Discovered while implementing CB #1528 item 2. A freshly built
    ``UnifiedAnalysisState(text)`` is not empty — it already carries
    ``raw_text``, ``deanonymized`` and a ``stakes_and_stakeholders`` scaffold:
    3 non-empty fields out of 51, i.e. **5.9 %**, before a single phase runs.

    Counting those made an empty run score ``fill > 0``, which
    ``_compute_decides`` reads as "produced something". That is exactly the
    ``pipeline_standard | 45.01s | Decides ✅ | 0/15 phases | 5.9 %`` row
    measured firsthand at R723: the 5.9 % WAS the empty baseline echoed back,
    and the ✅ was manufactured by the constructor. Same family as
    #1560/#1019 — a number that looks like a measurement and is an artifact
    of the instrument.

    These guards pin the corrected definition at BOTH ends: an untouched
    state scores 0.0, and real content still scores > 0.
    """

    @staticmethod
    def _harness():
        return _load_harness_module()

    @staticmethod
    def _state(text: str = "some argument text about a claim"):
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        return UnifiedAnalysisState(text)

    def test_pristine_state_scores_zero_not_the_baseline(self) -> None:
        """A state nobody wrote to has produced nothing → 0.0, not 5.9 %."""
        mod = self._harness()
        assert mod._state_fill_rate(self._state()) == 0.0

    def test_pristine_state_alone_does_not_decide(self) -> None:
        """The end-to-end consequence: constructing a state is not a verdict.

        This is the defect as it was actually observed — the fill fed
        ``_compute_decides``, so a run that completed 0 phases reported ✅.
        """
        mod = self._harness()
        r = mod.ModeResult(
            mode="hierarchical_bridge",
            corpus_id="corpus_A",
            success=False,
            terminates=True,
            terminated_by_budget=True,
            phases_completed=0,
            state_fill_rate=mod._state_fill_rate(self._state()),
        )
        assert mod._compute_decides(r) is False

    def test_produced_content_still_scores_above_zero(self) -> None:
        """Anti-pendule: subtracting the baseline must not zero out real work.

        The failure mode of an over-corrected fix would be a state that DID
        accumulate content still reporting 0.0 — trading a fabricated ✅ for a
        fabricated ❌.
        """
        mod = self._harness()
        state = self._state()
        state.add_argument("corpus_A asserts a contested premise")
        fill = mod._state_fill_rate(state)
        assert fill is not None and fill > 0.0

    def test_absent_state_still_reads_none_not_zero(self) -> None:
        """CG #1540: "not instrumented" and "measured empty" stay distinct."""
        mod = self._harness()
        assert mod._state_fill_rate(None) is None

    # --- #1566: the snapshot-dict form (success paths) ---------------------
    # The success returns (``run_pipeline_mode`` / ``run_conversational_mode``)
    # hold only a snapshot DICT, never the state object, so they call the dict
    # form. Its baseline must be subtracted in the SAME shape the runner
    # snapshotted in — a raw baseline on a summarized snapshot (or the reverse)
    # would re-manufacture the very drift this class pins out.

    @staticmethod
    def _snap(
        text: str = "some argument text about a claim", summarize: bool = False
    ) -> dict:
        """A snapshot dict in the requested form (what the runners hold)."""
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState

        return UnifiedAnalysisState(text).get_state_snapshot(summarize=summarize) or {}

    def test_dict_form_pristine_scores_zero_both_shapes(self) -> None:
        """A snapshot nobody wrote to → 0.0 in BOTH forms (raw + summarized)."""
        mod = self._harness()
        assert mod._state_fill_rate(self._snap(summarize=False), summarize=False) == 0.0
        assert mod._state_fill_rate(self._snap(summarize=True), summarize=True) == 0.0

    def test_dict_form_produced_content_scores_above_zero(self) -> None:
        """Anti-pendule: baseline subtraction must not zero out real work."""
        mod = self._harness()
        state = self._state()
        state.add_argument("corpus_A asserts a contested premise")
        raw = state.get_state_snapshot(summarize=False) or {}
        fill = mod._state_fill_rate(raw, summarize=False)
        assert fill is not None and fill > 0.0

    def test_dict_form_requires_explicit_summarize(self) -> None:
        """A dict passed without ``summarize`` is ambiguous → refuse, do not guess.

        Silent-defaulting to raw or summarized would be exactly the drift this
        helper exists to remove; the form MUST be stated.
        """
        import pytest

        mod = self._harness()
        with pytest.raises(ValueError):
            mod._state_fill_rate(self._snap(summarize=False))

    def test_dict_form_baselines_differ_between_shapes(self) -> None:
        """The raw baseline (51-key: raw_text + deanonymized + stakes) and the
        summarized baseline (41-key: raw_text + raw_text_snippet) are DIFFERENT
        sets — subtracting the wrong one re-manufactures the drift."""
        mod = self._harness()
        raw_base = mod._construction_baseline_keys(False)
        sum_base = mod._construction_baseline_keys(True)
        assert raw_base != sum_base
        # Measured firsthand (R729 / coord R730): 3 raw, 2 summarized.
        assert len(raw_base) == 3
        assert len(sum_base) == 2

    def test_dict_form_agrees_with_object_form(self) -> None:
        """Object form and dict form give the SAME fill for the same state —
        they are one definition, two call shapes, not two definitions."""
        mod = self._harness()
        state = self._state()
        state.add_argument("corpus_A asserts a contested premise")
        state.add_argument("corpus_A further develops the claim with evidence")
        via_object = mod._state_fill_rate(state)
        via_dict = mod._state_fill_rate(
            state.get_state_snapshot(summarize=False) or {}, summarize=False
        )
        assert via_object is not None and via_dict is not None
        assert via_object == via_dict


class TestDeterministicFillTranche:
    """#1566 tranche — the deterministic mode's 5th site (coord R730 left open).

    ``run_conversation_deterministic_mode`` exposes NO ``UnifiedAnalysisState``;
    it published a weighted QUALITY grade in the State Fill column. Branch A
    (kept): ``state_fill_rate=None`` (renders "—", CG #1540 not-applicable) and
    the grade moves to ``extra_metrics["quality_score"]``.
    """

    @staticmethod
    def _harness():
        return _load_harness_module()

    def test_deterministic_publishes_none_fill_and_quality_score(self) -> None:
        """The quality grade is NOT a fill rate — it lives in extra_metrics."""
        mod = self._harness()
        r = mod.ModeResult(
            mode="conversation_deterministic",
            corpus_id="corpus_A",
            success=True,
            terminates=True,
            phases_completed=3,
            state_fill_rate=None,  # branch A: not-applicable, not measured-empty
            extra_metrics={
                "messages_count": 6,
                "tools_count": 3,
                "processing_time": 1.2,
                "quality_score": 0.74,
            },
        )
        assert r.state_fill_rate is None
        assert r.extra_metrics["quality_score"] == 0.74
        # _fmt_fill renders None as "—" (CG #1540), never "0.0%".
        assert mod._fmt_fill(r.state_fill_rate) == "—"
        # `decides` still carries on phases_completed, unaffected by the tranche.
        assert mod._compute_decides(r) is True


class TestBridgeLedgerReason1756:
    """#1756 — the bridge reader must not pretend to read an absent key.

    ``HierarchicalOrchestrator.analyze`` (bridge) returns 8 keys, NONE of the
    three capability-ledger keys. The old reader did
    ``result.get("capabilities_used", [])`` — the ``[]`` was FABRICATED ("I
    looked, there are none") for a mode that never kept a ledger. The
    ``n/a (mode emits no capability ledger)`` line was rendered by
    coincidence (three empty containers), not by knowledge.

    Two controls, both red on the pre-fix tree:

    1. **The reason today**: a bridge return with NO ledger key must leave
       ``capabilities_used is None`` — not a fabricated ``[]`` — and still
       render the ``n/a`` line.
    2. **The reason the day the producer changes** (the issue's core): a
       bridge return carrying ONE of the three keys must render the other
       two as ``n/a``, never as a measured-looking ``0``. On the pre-fix
       tree ``capabilities_missing`` defaulted to ``[]`` and rendered
       ``0 missing`` — a zero nobody measured.

    A test that merely asserts "the line shows n/a" (the current, correct
    rendering) would be green on both trees and measure nothing — that is
    exactly why these controls pin the MECHANISM, not the output.
    """

    def _harness(self):
        return _load_harness_module()

    @staticmethod
    def _fake_bridge_result(with_partial_ledger: bool) -> dict:
        """The real ``HierarchicalOrchestrator.analyze`` bridge return shape:
        8 keys, none of the ledger keys — plus, when ``with_partial_ledger``,
        ONE ledger key (the future-producer scenario the issue warns about)."""
        base = {
            "objectives": [{"id": "obj-1"}],
            "strategic_plan": {"phases": ["p1", "p2"]},
            "phase_results": {
                "p1": {"status": "completed", "output": {}, "error": None}
            },
            "conclusion": "Analyse terminée.",
            "evaluation": {"overall_success_rate": 1.0},
            "duration_seconds": 1.5,
            "summary": {"completed": 1, "total": 2},
            "workflow_name": "standard",
        }
        if with_partial_ledger:
            base["capabilities_used"] = ["argument_quality"]
        return base

    def _drive_bridge(self, mod, fake: dict):
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
                return await mod.run_hierarchical_bridge_mode(
                    "text", "corpus_A", max_wall_seconds=None
                )

        return asyncio.run(_drive())

    def test_no_ledger_is_none_not_fabricated_empty(self) -> None:
        """Bridge return WITHOUT any ledger key: the reader must leave None
        (absence), not a fabricated [] (measured-empty). Red pre-fix: the
        old ``.get(k, [])`` produced []."""
        mod = self._harness()
        r = self._drive_bridge(mod, self._fake_bridge_result(with_partial_ledger=False))
        assert r.capabilities_used is None, (
            "the bridge producer emits no `capabilities_used` — the reader "
            "must not fabricate a [] that reads as a measurement (#1756)"
        )
        assert r.capabilities_missing is None
        assert r.capabilities_degraded is None
        # ...and the n/a line is rendered FOR THAT REASON (no_ledger).
        lines = mod._capability_ledger_lines(r)
        assert any("emits no capability ledger" in line for line in lines)

    def test_partial_ledger_other_two_render_na_not_zero(self) -> None:
        """The issue's core scenario: the day the producer starts emitting
        ONE of the three keys, the other two must render n/a — never a 0
        nobody measured. Red pre-fix: missing defaulted to [] → '0 missing'."""
        mod = self._harness()
        r = self._drive_bridge(mod, self._fake_bridge_result(with_partial_ledger=True))
        assert r.capabilities_used == ["argument_quality"]
        lines = mod._capability_ledger_lines(r)
        head = lines[0]
        assert "1 used" in head
        assert "n/a degraded" in head
        assert (
            "n/a missing" in head
        ), "a non-emitted ledger key must render n/a, not a fabricated 0"
        assert "0 missing" not in head
        assert "0 degraded" not in head


class TestCountPerimeter1740:
    """#1740 — a count only means something if its PRODUCER actually ran.

    ``get_state_snapshot`` derives every count as ``len()`` over a
    PRE-DECLARED container (``shared_state.py``), so the count key is never
    absent and the CG #1540 "absent → None → —" convention is inert on it.
    The discriminator therefore has to come from the executed perimeter: a
    pipeline whose workflow never exercised the producing capability must
    render ``n/a``, never a fabricated ``0``. That is the ``#1735`` defect —
    a budget/scope-truncated run read as "0 mistakes found".

    Each control is green on the current tree and RED under a degenerate
    substitution (proof in the round log): re-wiring the hop to a constant
    ``"0"`` reddens the without-producer control; to a constant ``"n/a"``
    reddens the with-producer control. A test that merely asserted the
    current output would be green on both trees and measure nothing.
    """

    def _harness(self):
        return _load_harness_module()

    @staticmethod
    def _workflow_capabilities(builder):
        """The phase-capability set of a real workflow builder."""
        return frozenset(p.capability for p in builder().phases)

    def test_light_workflow_has_no_fallacy_producer(self) -> None:
        mod = self._harness()
        from argumentation_analysis.orchestration.workflows import (
            build_light_workflow,
        )

        caps = self._workflow_capabilities(build_light_workflow)
        assert not (caps & mod._FALLACY_PRODUCING_CAPABILITIES), (
            "the light workflow must not exercise a fallacy producer, or this "
            "control loses its discriminating power (#1740)"
        )
        assert "fact_extraction" in caps, (
            "the light workflow must still exercise the ARGUMENT producer, so "
            "the perimeter contrast is on the FALLACY axis only — otherwise the "
            "render difference is trivially the workflow, not the perimeter hop"
        )

    def test_standard_workflow_exercises_both_fallacy_producers(self) -> None:
        mod = self._harness()
        from argumentation_analysis.orchestration.workflows import (
            build_standard_workflow,
        )

        caps = self._workflow_capabilities(build_standard_workflow)
        assert (caps & mod._FALLACY_PRODUCING_CAPABILITIES) == (
            mod._FALLACY_PRODUCING_CAPABILITIES
        ), (
            "the standard workflow must exercise both fallacy producers, so its "
            "perimeter is exhaustive over the fallacy axis (#1740)"
        )

    def test_workflow_without_producer_renders_na_not_zero(self) -> None:
        mod = self._harness()
        from argumentation_analysis.orchestration.workflows import (
            build_light_workflow,
        )

        caps = self._workflow_capabilities(build_light_workflow)
        rendered = mod._fmt_count_in_perimeter(
            0, mod._FALLACY_PRODUCING_CAPABILITIES, sorted(caps), True
        )
        assert rendered == "n/a", (
            "the light workflow ran no fallacy producer, so its 0 is NOT a "
            "measurement — it must render n/a (#1740), not " + repr(rendered)
        )

    def test_workflow_with_producer_renders_measured_zero(self) -> None:
        mod = self._harness()
        from argumentation_analysis.orchestration.workflows import (
            build_standard_workflow,
        )

        caps = self._workflow_capabilities(build_standard_workflow)
        rendered = mod._fmt_count_in_perimeter(
            0, mod._FALLACY_PRODUCING_CAPABILITIES, sorted(caps), True
        )
        assert rendered == "0", (
            "the standard workflow ran the fallacy producer, so 0 is a genuine "
            "measurement — it must render 0 (#1740), not " + repr(rendered)
        )

    def test_workflow_without_and_with_producer_render_differ(self) -> None:
        mod = self._harness()
        from argumentation_analysis.orchestration.workflows import (
            build_light_workflow,
            build_standard_workflow,
        )

        light = self._workflow_capabilities(build_light_workflow)
        standard = self._workflow_capabilities(build_standard_workflow)
        light_render = mod._fmt_count_in_perimeter(
            0, mod._FALLACY_PRODUCING_CAPABILITIES, sorted(light), True
        )
        standard_render = mod._fmt_count_in_perimeter(
            0, mod._FALLACY_PRODUCING_CAPABILITIES, sorted(standard), True
        )
        assert (light_render, standard_render) == ("n/a", "0"), (
            "the two workflows' Fallacies cells must differ (n/a vs 0) — the "
            "#1735 defect collapsed them to the same 0, "
            f"here {light_render!r} vs {standard_render!r}"
        )

    def test_producing_capability_sets_pinned_against_state_writers(self) -> None:
        """The :469 promise: the producing sets are pinned so they cannot
        drift silently when a workflow gains a capability."""
        mod = self._harness()
        from argumentation_analysis.orchestration.state_writers import (
            CAPABILITY_STATE_WRITERS,
        )

        writer_keys = set(CAPABILITY_STATE_WRITERS.keys())
        fallacy_writer_keys = frozenset(
            k for k in writer_keys if "fallacy" in k.lower()
        )
        assert mod._FALLACY_PRODUCING_CAPABILITIES == fallacy_writer_keys, (
            "the fallacy-producing set drifted from the *fallacy*-named "
            "state-writer keys it must mirror (#1740)"
        )
        assert mod._ARGUMENT_PRODUCING_CAPABILITIES == {"fact_extraction"}
        assert mod._ARGUMENT_PRODUCING_CAPABILITIES <= writer_keys, (
            "fact_extraction is no longer a state writer — the argument "
            "producer is gone and the count can never be measured (#1740)"
        )


class TestDeprecatedModeAliases1740:
    """#1740 / #1747 — deprecated aliases stay DISPATCHABLE but are excluded
    from the DEFAULT sweep, so a report cannot double-count a mode.

    The #1735 baseline ran ``hierarchical`` AND ``hierarchical_bridge`` by
    default; both self-label ``hierarchical_bridge``, so the bridge appeared
    SIX times for three corpora while the report announced "Modes tested: 7"
    — anyone aggregating that table counted the bridge twice.
    """

    def _harness(self):
        return _load_harness_module()

    def test_aliases_are_dispatchable(self) -> None:
        mod = self._harness()
        assert mod._DEPRECATED_MODE_ALIASES <= set(mod.MODE_RUNNERS), (
            "a deprecated alias absent from MODE_RUNNERS is a broken lane, not "
            "a deprecation (#1740) — the alias must still dispatch"
        )

    def test_default_sweep_excludes_aliases(self) -> None:
        mod = self._harness()
        defaults = set(mod.default_modes())
        assert not (defaults & mod._DEPRECATED_MODE_ALIASES), (
            "the default sweep must exclude deprecated aliases (#1740) — "
            "running them by default is what double-counted the bridge"
        )
        assert "pipeline_standard" in defaults
        assert "hierarchical_bridge" in defaults

    def test_modes_tested_counts_distinct_labels(self) -> None:
        mod = self._harness()
        r1 = mod.ModeResult(
            mode="pipeline_standard", corpus_id="corpus_A", success=True
        )
        r2 = mod.ModeResult(
            mode="pipeline_standard", corpus_id="corpus_B", success=True
        )
        report = mod.generate_report([r1, r2])
        assert "Modes tested: 1" in report, (
            "a report must count DISTINCT mode labels, so an alias and its "
            "canonical key cannot inflate the count (#1740/#1747)"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
