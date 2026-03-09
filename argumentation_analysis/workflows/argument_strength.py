"""
Argument Strength workflow: quantify argument strength with formal methods.

A 4-phase pipeline that combines informal and formal evaluation:
1. quality_baseline       — 9-virtue quality evaluation
2. formal_ranking         — Rank arguments via ranking semantics
3. uncertainty_analysis   — Probabilistic acceptance (optional)
4. vulnerability_scan     — Counter-argument vulnerability check
"""

import logging
from typing import Any, Dict, Optional

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
)

logger = logging.getLogger("ArgumentStrength")


def build_argument_strength_workflow() -> WorkflowDefinition:
    """Build the Argument Strength workflow.

    Combines informal quality evaluation with formal ranking semantics
    and optional probabilistic analysis to produce a comprehensive
    argument strength assessment.

    Returns:
        A 4-phase WorkflowDefinition.
    """
    return (
        WorkflowBuilder("argument_strength")
        # Phase 1: Quality baseline
        .add_phase(
            "quality_baseline",
            capability="argument_quality",
        )
        # Phase 2: Formal ranking
        .add_phase(
            "formal_ranking",
            capability="ranking_semantics",
            depends_on=["quality_baseline"],
        )
        # Phase 2b: Bipolar AF for support+attack analysis (optional, #85)
        .add_phase(
            "bipolar_strength",
            capability="bipolar_argumentation",
            optional=True,
            depends_on=["formal_ranking"],
        )
        # Phase 3: Optional probabilistic analysis
        .add_phase(
            "uncertainty_analysis",
            capability="probabilistic_argumentation",
            optional=True,
            depends_on=["formal_ranking"],
        )
        # Phase 4: Vulnerability scan
        .add_phase(
            "vulnerability_scan",
            capability="counter_argument_generation",
            depends_on=["formal_ranking"],
        )
        .set_metadata("domain", "argument_evaluation")
        .set_metadata("version", "1.0")
        .build()
    )


async def run_argument_strength(
    text: str,
    registry=None,
    create_state: bool = True,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the Argument Strength pipeline.

    Args:
        text: Argument text to evaluate.
        registry: CapabilityRegistry to use (auto-created if None).
        create_state: Whether to create UnifiedAnalysisState.
        context: Additional context passed to phases.

    Returns:
        Dict with argument strength evaluation results.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    workflow = build_argument_strength_workflow()
    return await run_unified_analysis(
        text=text,
        workflow_name="argument_strength",
        registry=registry,
        custom_workflow=workflow,
        context=context,
        create_state=create_state,
    )
