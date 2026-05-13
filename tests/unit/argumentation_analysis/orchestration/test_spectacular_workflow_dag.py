"""Unit tests for the spectacular workflow DAG structure.

Validates that build_spectacular_workflow() produces a well-formed DAG
with all expected phases, capabilities, and dependency chains (#347).
"""

import pytest

from argumentation_analysis.orchestration.workflows import (
    build_spectacular_workflow,
    reset_workflow_catalog,
)


@pytest.fixture(autouse=True)
def _reset_catalog():
    reset_workflow_catalog()
    yield
    reset_workflow_catalog()


class TestSpectacularWorkflowDAG:
    """Validate the spectacular workflow structure."""

    def test_workflow_builds_without_error(self):
        wf = build_spectacular_workflow()
        assert wf is not None
        assert wf.name == "spectacular_analysis"

    def test_phase_count(self):
        wf = build_spectacular_workflow()
        assert len(wf.phases) == 17

    def test_all_expected_phases_present(self):
        wf = build_spectacular_workflow()
        phase_names = {p.name for p in wf.phases}
        expected = {
            "extract",
            "quality",
            "nl_to_logic",
            "neural_detect",
            "hierarchical_fallacy",
            "pl",
            "fol",
            "modal",
            "dung_extensions",
            "aspic_analysis",
            "counter",
            "jtms",
            "debate",
            "atms",
            "governance",
            "formal_synthesis",
            "narrative_synthesis",
        }
        assert expected == phase_names

    def test_all_capabilities_unique(self):
        wf = build_spectacular_workflow()
        caps = [p.capability for p in wf.phases]
        assert len(caps) == len(set(caps)), f"Duplicate capabilities: {caps}"

    def test_dag_validates(self):
        wf = build_spectacular_workflow()
        errors = wf.validate()
        assert errors == [], f"DAG validation errors: {errors}"

    def test_execution_order_resolvable(self):
        wf = build_spectacular_workflow()
        levels = wf.get_execution_order()
        assert len(levels) >= 2
        all_phases = {name for level in levels for name in level}
        assert len(all_phases) == len(wf.phases)

    def test_extract_is_first_phase(self):
        wf = build_spectacular_workflow()
        levels = wf.get_execution_order()
        assert "extract" in levels[0]
        assert len(levels[0]) == 1  # extract is sole entry point

    def test_formal_logic_depends_on_nl_to_logic(self):
        wf = build_spectacular_workflow()
        for name in ("pl", "fol", "modal"):
            phase = wf.get_phase(name)
            assert "nl_to_logic" in phase.depends_on

    def test_dung_depends_on_fallacy_and_pl(self):
        wf = build_spectacular_workflow()
        phase = wf.get_phase("dung_extensions")
        assert "hierarchical_fallacy" in phase.depends_on
        assert "pl" in phase.depends_on

    def test_atms_depends_on_jtms(self):
        wf = build_spectacular_workflow()
        phase = wf.get_phase("atms")
        assert "jtms" in phase.depends_on

    def test_formal_synthesis_aggregates(self):
        wf = build_spectacular_workflow()
        phase = wf.get_phase("formal_synthesis")
        assert "fol" in phase.depends_on
        assert "modal" in phase.depends_on
        assert "aspic_analysis" in phase.depends_on

    def test_catalog_includes_spectacular(self):
        from argumentation_analysis.orchestration.workflows import get_workflow_catalog

        catalog = get_workflow_catalog()
        assert "spectacular" in catalog
        assert catalog["spectacular"].name == "spectacular_analysis"

    def test_spectacular_has_more_phases_than_standard(self):
        from argumentation_analysis.orchestration.workflows import (
            build_standard_workflow,
        )

        standard = build_standard_workflow()
        spectacular = build_spectacular_workflow()
        assert len(spectacular.phases) > len(standard.phases)

    def test_spectacular_includes_modal_logic(self):
        wf = build_spectacular_workflow()
        caps = wf.get_required_capabilities()
        assert "modal_logic" in caps

    def test_spectacular_includes_atms(self):
        wf = build_spectacular_workflow()
        caps = wf.get_required_capabilities()
        assert "atms_reasoning" in caps
