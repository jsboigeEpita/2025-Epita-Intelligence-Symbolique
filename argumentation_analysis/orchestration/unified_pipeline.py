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

import asyncio
import json
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


# --- Invoke callables for registered components ---
# Each callable: async (input_text: str, context: Dict[str, Any]) -> Any


async def _invoke_quality_evaluator(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke 9-virtue argument quality evaluator (sync, no dependencies)."""
    from argumentation_analysis.agents.core.quality.quality_evaluator import (
        ArgumentQualityEvaluator,
    )

    evaluator = ArgumentQualityEvaluator()
    return await asyncio.to_thread(evaluator.evaluate, input_text)


async def _invoke_counter_argument(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke counter-argument analysis via plugin (no kernel needed)."""
    from argumentation_analysis.agents.core.counter_argument.counter_agent import (
        CounterArgumentPlugin,
    )

    plugin = CounterArgumentPlugin()
    parsed_json = plugin.parse_argument(input_text)
    strategy_json = plugin.suggest_strategy(input_text)
    return {
        "parsed_argument": json.loads(parsed_json),
        "suggested_strategy": json.loads(strategy_json),
        "quality_context": context.get("phase_quality_output"),
    }


async def _invoke_debate_analysis(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke debate argument analysis via plugin (no kernel needed)."""
    from argumentation_analysis.agents.core.debate.debate_agent import DebatePlugin

    plugin = DebatePlugin()
    scores_json = plugin.analyze_argument_quality(input_text)
    return json.loads(scores_json)


async def _invoke_governance(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke governance conflict detection on prior results."""
    from argumentation_analysis.plugins.governance_plugin import GovernancePlugin

    plugin = GovernancePlugin()
    methods_json = plugin.list_governance_methods()
    return {
        "available_methods": json.loads(methods_json),
        "note": "Governance requires structured scenario input. "
        "Use GovernancePlugin directly for full simulation.",
    }


async def _invoke_jtms(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke JTMS belief maintenance — extract claims and track beliefs."""
    from argumentation_analysis.services.jtms.jtms_core import JTMS

    jtms = JTMS()
    sentences = [s.strip() for s in input_text.split(".") if s.strip()]
    for i, sentence in enumerate(sentences[:10]):  # cap at 10 beliefs
        jtms.add_belief(f"claim_{i}")
    return {
        "beliefs": {name: str(b.valid) for name, b in jtms.beliefs.items()},
        "belief_count": len(jtms.beliefs),
    }


async def _invoke_camembert_fallacy(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke CamemBERT-based French fallacy detector (sync, heavy model)."""
    from argumentation_analysis.adapters.french_fallacy_adapter import (
        FrenchFallacyAdapter,
    )

    adapter = FrenchFallacyAdapter(enable_nli=False, enable_llm=False)
    return await asyncio.to_thread(adapter.detect, input_text)


async def _invoke_local_llm(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke local LLM service for text analysis."""
    from argumentation_analysis.services.local_llm_service import LocalLLMService

    service = LocalLLMService()
    messages = [{"role": "user", "content": input_text}]
    return await service.chat_completion(messages)


async def _invoke_semantic_index(input_text: str, context: Dict[str, Any]) -> Dict:
    """Invoke semantic index service for argument search."""
    from argumentation_analysis.services.semantic_index_service import (
        SemanticIndexService,
    )

    service = SemanticIndexService()
    results = await asyncio.to_thread(service.search, input_text)
    return {"results": results}


async def _invoke_speech_transcription(
    input_text: str, context: Dict[str, Any]
) -> Dict:
    """Invoke speech transcription — requires audio_path in context."""
    return {
        "status": "ready",
        "note": "Pass audio file path via context['audio_path'] for transcription.",
    }


# --- State writers: map capability → (output, state, ctx) → None ---
# Each writer extracts relevant data from phase output and writes to
# UnifiedAnalysisState via its typed add_*() methods.
# Writers are defensive: guard with isinstance checks and .get() everywhere.


def _write_quality_to_state(output, state, ctx) -> None:
    """Write quality evaluator results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    arg_id = ctx.get("current_arg_id", "arg_input")
    scores = {
        k: v
        for k, v in output.items()
        if k != "note_finale" and isinstance(v, (int, float))
    }
    overall = output.get("note_finale", 0.0)
    if isinstance(overall, (int, float)):
        state.add_quality_score(arg_id, scores, float(overall))


def _write_counter_argument_to_state(output, state, ctx) -> None:
    """Write counter-argument results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    parsed = output.get("parsed_argument", {})
    strategy = output.get("suggested_strategy", {})
    if not isinstance(parsed, dict):
        parsed = {}
    if not isinstance(strategy, dict):
        strategy = {}
    original = str(parsed.get("premise", ctx.get("input_data", "")))[:200]
    strategy_name = str(strategy.get("strategy_name", "unknown"))
    score = strategy.get("confidence", 0.0)
    if not isinstance(score, (int, float)):
        score = 0.0
    state.add_counter_argument(original, strategy_name, strategy_name, float(score))


def _write_jtms_to_state(output, state, ctx) -> None:
    """Write JTMS results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    beliefs = output.get("beliefs", {})
    if not isinstance(beliefs, dict):
        return
    for name, valid_str in beliefs.items():
        valid = True if valid_str == "True" else (False if valid_str == "False" else None)
        state.add_jtms_belief(str(name), valid, justifications=[])


def _write_debate_to_state(output, state, ctx) -> None:
    """Write debate analysis results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    topic = str(ctx.get("input_data", ""))[:100]
    winner = output.get("winner")
    state.add_debate_transcript(
        topic=topic,
        exchanges=[],
        winner=str(winner) if winner is not None else None,
    )


def _write_governance_to_state(output, state, ctx) -> None:
    """Write governance results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    methods = output.get("available_methods", [])
    if isinstance(methods, list) and methods:
        state.add_governance_decision(
            method="listing",
            winner="N/A",
            scores={str(m): 0.0 for m in methods},
        )


def _write_camembert_to_state(output, state, ctx) -> None:
    """Write CamemBERT neural fallacy results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    detections = output.get("detections", [])
    if not isinstance(detections, list):
        return
    for det in detections:
        if not isinstance(det, dict):
            continue
        state.add_neural_fallacy_score(
            text_segment=str(det.get("text", "")),
            label=str(det.get("label", "unknown")),
            confidence=float(det.get("confidence", 0.0)),
        )


def _write_semantic_index_to_state(output, state, ctx) -> None:
    """Write semantic index results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    results = output.get("results", [])
    if not isinstance(results, list):
        return
    query = str(ctx.get("input_data", ""))
    for r in results:
        if not isinstance(r, dict):
            continue
        state.add_semantic_index_ref(
            query=query,
            document_id=str(r.get("id", "unknown")),
            score=float(r.get("score", 0.0)),
            snippet=r.get("snippet"),
        )


def _write_speech_to_state(output, state, ctx) -> None:
    """Write speech transcription results to UnifiedAnalysisState."""
    if not output or not isinstance(output, dict):
        return
    segments = output.get("segments", [])
    if not isinstance(segments, list):
        return
    for seg in segments:
        if not isinstance(seg, dict):
            continue
        state.add_transcription_segment(
            start_time=float(seg.get("start", 0.0)),
            end_time=float(seg.get("end", 0.0)),
            text=str(seg.get("text", "")),
            speaker=seg.get("speaker"),
        )


CAPABILITY_STATE_WRITERS: Dict[str, Any] = {
    "argument_quality": _write_quality_to_state,
    "counter_argument_generation": _write_counter_argument_to_state,
    "belief_maintenance": _write_jtms_to_state,
    "adversarial_debate": _write_debate_to_state,
    "governance_simulation": _write_governance_to_state,
    "neural_fallacy_detection": _write_camembert_to_state,
    "semantic_indexing": _write_semantic_index_to_state,
    "speech_transcription": _write_speech_to_state,
}


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
        # Wire invoke callable (registration was created by register_counter_arg)
        if "counter_argument_agent" in registry._registrations:
            registry._registrations["counter_argument_agent"].invoke = (
                _invoke_counter_argument
            )
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
            invoke=_invoke_quality_evaluator,
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
            invoke=_invoke_debate_analysis,
        )
        registered.append("debate_agent")
    except ImportError as e:
        skipped.append(("debate_agent", str(e)))

    # Governance agent (2.1.6)
    try:
        from argumentation_analysis.agents.core.governance.governance_agent import (
            Agent as GovernanceAgent,
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
            invoke=_invoke_governance,
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
            invoke=_invoke_jtms,
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
            invoke=_invoke_local_llm,
        )
        registered.append("local_llm_service")
    except ImportError as e:
        skipped.append(("local_llm_service", str(e)))

    # --- Optional adapters (may need heavy dependencies) ---

    if include_optional:
        # CamemBERT fallacy detector (2.3.2)
        try:
            from argumentation_analysis.adapters.french_fallacy_adapter import (
                FrenchFallacyAdapter,
            )

            registry.register_agent(
                name="camembert_fallacy_detector",
                agent_class=FrenchFallacyAdapter,
                capabilities=["neural_fallacy_detection", "fallacy_detection"],
                requires=["camembert_model"],
                metadata={
                    "description": "CamemBERT-based neural fallacy detector (2.3.2)"
                },
                invoke=_invoke_camembert_fallacy,
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
                invoke=_invoke_semantic_index,
            )
            registered.append("semantic_index_service")
        except ImportError as e:
            skipped.append(("semantic_index_service", str(e)))

        # Speech transcription service (speech-to-text)
        try:
            from argumentation_analysis.services.speech_transcription_service import (
                SpeechTranscriptionService,
            )

            registry.register_service(
                name="speech_transcription_service",
                service_class=SpeechTranscriptionService,
                capabilities=["speech_transcription", "speech_to_text"],
                metadata={"description": "Whisper-based speech transcription service"},
                invoke=_invoke_speech_transcription,
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
            logger.warning("Could not import UnifiedAnalysisState; state tracking disabled")
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
    else:
        catalog = get_workflow_catalog()
        if workflow_name not in catalog:
            raise ValueError(
                f"Unknown workflow '{workflow_name}'. "
                f"Available: {list(catalog.keys())}"
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
