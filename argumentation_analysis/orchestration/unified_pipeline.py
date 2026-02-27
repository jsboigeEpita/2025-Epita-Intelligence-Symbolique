"""
Unified pipeline wiring all integrated student components via CapabilityRegistry.

Provides:
- setup_registry(): register all available components (agents, services, adapters)
- Pre-built workflow definitions (light, standard, full, custom)
- run_unified_analysis(): convenience function for end-to-end analysis

This module ties together the Lego architecture built in Phases 0-4:
- CapabilityRegistry (core/capability_registry.py)
- WorkflowDSL (orchestration/workflow_dsl.py)
- All integrated student project components
"""

import logging
from typing import Dict, Any, Optional, List

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ServiceDiscovery,
    ComponentType,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
    WorkflowExecutor,
    PhaseResult,
    PhaseStatus,
)

logger = logging.getLogger("UnifiedPipeline")


def setup_registry(
    include_optional: bool = True,
) -> CapabilityRegistry:
    """
    Create and populate a CapabilityRegistry with all available components.

    Registers agents, services, and adapters from the integrated student projects.
    Each registration is wrapped in try/except so missing optional dependencies
    don't prevent the registry from being created.

    Args:
        include_optional: If True, attempt to register components with optional
                         dependencies (CamemBERT, Dung/JVM, speech-to-text).

    Returns:
        Populated CapabilityRegistry instance.
    """
    registry = CapabilityRegistry()
    registered = []
    skipped = []

    # --- Core agents (always available) ---

    # Counter-argument generation (2.3.3)
    try:
        from argumentation_analysis.agents.core.counter_argument import (
            register_with_capability_registry as register_counter_arg,
        )

        register_counter_arg(registry)
        registered.append("counter_argument_agent")
    except ImportError as e:
        skipped.append(("counter_argument_agent", str(e)))

    # Argument quality evaluation (2.3.5)
    try:
        from argumentation_analysis.agents.core.quality.quality_evaluator import (
            ArgumentQualityEvaluator,
        )

        registry.register_agent(
            name="quality_evaluator",
            agent_class=ArgumentQualityEvaluator,
            capabilities=[
                "argument_quality",
                "virtue_detection",
                "quality_scoring",
            ],
            metadata={"description": "9-virtue argument quality evaluator"},
        )
        registered.append("quality_evaluator")
    except ImportError as e:
        skipped.append(("quality_evaluator", str(e)))

    # Debate agent (1.2.7)
    try:
        from argumentation_analysis.agents.core.debate.debate_agent import (
            DebateAgent,
        )

        registry.register_agent(
            name="debate_agent",
            agent_class=DebateAgent,
            capabilities=[
                "adversarial_debate",
                "argument_stress_test",
                "debate_scoring",
            ],
            metadata={"description": "Multi-personality adversarial debate agent"},
        )
        registered.append("debate_agent")
    except ImportError as e:
        skipped.append(("debate_agent", str(e)))

    # Governance agent (2.1.6)
    try:
        from argumentation_analysis.agents.core.governance.governance_agent import (
            GovernanceAgent,
        )

        registry.register_agent(
            name="governance_agent",
            agent_class=GovernanceAgent,
            capabilities=[
                "governance_simulation",
                "multi_method_voting",
                "preference_aggregation",
            ],
            metadata={"description": "7-method governance voting agent"},
        )
        registered.append("governance_agent")
    except ImportError as e:
        skipped.append(("governance_agent", str(e)))

    # --- Core services ---

    # JTMS belief maintenance (1.4.1)
    try:
        from argumentation_analysis.services.jtms.jtms_core import JTMS

        registry.register_service(
            name="jtms_service",
            service_class=JTMS,
            capabilities=["belief_maintenance", "truth_maintenance", "jtms_reasoning"],
            metadata={"description": "Justification-based Truth Maintenance System"},
        )
        registered.append("jtms_service")
    except ImportError as e:
        skipped.append(("jtms_service", str(e)))

    # Local LLM service (2.3.6)
    try:
        from argumentation_analysis.services.local_llm_service import (
            LocalLLMService,
        )

        registry.register_service(
            name="local_llm_service",
            service_class=LocalLLMService,
            capabilities=["local_llm", "chat_completion"],
            metadata={"description": "OpenAI-compatible local LLM adapter"},
        )
        registered.append("local_llm_service")
    except ImportError as e:
        skipped.append(("local_llm_service", str(e)))

    # --- Optional adapters (may need heavy dependencies) ---

    if include_optional:
        # CamemBERT fallacy detector (2.3.2)
        try:
            from argumentation_analysis.adapters.camembert_fallacy import (
                CamembertFallacyAdapter,
            )

            registry.register_agent(
                name="camembert_fallacy_detector",
                agent_class=CamembertFallacyAdapter,
                capabilities=["neural_fallacy_detection", "fallacy_detection"],
                requires=["camembert_model"],
                metadata={
                    "description": "CamemBERT-based neural fallacy detector (2.3.2)"
                },
            )
            registered.append("camembert_fallacy_detector")
        except ImportError as e:
            skipped.append(("camembert_fallacy_detector", str(e)))

        # Semantic index service (Arg_Semantic_Index)
        try:
            from argumentation_analysis.services.semantic_index_service import (
                SemanticIndexService,
            )

            registry.register_service(
                name="semantic_index_service",
                service_class=SemanticIndexService,
                capabilities=["semantic_indexing", "argument_search"],
                metadata={"description": "Semantic argument indexing service"},
            )
            registered.append("semantic_index_service")
        except ImportError as e:
            skipped.append(("semantic_index_service", str(e)))

        # Speech transcription service (speech-to-text)
        try:
            from argumentation_analysis.services.speech_transcription import (
                SpeechTranscriptionService,
            )

            registry.register_service(
                name="speech_transcription_service",
                service_class=SpeechTranscriptionService,
                capabilities=["speech_transcription", "speech_to_text"],
                metadata={"description": "Whisper-based speech transcription service"},
            )
            registered.append("speech_transcription_service")
        except ImportError as e:
            skipped.append(("speech_transcription_service", str(e)))

    # --- Declare unfilled slots for future Tweety extensions ---
    _declare_tweety_slots(registry)

    logger.info(
        f"Registry setup complete: {len(registered)} registered, "
        f"{len(skipped)} skipped"
    )
    if skipped:
        logger.debug(f"Skipped components: {[s[0] for s in skipped]}")

    return registry


def _declare_tweety_slots(registry: CapabilityRegistry) -> None:
    """Declare Tweety module capability slots for future extensions."""
    tweety_slots = [
        ("aspic_plus_reasoning", "ASPIC+ structured argumentation"),
        ("aba_reasoning", "Assumption-Based Argumentation"),
        ("adf_reasoning", "Abstract Dialectical Frameworks"),
        ("bipolar_argumentation", "Bipolar argumentation (support + attack)"),
        ("ranking_semantics", "Qualitative argument ranking (Categoriser, Burden)"),
        ("probabilistic_argumentation", "Probabilistic argument acceptance"),
        ("dialogue_protocols", "Agent dialogue and negotiation protocols"),
        ("belief_revision", "Belief dynamics and revision operators"),
    ]
    for slot_name, description in tweety_slots:
        registry.declare_slot(slot_name, requires=["jvm"], description=description)


# --- Pre-built workflow definitions ---


def build_light_workflow() -> WorkflowDefinition:
    """Minimal 3-phase analysis workflow."""
    return (
        WorkflowBuilder("light_analysis")
        .add_phase("quality", capability="argument_quality")
        .add_phase(
            "counter",
            capability="counter_argument_generation",
            depends_on=["quality"],
        )
        .add_phase("jtms", capability="belief_maintenance", optional=True)
        .build()
    )


def build_standard_workflow() -> WorkflowDefinition:
    """Standard 5-phase workflow with quality-gated counter-arguments."""
    return (
        WorkflowBuilder("standard_analysis")
        .add_phase("quality", capability="argument_quality")
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
    """Full pipeline traversing all 12 capabilities."""
    return (
        WorkflowBuilder("full_analysis")
        .add_phase(
            "transcribe",
            capability="speech_transcription",
            optional=True,
        )
        .add_phase("quality", capability="argument_quality")
        .add_phase(
            "neural_fallacy",
            capability="neural_fallacy_detection",
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
        }
    return WORKFLOW_CATALOG


async def run_unified_analysis(
    text: str,
    workflow_name: str = "standard",
    registry: Optional[CapabilityRegistry] = None,
    custom_workflow: Optional[WorkflowDefinition] = None,
) -> Dict[str, Any]:
    """
    Run a unified analysis pipeline on input text.

    Args:
        text: The text to analyze.
        workflow_name: Name of pre-built workflow ("light", "standard", "full").
        registry: CapabilityRegistry to use. If None, creates one via setup_registry().
        custom_workflow: If provided, use this workflow instead of a named one.

    Returns:
        Dict with keys:
            - workflow_name: Name of the executed workflow
            - phases: Dict[str, PhaseResult] — per-phase results
            - summary: Dict with completed/failed/skipped counts
            - capabilities_used: List of capabilities that were successfully resolved
            - capabilities_missing: List of capabilities with no provider
    """
    if registry is None:
        registry = setup_registry()

    if custom_workflow is not None:
        workflow = custom_workflow
    else:
        catalog = get_workflow_catalog()
        if workflow_name not in catalog:
            raise ValueError(
                f"Unknown workflow '{workflow_name}'. "
                f"Available: {list(catalog.keys())}"
            )
        workflow = catalog[workflow_name]

    executor = WorkflowExecutor(registry)
    phase_results = await executor.execute(workflow, input_data=text)

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

    return {
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
