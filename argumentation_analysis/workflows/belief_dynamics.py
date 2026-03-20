"""
Belief Dynamics workflow: adversarial testing with belief revision.

A 5-phase pipeline that revises beliefs after adversarial debate:
1. adversarial_test   — Stress-test arguments via adversarial debate
2. belief_update      — Revise beliefs based on debate outcome
3. belief_tracking    — Track revised beliefs in JTMS
4. consensus_check    — Multi-method governance vote on revised position
5. quality_recheck    — Re-evaluate quality (conditional: low consensus)
"""

import logging
from typing import Any, Dict, Optional

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
)

logger = logging.getLogger("BeliefDynamics")

DEFAULT_CONSENSUS_THRESHOLD = 0.7


def _needs_quality_recheck(ctx: Dict[str, Any]) -> bool:
    """Check if consensus is below threshold, triggering quality recheck."""
    vote_output = ctx.get("phase_consensus_check_output")
    if not vote_output or not isinstance(vote_output, dict):
        return False
    consensus = vote_output.get("consensus", vote_output.get("consensus_rate", 0.0))
    if not isinstance(consensus, (int, float)):
        return False
    return consensus < DEFAULT_CONSENSUS_THRESHOLD


def build_belief_dynamics_workflow() -> WorkflowDefinition:
    """Build the Belief Dynamics workflow.

    Combines adversarial debate with AGM belief revision and JTMS
    tracking to create a pipeline that updates beliefs based on
    argument strength and re-evaluates when consensus is low.

    Returns:
        A 5-phase WorkflowDefinition with conditional quality recheck.
    """
    return (
        WorkflowBuilder("belief_dynamics")
        # Phase 0: Extract arguments and claims from text
        .add_phase(
            "extract",
            capability="fact_extraction",
        )
        # Phase 1: Adversarial stress test
        .add_phase(
            "adversarial_test",
            capability="adversarial_debate",
            depends_on=["extract"],
        )
        # Phase 2: Revise beliefs based on debate
        .add_phase(
            "belief_update",
            capability="belief_revision",
            depends_on=["adversarial_test"],
        )
        # Phase 3: Track revised beliefs in JTMS
        .add_phase(
            "belief_tracking",
            capability="belief_maintenance",
            depends_on=["belief_update"],
        )
        # Phase 4: Governance consensus check
        .add_phase(
            "consensus_check",
            capability="governance_simulation",
            depends_on=["belief_tracking"],
        )
        # Phase 5: Conditional quality recheck
        .add_phase(
            "quality_recheck",
            capability="argument_quality",
            depends_on=["consensus_check"],
            optional=True,
            condition=_needs_quality_recheck,
        )
        .set_metadata("domain", "belief_dynamics")
        .set_metadata("version", "1.0")
        .build()
    )


async def run_belief_dynamics(
    text: str,
    registry=None,
    create_state: bool = True,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the Belief Dynamics pipeline.

    Args:
        text: Proposition or argument to analyze.
        registry: CapabilityRegistry to use (auto-created if None).
        create_state: Whether to create UnifiedAnalysisState.
        context: Additional context passed to phases.

    Returns:
        Dict with belief dynamics results.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    workflow = build_belief_dynamics_workflow()
    return await run_unified_analysis(
        text=text,
        workflow_name="belief_dynamics",
        registry=registry,
        custom_workflow=workflow,
        context=context,
        create_state=create_state,
    )
