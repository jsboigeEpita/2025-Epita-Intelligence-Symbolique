"""Tests for BeliefRevisionPlugin wiring in spectacular (#507)."""


class TestBeliefRevisionSpectacularPhase:
    """Verify belief_revision phase exists in spectacular with correct DAG deps."""

    def test_spectacular_has_belief_revision_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        phase = {p.name: p for p in wf.phases}
        assert "belief_revision" in phase
        assert phase["belief_revision"].capability == "belief_revision"
        assert "jtms" in phase["belief_revision"].depends_on
        assert "dung_extensions" in phase["belief_revision"].depends_on
        assert phase["belief_revision"].optional is True

    def test_spectacular_phase_count_with_belief_revision(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        assert len(wf.phases) == 21

    def test_belief_revision_state_writer_exists(self):
        from argumentation_analysis.orchestration.state_writers import (
            CAPABILITY_STATE_WRITERS,
        )

        assert "belief_revision" in CAPABILITY_STATE_WRITERS

    def test_belief_revision_service_in_registry(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry()
        providers = registry.find_for_capability("belief_revision")
        names = [p.name for p in providers]
        assert any("belief_revision" in n for n in names)
        provider = next(p for p in providers if "belief_revision" in p.name)
        assert provider.invoke is not None
