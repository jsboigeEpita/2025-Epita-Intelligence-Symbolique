"""
Democratech workflow: democratic deliberation pipeline.

A 9-phase pipeline that takes a proposition and subjects it to multi-agent
argumentative analysis, producing a democratic decision with full audit trail.

Phases:
1. transcription          — Speech-to-text (optional, if audio input)
2. quality_baseline       — 9-virtue argument quality evaluation
3. fallacy_detection      — Neural fallacy detection (optional)
4. counter_arguments      — Generate counter-arguments (5 strategies)
5. adversarial_debate     — Multi-agent debate simulation
6. belief_tracking        — JTMS belief maintenance (optional)
7. democratic_vote        — Multi-method governance voting
8. indexing               — Semantic indexing for future retrieval (optional)
9. quality_recheck        — Re-evaluate quality if consensus is low (conditional)
"""

import logging
from typing import Any, Dict, Optional

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
)

logger = logging.getLogger("Democratech")

DEFAULT_CONSENSUS_THRESHOLD = 0.7


def _needs_refinement(ctx: Dict[str, Any], threshold: float) -> bool:
    """Return True when governance consensus is below threshold.

    This condition triggers the quality_recheck phase to reassess
    argument quality after a low-consensus vote.
    """
    vote_output = ctx.get("phase_democratic_vote_output")
    if not vote_output or not isinstance(vote_output, dict):
        return False
    consensus = vote_output.get("consensus", vote_output.get("consensus_rate", 0.0))
    if not isinstance(consensus, (int, float)):
        return False
    return consensus < threshold


def build_democratech_workflow(
    consensus_threshold: float = DEFAULT_CONSENSUS_THRESHOLD,
) -> WorkflowDefinition:
    """Build the Democratech deliberation workflow.

    Args:
        consensus_threshold: Minimum consensus level (0-1) to skip the
            quality recheck phase. Below this, quality is reassessed.

    Returns:
        A 9-phase WorkflowDefinition composing the full analysis stack.
    """

    def recheck_condition(ctx: Dict[str, Any]) -> bool:
        return _needs_refinement(ctx, consensus_threshold)

    return (
        WorkflowBuilder("democratech")
        # Phase 1: Optional transcription
        .add_phase(
            "transcription",
            capability="speech_transcription",
            optional=True,
        )
        # Phase 2: Quality baseline (required)
        .add_phase(
            "quality_baseline",
            capability="argument_quality",
        )
        # Phase 3: Optional fallacy detection
        .add_phase(
            "fallacy_detection",
            capability="neural_fallacy_detection",
            optional=True,
            depends_on=["quality_baseline"],
        )
        # Phase 4: Generate counter-arguments
        .add_phase(
            "counter_arguments",
            capability="counter_argument_generation",
            depends_on=["quality_baseline"],
        )
        # Phase 5: Adversarial debate
        .add_phase(
            "adversarial_debate",
            capability="adversarial_debate",
            depends_on=["counter_arguments"],
        )
        # Phase 6: Optional belief tracking
        .add_phase(
            "belief_tracking",
            capability="belief_maintenance",
            optional=True,
            depends_on=["adversarial_debate"],
        )
        # Phase 7: Democratic vote
        .add_phase(
            "democratic_vote",
            capability="governance_simulation",
            depends_on=["adversarial_debate"],
        )
        # Phase 8: Optional semantic indexing
        .add_phase(
            "indexing",
            capability="semantic_indexing",
            optional=True,
            depends_on=["democratic_vote"],
        )
        # Phase 9: Conditional quality recheck
        .add_phase(
            "quality_recheck",
            capability="argument_quality",
            depends_on=["democratic_vote"],
            optional=True,
            condition=recheck_condition,
        )
        .set_metadata("domain", "democratic_decision_making")
        .set_metadata("version", "1.0")
        .build()
    )


async def run_deliberation(
    text: str,
    registry=None,
    create_state: bool = True,
    consensus_threshold: float = DEFAULT_CONSENSUS_THRESHOLD,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the Democratech deliberation pipeline.

    Convenience wrapper around run_unified_analysis with the
    Democratech workflow.

    Args:
        text: Proposition or policy text to analyze.
        registry: CapabilityRegistry to use (auto-created if None).
        create_state: Whether to create UnifiedAnalysisState for tracking.
        consensus_threshold: Governance consensus threshold for recheck.
        context: Additional context passed to phases.

    Returns:
        Dict with workflow results including phase outputs and state snapshot.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    workflow = build_democratech_workflow(consensus_threshold)
    return await run_unified_analysis(
        text=text,
        workflow_name="democratech",
        registry=registry,
        custom_workflow=workflow,
        context=context,
        create_state=create_state,
    )
