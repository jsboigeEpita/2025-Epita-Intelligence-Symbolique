# tests/unit/argumentation_analysis/orchestration/test_cg1540_unwritten_vs_measured.py
"""Track CG of #1540 — distinguish "not written" from "measured empty" in the
comparison table.

Three columns (State Fill / Fallacies / Args) used to render a mode that does
NOT populate the shared analysis state (hierarchical_bridge /
hierarchical_delegation decide by conclusion/verdict_artifact/phases_completed,
see _compute_decides DoD-4 #1529) as ``0.0 % / 0 / 0`` — indistinguishable
from a mode that DID write the state and measured it empty (a conversational
run cut at the safety-net: 0/0 phases, 0 % fill). That is exactly the leçon
#1531 / #1500 ("a value read from an absent field is indistinguishable from a
measured zero") replayed in the RENDERING layer.

CG #1540 applies the same treatment CA #1529 used for ``decides``:
``Optional``, default ``None`` ("not written"), rendered ``—``. A genuinely
measured-empty run still renders ``0.0 % / 0 / 0`` — the distinction is VISIBLE
in the same table.

These tests are JVM/LLM-free and deterministic.
"""

from __future__ import annotations

import sys
from pathlib import Path

# scripts/ is not a package; add it to sys.path so the harness module
# (scripts/compare_orchestration_modes.py) is importable — mirrors the
# test_ce1537_execution_path.py / test_depth_parity_1500.py setup.
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = str(_PROJECT_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import compare_orchestration_modes as harness  # noqa: E402

# ---------------------------------------------------------------------------
# DoD #4: _compute_decides is None-safe (None is not an artifact of verdict)
# ---------------------------------------------------------------------------


class TestComputeDecidesIsNoneSafe:
    def test_none_fields_do_not_raise(self):
        """A ModeResult with None fields (a not-writing mode) must not raise
        when _compute_decides reads them (None > 0 is a TypeError in Py3)."""
        r = harness.ModeResult(
            mode="hierarchical_bridge",
            corpus_id="corpus_A",
            success=True,
            # state_fill_rate / fallacy_count / argument_count default to None
            phases_completed=3,
            phases_total=3,
            scope_of_work="bridge",
        )
        # Must not raise — None is not an artifact and must not short-circuit
        # True either (a decision is still reachable via phases_completed).
        assert harness._compute_decides(r) is True

    def test_none_only_does_not_manufacture_a_decision(self):
        """A result with ALL of state_fill/fallacies/args/phases = None/0 must
        NOT decide True (anti-pendule: None is not a verdict)."""
        r = harness.ModeResult(
            mode="x",
            corpus_id="corpus_A",
            success=True,
            phases_completed=0,
            phases_total=0,
        )
        assert harness._compute_decides(r) is False

    def test_explicit_zero_stays_false(self):
        """Non-regression: a measured-empty run (explicit 0.0/0/0) still
        decides False — the None-handling did not weaken the 0 check."""
        r = harness.ModeResult(
            mode="conversational",
            corpus_id="corpus_A",
            success=True,
            state_fill_rate=0.0,
            fallacy_count=0,
            argument_count=0,
            phases_completed=0,
            phases_total=3,
        )
        assert harness._compute_decides(r) is False


# ---------------------------------------------------------------------------
# DoD #1 / #2 / #3: the table distinguishes "not written" from "measured empty"
# ---------------------------------------------------------------------------


def _md_for(r: harness.ModeResult) -> str:
    return harness.generate_report([r])


class TestTableDistinguishesUnwrittenFromMeasured:
    def test_unwritten_renders_dash_not_zero(self):
        """DoD #1: a mode that does NOT write the shared state renders '—'
        in State Fill / Fallacies / Args, NOT '0.0%' / '0' / '0'."""
        r = harness.ModeResult(
            mode="hierarchical_bridge",
            corpus_id="corpus_A",
            success=True,
            duration_seconds=5.0,
            # state_fill_rate / fallacy_count / argument_count = None (default)
            phases_completed=3,
            phases_total=3,
            scope_of_work="bridge (decides by conclusion)",
            decides=True,
        )
        md = _md_for(r)
        assert "—" in md, "expected '—' for unwritten state_fill_rate"
        # And it must NOT fabricate a 0.0% in its own row:
        assert "0.0%" not in md, (
            "CG #1540 regression: unwritten state rendered as 0.0% "
            "(indistinguishable from measured-empty)"
        )

    def test_measured_empty_renders_zero_not_dash(self):
        """DoD #2: a mode that DID write the state and measured it empty
        renders '0.0%' / '0' / '0' — the real zero stays visible (the
        conversational cut-at-safety-net failure mode must not be hidden)."""
        r = harness.ModeResult(
            mode="conversational",
            corpus_id="corpus_A",
            success=True,
            duration_seconds=90.0,
            state_fill_rate=0.0,
            fallacy_count=0,
            argument_count=0,
            phases_completed=0,
            phases_total=3,
            scope_of_work="conversational (cut at safety-net)",
            decides=False,
        )
        md = _md_for(r)
        assert "0.0%" in md, "measured-empty run must still show 0.0%"

    def test_two_cases_render_differently_side_by_side(self):
        """DoD #3: the two cases (None vs explicit 0.0) must NOT render the
        same — that is the whole point of CG #1540."""
        unwritten = harness.ModeResult(
            mode="hierarchical_bridge",
            corpus_id="corpus_A",
            success=True,
            duration_seconds=5.0,
            phases_completed=3,
            phases_total=3,
            scope_of_work="bridge",
            decides=True,
        )
        measured_empty = harness.ModeResult(
            mode="conversational",
            corpus_id="corpus_A",
            success=True,
            duration_seconds=90.0,
            state_fill_rate=0.0,
            fallacy_count=0,
            argument_count=0,
            phases_completed=0,
            phases_total=3,
            scope_of_work="conversational cut",
            decides=False,
        )
        md_unwritten = _md_for(unwritten)
        md_measured = _md_for(measured_empty)
        # The State Fill column differs: '—' vs '0.0%'
        assert "—" in md_unwritten and "0.0%" not in md_unwritten
        assert "0.0%" in md_measured


# ---------------------------------------------------------------------------
# Cross-mode fill-rate comparison must skip None (not treat it as 0.0%)
# ---------------------------------------------------------------------------


class TestCrossModeFillSkipsNone:
    def test_unwritten_mode_not_listed_as_highest_fill(self):
        """The 'Highest state fill' cross-mode line must not surface a mode
        whose state_fill_rate is None (it would read as a real 0.0% contender
        and, if a coercion bug crept in, as a spurious winner)."""
        unwritten = harness.ModeResult(
            mode="hierarchical_bridge",
            corpus_id="corpus_A",
            success=True,
            duration_seconds=5.0,
            phases_completed=3,
            phases_total=3,
            scope_of_work="bridge",
            decides=True,
        )
        with_fill = harness.ModeResult(
            mode="pipeline",
            corpus_id="corpus_A",
            success=True,
            duration_seconds=10.0,
            state_fill_rate=0.5,
            fallacy_count=2,
            argument_count=3,
            phases_completed=15,
            phases_total=15,
            scope_of_work="pipeline",
            decides=True,
        )
        md = harness.generate_report([unwritten, with_fill])
        # pipeline is the only mode with a real fill; it must be named the
        # highest, and bridge must NOT appear in a "Highest state fill" line.
        if "Highest state fill" in md:
            assert "pipeline" in md.split("Highest state fill")[1].splitlines()[0]
            assert (
                "hierarchical_bridge"
                not in md.split("Highest state fill")[1].splitlines()[0]
            )
