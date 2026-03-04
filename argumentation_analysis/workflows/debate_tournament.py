"""
Debate Tournament workflow: multi-round adversarial debate with scoring.

A 6-phase pipeline that simulates a structured debate tournament:
1. quality_prep         — Evaluate initial argument quality
2. vulnerability_scan   — Identify argument vulnerabilities
3. debate_rounds        — Iterative debate (loop with convergence)
4. final_scoring        — Score final arguments after debate
5. jury_vote            — Multi-method governance vote on winner
6. belief_record        — Record final beliefs (optional)
"""

import logging
from typing import Any, Dict, Optional

from argumentation_analysis.orchestration.workflow_dsl import (
    LoopConfig,
    WorkflowBuilder,
    WorkflowDefinition,
)

logger = logging.getLogger("DebateTournament")

DEFAULT_MAX_ROUNDS = 3


def _debate_score_converged(prev: Any, curr: Any) -> bool:
    """Check if debate scores have stabilized between iterations.

    Convergence is reached when the overall debate score changes by
    less than 5% between rounds, indicating arguments have plateaued.
    """
    if not isinstance(prev, dict) or not isinstance(curr, dict):
        return False

    def _extract_score(output: Dict) -> float:
        if "logical_coherence" in output:
            scores = [
                output.get("logical_coherence", 0),
                output.get("evidence_quality", 0),
                output.get("relevance_score", 0),
                output.get("persuasiveness", 0),
            ]
            return sum(scores) / len(scores) if scores else 0.0
        return output.get("debate_score", output.get("score", 0.0))

    prev_score = _extract_score(prev)
    curr_score = _extract_score(curr)
    return abs(curr_score - prev_score) < 0.05


def build_debate_tournament_workflow(
    max_rounds: int = DEFAULT_MAX_ROUNDS,
) -> WorkflowDefinition:
    """Build the Debate Tournament workflow.

    Args:
        max_rounds: Maximum number of debate iterations before forcing
            a final scoring round.

    Returns:
        A 6-phase WorkflowDefinition with iterative debate rounds.
    """
    return (
        WorkflowBuilder("debate_tournament")
        # Phase 1: Initial quality assessment
        .add_phase(
            "quality_prep",
            capability="argument_quality",
        )
        # Phase 2: Identify vulnerabilities
        .add_phase(
            "vulnerability_scan",
            capability="counter_argument_generation",
            depends_on=["quality_prep"],
        )
        # Phase 3: Iterative debate rounds
        .add_phase(
            "debate_rounds",
            capability="adversarial_debate",
            depends_on=["vulnerability_scan"],
            loop_config=LoopConfig(
                max_iterations=max_rounds,
                convergence_fn=_debate_score_converged,
            ),
        )
        # Phase 4: Final scoring after debate
        .add_phase(
            "final_scoring",
            capability="argument_quality",
            depends_on=["debate_rounds"],
        )
        # Phase 5: Jury vote
        .add_phase(
            "jury_vote",
            capability="governance_simulation",
            depends_on=["final_scoring"],
        )
        # Phase 6: Optional belief recording
        .add_phase(
            "belief_record",
            capability="belief_maintenance",
            optional=True,
            depends_on=["jury_vote"],
        )
        .set_metadata("domain", "adversarial_debate")
        .set_metadata("version", "1.0")
        .build()
    )


async def run_tournament(
    text: str,
    registry=None,
    max_rounds: int = DEFAULT_MAX_ROUNDS,
    create_state: bool = True,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the Debate Tournament pipeline.

    Args:
        text: Proposition or debate topic.
        registry: CapabilityRegistry to use (auto-created if None).
        max_rounds: Maximum debate iterations.
        create_state: Whether to create UnifiedAnalysisState.
        context: Additional context passed to phases.

    Returns:
        Dict with tournament results including debate rounds and final vote.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    workflow = build_debate_tournament_workflow(max_rounds)
    return await run_unified_analysis(
        text=text,
        workflow_name="debate_tournament",
        registry=registry,
        custom_workflow=workflow,
        context=context,
        create_state=create_state,
    )
