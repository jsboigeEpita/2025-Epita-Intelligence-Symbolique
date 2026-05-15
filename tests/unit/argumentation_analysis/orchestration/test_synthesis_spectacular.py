"""Tests for synthesis phase wiring in spectacular (#508)."""

from unittest.mock import MagicMock


class TestSynthesisSpectacularPhase:
    """Verify synthesis phase exists in spectacular with correct DAG deps."""

    def test_spectacular_has_synthesis_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        phase = {p.name: p for p in wf.phases}
        assert "synthesis" in phase
        assert phase["synthesis"].capability == "analysis_synthesis"
        deps = phase["synthesis"].depends_on
        assert "quality" in deps
        assert "counter" in deps
        assert "debate" in deps
        assert "governance" in deps
        assert "formal_synthesis" in deps
        assert phase["synthesis"].optional is True

    def test_spectacular_phase_count_with_synthesis(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        assert len(wf.phases) == 21

    def test_analysis_synthesis_state_writer_registered(self):
        from argumentation_analysis.orchestration.state_writers import (
            CAPABILITY_STATE_WRITERS,
        )

        assert "analysis_synthesis" in CAPABILITY_STATE_WRITERS

    def test_analysis_synthesis_service_in_registry(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry()
        providers = registry.find_for_capability("analysis_synthesis")
        names = [p.name for p in providers]
        assert "analysis_synthesis_service" in names
        provider = next(p for p in providers if p.name == "analysis_synthesis_service")
        assert provider.invoke is not None

    def test_write_analysis_synthesis_to_state(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_analysis_synthesis_to_state,
        )

        state = MagicMock()
        output = {
            "synthesis": {
                "quality": {"evaluated": 3},
                "fallacies": {"count": 2},
            },
            "phase_count": 5,
            "overall_completeness": 0.8,
        }
        _write_analysis_synthesis_to_state(output, state, {})
        assert state.analysis_synthesis["phase_count"] == 5
        assert state.analysis_synthesis["overall_completeness"] == 0.8
