"""#1735 T1 — the conversational PM's capability map is DERIVED from the
CapabilityRegistry, not hand-written.

The TODO deleted by ``233a11a8`` asked for exactly this transplant
(RegistryBackedOperationalRegistry pattern, hierarchy_bridge.py:45): the PM
prompt's ``{capability_map}`` placeholder is rendered at build time from
``registry.get_all_registrations()``. Consequences guarded here:

* hors-cascade axes (aspic_plus_reasoning, sat_solving, ...) — registered
  capabilities the hand-written map never named — appear in the PM's map;
* a capability registered at RUNTIME (fresh registry instance) reaches the
  PM instructions of a build — the derivation is live, not a frozen copy;
* the room truth (#1760) composes with the derived map — no regression of
  the steering couple while its knowledge source changes.
"""

from unittest.mock import MagicMock, patch, create_autospec

import pytest

from semantic_kernel import Kernel

from argumentation_analysis.core.shared_state import RhetoricalAnalysisState

SAMPLE_TEXT = "Le ministre affirme que X donc Y, mais la commission doute."


class _Registration:
    def __init__(self, name, capabilities, description=""):
        self.name = name
        self.component_type = "agent"
        self.capabilities = list(capabilities)
        self.metadata = {"description": description} if description else {}


class _FakeRegistry:
    """Minimal CapabilityRegistry duck-type: get_all_registrations()."""

    def __init__(self, registrations):
        self._regs = list(registrations)

    def get_all_registrations(self, component_type=None):
        return list(self._regs)


def _runtime_registry():
    """A registry carrying a capability registered at 'runtime' — one the
    static setup could never have known: the né-rouge witness for liveness."""
    return _FakeRegistry(
        [
            _Registration(
                "logic_plugin",
                ["propositional_reasoning", "formal_quantum_axis"],
            ),
            _Registration("jtms_service", ["belief_maintenance"]),
            _Registration("quality_evaluator", ["argument_quality"]),
        ]
    )


@pytest.fixture
def state():
    return RhetoricalAnalysisState(SAMPLE_TEXT)


@pytest.fixture
def mock_kernel():
    kernel = create_autospec(Kernel, instance=True)
    kernel.get_service.return_value = MagicMock()
    return kernel


class TestDerivedMap:
    def test_derive_function_exists_and_names_the_registry(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            derive_pm_capability_map,
        )
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        rendered = derive_pm_capability_map(setup_registry())
        assert "derivee du CapabilityRegistry" in rendered

    def test_hors_cascade_axes_appear(self):
        """DoD T1: registered formal axes outside the prescribed cascade —
        invisible to the hand-written map — are now PM-visible."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            derive_pm_capability_map,
        )
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        rendered = derive_pm_capability_map(setup_registry())
        assert "aspic_plus_reasoning" in rendered, (
            "the aspic axis is a registered capability but the derived map "
            "does not surface it"
        )
        assert "sat_solving" in rendered

    def test_runtime_registered_capability_reaches_the_map(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            derive_pm_capability_map,
        )

        rendered = derive_pm_capability_map(_runtime_registry())
        formal_line = next(
            line for line in rendered.splitlines() if line.startswith("- FormalAgent")
        )
        assert "formal_quantum_axis" in formal_line, (
            "a capability registered at runtime did not reach the PM's map — "
            "the derivation is not live"
        )
        # transverse line for the JTMS service, not a specialist slot
        assert "belief_maintenance" in rendered
        assert "JTMS" in rendered

    def test_every_specialist_keeps_a_line(self):
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            AGENT_CONFIG,
            derive_pm_capability_map,
        )

        rendered = derive_pm_capability_map(_runtime_registry())
        for name in AGENT_CONFIG:
            if name == "ProjectManager":
                continue
            assert f"- {name}" in rendered, f"{name} lost its capability line"


class TestExplicitRegistryIsNotCached:
    def test_get_capability_map_rerenders_explicit_registries(self):
        """Two different explicit registries must yield two different maps —
        an explicit registry never reads the module-level cache."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _get_capability_map,
        )

        first = _get_capability_map(_runtime_registry())
        assert "formal_quantum_axis" in first
        second = _get_capability_map(
            _FakeRegistry([_Registration("lone", ["argument_quality"])])
        )
        assert "formal_quantum_axis" not in second
        assert "argument_quality" in second


class TestBuildCarriesDerivedMap:
    def test_create_agents_pm_instructions_carry_the_derived_map(
        self, mock_kernel, state
    ):
        """DoD garde né-rouge: a PM built with an injected registry carries
        the runtime capability in its instructions."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            create_conversational_agents,
        )

        with patch(
            "argumentation_analysis.orchestration.conversational_orchestrator.ChatCompletionAgent"
        ) as MockAgent, patch(
            "argumentation_analysis.agents.factory.get_plugin_instances",
            return_value=[MagicMock()],
        ):
            MockAgent.return_value = MagicMock()
            create_conversational_agents(
                mock_kernel,
                state,
                "test_llm",
                agent_names=["ProjectManager"],
                capability_registry=_runtime_registry(),
            )
            instructions = MockAgent.call_args[1]["instructions"]
        assert "formal_quantum_axis" in instructions
        assert "CARTE DES CAPACITES" in instructions

    def test_room_truth_composes_with_derived_map(self):
        """#1760 non-regression: the room section and the derived map coexist
        in the phase-entry PM instructions."""
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            _pm_instructions_with_room,
        )

        instructions = _pm_instructions_with_room(
            30,
            ["ProjectManager", "FormalAgent", "QualityAgent"],
            capability_registry=_runtime_registry(),
        )
        assert "SALLE ACTUELLE" in instructions
        assert "formal_quantum_axis" in instructions
        assert "{capability_map}" not in instructions
