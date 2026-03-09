"""
Formal Debate workflow: structured argumentation with formal reasoning.

A 5-phase pipeline that formalizes arguments before structured debate:
1. quality_baseline       — Evaluate initial argument quality
2. formalization          — Formalize arguments as ASPIC+ rules
3. structured_dialogue    — Execute formal dialogue protocol
4. strength_ranking       — Rank arguments by formal strength
5. final_vote             — Multi-method governance vote on outcome
"""

import logging
from typing import Any, Dict, Optional

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
)

logger = logging.getLogger("FormalDebate")


def build_formal_debate_workflow() -> WorkflowDefinition:
    """Build the Formal Debate workflow.

    Combines informal quality assessment with formal ASPIC+ argumentation,
    structured dialogue protocols, and ranking semantics to produce
    a rigorous argument evaluation before governance voting.

    Returns:
        A 5-phase WorkflowDefinition.
    """
    return (
        WorkflowBuilder("formal_debate")
        # Phase 1: Quality baseline
        .add_phase(
            "quality_baseline",
            capability="argument_quality",
        )
        # Phase 2: Formalize arguments as ASPIC+ rules
        .add_phase(
            "formalization",
            capability="aspic_plus_reasoning",
            depends_on=["quality_baseline"],
        )
        # Phase 2b: ABA alternative formalization (optional, #85)
        .add_phase(
            "aba_formalization",
            capability="aba_reasoning",
            depends_on=["quality_baseline"],
            optional=True,
        )
        # Phase 3: Structured dialogue protocol
        .add_phase(
            "structured_dialogue",
            capability="dialogue_protocols",
            depends_on=["formalization"],
        )
        # Phase 4: Rank arguments by formal strength
        .add_phase(
            "strength_ranking",
            capability="ranking_semantics",
            depends_on=["structured_dialogue"],
        )
        # Phase 4b: Social AF for voting-based ranking (optional, #87)
        .add_phase(
            "social_ranking",
            capability="social_argumentation",
            optional=True,
            depends_on=["strength_ranking"],
        )
        # Phase 5: Governance vote on outcome
        .add_phase(
            "final_vote",
            capability="governance_simulation",
            depends_on=["strength_ranking"],
        )
        .set_metadata("domain", "formal_argumentation")
        .set_metadata("version", "1.0")
        .build()
    )


async def run_formal_debate(
    text: str,
    registry=None,
    create_state: bool = True,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the Formal Debate pipeline.

    Args:
        text: Proposition or argument to analyze.
        registry: CapabilityRegistry to use (auto-created if None).
        create_state: Whether to create UnifiedAnalysisState.
        context: Additional context passed to phases.

    Returns:
        Dict with formal debate results.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    workflow = build_formal_debate_workflow()
    return await run_unified_analysis(
        text=text,
        workflow_name="formal_debate",
        registry=registry,
        custom_workflow=workflow,
        context=context,
        create_state=create_state,
    )
