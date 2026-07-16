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

Refactored in #310: implementation split into sub-modules.
This file is the public facade — all symbols are re-exported for
backward compatibility.
"""

import logging
from typing import Dict, Any, Optional

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

# ── Re-export all symbols from sub-modules for backward compatibility ──

# Invoke callables (40+ functions)
from argumentation_analysis.orchestration.invoke_callables import *  # noqa: F401,F403

# State writers
from argumentation_analysis.orchestration.state_writers import *  # noqa: F401,F403

# Registry setup
from argumentation_analysis.orchestration.registry_setup import (  # noqa: F401
    setup_registry,
    _declare_tweety_slots,
)

# Workflow definitions
from argumentation_analysis.orchestration.workflows import *  # noqa: F401,F403

logger = logging.getLogger("UnifiedPipeline")


async def run_unified_analysis(
    text: str,
    workflow_name: str = "standard",
    registry: Optional[CapabilityRegistry] = None,
    custom_workflow: Optional[WorkflowDefinition] = None,
    context: Optional[Dict[str, Any]] = None,
    state: Optional[Any] = None,
    create_state: bool = True,
    checkpoint_callback: Optional[Any] = None,
    resume_from: Optional[set] = None,
    render_restitution: bool = False,
    deanonymized: bool = True,
    source_metadata: Optional[Dict[str, str]] = None,
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
        checkpoint_callback: Optional callable passed to WorkflowExecutor for
              per-level checkpointing.  Signature: ``(results, ctx) -> None``.
        resume_from: Optional set of phase names to skip on resume.
        render_restitution: If True (and state tracking is enabled), assemble the
              readable 3-act restitution report from the completed state and add it
              to the result as ``restitution_report`` (a ``RenderedReport`` with
              ``markdown`` + gate ``verdict``). This is the R6-final wiring (#1140):
              it replaces the unreadable dimensional dump as the default report a
              reader meets first. Honest on non-spectacular states (missing acts
              are named, not fabricated — #1019/#369).
        deanonymized: Epic #1258 / Track 1 #1259. If True (default for CLI/local),
              the working state carries REAL source metadata and the restitution
              prompt builders DROP the opaque-ID directives, so the readable report
              names the real speaker/arena. If False, the opaque-ID discipline is
              restored verbatim (git/dashboard/API paths). The export BOUNDARY
              guard (sanitize_state) is Track 3, orthogonal to this flag.
        source_metadata: Epic #1258 / Track 1 #1259. Optional dict of real
              source-level metadata (speaker, arena, epoch...) threaded into
              ``state.source_metadata``. Only short metadata fields — no
              ``raw_text``/``full_text`` (privacy HARD).

    Returns:
        Dict with keys:
            - workflow_name: Name of the executed workflow
            - phases: Dict[str, PhaseResult] — per-phase results
            - summary: Dict with completed/failed/skipped counts
            - capabilities_used: List of capabilities that were successfully resolved
            - capabilities_missing: List of capabilities with no provider
            - unified_state: UnifiedAnalysisState (if state tracking enabled)
            - state_snapshot: Dict snapshot of the state (if state tracking enabled)
            - restitution_report: RenderedReport (if render_restitution=True) — the
                  readable 3-act Markdown + gate-lisibilité verdict
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

    # Epic #1258 / Track 1 #1259 — thread the deanonymization switch + real
    # source metadata onto the working state. Threaded via ``state`` because the
    # ``build_actN_*`` / stakes / strategic prompt builders cannot see ``context``
    # (#1259). Applied to both the freshly-created state and any externally
    # provided state. ``getattr`` fallback keeps the defaults safe if a caller
    # passes a minimal state object lacking the attribute.
    if state is not None:
        try:
            state.deanonymized = bool(deanonymized)
            if source_metadata is not None:
                if hasattr(state, "set_source_metadata"):
                    state.set_source_metadata(source_metadata)
                else:
                    state.source_metadata = dict(source_metadata)
        except Exception as e:
            logger.warning("Failed to thread deanonymized/source_metadata: %s", e)

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

            conv_result = await run_conversational_analysis(text, spectacular=True)

            # Result already contains summary, capabilities_used, workflow_name (#363)
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

    # #905: Apply formal extension filter before execution
    formal_filter = context.get("formal_extension_filter", "all") if context else "all"
    if formal_filter != "all":
        from argumentation_analysis.orchestration.workflows import filter_formal_extensions

        workflow = filter_formal_extensions(workflow, formal_filter)

    # JPype warmup: eagerly initialise JVM + Tweety classes before DAG
    # execution to eliminate the race condition where multiple parallel
    # phases call asyncio.to_thread() → TweetyInitializer concurrently
    # (root cause of the ~20% timeout rate observed in #529).
    _jpype_phases = {
        "pl",
        "fol",
        "modal",
        "dung_extensions",
        "ranking",
        "bipolar",
        "probabilistic",
        "aspic_analysis",
        "fol_solver",
        "modal_solver",
    }
    if workflow_name == "spectacular" and any(
        p.name in _jpype_phases for p in workflow.phases
    ):
        try:
            from argumentation_analysis.agents.core.logic.tweety_initializer import (
                TweetyInitializer,
            )

            init = TweetyInitializer()
            init.ensure_jvm_and_components_are_ready()
            logger.info("JPype/Tweety warmup complete before DAG execution")
        except Exception as e:
            logger.warning(f"JPype warmup failed (will retry in-phase): {e}")

    executor = WorkflowExecutor(registry)

    # Inject shield phase if shield_config present in context (#896)
    # This adds a pre-extraction "shield" phase that validates input before
    # any LLM call. The phase is optional and fails gracefully.
    if context and context.get("shield_config"):
        try:
            builder = WorkflowBuilder("shielded_" + workflow.name)
            builder.add_phase(
                name="shield",
                capability="input_validation",
                optional=True,
            )
            # Copy all original phases after shield
            for phase in workflow.phases:
                builder._phases.append(phase)
            workflow = builder.build()
            logger.info(
                "Shield phase injected (preset=%s)",
                context["shield_config"].get("preset"),
            )
        except Exception as e:
            logger.warning(
                "Shield phase injection failed, using original workflow: %s", e
            )

    phase_results = await executor.execute(
        workflow,
        input_data=text,
        context=context,
        state=state,
        state_writers=CAPABILITY_STATE_WRITERS if state is not None else None,
        checkpoint_callback=checkpoint_callback,
        resume_from=resume_from,
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

    # Constat n°5 (#1355): a COMPLETED phase may still be *degraded* — e.g.
    # setaf/weighted ``absent_no_translator`` (no genuine extraction on this
    # corpus, honest LLM non-determinism), or a solver ParserException caught
    # into an honest-degraded verdict. capabilities_used (built from
    # PhaseStatus.COMPLETED alone) would report these identical to a genuine
    # decision — the exact theatre #1019 forbids. Cross with the honest
    # ``structured_arg_status`` layer (already populated on the state) so a
    # degraded capability surfaces via capabilities_degraded, NOT as ``used``.
    # Mirrors the conversational_orchestrator fix (#1446). Additive key: zero
    # blast radius on consumers (all read capabilities_used via .get(..., [])).
    capabilities_degraded: list[str] = []
    degraded_caps: set[str] = set()
    if state is not None:
        structured = getattr(state, "structured_arg_status", None) or {}
        degraded_caps = {
            cap
            for cap, info in structured.items()
            if isinstance(info, dict) and info.get("degraded")
        }

    # BO-2 #1472 — ``structured_arg_status`` only covers the formal/logic
    # axes (ASPIC+/SetAF/weighted/Dung). Non-formal workflows (e.g.
    # ``democratech``) carry their honest-degraded verdict in the phase
    # output itself, via the codebase's standard ``output["degraded"] = True``
    # canon (state_writers._write_external_*_solver, fallacy_detection,
    # governance per GE-4 #1462). Without this cross-check, a 9-phase
    # deliberation whose governance verdict is empty (no derivable
    # preferences — no LLM key, sparse upstream) reports as 9/9 success —
    # exactly the theatre #1019 forbids. Surface phase-level degraded
    # markers here too. Additive: phases without the marker are unaffected.
    for pr in phase_results.values():
        if pr.status != PhaseStatus.COMPLETED:
            continue
        out = getattr(pr, "output", None)
        if isinstance(out, dict) and out.get("degraded") is True:
            degraded_caps.add(pr.capability)

    if degraded_caps:
        capabilities_degraded = sorted(degraded_caps)
        capabilities_used = [
            c for c in capabilities_used if c not in degraded_caps
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
        "capabilities_degraded": capabilities_degraded,
        "capabilities_missing": capabilities_missing,
    }

    # Include state in results if available
    if state is not None:
        result["unified_state"] = state
        try:
            result["state_snapshot"] = state.get_state_snapshot(summarize=True)
        except Exception:
            result["state_snapshot"] = None

    # R6-final wiring (#1140): assemble the readable 3-act restitution report
    # from the completed state. Lazy import keeps the renderer decoupled from
    # the pipeline (file-disjoint lane). Honest on any state — missing acts are
    # named by the renderer, never fabricated (#1019/#369).
    if render_restitution and state is not None:
        try:
            from argumentation_analysis.reporting.restitution.pipeline_adapter import (
                render_spectacular_restitution,
            )

            result["restitution_report"] = render_spectacular_restitution(state)
        except Exception as exc:  # noqa: BLE001 — reporting must never fail the run
            logger.warning(
                "Restitution report rendering failed (fail-loud, non-fatal): %s",
                exc,
            )
            result["restitution_report"] = None

    return result
