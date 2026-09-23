"""Every capability the tactical tier emits resolves to a registry provider (#2345).

The tactical coordinator names its tasks' capabilities in a legacy vocabulary
(``TACTICAL_AGENT_CAPABILITIES``); delegation mode translates them to registry
names (``LEGACY_TO_REGISTRY_CAPABILITY``) at the lookup seam. Nothing held that
translation to the registry: #1842 removed the only provider of
``argument_parsing`` -- the translation of ``argument_identification`` -- and
every "Identifier les arguments" task failed with
``no_provider_for_required_capabilities`` from then on, while the band test's
``>= 4 of 5 completed`` tolerance stayed green.

The resolution below goes through ``resolve_registry_capability``, the one
reader the executor uses, against the registry production builds.
"""

import ast
import inspect
import textwrap

import pytest

from argumentation_analysis.orchestration.hierarchical import delegation_orchestrator
from argumentation_analysis.orchestration.hierarchical.delegation_orchestrator import (
    LEGACY_TO_REGISTRY_CAPABILITY,
    make_registry_operational_executor,
    resolve_registry_capability,
)
from argumentation_analysis.orchestration.hierarchical.hierarchy_bridge import (
    RegistryBackedOperationalRegistry,
)
from argumentation_analysis.orchestration.hierarchical.tactical.coordinator import (
    TACTICAL_AGENT_CAPABILITIES,
    TaskCoordinator,
)
from argumentation_analysis.orchestration.registry_setup import setup_registry

# Table entries the tactical tier never emits and that no provider serves.
# Named, so the set cannot grow in silence: a new unresolved entry reddens
# ``test_unresolved_table_entries_are_exactly_the_named_gaps``.
# ``summary_generation`` left the set when its translation moved from the
# provider-less ``synthesis`` to ``deep_synthesis`` (#2424).
KNOWN_UNRESOLVED = {"argument_visualization"}


def _emitted_capabilities() -> set:
    """Every literal of a ``required_capabilities`` list in the decomposition."""
    tree = ast.parse(
        textwrap.dedent(
            inspect.getsource(TaskCoordinator._decompose_objective_to_tasks)
        )
    )
    caps = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if (
                isinstance(key, ast.Constant)
                and key.value == "required_capabilities"
                and isinstance(value, ast.List)
            ):
                caps.update(e.value for e in value.elts if isinstance(e, ast.Constant))
    return caps


EMITTED = sorted(_emitted_capabilities())
TABLE = {cap for caps in TACTICAL_AGENT_CAPABILITIES.values() for cap in caps}


@pytest.fixture(scope="module")
def capability_registry():
    # Same call as production (``orchestrator.py``: ``setup_registry()``).
    return setup_registry()


@pytest.fixture(scope="module")
def op_registry(capability_registry):
    return RegistryBackedOperationalRegistry(capability_registry)


def test_the_decomposition_emits_capabilities():
    # Non-vacuity: three branches of the decomposition name a capability.
    assert len(EMITTED) >= 3, EMITTED


def test_emitted_capabilities_are_in_the_table():
    assert set(EMITTED) <= TABLE, sorted(set(EMITTED) - TABLE)


def test_translation_keys_are_tactical_capabilities():
    assert set(LEGACY_TO_REGISTRY_CAPABILITY) <= TABLE, sorted(
        set(LEGACY_TO_REGISTRY_CAPABILITY) - TABLE
    )


@pytest.mark.parametrize("capability", EMITTED)
def test_every_emitted_capability_resolves(capability, op_registry):
    chosen = resolve_registry_capability([capability], op_registry)
    assert chosen is not None, (
        f"{capability!r} is emitted by the tactical tier but resolves to no "
        f"provider (translation: {LEGACY_TO_REGISTRY_CAPABILITY.get(capability)!r})"
    )


def test_unresolved_table_entries_are_exactly_the_named_gaps(op_registry):
    unresolved = {
        cap for cap in TABLE if resolve_registry_capability([cap], op_registry) is None
    }
    assert unresolved == KNOWN_UNRESOLVED


async def test_the_executor_routes_through_the_one_resolver(
    capability_registry, monkeypatch
):
    # The guard above measures production only if the executor reads the same
    # resolver: make it answer None, and the executor must report the failure.
    calls = []

    def refuse(required, op_registry):
        calls.append(list(required))
        return None

    monkeypatch.setattr(delegation_orchestrator, "resolve_registry_capability", refuse)
    executor = make_registry_operational_executor(capability_registry)
    result = await executor(
        {"tactical_task_id": "t1", "required_capabilities": ["fallacy_detection"]}
    )
    assert calls == [["fallacy_detection"]]
    assert result["status"] == "failed"
    assert result["reason"] == "no_provider_for_required_capabilities"
