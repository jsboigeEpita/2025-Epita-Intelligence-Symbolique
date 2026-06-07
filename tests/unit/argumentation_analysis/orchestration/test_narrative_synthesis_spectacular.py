"""Tests for narrative_synthesis service registration in spectacular (#503).

The narrative_synthesis phase existed in workflows.py and had a state writer,
but was missing the service registration in registry_setup.py — causing the
phase to be skipped in pipeline mode.
"""

import pytest
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

    def test_full_has_narrative_synthesis_phase(self):
        """II #698: the sequential `full` path computes convergence in-run too.

        Previously only build_spectacular_workflow ran narrative_synthesis, so
        the `full` path produced no convergence metric in-run. This wires it,
        depending on every phase that populates one of the 5 convergence
        signals.
        """
        from argumentation_analysis.orchestration.workflows import (
            build_full_workflow,
        )

        wf = build_full_workflow()
        phase = {p.name: p for p in wf.phases}
        assert "narrative_synthesis" in phase
        assert phase["narrative_synthesis"].capability == "narrative_synthesis"
        deps = phase["narrative_synthesis"].depends_on
        # All 5 convergence-signal producers must be upstream dependencies.
        for signal_phase in (
            "quality",
            "hierarchical_fallacy",
            "counter",
            "jtms",
            "dung_extensions",
        ):
            assert signal_phase in deps, f"{signal_phase} missing from deps"
        assert phase["narrative_synthesis"].optional is True


class TestNarrativeSynthesisGracefulDegradation:
    """Test narrative synthesis produces non-empty output from context (#994)."""

    @pytest.mark.asyncio
    async def test_narrative_from_context_when_state_empty(self):
        """When state is empty, narrative rebuilds from context phase outputs."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_narrative_synthesis,
        )

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "Argument about national defense"},
                    {"text": "Another argument about technology"},
                ]
            },
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {"type": "Appel a l'autorite", "target_text": "Argument about defense"},
                ]
            },
            "phase_counter_output": {
                "llm_counter_arguments": [
                    {"target_argument": "Argument about national defense", "counter_argument": "Counter 1"}
                ]
            },
        }

        result = await _invoke_narrative_synthesis("test text", context)

        # Must be non-empty
        assert result["narrative"], f"Expected non-empty narrative, got: {result}"
        # Should mention extracted args count
        assert "2 argument(s)" in result["narrative"]
        # Should mention fallacy
        assert "1 sophisme(s)" in result["narrative"]
        # Should mention counter-arguments
        assert "contre-arguments" in result["narrative"].lower()
        # Degraded flag
        assert result.get("degraded") is True

    @pytest.mark.asyncio
    async def test_sentinel_triggers_context_rebuild(self):
        """When build_narrative returns the fallback sentinel, context rebuild activates (#994)."""
        from unittest.mock import patch, MagicMock
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_narrative_synthesis,
        )

        sentinel = (
            "L'analyse n'a pas produit suffisamment de donnees pour generer "
            "une synthese narrative"
        )
        mock_state = MagicMock()
        context = {
            "_state_object": mock_state,
            "phase_extract_output": {
                "arguments": [{"text": "Arg1"}, {"text": "Arg2"}]
            },
        }
        with patch(
            "argumentation_analysis.plugins.narrative_synthesis_plugin.build_narrative",
            return_value=sentinel,
        ):
            result = await _invoke_narrative_synthesis("test text", context)

        # Should have rebuilt from context
        assert result["narrative"], f"Expected rebuilt narrative, got: {result}"
        assert "2 argument(s)" in result["narrative"]
        assert result.get("degraded") is True

    @pytest.mark.asyncio
    async def test_non_degraded_path_no_rebuild(self):
        """When build_narrative returns valid prose, no degraded flag is set (#994)."""
        from unittest.mock import patch, MagicMock
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_narrative_synthesis,
        )

        valid_narrative = "L'argument principal repose sur une analogie solide."
        mock_state = MagicMock()
        context = {"_state_object": mock_state}

        with patch(
            "argumentation_analysis.plugins.narrative_synthesis_plugin.build_narrative",
            return_value=valid_narrative,
        ):
            result = await _invoke_narrative_synthesis("test text", context)

        assert result["narrative"] == valid_narrative
        assert result.get("degraded") is not True
        assert "degraded_reason" not in result

    @pytest.mark.asyncio
    async def test_narrative_empty_context_still_returns(self):
        """Even with completely empty context, narrative callable does not crash."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_narrative_synthesis,
        )

        result = await _invoke_narrative_synthesis("test text", {})

        assert isinstance(result, dict)
        assert "narrative" in result
        # May be the fallback message, but should never raise
