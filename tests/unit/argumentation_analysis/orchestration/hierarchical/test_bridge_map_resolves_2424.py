"""The bridge map routes objectives to capabilities the registry serves (#2424).

In hierarchical ``bridge`` mode, ``objectives_to_workflow`` turns each
strategic objective into phases through the keywords of
``_OBJECTIVE_CAPABILITY_MAP``. The map was written in the hierarchy's own
vocabulary: 8 of its 13 capability names had no provider, and
``_match_capabilities`` dropped them without a trace. The third default
objective asked for first-order analysis through two of its keywords and got
propositional logic only; an objective about debate, governance or synthesis
matched nothing and became an optional ``objective_<id>`` phase that no
provider serves.

Measured through ``objectives_to_workflow`` against ``setup_registry()``, the
registry the hierarchical orchestrator builds, not by reading the map. The
table-level guard (every name any capability table demands has a provider)
lives in ``test_one_capability_surface_1842.py``.
"""

import pytest

from argumentation_analysis.core.capability_registry import (
    CapabilityRegistry,
    ComponentType,
)
from argumentation_analysis.orchestration.hierarchical.hierarchy_bridge import (
    objectives_to_workflow,
)
from argumentation_analysis.orchestration.hierarchical.orchestrator import (
    HierarchicalOrchestrator,
)
from argumentation_analysis.orchestration.hierarchical.strategic.manager import (
    StrategicManager,
)
from argumentation_analysis.orchestration.registry_setup import setup_registry


@pytest.fixture(scope="module")
def registry():
    # Same call as production (``orchestrator.py``: ``setup_registry()``).
    return setup_registry()


def _default_objectives():
    # The objectives the manager falls back to; the orchestrator uses the same
    # four descriptions when the manager returns none.
    return StrategicManager()._fallback_objectives()


def _capabilities_of(workflow, objective_id):
    return [
        phase.capability
        for phase in workflow.phases
        if phase.parameters["objective"]["id"] == objective_id
    ]


def test_default_objectives_ask_only_for_served_capabilities(registry):
    workflow = objectives_to_workflow(_default_objectives(), registry)
    assert workflow.metadata["unresolved_capabilities"] == {}
    placeholders = [
        p.capability for p in workflow.phases if p.capability.startswith("objective_")
    ]
    assert placeholders == []


def test_the_logical_structure_objective_reaches_first_order_logic(registry):
    """obj-3 "Analyser la structure logique" asks for FOL through ``analyser``,
    ``structure`` and ``logique``; on ``main`` it got propositional logic only."""
    workflow = objectives_to_workflow(_default_objectives(), registry)
    assert _capabilities_of(workflow, "obj-3") == [
        "fol_reasoning",
        "propositional_logic",
    ]
    assert registry.find_for_capability("fol_reasoning")


@pytest.mark.parametrize(
    "description, capability, provider",
    [
        ("Organiser un débat contradictoire", "adversarial_debate", "debate_agent"),
        (
            "Simuler la gouvernance du groupe",
            "governance_simulation",
            "governance_agent",
        ),
        (
            "Produire une synthèse des résultats",
            "deep_synthesis",
            "deep_synthesis_service",
        ),
    ],
)
def test_specialist_objectives_reach_their_specialist(
    registry, description, capability, provider
):
    objective = {"id": "obj-s", "description": description, "priority": "medium"}
    workflow = objectives_to_workflow([objective], registry)
    assert _capabilities_of(workflow, "obj-s") == [capability]
    assert provider in {p.name for p in registry.find_for_capability(capability)}
    assert workflow.metadata["unresolved_capabilities"] == {}


def _registry_serving(*capabilities):
    async def _invoke(*args, **kwargs):
        return {"ok": True}

    registry = CapabilityRegistry()
    registry.register(
        name="stub_provider",
        component_type=ComponentType.AGENT,
        capabilities=list(capabilities),
        invoke=_invoke,
        metadata={},
    )
    return registry


def test_an_unserved_capability_is_recorded_in_the_workflow():
    """What the registry cannot serve is metadata, not only a log line."""
    objectives = [
        {
            "id": "o1",
            "description": "Analyser la structure et détecter les sophismes",
            "priority": "high",
        },
        {"id": "o2", "description": "Organiser un débat", "priority": "medium"},
    ]
    workflow = objectives_to_workflow(
        objectives, _registry_serving("fallacy_detection")
    )
    assert workflow.metadata["unresolved_capabilities"] == {
        "o1": ["fol_reasoning"],
        "o2": ["adversarial_debate"],
    }
    assert _capabilities_of(workflow, "o1") == ["fallacy_detection"]
    # o2 resolved nothing: it still becomes the optional placeholder phase.
    assert _capabilities_of(workflow, "o2") == ["objective_o2"]


async def test_the_orchestrator_result_carries_the_unserved_capabilities():
    """The metadata has a reader: the bridge-mode result exposes it."""
    orchestrator = HierarchicalOrchestrator(
        capability_registry=_registry_serving("fallacy_detection")
    )
    result = await orchestrator.analyze("Un texte court. Donc il faut agir.")
    # No kernel: the manager falls back to its four default objectives.
    assert [o["id"] for o in result["objectives"]] == [
        "obj-1",
        "obj-2",
        "obj-3",
        "obj-4",
    ]
    assert result["unresolved_capabilities"] == {
        "obj-1": ["fact_extraction"],
        "obj-3": ["fol_reasoning", "propositional_logic"],
        "obj-4": ["argument_quality"],
    }
