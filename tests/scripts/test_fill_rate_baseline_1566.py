# -*- coding: utf-8 -*-
"""Tests for #1566 — state fill rate excludes the construction baseline.

The harness ``_state_fill_rate`` (scripts/compare_orchestration_modes.py)
excludes the keys a pristine ``UnifiedAnalysisState(text)`` fills at
construction (``raw_text`` / ``raw_text_snippet`` summarized; ``raw_text`` /
``deanonymized`` / ``stakes_and_stakeholders`` raw) so a run that produced
nothing scores 0.0, not ~5-6 %, and the success paths compare to the breach
path on the same footing. The deterministic mode now publishes ``None`` (it
has no UnifiedAnalysisState) and surfaces its quality grade in
``extra_metrics["quality_score"]``.

These tests are no-key / no-LLM. ``tests/scripts/`` is outside the CI gate
(#1563), so run locally and cite in the PR.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_PATH = REPO_ROOT / "scripts" / "compare_orchestration_modes.py"


def _load_harness_module():
    """Import the harness by file path (independent of scripts namespace)."""
    spec = importlib.util.spec_from_file_location(
        "compare_orchestration_modes", str(HARNESS_PATH)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _pristine_snapshot(summarize: bool):
    """Snapshot of a pristine state (no phase has run) — the construction
    baseline. Opaque synthetic probe text (privacy HARD)."""
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    pristine = UnifiedAnalysisState("baseline_probe_opaque_synthetic")
    return pristine.get_state_snapshot(summarize=summarize)


# ---------------------------------------------------------------------------
# DoD #4 — a pristine state scores 0.0 on BOTH success-path forms
# ---------------------------------------------------------------------------


class TestFillRateExcludesConstructionBaseline:
    """A pristine state (nothing produced) scores 0.0, not ~5-6 %."""

    def test_pristine_summarized_scores_zero(self):
        h = _load_harness_module()
        snap = _pristine_snapshot(summarize=True)
        # BEFORE #1566 this was 2/41 ≈ 4.9 % (raw_text + raw_text_snippet
        # counted as "filled"). It must now be 0.0.
        assert h._state_fill_rate(snap, summarize=True) == 0.0

    def test_pristine_brut_scores_zero(self):
        h = _load_harness_module()
        snap = _pristine_snapshot(summarize=False)
        # BEFORE #1566 this was 3/51 ≈ 5.9 % (raw_text + deanonymized +
        # stakes_and_stakeholders). It must now be 0.0.
        assert h._state_fill_rate(snap, summarize=False) == 0.0

    def test_produced_content_summarized_is_positive(self):
        """A summarized snapshot with real analysis output scores > 0."""
        h = _load_harness_module()
        snap = _pristine_snapshot(summarize=True)
        # Simulate a phase that filled 3 analysis counts.
        snap["argument_count"] = 3
        snap["fallacy_count"] = 2
        snap["belief_set_count"] = 1
        rate = h._state_fill_rate(snap, summarize=True)
        assert rate > 0.0
        # 3 produced fields out of (41 total - 2 baseline) = 3/39 ≈ 0.077.
        assert rate == round(3 / 39, 3)

    def test_produced_content_brut_is_positive(self):
        """A raw snapshot with real analysis output scores > 0."""
        h = _load_harness_module()
        snap = _pristine_snapshot(summarize=False)
        snap["identified_arguments"] = ["opaque_arg_0", "opaque_arg_1"]
        snap["identified_fallacies"] = ["opaque_fallacy_0"]
        rate = h._state_fill_rate(snap, summarize=False)
        assert rate > 0.0
        # 2 produced fields out of (51 total - 3 baseline) = 2/48 ≈ 0.042.
        assert rate == round(2 / 48, 3)

    def test_baseline_keys_differ_between_forms(self):
        """The baseline MUST be snapshotted in the same form as the
        measurement — a raw baseline subtracted from a summarized snapshot
        would re-manufacture drift. Prove the two baselines are genuinely
        different sets (so mixing them would be wrong)."""
        h = _load_harness_module()
        b_sum = h._construction_baseline_keys(True)
        b_raw = h._construction_baseline_keys(False)
        assert b_sum != b_raw
        # raw_text is filled in BOTH forms; the divergence proves the forms
        # carry different keys (raw_text_snippet only summarized,
        # deanonymized/stakes_and_stakeholders only raw).
        assert "raw_text" in b_sum and "raw_text" in b_raw
        assert "raw_text_snippet" in b_sum and "raw_text_snippet" not in b_raw
        assert "deanonymized" in b_raw and "deanonymized" not in b_sum

    def test_zero_sentinels_do_not_count_as_fill(self):
        """A field set to an empty sentinel (0, [], {}, "", None) does NOT
        inflate the fill — mirrors the pre-#1566 inline check."""
        h = _load_harness_module()
        snap = {"raw_text": "x", "raw_text_snippet": "x", "a": 0, "b": [], "c": {}}
        # 5 fields, 2 baseline, 3 measured all empty → 0.0 (not 3/3).
        assert h._state_fill_rate(snap, summarize=True) == 0.0


# ---------------------------------------------------------------------------
# DoD "tranche" — deterministic mode no longer masquerades a quality grade
# as a fill rate
# ---------------------------------------------------------------------------


class TestDeterministicFillTranche:
    """run_conversation_deterministic_mode publishes state_fill_rate=None
    (no UnifiedAnalysisState) and the quality grade in extra_metrics."""

    def test_deterministic_emits_none_fill_and_quality_score(self):
        h = _load_harness_module()
        result = asyncio.run(
            h.run_conversation_deterministic_mode(
                "opaque_synthetic_deliberation_probe corpus_A.", "corpus_A"
            )
        )
        # The State Fill column renders "—" (CG #1540: not applicable, not
        # measured-empty). The previous behavior published the quality grade
        # here — a different quantity under the same column name.
        assert result.state_fill_rate is None
        # The quality grade is preserved in its own channel, not dropped.
        assert "quality_score" in result.extra_metrics
        assert isinstance(result.extra_metrics["quality_score"], (int, float))
        # decides is unaffected (phases_completed=3 → True); fill is not the
        # verdict signal for this mode.
        assert result.phases_completed == 3
