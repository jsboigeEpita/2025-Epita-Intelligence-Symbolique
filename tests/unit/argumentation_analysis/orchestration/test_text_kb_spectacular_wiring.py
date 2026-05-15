"""Tests for TextToKB/KBToTweety/TweetyInterpretation wiring in spectacular (#506).

Verifies:
- 3 new phases present in spectacular workflow
- DAG dependencies correct
- Invoke callables importable and callable
- State writers registered in CAPABILITY_STATE_WRITERS
- Services registered in CapabilityRegistry
- Phase capabilities resolve to providers
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestSpectacularWorkflowPhases:
    """Verify the 3 new phases exist in spectacular with correct DAG deps."""

    def test_spectacular_has_text_to_kb_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        phase = {p.name: p for p in wf.phases}
        assert "text_to_kb" in phase
        assert phase["text_to_kb"].capability == "nl_extraction"
        assert "extract" in phase["text_to_kb"].depends_on
        assert phase["text_to_kb"].optional is True

    def test_spectacular_has_kb_to_tweety_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        phase = {p.name: p for p in wf.phases}
        assert "kb_to_tweety" in phase
        assert phase["kb_to_tweety"].capability == "kb_to_tweety"
        assert "text_to_kb" in phase["kb_to_tweety"].depends_on
        assert phase["kb_to_tweety"].optional is True

    def test_spectacular_has_tweety_interpretation_phase(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        phase = {p.name: p for p in wf.phases}
        assert "tweety_interpretation" in phase
        assert (
            phase["tweety_interpretation"].capability == "formal_result_interpretation"
        )
        deps = phase["tweety_interpretation"].depends_on
        assert "fol" in deps
        assert "modal" in deps
        assert "dung_extensions" in deps
        assert phase["tweety_interpretation"].optional is True

    def test_spectacular_phase_count(self):
        from argumentation_analysis.orchestration.workflows import (
            build_spectacular_workflow,
        )

        wf = build_spectacular_workflow()
        assert len(wf.phases) == 23


class TestInvokeCallables:
    """Verify the 3 invoke callables are importable and produce correct output."""

    @pytest.mark.asyncio
    async def test_invoke_text_to_kb_empty_input(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_text_to_kb,
        )

        result = await _invoke_text_to_kb("", {})
        assert "error" in result
        assert result["arguments"] == []

    @pytest.mark.asyncio
    async def test_invoke_text_to_kb_with_text(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_text_to_kb,
        )

        mock_plugin = MagicMock()
        mock_plugin.extract_kb = AsyncMock(
            return_value='{"arguments": [{"text": "arg1"}], "belief_candidates": ["b1"], "fol_signature": null, "count": 1}'
        )
        with patch(
            "argumentation_analysis.orchestration.invoke_callables.TextToKBPlugin",
            return_value=mock_plugin,
            create=True,
        ), patch.dict(
            "argumentation_analysis.orchestration.invoke_callables.__dict__",
            {},  # force re-import side-effects
        ):
            # Direct call with patch
            import argumentation_analysis.orchestration.invoke_callables as ic

            original = getattr(ic, "TextToKBPlugin", None)
            try:
                from argumentation_analysis.plugins.text_to_kb_plugin import (
                    TextToKBPlugin,
                )

                ic.TextToKBPlugin = type(
                    "FakeTextToKB", (), {"extract_kb": mock_plugin.extract_kb}
                )

                result = await ic._invoke_text_to_kb("Some argument text", {})
                assert result["source_length"] == len("Some argument text")
            finally:
                if original:
                    ic.TextToKBPlugin = original
                elif hasattr(ic, "TextToKBPlugin"):
                    del ic.TextToKBPlugin

    @pytest.mark.asyncio
    async def test_invoke_kb_to_tweety_empty_input(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_kb_to_tweety,
        )

        result = await _invoke_kb_to_tweety("", {})
        assert "error" in result
        assert result["formulas"] == []

    @pytest.mark.asyncio
    async def test_invoke_tweety_interpretation_empty_input(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_tweety_interpretation,
        )

        result = await _invoke_tweety_interpretation("", {})
        assert "error" in result
        assert result["interpretation"] == ""


class TestStateWriters:
    """Verify the 3 new state writers are registered and functional."""

    def test_state_writers_registered(self):
        from argumentation_analysis.orchestration.state_writers import (
            CAPABILITY_STATE_WRITERS,
        )

        assert "nl_extraction" in CAPABILITY_STATE_WRITERS
        assert "kb_to_tweety" in CAPABILITY_STATE_WRITERS
        assert "formal_result_interpretation" in CAPABILITY_STATE_WRITERS

    def test_write_text_to_kb_to_state(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_text_to_kb_to_state,
        )

        state = MagicMock()
        output = {
            "arguments": [{"text": "arg1"}, {"text": "arg2"}],
            "belief_candidates": ["belief A"],
            "fol_signature": {"predicates": ["P"]},
        }
        _write_text_to_kb_to_state(output, state, {})
        assert state.add_argument.call_count == 2
        assert state.add_belief_set.call_count == 1

    def test_write_kb_to_tweety_to_state(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_kb_to_tweety_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": [
                {"formula": "P(a)", "logic_type": "fol"},
                {"formula": "Q(b)", "logic_type": "propositional"},
            ],
            "formula_count": 2,
        }
        _write_kb_to_tweety_to_state(output, state, {})
        assert state.add_belief_set.call_count == 2
        assert state.tweety_formulas_from_kb["formula_count"] == 2

    def test_write_tweety_interpretation_to_state(self):
        from argumentation_analysis.orchestration.state_writers import (
            _write_tweety_interpretation_to_state,
        )

        state = MagicMock()
        output = {"interpretation": "Les arguments sont valides."}
        _write_tweety_interpretation_to_state(output, state, {})
        state.add_extract.assert_called_once_with(
            "formal_interpretation", "Les arguments sont valides."
        )


class TestRegistryServices:
    """Verify the 3 new services are registered in CapabilityRegistry."""

    def test_text_to_kb_service_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry()
        providers = registry.find_for_capability("nl_extraction")
        names = [p.name for p in providers]
        assert "text_to_kb_service" in names
        provider = next(p for p in providers if p.name == "text_to_kb_service")
        assert provider.invoke is not None

    def test_kb_to_tweety_service_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry()
        providers = registry.find_for_capability("kb_to_tweety")
        names = [p.name for p in providers]
        assert "kb_to_tweety_service" in names
        provider = next(p for p in providers if p.name == "kb_to_tweety_service")
        assert provider.invoke is not None

    def test_tweety_interpretation_service_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry()
        providers = registry.find_for_capability("formal_result_interpretation")
        names = [p.name for p in providers]
        assert "tweety_interpretation_service" in names
        provider = next(
            p for p in providers if p.name == "tweety_interpretation_service"
        )
        assert provider.invoke is not None
