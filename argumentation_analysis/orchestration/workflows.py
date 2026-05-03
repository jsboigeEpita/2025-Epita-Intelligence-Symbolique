"""Pre-built workflow definitions for the unified pipeline.

Provides build_*_workflow() functions and the workflow catalog.

Split from unified_pipeline.py (#310).
"""

import logging
from typing import Dict, Any

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
)

try:
    from argumentation_analysis.orchestration.sherlock_modern_orchestrator import (
        build_sherlock_modern_workflow,
    )
except ImportError:
    build_sherlock_modern_workflow = None  # type: ignore[assignment]

logger = logging.getLogger("UnifiedPipeline")

__all__ = [
    "build_light_workflow",
    "build_standard_workflow",
    "build_full_workflow",
    "_should_rerun_fallacy",
    "_increment_fallacy_rerun",
    "build_iterative_analysis_workflow",
    "build_nl_to_logic_workflow",
    "build_quality_gated_counter_workflow",
    "build_debate_governance_loop_workflow",
    "build_jtms_dung_loop_workflow",
    "build_neural_symbolic_fallacy_workflow",
    "build_hierarchical_fallacy_workflow",
    "build_spectacular_workflow",
    "build_sherlock_modern_workflow",
    "WORKFLOW_CATALOG",
    "get_workflow_catalog",
    "reset_workflow_catalog",
]

# --- Pre-built workflow definitions ---


def build_light_workflow() -> WorkflowDefinition:
    """Minimal 3-phase analysis workflow with fact extraction."""
    return (
        WorkflowBuilder("light_analysis")
        .add_phase("extract", capability="fact_extraction")
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        .build()
    )


def build_standard_workflow() -> WorkflowDefinition:
    """Standard workflow with fact extraction, fallacy detection, and quality-gated counter-arguments.

    Self-hosted LLM (Tier 2) and hierarchical fallacy detection run as optional
    phases after extraction (#297). Dung/ASPIC analysis builds attack graphs
    from detected fallacies for abstract argumentation (#286).
    """
    return (
        WorkflowBuilder("standard_analysis")
        .add_phase("extract", capability="fact_extraction")
        .add_phase(
            "neural_detect",
            capability="neural_fallacy_detection",
            depends_on=["extract"],
            optional=True,
        )
        .add_phase(
            "hierarchical_fallacy",
            capability="hierarchical_fallacy_detection",
            depends_on=["extract"],
            optional=True,
        )
        .add_phase(
            "nl_to_logic",
            capability="nl_to_logic_translation",
            depends_on=["extract"],
            optional=True,
        )
        .add_phase(
            "pl",
            capability="propositional_logic",
            depends_on=["nl_to_logic"],
            optional=True,
        )
        .add_phase(
            "fol",
            capability="fol_reasoning",
            depends_on=["nl_to_logic"],
            optional=True,
        )
        .add_phase(
            "dung_extensions",
            capability="dung_extensions",
            depends_on=["hierarchical_fallacy", "pl"],
            optional=True,
        )
        .add_phase(
            "aspic_analysis",
            capability="aspic_plus_reasoning",
            depends_on=["dung_extensions"],
            optional=True,
        )
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        .add_phase(
            "jtms",
            capability="belief_maintenance",
            depends_on=["counter"],
            optional=True,
        )
        .add_phase(
            "governance",
            capability="governance_simulation",
            depends_on=["quality"],
            optional=True,
        )
        .add_phase(
            "debate",
            capability="adversarial_debate",
            depends_on=["counter"],
            optional=True,
        )
        .build()
    )


def build_full_workflow() -> WorkflowDefinition:
    """Full pipeline traversing all 12 capabilities with LLM extraction.

    Includes Dung/ASPIC abstract argumentation phases that build attack
    graphs from detected fallacies (#286).
    """
    return (
        WorkflowBuilder("full_analysis")
        .add_phase(
            "transcribe",
            capability="speech_transcription",
            optional=True,
        )
        .add_phase("extract", capability="fact_extraction")
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
        .add_phase(
            "neural_fallacy",
            capability="neural_fallacy_detection",
            depends_on=["extract"],
            optional=True,
        )
        .add_phase(
            "hierarchical_fallacy",
            capability="hierarchical_fallacy_detection",
            depends_on=["extract"],
            optional=True,
        )
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        .add_phase(
            "jtms",
            capability="belief_maintenance",
            depends_on=["counter"],
            optional=True,
        )
        .add_phase(
            "governance",
            capability="governance_simulation",
            depends_on=["quality"],
            optional=True,
        )
        .add_phase(
            "debate",
            capability="adversarial_debate",
            depends_on=["counter"],
            optional=True,
        )
        .add_phase(
            "index",
            capability="semantic_indexing",
            depends_on=["counter"],
            optional=True,
        )
        .add_phase(
            "nl_to_logic",
            capability="nl_to_logic_translation",
            depends_on=["extract"],
            optional=True,
        )
        .add_phase(
            "pl",
            capability="propositional_logic",
            depends_on=["nl_to_logic"],
            optional=True,
        )
        .add_phase(
            "fol",
            capability="fol_reasoning",
            depends_on=["nl_to_logic"],
            optional=True,
        )
        .add_phase(
            "dung_extensions",
            capability="dung_extensions",
            depends_on=["hierarchical_fallacy", "pl"],
            optional=True,
        )
        .add_phase(
            "aspic_analysis",
            capability="aspic_plus_reasoning",
            depends_on=["dung_extensions"],
            optional=True,
        )
        .build()
    )


def _should_rerun_fallacy(context: Dict[str, Any]) -> bool:
    """Check whether the fallacy detection phase should be re-run after JTMS.

    Returns True when JTMS retracted beliefs AND we haven't exceeded the
    maximum number of fallacy reruns (2). This prevents infinite loops while
    allowing iterative enrichment when formal analysis invalidates beliefs.

    Args:
        context: Workflow execution context containing phase outputs.

    Returns:
        True if a fallacy re-run is warranted.
    """
    # Check rerun count limit
    rerun_count = context.get("_fallacy_rerun_count", 0)
    if rerun_count >= 2:
        return False

    # Check if JTMS phase produced retracted beliefs
    jtms_output = context.get("phase_jtms_output", {})
    if not isinstance(jtms_output, dict):
        return False

    # Method 1: explicit undermined_count field
    undermined = jtms_output.get("undermined_count", 0)
    if undermined > 0:
        return True

    # Method 2: scan beliefs dict for invalid entries
    beliefs = jtms_output.get("beliefs", {})
    if isinstance(beliefs, dict):
        retracted = [name for name, bdata in beliefs.items()
                     if isinstance(bdata, dict) and bdata.get("valid") is False]
        if retracted:
            return True

    return False


def _increment_fallacy_rerun(context: Dict[str, Any]) -> None:
    """Increment the fallacy rerun counter in context."""
    context["_fallacy_rerun_count"] = context.get("_fallacy_rerun_count", 0) + 1


def build_iterative_analysis_workflow() -> WorkflowDefinition:
    """Iterative workflow with JTMS-driven fallacy re-analysis (#305).

    Runs the standard pipeline phases, then conditionally re-runs
    hierarchical_fallacy after JTMS if beliefs were retracted. This
    implements the PM re-prompting mechanism for the sequential pipeline:
    formal analysis findings feed back into informal analysis.

    Flow:
        extract → hierarchical_fallacy → quality → counter → jtms
        → [if retractions] fallacy_reanalysis → governance → debate
    """

    def _fallacy_rerun_condition(ctx: Dict[str, Any]) -> bool:
        """Condition for the fallacy re-analysis phase."""
        should_rerun = _should_rerun_fallacy(ctx)
        if should_rerun:
            _increment_fallacy_rerun(ctx)
            logger.info(
                "Iterative workflow: JTMS retracted beliefs detected, "
                "re-running fallacy detection (rerun #%d)",
                ctx.get("_fallacy_rerun_count", 1),
            )
        return should_rerun

    return (
        WorkflowBuilder("iterative_analysis")
        # Phase 1: extraction
        .add_phase("extract", capability="fact_extraction")
        # Phase 2: initial fallacy detection
        .add_phase(
            "hierarchical_fallacy",
            capability="hierarchical_fallacy_detection",
            depends_on=["extract"],
            optional=True,
        )
        # Phase 3: quality evaluation
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
        # Phase 4: counter-argument generation
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        # Phase 5: JTMS belief maintenance
        .add_phase(
            "jtms",
            capability="belief_maintenance",
            depends_on=["counter"],
            optional=True,
        )
        # Phase 6: CONDITIONAL fallacy re-analysis after JTMS
        .add_conditional_phase(
            "fallacy_reanalysis",
            capability="hierarchical_fallacy_detection",
            condition=_fallacy_rerun_condition,
            depends_on=["jtms"],
            optional=True,
        )
        # Phase 7: governance (depends on quality + optional reanalysis)
        .add_phase(
            "governance",
            capability="governance_simulation",
            depends_on=["quality"],
            optional=True,
        )
        # Phase 8: debate
        .add_phase(
            "debate",
            capability="adversarial_debate",
            depends_on=["counter"],
            optional=True,
        )
        .build()
    )


def build_nl_to_logic_workflow() -> WorkflowDefinition:
    """NL-to-formal-logic pipeline: extract → translate → validate → reason (#173).

    Bridges informal NL analysis and formal reasoning by translating
    extracted arguments into propositional/FOL formulas with Tweety validation.
    """
    return (
        WorkflowBuilder("nl_to_logic_analysis")
        .add_phase("extract", capability="fact_extraction")
        .add_phase(
            "nl_to_logic",
            capability="nl_to_logic_translation",
            depends_on=["extract"],
        )
        .add_phase(
            "pl",
            capability="propositional_logic",
            depends_on=["nl_to_logic"],
            optional=True,
        )
        .add_phase(
            "fol",
            capability="fol_reasoning",
            depends_on=["nl_to_logic"],
            optional=True,
        )
        .build()
    )


def build_quality_gated_counter_workflow() -> WorkflowDefinition:
    """Quality-gated counter-argument with iterative refinement (Loop 3)."""

    def quality_gate(ctx: Dict[str, Any]) -> bool:
        """Only generate counter-argument if quality score > 3.0."""
        output = ctx.get("phase_quality_output")
        if not output or not isinstance(output, dict):
            return True  # proceed if no quality data
        return bool(output.get("note_finale", 0) > 3.0)

    def counter_quality_convergence(prev: Any, curr: Any) -> bool:
        """Converge when counter-argument quality stops improving."""
        if not isinstance(prev, dict) or not isinstance(curr, dict):
            return False
        prev_score = prev.get("note_finale", 0)
        curr_score = curr.get("note_finale", 0)
        return bool(curr_score >= prev_score)  # stop when no improvement

    return (
        WorkflowBuilder("quality_gated_counter")
        .add_phase("extract", capability="fact_extraction")
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
        .add_conditional_phase(
            "counter",
            capability="counter_argument_generation",
            condition=quality_gate,
            depends_on=["quality"],
        )
        .add_loop(
            "quality_recheck",
            capability="argument_quality",
            max_iterations=3,
            convergence_fn=counter_quality_convergence,
            depends_on=["counter"],
            input_transform=lambda inp, ctx: str(
                ctx.get("phase_counter_output", {})
                .get("suggested_strategy", {})
                .get("strategy_name", inp)
            ),
        )
        .build()
    )


def build_debate_governance_loop_workflow() -> WorkflowDefinition:
    """Debate-Governance vote-contest-debate-revote loop (Loop 1). STUB."""
    return (
        WorkflowBuilder("debate_governance_loop")
        .add_phase(
            "governance_vote",
            capability="governance_simulation",
            optional=True,
        )
        .add_phase(
            "debate",
            capability="adversarial_debate",
            depends_on=["governance_vote"],
            optional=True,
        )
        .add_phase(
            "governance_revote",
            capability="governance_simulation",
            depends_on=["debate"],
            optional=True,
        )
        .build()
    )


def build_jtms_dung_loop_workflow() -> WorkflowDefinition:
    """JTMS-Dung belief retraction/extension recalc loop (Loop 2).

    Builds attack graph from arguments and detected fallacies, computes
    Dung extensions (grounded, preferred, stable), then feeds results
    back into JTMS for belief revision.
    """
    return (
        WorkflowBuilder("jtms_dung_loop")
        .add_phase(
            "jtms_beliefs",
            capability="belief_maintenance",
            optional=True,
        )
        .add_phase(
            "dung_extensions",
            capability="dung_extensions",
            depends_on=["jtms_beliefs"],
            optional=True,
        )
        .add_phase(
            "aspic_analysis",
            capability="aspic_plus_reasoning",
            depends_on=["dung_extensions"],
            optional=True,
        )
        .build()
    )


def build_neural_symbolic_fallacy_workflow() -> WorkflowDefinition:
    """Neural-Symbolic-Hierarchical fallacy fusion (Loop 4).

    Three complementary fallacy detection approaches:
    - Neural: Self-hosted LLM with function calling (#297, replaces CamemBERT)
    - Hierarchical: Taxonomy-guided iterative deepening (precise, explainable)
    - Quality baseline: argument quality evaluation for context
    """
    return (
        WorkflowBuilder("neural_symbolic_fallacy")
        .add_phase(
            "neural_detect",
            capability="neural_fallacy_detection",
            optional=True,
        )
        .add_phase(
            "hierarchical_detect",
            capability="hierarchical_fallacy_detection",
            optional=True,
        )
        .add_phase("quality_baseline", capability="argument_quality")
        .build()
    )


def build_hierarchical_fallacy_workflow() -> WorkflowDefinition:
    """Hierarchical taxonomy-guided fallacy detection workflow (#84).

    Dedicated workflow for the master-slave iterative deepening approach:
    1. Extract facts/arguments (provides context for fallacy detection)
    2. Hierarchical fallacy detection via taxonomy navigation
    3. Quality evaluation for cross-validation
    """
    return (
        WorkflowBuilder("hierarchical_fallacy")
        .add_phase("extract", capability="fact_extraction")
        .add_phase(
            "hierarchical_fallacy",
            capability="hierarchical_fallacy_detection",
            depends_on=["extract"],
        )
        .add_phase(
            "quality",
            capability="argument_quality",
            depends_on=["extract"],
            optional=True,
        )
        .build()
    )


def build_spectacular_workflow() -> WorkflowDefinition:
    """Full-chain spectacular analysis composing every available capability.

    Designed to maximise UnifiedAnalysisState field coverage (target ≥28/32).
    Phases are arranged in a DAG so formal logic, fallacy detection, and
    quality evaluation run in parallel after extraction; downstream phases
    (Dung, ASPIC, JTMS, ATMS, debate, governance, synthesis) aggregate
    results from earlier stages.

    DAG levels (approximate):
        L0  extract
        L1  quality | nl_to_logic | neural_detect | hierarchical_fallacy
        L2  pl | fol | modal                     (from nl_to_logic)
        L3  dung_extensions                       (from fallacy + pl)
        L4  aspic_analysis                        (from dung)
        L5  counter                               (from quality)
        L6  jtms | debate                         (from counter)
        L7  atms                                  (from jtms)
        L8  governance | formal_synthesis         (aggregation)
    """
    return (
        WorkflowBuilder("spectacular_analysis")
        # L0 — extraction
        .add_phase("extract", capability="fact_extraction")
        # L1 — parallel after extraction
        .add_phase("quality", capability="argument_quality", depends_on=["extract"])
        .add_phase(
            "nl_to_logic",
            capability="nl_to_logic_translation",
            depends_on=["extract"],
            optional=True,
        )
        .add_phase(
            "neural_detect",
            capability="neural_fallacy_detection",
            depends_on=["extract"],
            optional=True,
        )
        .add_phase(
            "hierarchical_fallacy",
            capability="hierarchical_fallacy_detection",
            depends_on=["extract"],
            optional=True,
        )
        # L2 — formal logic (parallel, from nl_to_logic)
        .add_phase(
            "pl",
            capability="propositional_logic",
            depends_on=["nl_to_logic"],
            optional=True,
        )
        .add_phase(
            "fol",
            capability="fol_reasoning",
            depends_on=["nl_to_logic"],
            optional=True,
        )
        .add_phase(
            "modal",
            capability="modal_logic",
            depends_on=["nl_to_logic"],
            optional=True,
        )
        # L3 — Dung extensions (from fallacy + PL results)
        .add_phase(
            "dung_extensions",
            capability="dung_extensions",
            depends_on=["hierarchical_fallacy", "pl"],
            optional=True,
        )
        # L4 — ASPIC+ structured argumentation
        .add_phase(
            "aspic_analysis",
            capability="aspic_plus_reasoning",
            depends_on=["dung_extensions"],
            optional=True,
        )
        # L5 — counter-argument generation
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        # L6 — JTMS belief tracking + adversarial debate (parallel)
        .add_phase(
            "jtms",
            capability="belief_maintenance",
            depends_on=["counter"],
            optional=True,
        )
        .add_phase(
            "debate",
            capability="adversarial_debate",
            depends_on=["counter"],
            optional=True,
        )
        # L7 — ATMS multi-context (from JTMS beliefs)
        .add_phase(
            "atms",
            capability="assumption_based_reasoning",
            depends_on=["jtms"],
            optional=True,
        )
        # L8 — governance + formal synthesis (terminal aggregation)
        .add_phase(
            "governance",
            capability="governance_simulation",
            depends_on=["quality"],
            optional=True,
        )
        .add_phase(
            "formal_synthesis",
            capability="formal_synthesis",
            depends_on=["fol", "modal", "aspic_analysis"],
            optional=True,
        )
        .add_phase(
            "narrative_synthesis",
            capability="narrative_synthesis",
            depends_on=["quality", "jtms", "atms", "dung_extensions"],
            optional=True,
        )
        .build()
    )


WORKFLOW_CATALOG: Dict[str, WorkflowDefinition] = {}


def get_workflow_catalog() -> Dict[str, WorkflowDefinition]:
    """Get the catalog of pre-built workflows (lazy-initialized)."""
    global WORKFLOW_CATALOG
    if not WORKFLOW_CATALOG:
        WORKFLOW_CATALOG = {
            "light": build_light_workflow(),
            "standard": build_standard_workflow(),
            "full": build_full_workflow(),
            "iterative": build_iterative_analysis_workflow(),
            "quality_gated": build_quality_gated_counter_workflow(),
            "debate_governance": build_debate_governance_loop_workflow(),
            "jtms_dung": build_jtms_dung_loop_workflow(),
            "neural_symbolic": build_neural_symbolic_fallacy_workflow(),
            "hierarchical_fallacy": build_hierarchical_fallacy_workflow(),
            "nl_to_logic": build_nl_to_logic_workflow(),
            "spectacular": build_spectacular_workflow(),
        }
        # Collaborative multi-agent debate (#175)
        try:
            from argumentation_analysis.orchestration.collaborative_debate import (
                build_collaborative_analysis_workflow,
            )

            WORKFLOW_CATALOG["collaborative"] = build_collaborative_analysis_workflow()  # type: ignore[no-untyped-call]
        except Exception as e:
            logger.warning(f"Collaborative workflow not registered: {e}")
        # Macro workflows (Track D)
        try:
            from argumentation_analysis.workflows.democratech import (
                build_democratech_workflow,
            )
            from argumentation_analysis.workflows.debate_tournament import (
                build_debate_tournament_workflow,
            )
            from argumentation_analysis.workflows.fact_check_pipeline import (
                build_fact_check_workflow,
            )

            WORKFLOW_CATALOG["democratech"] = build_democratech_workflow()
            WORKFLOW_CATALOG["debate_tournament"] = build_debate_tournament_workflow()
            WORKFLOW_CATALOG["fact_check"] = build_fact_check_workflow()
        except Exception as e:
            logger.warning(f"Macro workflows not registered: {e}")
        # Formal workflows (Track A plugins + orchestration)
        try:
            from argumentation_analysis.workflows.formal_debate import (
                build_formal_debate_workflow,
            )
            from argumentation_analysis.workflows.belief_dynamics import (
                build_belief_dynamics_workflow,
            )
            from argumentation_analysis.workflows.argument_strength import (
                build_argument_strength_workflow,
            )

            WORKFLOW_CATALOG["formal_debate"] = build_formal_debate_workflow()
            WORKFLOW_CATALOG["belief_dynamics"] = build_belief_dynamics_workflow()
            WORKFLOW_CATALOG["argument_strength"] = build_argument_strength_workflow()
        except Exception as e:
            logger.warning(f"Formal workflows not registered: {e}")
        # Formal verification pipeline (#71)
        try:
            from argumentation_analysis.workflows.formal_verification import (
                build_formal_verification_workflow,
            )

            WORKFLOW_CATALOG[
                "formal_verification"
            ] = build_formal_verification_workflow()
        except Exception as e:
            logger.warning(f"Formal verification workflow not registered: {e}")
        # Comprehensive analysis (LLM-only, benchmark-optimized)
        try:
            from argumentation_analysis.workflows.comprehensive_analysis import (
                build_comprehensive_analysis_workflow,
            )

            WORKFLOW_CATALOG["comprehensive"] = build_comprehensive_analysis_workflow()
        except Exception as e:
            logger.warning(f"Comprehensive workflow not registered: {e}")
        # Sherlock Modern investigation (#357)
        try:
            from argumentation_analysis.orchestration.sherlock_modern_orchestrator import (
                build_sherlock_modern_workflow,
            )

            wf = build_sherlock_modern_workflow()  # type: ignore[no-untyped-call]
            if wf is not None:  # builder returns None on failure (review #382)
                WORKFLOW_CATALOG["sherlock_modern"] = wf
            else:
                logger.warning("Sherlock modern workflow builder returned None")
        except Exception as e:
            logger.warning(f"Sherlock modern workflow not registered: {e}")
    return WORKFLOW_CATALOG


def reset_workflow_catalog() -> None:
    """
    Reset the global workflow catalog to an empty state.

    This is primarily useful for testing to ensure that tests don't pollute
    each other's state through the global WORKFLOW_CATALOG variable.

    After calling this function, the next call to get_workflow_catalog() will
    re-initialize the catalog with all available workflows.
    """
    global WORKFLOW_CATALOG
    WORKFLOW_CATALOG = {}
    logger.debug("Workflow catalog reset to empty state")


