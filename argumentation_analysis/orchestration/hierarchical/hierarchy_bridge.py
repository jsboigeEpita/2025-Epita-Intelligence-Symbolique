"""
Bridge between the hierarchical (Strategic→Tactical→Operational) architecture
and the Lego (CapabilityRegistry + WorkflowDSL) architecture.

Provides:
- RegistryBackedOperationalRegistry: wraps CapabilityRegistry for use by
  the hierarchical tactical layer, replacing hardcoded agent lookups.
- HierarchicalTurnStrategy: wraps the 3-tier hierarchical system as a
  pluggable TurnStrategy for ConversationalPipeline.
- objectives_to_workflow: translates strategic objectives into a
  WorkflowDefinition with phases resolved by capability.

This module is the implementation of Issue #65: making CapabilityRegistry
the single source of truth across both orchestration paradigms.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentRegistration,
)
from argumentation_analysis.orchestration.workflow_dsl import (
    PhaseResult,
    PhaseStatus,
    WorkflowBuilder,
    WorkflowDefinition,
    WorkflowExecutor,
)
from argumentation_analysis.orchestration.turn_protocol import (
    TurnResult,
    TurnStrategy,
)

logger = logging.getLogger("HierarchyBridge")


# ---------------------------------------------------------------------------
# 1. RegistryBackedOperationalRegistry
# ---------------------------------------------------------------------------


class RegistryBackedOperationalRegistry:
    """
    Adapter bridging OperationalAgentRegistry interface with CapabilityRegistry.

    The hierarchical tactical layer discovers agents by *capability name*
    (e.g. "text_extraction", "fallacy_detection"). This class provides
    that discovery through the CapabilityRegistry instead of the hardcoded
    agent_classes dict in OperationalAgentRegistry.

    Usage:
        cap_registry = setup_registry()
        op_registry = RegistryBackedOperationalRegistry(cap_registry)
        provider = op_registry.find_for_capability("fallacy_detection")
        if provider:
            result = await provider.invoke(text, context)
    """

    def __init__(self, capability_registry: CapabilityRegistry):
        self._registry = capability_registry

    # --- Discovery ---

    def find_for_capability(
        self, capability: str
    ) -> Optional[ComponentRegistration]:
        """Find the best component providing a capability.

        Returns the first registered provider (any type) or None.
        """
        providers = self._registry.find_for_capability(capability)
        return providers[0] if providers else None

    def find_all_for_capability(
        self, capability: str
    ) -> List[ComponentRegistration]:
        """Find all components providing a capability."""
        return self._registry.find_for_capability(capability)

    def get_all_capabilities(self) -> List[str]:
        """List all capabilities registered in the underlying registry."""
        return list(self._registry._capability_index.keys())

    def has_capability(self, capability: str) -> bool:
        """Check whether at least one provider exists for a capability."""
        return len(self._registry.find_for_capability(capability)) > 0

    # --- Task dispatch ---

    async def invoke_capability(
        self,
        capability: str,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        """
        Invoke the best available provider for a capability.

        Returns None if no provider exists or if the provider has no invoke.
        """
        provider = self.find_for_capability(capability)
        if provider is None:
            logger.warning(f"No provider for capability '{capability}'")
            return None
        if provider.invoke is None:
            logger.warning(
                f"Provider '{provider.name}' for '{capability}' has no invoke"
            )
            return None
        return await provider.invoke(input_data, context or {})

    # --- Mapping from legacy capabilities to registry ---

    def map_agent_capabilities(
        self, legacy_capabilities: Dict[str, List[str]]
    ) -> Dict[str, List[ComponentRegistration]]:
        """
        Map a legacy agent_capabilities dict to registry-backed providers.

        Args:
            legacy_capabilities: e.g. {"informal_analyzer": ["argument_identification", ...]}

        Returns:
            Dict mapping legacy agent names to their registry-backed providers.
        """
        mapping: Dict[str, List[ComponentRegistration]] = {}
        for agent_name, caps in legacy_capabilities.items():
            providers = []
            for cap in caps:
                found = self._registry.find_for_capability(cap)
                providers.extend(found)
            # Deduplicate by name
            seen = set()
            unique = []
            for p in providers:
                if p.name not in seen:
                    seen.add(p.name)
                    unique.append(p)
            mapping[agent_name] = unique
        return mapping

    def select_agent_for_task(
        self, required_capabilities: List[str]
    ) -> Optional[ComponentRegistration]:
        """
        Select the best agent for a task given required capabilities.

        Scores each provider by how many of the required capabilities it covers.
        """
        if not required_capabilities:
            return None

        scores: Dict[str, int] = {}
        providers_by_name: Dict[str, ComponentRegistration] = {}

        for cap in required_capabilities:
            for provider in self._registry.find_for_capability(cap):
                scores[provider.name] = scores.get(provider.name, 0) + 1
                providers_by_name[provider.name] = provider

        if not scores:
            return None

        best_name = max(scores, key=scores.get)
        return providers_by_name[best_name]


# ---------------------------------------------------------------------------
# 2. objectives_to_workflow
# ---------------------------------------------------------------------------

# Mapping from strategic objective keywords to Lego capabilities
_OBJECTIVE_CAPABILITY_MAP: Dict[str, List[str]] = {
    "identifier": ["fact_extraction", "text_extraction"],
    "extraire": ["fact_extraction", "text_extraction"],
    "détecter": ["fallacy_detection", "french_fallacy_detection"],
    "sophisme": ["fallacy_detection", "french_fallacy_detection"],
    "analyser": ["formal_logic", "fol_analysis"],
    "structure": ["formal_logic", "fol_analysis"],
    "logique": ["formal_logic", "propositional_logic"],
    "évaluer": ["argument_quality", "coherence_evaluation"],
    "cohérence": ["argument_quality", "coherence_evaluation"],
    "contre-argument": ["counter_argument_generation"],
    "débat": ["debate_management"],
    "gouvernance": ["governance_voting"],
    "qualité": ["argument_quality"],
    "synthétiser": ["synthesis"],
    "synthèse": ["synthesis"],
}


def objectives_to_workflow(
    objectives: List[Dict[str, Any]],
    capability_registry: CapabilityRegistry,
    workflow_name: str = "hierarchical_workflow",
) -> WorkflowDefinition:
    """
    Translate strategic objectives into a WorkflowDefinition.

    Maps objective descriptions to available capabilities in the registry,
    creating phases that will be resolved at execution time.

    Args:
        objectives: Strategic objectives (each with 'id', 'description', 'priority').
        capability_registry: The capability registry for validating capabilities.
        workflow_name: Name for the resulting workflow.

    Returns:
        A WorkflowDefinition ready for execution via WorkflowExecutor.
    """
    builder = WorkflowBuilder(workflow_name)
    previous_phase: Optional[str] = None

    for objective in objectives:
        obj_id = objective.get("id", "unknown")
        description = objective.get("description", "").lower()
        priority = objective.get("priority", "medium")

        # Find matching capabilities from description keywords
        matched_capabilities = _match_capabilities(
            description, capability_registry
        )

        if not matched_capabilities:
            logger.warning(
                f"Objective '{obj_id}' matched no available capabilities "
                f"— adding as optional phase"
            )
            # Add as optional phase with a generic capability name
            phase_name = f"phase_{obj_id}"
            builder.add_phase(
                name=phase_name,
                capability=f"objective_{obj_id}",
                optional=True,
                depends_on=[previous_phase] if previous_phase else None,
                parameters={"objective": objective},
            )
            previous_phase = phase_name
            continue

        # Create a phase for each matched capability
        for i, capability in enumerate(matched_capabilities):
            phase_name = f"phase_{obj_id}_{capability}"
            builder.add_phase(
                name=phase_name,
                capability=capability,
                optional=(priority == "low"),
                depends_on=[previous_phase] if previous_phase else None,
                parameters={"objective": objective},
            )
            previous_phase = phase_name

    builder.set_metadata("source", "hierarchical_bridge")
    builder.set_metadata("objective_count", len(objectives))

    return builder.build()


def _match_capabilities(
    description: str,
    capability_registry: CapabilityRegistry,
) -> List[str]:
    """
    Match a text description to available capabilities.

    Returns unique capabilities found in the registry, ordered by specificity.
    """
    candidates: List[str] = []
    for keyword, caps in _OBJECTIVE_CAPABILITY_MAP.items():
        if keyword in description:
            candidates.extend(caps)

    # Deduplicate while preserving order
    seen: set = set()
    unique: List[str] = []
    for cap in candidates:
        if cap not in seen:
            seen.add(cap)
            # Only include if the registry has a provider
            if capability_registry.find_for_capability(cap):
                unique.append(cap)

    return unique


# ---------------------------------------------------------------------------
# 3. HierarchicalTurnStrategy
# ---------------------------------------------------------------------------


class HierarchicalTurnStrategy(TurnStrategy):
    """
    Wraps the hierarchical (Strategic→Tactical→Operational) system as a
    pluggable TurnStrategy for ConversationalPipeline.

    Each turn:
    1. Translates objectives into a WorkflowDefinition (via objectives_to_workflow)
    2. Executes the workflow using WorkflowExecutor (backed by CapabilityRegistry)
    3. Aggregates results into a TurnResult

    This unifies the hierarchical planning with Lego execution, allowing
    both paradigms to coexist within the same ConversationalPipeline.

    Usage:
        strategy = HierarchicalTurnStrategy(
            objectives=objectives,
            capability_registry=registry,
        )
        pipeline = ConversationalPipeline(strategy, config=config)
        result = await pipeline.execute(input_text)
    """

    def __init__(
        self,
        objectives: List[Dict[str, Any]],
        capability_registry: CapabilityRegistry,
        state_writers: Optional[Dict[str, Any]] = None,
    ):
        self._objectives = objectives
        self._registry = capability_registry
        self._executor = WorkflowExecutor(capability_registry)
        self._state_writers = state_writers

    async def execute_turn(
        self,
        input_data: Any,
        context: Dict[str, Any],
        state: Optional[Any] = None,
    ) -> TurnResult:
        """Execute one turn: objectives → workflow → results."""
        start = time.time()

        # 1. Build workflow from objectives
        workflow = objectives_to_workflow(
            self._objectives,
            self._registry,
            workflow_name=f"hierarchical_turn_{context.get('turn_number', 1)}",
        )

        # 2. Execute workflow via Lego WorkflowExecutor
        phase_results = await self._executor.execute(
            workflow,
            input_data,
            context=context,
            state=state,
            state_writers=self._state_writers,
        )

        duration = time.time() - start

        # 3. Aggregate into TurnResult
        confidence = _extract_confidence(phase_results)
        has_failures = any(
            r.status == PhaseStatus.FAILED for r in phase_results.values()
        )
        questions = _extract_questions(phase_results)

        return TurnResult(
            turn_number=context.get("turn_number", 1),
            phase_results=phase_results,
            confidence=confidence,
            needs_refinement=has_failures,
            questions_for_user=questions,
            duration_seconds=duration,
        )


# ---------------------------------------------------------------------------
# Shared helpers (same logic as conversational_executor)
# ---------------------------------------------------------------------------


def _extract_confidence(phase_results: Dict[str, PhaseResult]) -> float:
    """Extract average confidence from phase outputs."""
    scores = []
    for result in phase_results.values():
        if result.status == PhaseStatus.COMPLETED and result.output is not None:
            if isinstance(result.output, dict):
                conf = result.output.get("confidence")
                if conf is not None:
                    try:
                        scores.append(float(conf))
                    except (TypeError, ValueError):
                        pass
    return sum(scores) / len(scores) if scores else 0.5


def _extract_questions(phase_results: Dict[str, PhaseResult]) -> List[str]:
    """Extract user questions from phase outputs."""
    questions: List[str] = []
    for result in phase_results.values():
        if result.status == PhaseStatus.COMPLETED and isinstance(
            result.output, dict
        ):
            q = result.output.get("user_question")
            if q and isinstance(q, str):
                questions.append(q)
    return questions
