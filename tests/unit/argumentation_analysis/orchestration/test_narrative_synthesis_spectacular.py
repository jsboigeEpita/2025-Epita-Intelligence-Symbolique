"""Tests for narrative_synthesis service registration in spectacular (#503).

The narrative_synthesis phase existed in workflows.py and had a state writer,
but was missing the service registration in registry_setup.py — causing the
phase to be skipped in pipeline mode.
"""

from unittest.mock import MagicMock


class TestNarrativeSynthesisRegistration:
    """Verify narrative_synthesis service is properly registered."""

    def test_narrative_synthesis_service_in_registry(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry()
        providers = registry.find_for_capability("narrative_synthesis")
        names = [p.name for p in providers]
        assert "narrative_synthesis_service" in names
        provider = next(p for p in providers if p.name == "narrative_synthesis_service")
        assert provider.invoke is not None

    def test_narrative_synthesis_state_writer_registered(self):
        from argumentation_analysis.orchestration.state_writers import (
            CAPABILITY_STATE_WRITERS,
        )

        assert "narrative_synthesis" in CAPABILITY_STATE_WRITERS

    def test_write_narrative_synthesis_to_state(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_narrative_synthesis_to_state,
        )

        state = MagicMock()
        output = {
            "narrative": "The argument demonstrates strong logical coherence.",
            "paragraph_count": 1,
            "referenced_fields": 3,
        }
        _write_narrative_synthesis_to_state(output, state, {})
        assert state.narrative_synthesis == (
            "The argument demonstrates strong logical coherence."
        )

    def test_write_narrative_synthesis_empty_output(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_narrative_synthesis_to_state,
        )

        state = MagicMock()
        # Empty output should not raise and should not set narrative_synthesis
        _write_narrative_synthesis_to_state({}, state, {})
        # MagicMock creates phantom attrs, so just verify no string was assigned
        assert not isinstance(getattr(state, "narrative_synthesis", ""), str)

    def test_spectacular_has_narrative_synthesis_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        phase = {p.name: p for p in wf.phases}
        assert "narrative_synthesis" in phase
        assert phase["narrative_synthesis"].capability == "narrative_synthesis"
        deps = phase["narrative_synthesis"].depends_on
        assert "quality" in deps
        assert "jtms" in deps
        assert "atms" in deps
        assert "dung_extensions" in deps
        assert phase["narrative_synthesis"].optional is True
