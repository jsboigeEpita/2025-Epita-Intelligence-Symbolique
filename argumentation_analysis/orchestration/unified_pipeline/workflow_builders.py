"""Workflow builder functions and main analysis entry point.

Pre-built workflow definitions (light, standard, full, custom) and
the run_unified_analysis() convenience function.
"""
import logging
from typing import Any, Dict, Optional

from argumentation_analysis.core.capability_registry import CapabilityRegistry
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseStatus,
    WorkflowBuilder,
    WorkflowDefinition,
    WorkflowExecutor,
)

from argumentation_analysis.orchestration.unified_pipeline._helpers import (
    _increment_fallacy_rerun,
    _should_rerun_fallacy,
    logger,
)
from argumentation_analysis.orchestration.unified_pipeline.registry_setup import setup_registry
from argumentation_analysis.orchestration.unified_pipeline.state_writers import (
    CAPABILITY_STATE_WRITERS,
)


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
    phases after extraction (#297). Downstream phases (quality, counter,
    JTMS) read fallacy results via context['phase_hierarchical_fallacy_output'].
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
    """Full pipeline traversing all 12 capabilities with LLM extraction."""
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

    def quality_gate(ctx):
        """Only generate counter-argument if quality score > 3.0."""
        output = ctx.get("phase_quality_output")
        if not output or not isinstance(output, dict):
            return True  # proceed if no quality data
        return output.get("note_finale", 0) > 3.0

    def counter_quality_convergence(prev, curr):
        """Converge when counter-argument quality stops improving."""
        if not isinstance(prev, dict) or not isinstance(curr, dict):
            return False
        prev_score = prev.get("note_finale", 0)
        curr_score = curr.get("note_finale", 0)
        return curr_score >= prev_score  # stop when no improvement

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
    """JTMS-Dung belief retraction/extension recalc loop (Loop 2). STUB."""
    return (
        WorkflowBuilder("jtms_dung_loop")
        .add_phase(
            "jtms_beliefs",
            capability="belief_maintenance",
            optional=True,
        )
        .add_phase(
            "dung_extensions",
            capability="ranking_semantics",
            depends_on=["jtms_beliefs"],
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
        }
        # Collaborative multi-agent debate (#175)
        try:
            from argumentation_analysis.orchestration.collaborative_debate import (
                build_collaborative_analysis_workflow,
            )

            WORKFLOW_CATALOG["collaborative"] = build_collaborative_analysis_workflow()
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


async def run_unified_analysis(
    text: str,
    workflow_name: str = "standard",
    registry: Optional[CapabilityRegistry] = None,
    custom_workflow: Optional[WorkflowDefinition] = None,
    context: Optional[Dict[str, Any]] = None,
    state: Optional[Any] = None,
    create_state: bool = True,
) -> Dict[str, Any]:
    """
    Run a unified analysis pipeline on input text.

    Args:
        text: The text to analyze.
        workflow_name: Name of pre-built workflow ("light", "standard", "full").
        registry: CapabilityRegistry to use. If None, creates one via setup_registry().
        custom_workflow: If provided, use this workflow instead of a named one.
        context: Additional context passed to each phase (e.g. kernel, config).
        state: Optional UnifiedAnalysisState instance. If provided, phase results
               are written to it via state writers.
        create_state: If True and no state provided, automatically create an
                      UnifiedAnalysisState. Set to False to disable state tracking.

    Returns:
        Dict with keys:
            - workflow_name: Name of the executed workflow
            - phases: Dict[str, PhaseResult] — per-phase results
            - summary: Dict with completed/failed/skipped counts
            - capabilities_used: List of capabilities that were successfully resolved
            - capabilities_missing: List of capabilities with no provider
            - unified_state: UnifiedAnalysisState (if state tracking enabled)
            - state_snapshot: Dict snapshot of the state (if state tracking enabled)
    """
    if registry is None:
        registry = setup_registry()

    # Create or use provided state
    if state is None and create_state:
        try:
            from argumentation_analysis.core.shared_state import UnifiedAnalysisState

            state = UnifiedAnalysisState(text)
        except ImportError:
            logger.warning(
                "Could not import UnifiedAnalysisState; state tracking disabled"
            )
            state = None

    if custom_workflow is not None:
        workflow = custom_workflow
    elif workflow_name == "auto":
        try:
            from argumentation_analysis.orchestration.router import TextAnalysisRouter

            router = TextAnalysisRouter(registry=registry)
            workflow = await router.analyze_and_route_async(text, registry=registry)
        except Exception as e:
            logger.warning("Auto-routing failed, falling back to standard: %s", e)
            catalog = get_workflow_catalog()
            workflow = catalog["standard"]
    elif workflow_name == "conversational":
        # Special mode: use ConversationalOrchestrator (#208-L)
        try:
            from argumentation_analysis.orchestration.conversational_orchestrator import (
                run_conversational_analysis,
            )

            conv_result = await run_conversational_analysis(text)

            # Normalize result format for benchmark compatibility (#208-L)
            # Conversational returns {phases: [names], conversation_log, total_messages}
            # Benchmark expects {phases: {dict}, summary: {completed, total, ...}}
            phase_names = conv_result.get("phases", [])
            total_msgs = conv_result.get("total_messages", 0)
            conv_result["summary"] = {
                "completed": len(phase_names),
                "failed": 0,
                "skipped": 0,
                "total": len(phase_names),
                "total_messages": total_msgs,
            }
            conv_result["workflow_name"] = "conversational"
            return conv_result
        except Exception as e:
            logger.warning(
                f"Conversational mode failed ({e}), falling back to standard"
            )
            catalog = get_workflow_catalog()
            workflow = catalog["standard"]
    else:
        catalog = get_workflow_catalog()
        if workflow_name not in catalog:
            raise ValueError(
                f"Unknown workflow '{workflow_name}'. "
                f"Available: {list(catalog.keys()) + ['conversational']}"
            )
        workflow = catalog[workflow_name]

    executor = WorkflowExecutor(registry)
    phase_results = await executor.execute(
        workflow,
        input_data=text,
        context=context,
        state=state,
        state_writers=CAPABILITY_STATE_WRITERS if state is not None else None,
    )

    # Build summary
    completed = [
        name for name, r in phase_results.items() if r.status == PhaseStatus.COMPLETED
    ]
    failed = [
        name for name, r in phase_results.items() if r.status == PhaseStatus.FAILED
    ]
    skipped_phases = [
        name for name, r in phase_results.items() if r.status == PhaseStatus.SKIPPED
    ]

    capabilities_used = [
        r.capability
        for r in phase_results.values()
        if r.status == PhaseStatus.COMPLETED
    ]
    capabilities_missing = [
        r.capability
        for r in phase_results.values()
        if r.status in (PhaseStatus.FAILED, PhaseStatus.SKIPPED)
    ]

    result = {
        "workflow_name": workflow.name,
        "phases": phase_results,
        "summary": {
            "completed": len(completed),
            "failed": len(failed),
            "skipped": len(skipped_phases),
            "total": len(phase_results),
            "completed_phases": completed,
            "failed_phases": failed,
            "skipped_phases": skipped_phases,
        },
        "capabilities_used": capabilities_used,
        "capabilities_missing": capabilities_missing,
    }

    # Include state in results if available
    if state is not None:
        result["unified_state"] = state
        try:
            result["state_snapshot"] = state.get_state_snapshot(summarize=True)
        except Exception:
            result["state_snapshot"] = None

    return result
