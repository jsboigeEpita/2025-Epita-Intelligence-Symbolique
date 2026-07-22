# tests/unit/argumentation_analysis/orchestration/test_depth_parity_1500.py
"""Track C3 of #1500 — depth-parity trade-off (documented, firsthand-chiffred).

The 4 orchestration modes are comparable in interface (all produce a
verdict on the same synthetic input) but NOT in work-perimeter. R653
surfaced the asymmetry firsthand: pipeline = breadth (workflow DAG phase
count), hierarchical = delegation (4 default objectives / 3-tier),
conversational = dialogue-depth (3 macro-phases, multi-turn).

Aligning the catalogue would be a pendulum (gut pipeline's breadth OR
inflate hierarchical/conversational artificially — both anti-#1019). The
honest C3 deliverable is to DOCUMENT the trade-off with firsthand chiffres,
which ``compute_depth_parity`` + ``render_depth_parity_section`` do.

These tests are JVM/LLM-free: they introspect the pure workflow builders
(light/standard/full) deterministically and assert the structural chiffres
match the real workflow phase counts (verify-before-assert — re-introspect
in the test, never trust a hand-written constant).
"""

from __future__ import annotations

import sys
from pathlib import Path

# ``scripts/`` is not a package; add it to sys.path so the harness module
# (which lives at scripts/compare_orchestration_modes.py) is importable.
_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRIPTS_DIR = str(_PROJECT_ROOT / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import compare_orchestration_modes as harness  # noqa: E402
from argumentation_analysis.orchestration.workflows import (  # noqa: E402
    build_full_workflow,
    build_light_workflow,
    build_standard_workflow,
)


class TestComputeDepthParity:
    """``compute_depth_parity`` returns one row per comparable mode with the
    correct structural depth axis (breadth / delegation / dialogue-depth).
    """

    def test_returns_all_comparable_modes(self) -> None:
        rows = harness.compute_depth_parity()
        modes = {r.mode for r in rows}
        # The three depth dimensions, each represented.
        assert "pipeline_standard" in modes  # breadth
        assert "hierarchical_bridge" in modes  # delegation
        assert "conversational" in modes  # dialogue-depth

    def test_pipeline_breadth_matches_real_workflow_phase_counts(self) -> None:
        # Verify-before-assert: re-introspect the real builders, do NOT trust
        # the hand-written chiffres. If a workflow gains/loses a phase, this
        # test forces the depth-parity table to be updated (no silent drift).
        rows = {r.mode: r for r in harness.compute_depth_parity()}
        assert rows["pipeline_light"].depth_count == len(build_light_workflow().phases)
        assert rows["pipeline_standard"].depth_count == len(
            build_standard_workflow().phases
        )
        assert rows["pipeline_full"].depth_count == len(build_full_workflow().phases)

    def test_pipeline_breadth_is_the_widest_dimension(self) -> None:
        # The firsthand R653 observation: pipeline exercises a far wider
        # capability catalogue than the other modes. Standard alone must be
        # wider than the hierarchical default objectives and the conversational
        # macro-phases.
        rows = {r.mode: r for r in harness.compute_depth_parity()}
        pipeline = rows["pipeline_standard"].depth_count
        hierarchical = rows["hierarchical_bridge"].depth_count
        conversational = rows["conversational"].depth_count
        assert pipeline > hierarchical
        assert pipeline > conversational

    def test_hierarchical_bridge_has_four_default_objectives(self) -> None:
        # delegation_orchestrator.py:291 documents the M2 bridge injects 4
        # default objectives (the delegation tier refuses to fabricate —
        # anti-#1019). This is the documented structural constant.
        rows = {r.mode: r for r in harness.compute_depth_parity()}
        assert rows["hierarchical_bridge"].depth_count == 4
        assert rows["hierarchical_bridge"].nature == "delegation"

    def test_conversational_is_dialogue_depth_not_breadth(self) -> None:
        rows = {r.mode: r for r in harness.compute_depth_parity()}
        assert rows["conversational"].nature == "dialogue-depth"
        assert rows["conversational"].depth_count == 3  # 3 macro-phases

    def test_modes_do_not_share_a_single_depth_axis(self) -> None:
        # The honest point: the depth_dimension labels DIFFER across modes —
        # they are not comparable on one common scale. This is the trade-off.
        rows = harness.compute_depth_parity()
        dimensions = {r.depth_dimension for r in rows}
        assert len(dimensions) > 1  # at least breadth + delegation + dialogue


class TestRenderDepthParitySection:
    """``render_depth_parity_section`` produces the documented trade-off."""

    def test_section_has_title_and_table_header(self) -> None:
        section = harness.render_depth_parity_section()
        assert "## Depth-Parity Trade-off (C3 #1500)" in section
        assert "| Mode | Depth dimension | Count | Nature |" in section

    def test_section_states_the_trade_off_is_deliberate(self) -> None:
        # Anti-#1019: the verdict must make explicit that the asymmetry is a
        # deliberate design trade-off, not a defect to "fix" by aligning.
        section = harness.render_depth_parity_section()
        assert "DELIBERATE design trade-off" in section
        assert "anti-#1019" in section

    def test_section_contains_firsthand_chiffres(self) -> None:
        section = harness.render_depth_parity_section()
        # The pipeline breadth chiffres (verified firsthand above).
        assert (
            f"| pipeline_standard | workflow phases (DAG) | {len(build_standard_workflow().phases)} |"
            in section
        )
        # The hierarchical delegation constant.
        assert (
            "| hierarchical_bridge | strategic objectives (default axes) | 4 |"
            in section
        )
