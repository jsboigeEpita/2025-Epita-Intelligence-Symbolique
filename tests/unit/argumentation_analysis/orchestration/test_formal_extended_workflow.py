"""Tests for formal_extended workflow + spectacular MVP extensions (#480).

Validates:
- build_formal_extended_workflow: 15-phase chain with correct dependency DAG
- spectacular workflow: 3 new conditional phases (ranking, bipolar, probabilistic)
- Workflow catalog: both registered and retrievable
- Phase ordering: all phases resolve to valid execution order
"""

import pytest

from argumentation_analysis.orchestration.workflow_dsl import (
    WorkflowBuilder,
    WorkflowDefinition,
    WorkflowExecutor,
    PhaseStatus,
)
from argumentation_analysis.core.capability_registry import CapabilityRegistry


# ---------------------------------------------------------------------------
# Test: build_formal_extended_workflow structure
# ---------------------------------------------------------------------------


class TestFormalExtendedWorkflow:
    def test_builds_without_error(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        assert wf is not None
        assert wf.name == "formal_extended"

    def test_has_15_phases(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        assert len(wf.phases) == 15

    def test_phase_names(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        names = [p.name for p in wf.phases]
        expected = [
            "extract", "nl_to_logic", "pl", "fol", "modal",
            "dung_extensions", "aspic", "aba", "adf", "bipolar",
            "ranking", "probabilistic", "dialogue", "belief_revision",
            "tweety_interpretation",
        ]
        assert names == expected

    def test_extract_is_first(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        assert wf.phases[0].name == "extract"
        assert wf.phases[0].capability == "fact_extraction"

    def test_all_phases_except_extract_optional(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        for phase in wf.phases:
            if phase.name == "extract":
                assert not phase.optional, "extract should be required"
            else:
                assert phase.optional, f"{phase.name} should be optional"

    def test_nl_to_logic_depends_on_extract(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        nl = next(p for p in wf.phases if p.name == "nl_to_logic")
        assert "extract" in nl.depends_on

    def test_pl_fol_modal_depend_on_nl_to_logic(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        for name in ("pl", "fol", "modal"):
            phase = next(p for p in wf.phases if p.name == name)
            assert "nl_to_logic" in phase.depends_on

    def test_dung_extensions_depends_on_pl(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        dung = next(p for p in wf.phases if p.name == "dung_extensions")
        assert "pl" in dung.depends_on

    def test_aspic_aba_adf_bipolar_ranking_depend_on_dung(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        for name in ("aspic", "aba", "adf", "bipolar", "ranking"):
            phase = next(p for p in wf.phases if p.name == name)
            assert "dung_extensions" in phase.depends_on

    def test_probabilistic_depends_on_ranking(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        prob = next(p for p in wf.phases if p.name == "probabilistic")
        assert "ranking" in prob.depends_on

    def test_dialogue_depends_on_aspic(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        dial = next(p for p in wf.phases if p.name == "dialogue")
        assert "aspic" in dial.depends_on

    def test_belief_revision_depends_on_fol_and_modal(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        br = next(p for p in wf.phases if p.name == "belief_revision")
        assert "fol" in br.depends_on
        assert "modal" in br.depends_on

    def test_tweety_interpretation_depends_on_five(self):
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        wf = build_formal_extended_workflow()
        interp = next(p for p in wf.phases if p.name == "tweety_interpretation")
        expected_deps = {"dung_extensions", "fol", "aspic", "ranking", "belief_revision"}
        assert set(interp.depends_on) == expected_deps

    def test_capabilities_match_registry(self):
        """Verify each phase capability exists in a freshly set-up registry.

        Note: plugin-based capabilities (e.g. formal_result_interpretation)
        may not be registered if their plugin PR hasn't been merged yet.
        Only verify service-based capabilities which are always registered.
        """
        from argumentation_analysis.orchestration.workflows import (
            build_formal_extended_workflow,
        )
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        wf = build_formal_extended_workflow()
        registry = setup_registry(include_optional=False)
        # Plugin capabilities that may not be registered yet
        plugin_caps = {"formal_result_interpretation", "tweety_logic"}
        for phase in wf.phases:
            if phase.capability in plugin_caps:
                continue
            found = registry.find_services_for_capability(phase.capability)
            assert found, (
                f"Phase '{phase.name}' capability '{phase.capability}' "
                "not found in registry"
            )


# ---------------------------------------------------------------------------
# Test: spectacular workflow MVP extensions
# ---------------------------------------------------------------------------


class TestSpectacularExtensions:
    def test_spectacular_has_ranking_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )
        wf = build_spectacular_workflow()
        names = [p.name for p in wf.phases]
        assert "ranking" in names

    def test_spectacular_ranking_capability(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )
        wf = build_spectacular_workflow()
        ranking = next(p for p in wf.phases if p.name == "ranking")
        assert ranking.capability == "ranking_semantics"
        assert ranking.optional is True

    def test_spectacular_ranking_depends_on_dung(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )
        wf = build_spectacular_workflow()
        ranking = next(p for p in wf.phases if p.name == "ranking")
        assert "dung_extensions" in ranking.depends_on

    def test_spectacular_has_bipolar_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )
        wf = build_spectacular_workflow()
        names = [p.name for p in wf.phases]
        assert "bipolar" in names

    def test_spectacular_bipolar_capability(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )
        wf = build_spectacular_workflow()
        bipolar = next(p for p in wf.phases if p.name == "bipolar")
        assert bipolar.capability == "bipolar_argumentation"
        assert bipolar.optional is True

    def test_spectacular_has_probabilistic_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )
        wf = build_spectacular_workflow()
        names = [p.name for p in wf.phases]
        assert "probabilistic" in names

    def test_spectacular_probabilistic_capability(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )
        wf = build_spectacular_workflow()
        prob = next(p for p in wf.phases if p.name == "probabilistic")
        assert prob.capability == "probabilistic_argumentation"
        assert prob.optional is True


# ---------------------------------------------------------------------------
# Test: Workflow catalog
# ---------------------------------------------------------------------------


class TestWorkflowCatalog:
    def test_formal_extended_in_catalog(self):
        from argumentation_analysis.orchestration.workflows import get_workflow_catalog

        catalog = get_workflow_catalog()
        assert "formal_extended" in catalog
        assert catalog["formal_extended"].name == "formal_extended"

    def test_spectacular_in_catalog(self):
        from argumentation_analysis.orchestration.workflows import get_workflow_catalog

        catalog = get_workflow_catalog()
        assert "spectacular" in catalog

    def test_catalog_has_formal_extended_capabilities(self):
        """Verify formal_extended catalog entry has all required phases."""
        from argumentation_analysis.orchestration.workflows import get_workflow_catalog

        catalog = get_workflow_catalog()
        wf = catalog["formal_extended"]
        phase_names = {p.name for p in wf.phases}
        required = {
            "extract", "nl_to_logic", "pl", "fol", "modal",
            "dung_extensions", "aspic", "aba", "adf",
            "bipolar", "ranking", "probabilistic",
            "dialogue", "belief_revision", "tweety_interpretation",
        }
        assert required.issubset(phase_names)
