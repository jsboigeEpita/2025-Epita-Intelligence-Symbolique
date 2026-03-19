"""
Comprehensive Analysis workflow: maximum-depth LLM-only analysis.

An 8-phase pipeline that combines the most effective LLM capabilities
without requiring JVM/Tweety, designed based on benchmark results showing
that debate_tournament (100% completion) and standard (100% completion)
achieve the best phase completion rates.

Phases:
1. extract          — Extract claims and arguments from text
2. quality_baseline — Evaluate argument quality (9 virtues)
3. fallacy_screen   — Hierarchical fallacy detection
4. counter_args     — Generate counter-arguments (5 strategies)
5. debate_rounds    — Iterative adversarial debate (loop)
6. governance_vote  — Multi-method democratic vote
7. quality_recheck  — Re-evaluate quality after debate (conditional)
8. belief_record    — Optional JTMS belief recording
"""

import logging
from typing import Any, Dict, Optional

from argumentation_analysis.orchestration.workflow_dsl import (
    LoopConfig,
    WorkflowBuilder,
    WorkflowDefinition,
)

logger = logging.getLogger("ComprehensiveAnalysis")


def _quality_below_threshold(output: Any) -> bool:
    """Trigger quality recheck if governance consensus is below 70%."""
    if not isinstance(output, dict):
        return True
    score = output.get("consensus_score", output.get("score", 0))
    try:
        return float(score) < 0.7
    except (ValueError, TypeError):
        return True


def _debate_converged(prev: Any, curr: Any) -> bool:
    """Check debate convergence — scores stabilized within 5%."""
    if not isinstance(prev, dict) or not isinstance(curr, dict):
        return False
    prev_score = prev.get("debate_score", prev.get("score", 0.0))
    curr_score = curr.get("debate_score", curr.get("score", 0.0))
    try:
        return abs(float(curr_score) - float(prev_score)) < 0.05
    except (ValueError, TypeError):
        return False


def build_comprehensive_analysis_workflow(
    max_debate_rounds: int = 2,
) -> WorkflowDefinition:
    """Build the Comprehensive Analysis workflow.

    Combines extraction, quality, fallacy detection, counter-arguments,
    adversarial debate, governance, and conditional re-evaluation in a
    single pipeline. All phases use LLM capabilities (no JVM required).

    Args:
        max_debate_rounds: Max iterations for debate loop.

    Returns:
        8-phase WorkflowDefinition.
    """
    return (
        WorkflowBuilder("comprehensive_analysis")
        # Phase 1: Extract claims
        .add_phase("extract", capability="fact_extraction")
        # Phase 2: Quality baseline
        .add_phase(
            "quality_baseline",
            capability="argument_quality",
            depends_on=["extract"],
        )
        # Phase 3: Fallacy screening
        .add_phase(
            "fallacy_screen",
            capability="hierarchical_fallacy_detection",
            depends_on=["extract"],
        )
        # Phase 4: Counter-arguments
        .add_phase(
            "counter_args",
            capability="counter_argument_generation",
            depends_on=["quality_baseline", "fallacy_screen"],
        )
        # Phase 5: Iterative debate
        .add_phase(
            "debate_rounds",
            capability="adversarial_debate",
            depends_on=["counter_args"],
            loop_config=LoopConfig(
                max_iterations=max_debate_rounds,
                convergence_fn=_debate_converged,
            ),
        )
        # Phase 6: Governance vote
        .add_phase(
            "governance_vote",
            capability="governance_simulation",
            depends_on=["debate_rounds"],
        )
        # Phase 7: Conditional quality recheck
        .add_conditional_phase(
            "quality_recheck",
            capability="argument_quality",
            condition=lambda ctx: _quality_below_threshold(
                ctx.get("governance_vote_output")
            ),
            depends_on=["governance_vote"],
        )
        # Phase 8: Optional belief recording
        .add_phase(
            "belief_record",
            capability="belief_maintenance",
            optional=True,
            depends_on=["governance_vote"],
        )
        .set_metadata("domain", "comprehensive_analysis")
        .set_metadata("version", "1.0")
        .set_metadata("jvm_required", False)
        .build()
    )


async def run_comprehensive_analysis(
    text: str,
    registry=None,
    max_debate_rounds: int = 2,
    create_state: bool = True,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the Comprehensive Analysis pipeline.

    Args:
        text: Text to analyze.
        registry: CapabilityRegistry (auto-created if None).
        max_debate_rounds: Max debate iterations.
        create_state: Whether to create UnifiedAnalysisState.
        context: Additional context.

    Returns:
        Dict with comprehensive analysis results.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    workflow = build_comprehensive_analysis_workflow(max_debate_rounds)
    return await run_unified_analysis(
        text=text,
        workflow_name="comprehensive_analysis",
        registry=registry,
        custom_workflow=workflow,
        context=context,
        create_state=create_state,
    )
