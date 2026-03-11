"""
Fact-Check Pipeline workflow: claim verification via belief maintenance.

A 6-phase pipeline for fact-checking textual claims:
1. transcription        — Speech-to-text (optional)
2. quality_assessment   — Evaluate argument quality and structure
3. fallacy_screen       — Detect fallacious reasoning (optional)
4. belief_tracking      — Track claims as JTMS beliefs
5. counter_check        — Generate counter-arguments to stress-test claims
6. indexing             — Index verified claims for future retrieval (optional)
"""

import logging
from typing import Any, Dict, Optional

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
)

logger = logging.getLogger("FactCheckPipeline")


def build_fact_check_workflow() -> WorkflowDefinition:
    """Build the Fact-Check Pipeline workflow.

    Returns:
        A 6-phase WorkflowDefinition for claim verification.
    """
    return (
        WorkflowBuilder("fact_check")
        # Phase 1: Optional transcription
        .add_phase(
            "transcription",
            capability="speech_transcription",
            optional=True,
        )
        # Phase 2: Quality assessment (required)
        .add_phase(
            "quality_assessment",
            capability="argument_quality",
        )
        # Phase 3: Optional fallacy screening
        .add_phase(
            "fallacy_screen",
            capability="neural_fallacy_detection",
            optional=True,
            depends_on=["quality_assessment"],
        )
        # Phase 4: Belief tracking via JTMS
        .add_phase(
            "belief_tracking",
            capability="belief_maintenance",
            depends_on=["quality_assessment"],
        )
        # Phase 5: Counter-argument stress test
        .add_phase(
            "counter_check",
            capability="counter_argument_generation",
            depends_on=["quality_assessment"],
        )
        # Phase 6: Optional semantic indexing
        .add_phase(
            "indexing",
            capability="semantic_indexing",
            optional=True,
            depends_on=["belief_tracking"],
        )
        .set_metadata("domain", "fact_checking")
        .set_metadata("version", "1.0")
        .build()
    )


async def run_fact_check(
    text: str,
    registry=None,
    create_state: bool = True,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Run the Fact-Check Pipeline.

    Args:
        text: Article or discourse to fact-check.
        registry: CapabilityRegistry to use (auto-created if None).
        create_state: Whether to create UnifiedAnalysisState.
        context: Additional context passed to phases.

    Returns:
        Dict with fact-check results including beliefs and counter-arguments.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    return await run_unified_analysis(
        text=text,
        workflow_name="fact_check",
        registry=registry,
        custom_workflow=build_fact_check_workflow(),
        context=context,
        create_state=create_state,
    )
