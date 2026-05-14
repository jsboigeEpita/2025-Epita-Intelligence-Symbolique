"""
DSL declaratif pour la composition de workflows agentiques.

Ce module fournit un WorkflowBuilder permettant de definir des workflows
par capabilities plutot que par classes concretes. Le systeme resout
automatiquement quels agents/plugins satisfont les besoins.

Usage:
    from argumentation_analysis.orchestration.workflow_dsl import WorkflowBuilder

    workflow = WorkflowBuilder("analysis") \\
        .add_phase("extract", capability="fact_extraction") \\
        .add_phase("fallacy", capability="fallacy_detection") \\
        .add_phase("synthesis", capability="synthesis") \\
        .build()

    result = await workflow.execute(text, registry=registry)
"""

import asyncio
import logging
import time
import uuid
from typing import (
    Callable,
    Dict,
    List,
    Any,
    Optional,
    Set,
    Tuple,
)
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("WorkflowDSL")


class PhaseStatus(Enum):
    """Status d'execution d'une phase."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass
class LoopConfig:
    """Configuration for iterative phase execution."""

    max_iterations: int = 3
    convergence_fn: Optional[Callable[[Any, Any], bool]] = None


@dataclass
class WorkflowPhase:
    """Definition d'une phase dans un workflow."""

    name: str
    capability: str
    optional: bool = False
    depends_on: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: Optional[float] = None
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    loop_config: Optional[LoopConfig] = None
    input_transform: Optional[Callable[[Any, Dict[str, Any]], Any]] = None


@dataclass
class PhaseResult:
    """Resultat d'execution d'une phase."""

    phase_name: str
    status: PhaseStatus
    capability: str
    component_used: Optional[str] = None
    output: Any = None
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class WorkflowDefinition:
    """Definition complete d'un workflow."""

    name: str
    phases: List[WorkflowPhase]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_phase(self, name: str) -> Optional[WorkflowPhase]:
        """Get a phase by name."""
        for phase in self.phases:
            if phase.name == name:
                return phase
        return None

    def get_execution_order(self) -> List[List[str]]:
        """
        Compute execution order respecting dependencies.

        Returns a list of "levels" — phases at the same level can
        execute in parallel; each level depends on all previous levels.
        """
        remaining = {p.name for p in self.phases}
        completed: Set[str] = set()
        levels: List[List[str]] = []

        while remaining:
            # Find phases whose dependencies are all completed
            ready = []
            for phase_name in remaining:
                phase = self.get_phase(phase_name)
                if phase and all(d in completed for d in phase.depends_on):
                    ready.append(phase_name)

            if not ready:
                # Circular dependency or unsatisfiable — break
                logger.error(
                    f"Cannot resolve execution order for phases: {remaining}. "
                    f"Possible circular dependency."
                )
                # Add remaining as a final level to avoid infinite loop
                levels.append(sorted(remaining))
                break

            levels.append(sorted(ready))
            completed.update(ready)
            remaining -= set(ready)

        return levels

    def get_required_capabilities(self) -> List[str]:
        """Get list of all capabilities required by this workflow."""
        return [p.capability for p in self.phases]

    def validate(self) -> List[str]:
        """
        Validate workflow definition.

        Returns list of error messages (empty if valid).
        """
        errors = []
        phase_names = {p.name for p in self.phases}

        for phase in self.phases:
            # Check dependency references exist
            for dep in phase.depends_on:
                # Support wildcard pattern (e.g., "fallacy_*")
                if "*" in dep:
                    pattern = dep.replace("*", "")
                    matching = [n for n in phase_names if pattern in n]
                    if not matching:
                        errors.append(
                            f"Phase '{phase.name}': dependency pattern '{dep}' "
                            f"matches no phases"
                        )
                elif dep not in phase_names:
                    errors.append(
                        f"Phase '{phase.name}': dependency '{dep}' "
                        f"is not a defined phase"
                    )

        # Check for duplicate phase names
        names = [p.name for p in self.phases]
        duplicates = [n for n in names if names.count(n) > 1]
        if duplicates:
            errors.append(f"Duplicate phase names: {set(duplicates)}")

        return errors


class WorkflowBuilder:
    """
    Builder fluent pour construire des WorkflowDefinition.

    Usage:
        workflow = WorkflowBuilder("my_analysis") \\
            .add_phase("extract", capability="fact_extraction") \\
            .add_phase("fallacy", capability="fallacy_detection") \\
            .add_phase("counter", capability="counter_argument",
                       depends_on=["fallacy"]) \\
            .add_phase("synthesis", capability="synthesis") \\
            .build()
    """

    def __init__(self, name: str):
        self._name = name
        self._phases: List[WorkflowPhase] = []
        self._metadata: Dict[str, Any] = {}

    def add_phase(
        self,
        name: str,
        capability: str,
        optional: bool = False,
        depends_on: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        loop_config: Optional[LoopConfig] = None,
        input_transform: Optional[Callable[[Any, Dict[str, Any]], Any]] = None,
    ) -> "WorkflowBuilder":
        """
        Add a phase to the workflow.

        Args:
            name: Unique name for this phase
            capability: Required capability (matched against CapabilityRegistry)
            optional: If True, phase is skipped when no provider is available
            depends_on: List of phase names that must complete before this one
            parameters: Phase-specific parameters passed to the component
            timeout_seconds: Maximum execution time for this phase
            condition: Callable (ctx) -> bool; phase skipped when False
            loop_config: LoopConfig for iterative execution
            input_transform: Callable (input, ctx) -> transformed_input

        Returns:
            self (for chaining)
        """
        phase = WorkflowPhase(
            name=name,
            capability=capability,
            optional=optional,
            depends_on=depends_on or [],
            parameters=parameters or {},
            timeout_seconds=timeout_seconds,
            condition=condition,
            loop_config=loop_config,
            input_transform=input_transform,
        )
        self._phases.append(phase)
        return self

    def add_conditional_phase(
        self,
        name: str,
        capability: str,
        condition: Callable[[Dict[str, Any]], bool],
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add a phase that only executes when condition(ctx) returns True."""
        return self.add_phase(name, capability, condition=condition, **kwargs)

    def add_loop(
        self,
        name: str,
        capability: str,
        max_iterations: int = 3,
        convergence_fn: Optional[Callable[[Any, Any], bool]] = None,
        **kwargs: Any,
    ) -> "WorkflowBuilder":
        """Add a phase that loops until convergence or max_iterations."""
        loop_cfg = LoopConfig(
            max_iterations=max_iterations, convergence_fn=convergence_fn
        )
        return self.add_phase(name, capability, loop_config=loop_cfg, **kwargs)

    def set_metadata(self, key: str, value: Any) -> "WorkflowBuilder":
        """Set a metadata key-value pair on the workflow."""
        self._metadata[key] = value
        return self

    def build(self) -> WorkflowDefinition:
        """
        Build and validate the workflow definition.

        Returns:
            WorkflowDefinition ready for execution.

        Raises:
            ValueError: If validation fails.
        """
        definition = WorkflowDefinition(
            name=self._name,
            phases=list(self._phases),
            metadata=dict(self._metadata),
        )

        errors = definition.validate()
        if errors:
            raise ValueError(
                f"Workflow '{self._name}' validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

        logger.info(
            f"Built workflow '{self._name}' with {len(self._phases)} phases: "
            f"{[p.name for p in self._phases]}"
        )
        return definition


class WorkflowExecutor:
    """
    Execute un WorkflowDefinition en resolvant les capabilities
    via un CapabilityRegistry.
    """

    def __init__(self, registry: Any):
        """
        Args:
            registry: CapabilityRegistry instance for resolving capabilities.
        """
        self._registry = registry
        self._base_logger = logging.getLogger("orchestration.workflow_executor")

    async def execute(
        self,
        workflow: WorkflowDefinition,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
        state: Optional[Any] = None,
        state_writers: Optional[Dict[str, Any]] = None,
        checkpoint_callback: Optional[Callable[..., None]] = None,
        resume_from: Optional[Set[str]] = None,
    ) -> Dict[str, PhaseResult]:
        """
        Execute a workflow definition.

        Phases at the same DAG level execute concurrently via asyncio.gather().
        Phases at different levels execute sequentially (respecting depends_on).

        Args:
            workflow: The workflow to execute
            input_data: Input data (typically text to analyze)
            context: Additional context passed to each phase
            state: Optional UnifiedAnalysisState (typed as Any to avoid
                   circular import). If provided, phase results are written
                   to it via state_writers.
            state_writers: Dict mapping capability name to a callable
                ``(output, state, ctx) -> None`` that writes phase output
                to the state object.
            checkpoint_callback: Optional callable invoked after each DAG level
                with signature ``(results, ctx) -> None``.  Used for per-document
                checkpointing in long batch runs.
            resume_from: Optional set of phase names to skip (already completed
                in a previous run).  Their outputs must already be present in
                *context* (keyed ``phase_{name}_output`` / ``phase_{name}_result``).

        Returns:
            Dict mapping phase name to PhaseResult.
        """
        results: Dict[str, PhaseResult] = {}
        execution_order = workflow.get_execution_order()
        ctx = dict(context or {})
        ctx["input_data"] = input_data
        skip_phases: Set[str] = resume_from or set()

        if state is not None:
            ctx["unified_state"] = state

        # Structured logging with correlation_id
        correlation_id = (
            ctx.get("correlation_id")
            or (getattr(state, "run_id", None) if state else None)
            or str(uuid.uuid4())
        )
        ctx["correlation_id"] = correlation_id

        from argumentation_analysis.orchestration.structured_logging import PhaseLogger
        slog = PhaseLogger(self._base_logger, correlation_id=correlation_id)

        slog.info(
            f"Executing workflow '{workflow.name}' — "
            f"{len(workflow.phases)} phases, {len(execution_order)} levels"
            f"{f', resuming (skip {len(skip_phases)} phases)' if skip_phases else ''}",
            extra={"workflow": workflow.name, "phases_total": len(workflow.phases)},
        )

        for level_idx, level_phases in enumerate(execution_order):
            logger.debug(f"Level {level_idx}: executing phases {level_phases}")

            # Split into skipped vs to-run
            to_run = [p for p in level_phases if p not in skip_phases]
            for phase_name in level_phases:
                if phase_name in skip_phases:
                    # Reconstruct a SKIPPED result from context if available
                    existing_result = ctx.get(f"phase_{phase_name}_result")
                    if existing_result is not None:
                        # Use the output/context from checkpoint but mark as SKIPPED
                        results[phase_name] = PhaseResult(
                            phase_name=phase_name,
                            status=PhaseStatus.SKIPPED,
                            capability=existing_result.capability,
                            component_used=existing_result.component_used,
                            output=existing_result.output,
                            error="Skipped (resumed from checkpoint)",
                            duration_seconds=existing_result.duration_seconds,
                        )
                    else:
                        _skipped_phase = workflow.get_phase(phase_name)
                        results[phase_name] = PhaseResult(
                            phase_name=phase_name,
                            status=PhaseStatus.SKIPPED,
                            capability=(
                                _skipped_phase.capability
                                if _skipped_phase
                                else "unknown"
                            ),
                            error="Skipped (resumed from checkpoint)",
                        )

            phase_coros = []
            for phase_name in to_run:
                phase = workflow.get_phase(phase_name)
                if phase:
                    slog.info(
                        "Starting phase",
                        extra={"phase_name": phase_name, "capability": phase.capability},
                    )
                    phase_coros.append(
                        self._execute_phase(phase, phase_name, input_data, ctx)
                    )

            if phase_coros:
                level_results = await asyncio.gather(*phase_coros)
                for phase_name, result, output in level_results:
                    self._store_phase_result(
                        phase_name, result, output, results, ctx, state, state_writers
                    )

            if checkpoint_callback is not None:
                try:
                    checkpoint_callback(results, ctx)
                except Exception as cb_err:
                    logger.warning("Checkpoint callback failed: %s", cb_err)

        # Summary
        completed = sum(
            1 for r in results.values() if r.status == PhaseStatus.COMPLETED
        )
        failed = sum(1 for r in results.values() if r.status == PhaseStatus.FAILED)
        skipped = sum(1 for r in results.values() if r.status == PhaseStatus.SKIPPED)
        slog.info(
            f"Workflow '{workflow.name}' finished: "
            f"{completed} completed, {failed} failed, {skipped} skipped",
            extra={
                "workflow": workflow.name,
                "phases_completed": completed,
                "phases_total": len(results),
            },
        )

        if state is not None and hasattr(state, "set_workflow_results"):
            try:
                state.set_workflow_results(
                    workflow.name,
                    {
                        "completed": completed,
                        "failed": failed,
                        "skipped": skipped,
                        "phases": {name: r.status.value for name, r in results.items()},
                    },
                )
            except Exception as sw_err:
                logger.warning(f"Failed to store workflow results in state: {sw_err}")

        return results

    async def _execute_phase(
        self,
        phase: WorkflowPhase,
        phase_name: str,
        input_data: Any,
        ctx: Dict[str, Any],
    ) -> Tuple[str, PhaseResult, Any]:
        """Execute a single workflow phase, returning (name, result, output)."""
        start = time.time()

        # Condition check
        if phase.condition is not None:
            try:
                if not phase.condition(ctx):
                    return (
                        phase_name,
                        PhaseResult(
                            phase_name=phase_name,
                            status=PhaseStatus.SKIPPED,
                            capability=phase.capability,
                            error="Condition not met",
                        ),
                        None,
                    )
            except Exception as cond_err:
                logger.warning(
                    f"Condition eval failed for '{phase_name}': "
                    f"{cond_err} — proceeding anyway"
                )

        # Resolve capability
        try:
            providers = self._registry.find_for_capability(phase.capability)
        except Exception as resolve_err:
            duration = time.time() - start
            return (
                phase_name,
                PhaseResult(
                    phase_name=phase_name,
                    status=PhaseStatus.FAILED,
                    capability=phase.capability,
                    error=f"Capability resolution error: {resolve_err}",
                    duration_seconds=duration,
                ),
                None,
            )

        if not providers:
            if phase.optional:
                return (
                    phase_name,
                    PhaseResult(
                        phase_name=phase_name,
                        status=PhaseStatus.SKIPPED,
                        capability=phase.capability,
                        error="No provider available (optional phase)",
                    ),
                    None,
                )
            return (
                phase_name,
                PhaseResult(
                    phase_name=phase_name,
                    status=PhaseStatus.FAILED,
                    capability=phase.capability,
                    error=f"No provider for required capability '{phase.capability}'",
                ),
                None,
            )

        provider = providers[0]
        try:
            phase_input = input_data
            if phase.input_transform is not None:
                try:
                    phase_input = phase.input_transform(input_data, ctx)
                except Exception as tf_err:
                    logger.warning(
                        f"Input transform failed for '{phase_name}': "
                        f"{tf_err} — using original input"
                    )
                    phase_input = input_data

            output = None
            if provider.invoke is not None:
                if phase.loop_config is not None:
                    output = await self._execute_loop(
                        phase,
                        provider,
                        phase_input,
                        ctx,
                        phase.loop_config,
                    )
                elif phase.timeout_seconds:
                    output = await asyncio.wait_for(
                        provider.invoke(phase_input, ctx),
                        timeout=phase.timeout_seconds,
                    )
                else:
                    output = await provider.invoke(phase_input, ctx)
            else:
                logger.warning(
                    f"Phase '{phase_name}': component '{provider.name}' "
                    f"has no invoke callable, output will be None"
                )

            duration = time.time() - start
            return (
                phase_name,
                PhaseResult(
                    phase_name=phase_name,
                    status=PhaseStatus.COMPLETED,
                    capability=phase.capability,
                    component_used=provider.name,
                    output=output,
                    duration_seconds=duration,
                ),
                output,
            )

        except Exception as e:
            duration = time.time() - start
            return (
                phase_name,
                PhaseResult(
                    phase_name=phase_name,
                    status=PhaseStatus.FAILED,
                    capability=phase.capability,
                    component_used=provider.name,
                    error=str(e),
                    duration_seconds=duration,
                ),
                None,
            )

    def _store_phase_result(
        self,
        phase_name: str,
        result: PhaseResult,
        output: Any,
        results: Dict[str, PhaseResult],
        ctx: Dict[str, Any],
        state: Any,
        state_writers: Optional[Dict[str, Any]],
    ) -> None:
        """Store a phase result in results dict, context, and state."""
        results[phase_name] = result

        if result.status == PhaseStatus.COMPLETED:
            ctx[f"phase_{phase_name}_result"] = result
            ctx[f"phase_{phase_name}_output"] = output

            if (
                state is not None
                and state_writers
                and result.capability in state_writers
            ):
                try:
                    state_writers[result.capability](output, state, ctx)
                except Exception as sw_err:
                    logger.warning(
                        f"State writer for '{result.capability}' failed: {sw_err}"
                    )

            logger.info(
                f"Phase '{phase_name}' completed "
                f"using '{result.component_used}' ({result.duration_seconds:.2f}s)"
            )
        elif result.status == PhaseStatus.SKIPPED:
            logger.info(f"Phase '{phase_name}' skipped — {result.error}")
        elif result.status == PhaseStatus.FAILED:
            logger.error(f"Phase '{phase_name}' FAILED — " f"{result.error}")
            if state is not None and hasattr(state, "log_error"):
                try:
                    state.log_error(phase_name, str(result.error))
                except Exception:
                    pass

    async def _execute_loop(
        self,
        phase: WorkflowPhase,
        provider: Any,
        phase_input: Any,
        ctx: Dict[str, Any],
        loop_config: LoopConfig,
    ) -> Any:
        """Execute a phase iteratively until convergence or max_iterations."""
        import asyncio

        prev_output = None
        final_output = None

        for iteration in range(loop_config.max_iterations):
            if phase.timeout_seconds:
                output = await asyncio.wait_for(
                    provider.invoke(phase_input, ctx),
                    timeout=phase.timeout_seconds,
                )
            else:
                output = await provider.invoke(phase_input, ctx)

            # Store iteration result in context
            ctx[f"phase_{phase.name}_output"] = output
            ctx[f"phase_{phase.name}_iteration"] = iteration

            # Check convergence
            if loop_config.convergence_fn and prev_output is not None:
                try:
                    if loop_config.convergence_fn(prev_output, output):
                        logger.info(
                            f"Phase '{phase.name}' converged at "
                            f"iteration {iteration}"
                        )
                        final_output = output
                        break
                except Exception as conv_err:
                    logger.warning(
                        f"Convergence check failed for '{phase.name}': "
                        f"{conv_err} — continuing"
                    )

            prev_output = output
            final_output = output

        return final_output
