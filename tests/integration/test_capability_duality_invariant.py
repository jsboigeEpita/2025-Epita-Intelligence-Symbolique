"""Capability duality invariant test.

Ensures that no capability silently diverges between the @kernel_function
path (SK plugins) and the _invoke_* callable path (pipeline).  When both
exist for the same capability, the duality must be explicitly documented.

See docs/architecture/CAPABILITY_DUALITY.md for the accepted dualities.
"""

import pytest
from argumentation_analysis.core.capability_registry import CapabilityRegistry
from argumentation_analysis.orchestration.registry_setup import setup_registry

# ---------------------------------------------------------------------------
# Accepted dualities — capabilities that intentionally have both a plugin
# (kernel_function) and an invoke callable.  Each entry maps a capability
# name to a short rationale.
#
# NOTE (Epic G pre-wiring): Most dualities are listed as PENDING because
# the SK plugins are not yet wired into CapabilityRegistry (G.1 #468).
# Once G.1 lands, these will become real dualities enforced by
# test_dual_capabilities_are_documented.
# ---------------------------------------------------------------------------

ACCEPTED_DUALITIES: dict[str, str] = {
    "argument_quality": "QualityScoringPlugin wraps ArgumentQualityEvaluator (same backend)",
    "counter_argument_generation": "CounterArgumentAgent @kernel_functions delegate to _invoke_counter_argument",
    "adversarial_debate": "DebateAgent @kernel_functions delegate to _invoke_debate_analysis",
    "governance_simulation": "GovernancePlugin wraps GovernanceAgent (same backend)",
    "belief_maintenance": "JTMSPlugin wraps JTMS core; _invoke_jtms uses same core",
    "atms_reasoning": "ATMSPlugin wraps ATMS core; _invoke_atms uses same core",
    "aspic_plus_reasoning": "ASPICPlugin wraps ASPIC handler; _invoke_aspic uses same handler",
    "ranking_semantics": "RankingPlugin wraps ranking handler; _invoke_ranking uses same handler",
    "dung_extensions": "TweetyLogicPlugin exposes Dung handler; _invoke_dung_extensions uses same",
    "propositional_logic": "TweetyLogicPlugin + LogiqueComplexePlugin; _invoke_propositional_logic same backend",
    "fol_reasoning": "TweetyLogicPlugin; _invoke_fol_reasoning same backend",
    "modal_logic": "TweetyLogicPlugin; _invoke_modal_logic same backend",
    "fact_extraction": "_invoke_fact_extraction callable; potential NL extraction plugin",
    "nl_to_logic_translation": "NLToLogicPlugin @kernel_functions; _invoke_nl_to_logic callable",
    "belief_revision": "BeliefRevisionPlugin; _invoke_belief_revision same backend",
    "neural_fallacy_detection": "FrenchFallacyPlugin wraps detection; _invoke_camembert_fallacy callable",
    "formal_synthesis": "NarrativeSynthesisPlugin; _invoke_formal_synthesis aggregates formal results",
}


@pytest.fixture(scope="module")
def registry():
    """Build a fully populated registry."""
    return setup_registry()


def _get_invoke_capabilities(registry: CapabilityRegistry) -> set[str]:
    """Collect all capabilities served by an _invoke_* callable (any component type)."""
    caps = set()
    for reg in registry.get_all_registrations():
        if reg.invoke is not None:
            caps.update(reg.capabilities)
    return caps


def _get_plugin_capabilities(registry: CapabilityRegistry) -> set[str]:
    """Collect all capabilities served by a registered plugin."""
    caps = set()
    for reg in registry.get_all_registrations():
        # Plugins registered via register_plugin
        from argumentation_analysis.core.capability_registry import ComponentType

        if reg.component_type == ComponentType.PLUGIN:
            caps.update(reg.capabilities)
    return caps


def _get_primary_invoke_capabilities(registry: CapabilityRegistry) -> set[str]:
    """Invoke capabilities that are the primary capability of a service (not
    agent sub-capabilities like 'virtue_detection' or 'debate_scoring')."""
    from argumentation_analysis.orchestration.state_writers import (
        CAPABILITY_STATE_WRITERS,
    )

    invoke_caps = _get_invoke_capabilities(registry)
    # Only include capabilities that have state writers — these are the
    # primary pipeline capabilities. Agent sub-capabilities are secondary.
    return invoke_caps & set(CAPABILITY_STATE_WRITERS.keys())


class TestCapabilityDualityInvariant:
    """Every capability must be provided by either an invoke callable or a
    plugin (or both, if documented).  Undocumented dualities are errors."""

    def test_dual_capabilities_are_documented(self, registry):
        invoke_caps = _get_invoke_capabilities(registry)
        plugin_caps = _get_plugin_capabilities(registry)
        dual = invoke_caps & plugin_caps

        undocumented = dual - set(ACCEPTED_DUALITIES.keys())
        assert not undocumented, (
            f"Undocumented capability dualities found: {sorted(undocumented)}.\n"
            f"Each must be added to ACCEPTED_DUALITIES with a rationale, "
            f"or one implementation path must be removed.\n"
            f"See docs/architecture/CAPABILITY_DUALITY.md for guidance."
        )

    def test_accepted_dualities_still_have_invoke(self, registry):
        """Verify that capabilities in ACCEPTED_DUALITIES still have invoke providers."""
        invoke_caps = _get_invoke_capabilities(registry)
        missing = set(ACCEPTED_DUALITIES.keys()) - invoke_caps
        assert not missing, (
            f"ACCEPTED_DUALITIES entries without invoke providers: "
            f"{sorted(missing)}.\n"
            f"The _invoke_* callable was likely removed or renamed. Update the list."
        )

    def test_spectacular_workflow_capabilities_have_providers(self, registry):
        """Every capability in the spectacular workflow has at least one provider."""
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        all_caps = registry.get_all_capabilities()

        unprovided = []
        for phase in wf.phases:
            if phase.capability not in all_caps and not phase.optional:
                unprovided.append(phase.capability)

        assert (
            not unprovided
        ), f"Required workflow capabilities without providers: {unprovided}"

    def test_primary_invoke_capabilities_cover_workflow(self, registry):
        """Primary pipeline capabilities cover most workflow phases.

        This test catches silent capability removals — if an _invoke_*
        callable or its state writer is deleted without updating the workflow,
        it will surface here.
        """
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        primary = _get_primary_invoke_capabilities(registry)
        wf = build_spectacular_workflow()

        uncovered_optional = []
        for phase in wf.phases:
            if phase.capability not in primary and phase.optional:
                uncovered_optional.append(phase.capability)

        # These are expected to be missing (no invoke or no state writer yet)
        expected_missing = {
            "hierarchical_fallacy_detection",
            "narrative_synthesis",
        }
        actual_missing = set(uncovered_optional) - expected_missing
        assert not actual_missing, (
            f"Optional workflow capabilities unexpectedly without "
            f"primary invoke coverage: {sorted(actual_missing)}.\n"
            f"Either add _invoke_* + state_writer or update expected_missing."
        )
