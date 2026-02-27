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

import logging
from typing import (
    Dict,
    List,
    Any,
    Optional,
    Set,
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
class WorkflowPhase:
    """Definition d'une phase dans un workflow."""

    name: str
    capability: str
    optional: bool = False
    depends_on: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: Optional[float] = None


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
        )
        self._phases.append(phase)
        return self

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

    async def execute(
        self,
        workflow: WorkflowDefinition,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, PhaseResult]:
        """
        Execute a workflow definition.

        Args:
            workflow: The workflow to execute
            input_data: Input data (typically text to analyze)
            context: Additional context passed to each phase

        Returns:
            Dict mapping phase name to PhaseResult.
        """
        import time

        results: Dict[str, PhaseResult] = {}
        execution_order = workflow.get_execution_order()
        ctx = dict(context or {})
        ctx["input_data"] = input_data

        logger.info(
            f"Executing workflow '{workflow.name}' — "
            f"{len(workflow.phases)} phases, {len(execution_order)} levels"
        )

        for level_idx, level_phases in enumerate(execution_order):
            logger.debug(f"Level {level_idx}: executing phases {level_phases}")

            for phase_name in level_phases:
                phase = workflow.get_phase(phase_name)
                if not phase:
                    continue

                start = time.time()

                # Resolve capability
                providers = self._registry.find_for_capability(phase.capability)

                if not providers:
                    if phase.optional:
                        results[phase_name] = PhaseResult(
                            phase_name=phase_name,
                            status=PhaseStatus.SKIPPED,
                            capability=phase.capability,
                            error="No provider available (optional phase)",
                        )
                        logger.info(
                            f"Phase '{phase_name}' skipped — "
                            f"no provider for '{phase.capability}'"
                        )
                        continue
                    else:
                        results[phase_name] = PhaseResult(
                            phase_name=phase_name,
                            status=PhaseStatus.FAILED,
                            capability=phase.capability,
                            error=f"No provider for required capability '{phase.capability}'",
                        )
                        logger.error(
                            f"Phase '{phase_name}' FAILED — "
                            f"no provider for required capability '{phase.capability}'"
                        )
                        continue

                # Use the first available provider
                provider = providers[0]
                try:
                    # Phase execution is a placeholder —
                    # actual execution depends on component type
                    duration = time.time() - start
                    results[phase_name] = PhaseResult(
                        phase_name=phase_name,
                        status=PhaseStatus.COMPLETED,
                        capability=phase.capability,
                        component_used=provider.name,
                        output=None,  # Will be populated by actual execution
                        duration_seconds=duration,
                    )

                    # Store result in context for downstream phases
                    ctx[f"phase_{phase_name}_result"] = results[phase_name]

                    logger.info(
                        f"Phase '{phase_name}' completed "
                        f"using '{provider.name}' ({duration:.2f}s)"
                    )

                except Exception as e:
                    duration = time.time() - start
                    results[phase_name] = PhaseResult(
                        phase_name=phase_name,
                        status=PhaseStatus.FAILED,
                        capability=phase.capability,
                        component_used=provider.name,
                        error=str(e),
                        duration_seconds=duration,
                    )
                    logger.error(f"Phase '{phase_name}' FAILED: {e}")

        # Summary
        completed = sum(
            1 for r in results.values() if r.status == PhaseStatus.COMPLETED
        )
        failed = sum(1 for r in results.values() if r.status == PhaseStatus.FAILED)
        skipped = sum(1 for r in results.values() if r.status == PhaseStatus.SKIPPED)
        logger.info(
            f"Workflow '{workflow.name}' finished: "
            f"{completed} completed, {failed} failed, {skipped} skipped"
        )

        return results
