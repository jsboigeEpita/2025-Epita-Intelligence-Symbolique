"""
Hierarchical Orchestrator — Bridge implementation (Option B, R311-B4).

Provides `HierarchicalOrchestrator` which combines:
  - **StrategicManager** for high-level objective planning
  - **objectives_to_workflow()** for translating objectives into a WorkflowDefinition
  - **WorkflowExecutor** (backed by CapabilityRegistry) for execution

This "bridge" approach reuses the proven Lego Architecture (CapabilityRegistry +
WorkflowDSL + WorkflowExecutor) rather than the legacy 3-tier delegation chain
(StrategicManager → TacticalCoordinator → OperationalManager), which is dormant
and requires more work to reactivate.

Created as part of Epic #208 / R311 — Hierarchical Mode Reactivation.
"""

import logging
import time
from typing import Any, Callable, Dict, Optional

from argumentation_analysis.orchestration.hierarchical.strategic.manager import (
    StrategicManager,
)
from argumentation_analysis.orchestration.hierarchical.hierarchy_bridge import (
    objectives_to_workflow,
    RegistryBackedOperationalRegistry,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseResult,
    PhaseStatus,
    WorkflowExecutor,
)
from argumentation_analysis.core.capability_registry import CapabilityRegistry

logger = logging.getLogger("HierarchicalOrchestrator")


class HierarchicalOrchestrator:
    """
    Orchestrates analysis using the hierarchical (Strategic → Lego) bridge.

    Flow:
        1. StrategicManager.initialize_analysis(text) → objectives + plan
        2. objectives_to_workflow(objectives, registry) → WorkflowDefinition
        3. WorkflowExecutor.execute(workflow, text) → phase results
        4. StrategicManager.evaluate_final_results(results) → conclusion

    Args:
        capability_registry: A pre-populated CapabilityRegistry. If None,
            one will be created via ``run_unified_analysis``'s default setup.
        strategic_manager: Optional pre-configured StrategicManager.
    """

    def __init__(
        self,
        capability_registry: Optional[CapabilityRegistry] = None,
        strategic_manager: Optional[StrategicManager] = None,
    ):
        self._registry = capability_registry
        self._strategic_manager = strategic_manager or StrategicManager()
        self._executor: Optional[WorkflowExecutor] = None
        self._initialized = False

    def _ensure_registry(self) -> CapabilityRegistry:
        """Lazily create a CapabilityRegistry if one was not provided."""
        if self._registry is None:
            # Use the same registry setup as the unified pipeline.
            from argumentation_analysis.orchestration.registry_setup import (
                setup_registry,
            )

            self._registry = setup_registry()
            logger.info("CapabilityRegistry created via setup_registry()")
        return self._registry

    async def analyze(
        self,
        text: str,
        state: Optional[Any] = None,
        state_writers: Optional[Dict[str, Any]] = None,
        checkpoint_callback: Optional[Callable[..., None]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Run a full hierarchical analysis on the given text.

        Args:
            text: The argument text to analyze.
            state: Optional analysis-state object passed BY REFERENCE to the
                executor. CB #1528 item 2: the caller keeps the reference, so
                a run torn by an external ``asyncio.wait_for`` still leaves
                behind everything the completed phases wrote — the same
                mechanism ``run_pipeline_mode`` already relies on. Without it
                the breach yields a sterile result (state lost with the
                cancelled coroutine).
            state_writers: Capability-name → writer mapping (typically
                ``CAPABILITY_STATE_WRITERS``). Only consulted when ``state``
                is not None; each write is already guarded executor-side
                (workflow_dsl.py:788).
            checkpoint_callback: Optional ``(results, ctx)`` callable invoked
                after each fully-gathered DAG level. The bridge workflow is a
                strictly sequential chain (``objectives_to_workflow`` makes
                every phase depend on the previous one), so this fires once
                per completed phase — a torn phase never reaches it, so a
                bounded caller cannot over-count.
            **kwargs: Additional context passed through to WorkflowExecutor.

        Returns:
            Dict with keys:
              - ``objectives``: The strategic objectives generated
              - ``phase_results``: Dict[str, PhaseResult] from execution
              - ``conclusion``: The StrategicManager's final conclusion
              - ``duration_seconds``: Total wall-clock time
              - ``summary``: Completed/failed/skipped counts
        """
        start = time.time()
        registry = self._ensure_registry()
        self._executor = WorkflowExecutor(registry)

        # --- Phase 1: Strategic Planning ---
        logger.info("Phase 1: Strategic planning (StrategicManager)")
        init_result = self._strategic_manager.initialize_analysis(text)
        objectives = init_result.get("objectives", [])
        strategic_plan = init_result.get("strategic_plan", {})

        if not objectives:
            logger.warning(
                "StrategicManager returned no objectives — "
                "falling back to default 4-objective set"
            )
            objectives = [
                {
                    "id": "obj-1",
                    "description": "Identifier les arguments principaux",
                    "priority": "high",
                },
                {
                    "id": "obj-2",
                    "description": "Détecter les sophismes",
                    "priority": "high",
                },
                {
                    "id": "obj-3",
                    "description": "Analyser la structure logique",
                    "priority": "medium",
                },
                {
                    "id": "obj-4",
                    "description": "Évaluer la cohérence globale",
                    "priority": "medium",
                },
            ]

        logger.info(f"  → {len(objectives)} objectives generated")

        # --- Phase 2: Translate objectives → WorkflowDefinition ---
        logger.info("Phase 2: Translating objectives into WorkflowDefinition")
        workflow = objectives_to_workflow(
            objectives,
            registry,
            workflow_name="hierarchical_analysis",
        )
        phase_count = len(workflow.phases)
        logger.info(f"  → WorkflowDefinition with {phase_count} phases")

        # --- Phase 3: Execute via WorkflowExecutor ---
        logger.info("Phase 3: Executing workflow via WorkflowExecutor")
        context = {
            "source": "hierarchical",
            # CB #1528 item 2: the PLANNED phase count travels in the context
            # so a bounded caller's checkpoint callback can report
            # ``completed/planned`` at breach instead of the nonsensical
            # ``N/0`` (coord R710 wart). Read off the built WorkflowDefinition
            # — measured, never fabricated.
            "hierarchical_planned_phases": phase_count,
            **kwargs,
        }
        phase_results: Dict[str, PhaseResult] = await self._executor.execute(
            workflow,
            text,
            context=context,
            state=state,
            state_writers=state_writers,
            checkpoint_callback=checkpoint_callback,
        )

        # Compute summary
        completed = sum(
            1 for r in phase_results.values() if r.status == PhaseStatus.COMPLETED
        )
        failed = sum(
            1 for r in phase_results.values() if r.status == PhaseStatus.FAILED
        )
        skipped = sum(
            1 for r in phase_results.values() if r.status == PhaseStatus.SKIPPED
        )

        logger.info(f"  → {completed} completed, {failed} failed, {skipped} skipped")

        # --- Phase 4: Strategic Evaluation ---
        logger.info("Phase 4: Strategic evaluation of results")
        # Build a results dict keyed by objective ID for the StrategicManager
        eval_input: Dict[str, Any] = {}
        for obj in objectives:
            obj_id = obj["id"]
            # Find phase results that mention this objective
            obj_phases = {
                name: pr for name, pr in phase_results.items() if obj_id in name
            }
            # Compute a simple success rate based on phase outcomes
            if obj_phases:
                success = sum(
                    1
                    for pr in obj_phases.values()
                    if pr.status == PhaseStatus.COMPLETED
                )
                eval_input[obj_id] = {
                    "success_rate": success / len(obj_phases),
                    "phases": {
                        k: {"status": v.status.value} for k, v in obj_phases.items()
                    },
                }
            else:
                eval_input[obj_id] = {"success_rate": 0.0}

        conclusion_result = self._strategic_manager.evaluate_final_results(eval_input)

        duration = time.time() - start
        logger.info(f"Hierarchical analysis completed in {duration:.1f}s")

        return {
            "objectives": objectives,
            "strategic_plan": strategic_plan,
            "phase_results": {
                name: {
                    "status": pr.status.value,
                    "output": pr.output if pr.status == PhaseStatus.COMPLETED else None,
                    "error": str(pr.error) if pr.error else None,
                }
                for name, pr in phase_results.items()
            },
            "conclusion": conclusion_result.get("conclusion", ""),
            "evaluation": conclusion_result.get("evaluation", {}),
            "duration_seconds": duration,
            "summary": {
                "total": phase_count,
                "completed": completed,
                "failed": failed,
                "skipped": skipped,
            },
            "workflow_name": "hierarchical_analysis",
        }


# ---------------------------------------------------------------------------
# Module-level convenience function (used by run_orchestration.py)
# ---------------------------------------------------------------------------


async def run_hierarchical_analysis(
    text: str,
    capability_registry: Optional[CapabilityRegistry] = None,
    mode: str = "bridge",
    state: Optional[Any] = None,
    state_writers: Optional[Dict[str, Any]] = None,
    checkpoint_callback: Optional[Callable[..., None]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Convenience entry point for hierarchical analysis.

    Two selectable, comparable axes (anti-pendule #1019 / north-star R311 —
    the DAG is NOT thrown away):

    * ``mode="bridge"`` (default, M2) — short-circuits the 3-tier chain via
      ``objectives_to_workflow`` → ``WorkflowExecutor`` (Lego/DAG).
    * ``mode="delegation"`` (M3, RA-10 #1069) — true strategic→tactical→
      operational delegation driven by explicit sequential calls. Fails loud
      on a degraded chain instead of falling back to hardcoded objectives.

    Used by ``run_orchestration.py --mode hierarchical --hierarchical-mode ...``.

    CB #1528 item 2 — incremental-progress seam (opt-in, ``None`` = the
    original behaviour): ``state`` / ``state_writers`` / ``checkpoint_callback``
    let a wall-clock-bounded caller keep a reference to what the run produced
    BEFORE it was cut. Both modes expose the seam, with the shape each one
    actually has:

    * ``bridge`` — all three, forwarded to ``WorkflowExecutor`` (DAG levels).
    * ``delegation`` — ``checkpoint_callback`` only, fired per completed
      operational task. This mode has no ``UnifiedAnalysisState`` surface, so
      ``state`` / ``state_writers`` would have nothing to write into; they are
      rejected rather than silently ignored (a caller that passes them is
      expecting a fill rate it would never get).
    """
    if mode == "delegation":
        # Imported lazily to avoid a hard dependency cycle for the M2 path.
        from argumentation_analysis.orchestration.hierarchical.delegation_orchestrator import (
            run_delegation_analysis,
        )

        if state is not None or state_writers is not None:
            raise ValueError(
                "hierarchical mode='delegation' has no shared-state surface: "
                "state/state_writers cannot be honoured. Use "
                "checkpoint_callback (fired per completed operational task) "
                "to observe incremental progress."
            )
        return await run_delegation_analysis(
            text,
            capability_registry=capability_registry,
            checkpoint_callback=checkpoint_callback,
            **kwargs,
        )
    if mode != "bridge":
        raise ValueError(
            f"Unknown hierarchical mode {mode!r}; expected 'bridge' or 'delegation'."
        )

    orchestrator = HierarchicalOrchestrator(
        capability_registry=capability_registry,
    )
    return await orchestrator.analyze(
        text,
        state=state,
        state_writers=state_writers,
        checkpoint_callback=checkpoint_callback,
        **kwargs,
    )
