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
        # The workflow grew from 21 to 31 phases over #504/#506/#507/#508/#534/
        # Epic #1134 (3 acts + deep_synthesis + stakes + kb pipeline + solvers).
        # A fixed exact count is fragile test-debt; assert load-bearing invariants
        # instead: the synthesis chain is present and the mandatory acts exist.
        phase_names = {p.name for p in wf.phases}
        assert "synthesis" in phase_names
        assert "deep_synthesis" in phase_names
        assert {"act1_framing", "act2_narrative", "act3_conclusion"} <= phase_names
        assert len(wf.phases) >= 21  # never regresses below the original floor

    def test_deep_synthesis_state_writer_registered(self):
        """D1b (#1167): the deep_synthesis phase must have a state writer, else
        the grounded FB-18 synthesis is dropped and state.narrative_synthesis
        stays empty (Acte III never sees the most global component)."""
        from argumentation_analysis.orchestration.state_writers import (
            CAPABILITY_STATE_WRITERS,
            _write_deep_synthesis_to_state,
        )

        assert "deep_synthesis" in CAPABILITY_STATE_WRITERS
        assert (
            CAPABILITY_STATE_WRITERS["deep_synthesis"]
            is _write_deep_synthesis_to_state
        )

    def test_write_deep_synthesis_populates_narrative(self):
        """D1b (#1167): _write_deep_synthesis_to_state persists grounded_synthesis
        into state.narrative_synthesis (the field Acte III reads)."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_deep_synthesis_to_state,
        )

        state = MagicMock()
        state.narrative_synthesis = ""
        state.workflow_results = {}

        _write_deep_synthesis_to_state(
            {"grounded_synthesis": "Synthèse ancrée avec [artifact:arg_1]."},
            state,
            {},
        )
        assert (
            state.narrative_synthesis
            == "Synthèse ancrée avec [artifact:arg_1]."
        )

    def test_write_deep_synthesis_drops_empty_fail_loud(self):
        """D1b (#1167): empty/unavailable grounded_synthesis is left as the empty
        default — never fabricated (fail-loud, #1108/#1019)."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_deep_synthesis_to_state,
        )

        state = MagicMock()
        state.narrative_synthesis = ""
        _write_deep_synthesis_to_state({"grounded_synthesis": ""}, state, {})
        assert state.narrative_synthesis == ""
        _write_deep_synthesis_to_state({}, state, {})
        assert state.narrative_synthesis == ""

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
