"""Tests for TextToKB/KBToTweety/TweetyInterpretation wiring in spectacular (#506).

Verifies:
- 3 new phases present in spectacular workflow
- DAG dependencies correct
- Invoke callables importable and callable
- State writers registered in CAPABILITY_STATE_WRITERS
- Services registered in CapabilityRegistry
- Phase capabilities resolve to providers
"""

import json
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
        # #1179 (#1178) wired the 4 dormant-reasoner handlers into spectacular,
        # taking the phase count from 23 (the 3 text-to-kb phases of #506 atop
        # the original 20) to 40. Sibling tests (test_spectacular_regression_suite,
        # test_belief_revision_spectacular, test_external_solver_spectacular,
        # test_spectacular_workflow_dag) already assert 40; this one was missed.
        # #1625 (R759): L9 `analysis_synthesis` was retired (zero prod reader,
        # no LLM call). Phase count drops from 40 to 39.
        assert len(wf.phases) == 39


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
    async def test_invoke_kb_to_tweety_missing_kb_reports_input_error(self):
        """#1643 R761 — defect 1: when phase_text_to_kb_output is absent,
        the callable MUST NOT silently parse the raw prose as JSON. It must
        surface the missing input explicitly."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_kb_to_tweety,
        )

        prose = "Le président a déclaré que la croissance sera de 3% en 2026."
        result = await _invoke_kb_to_tweety(prose, {})  # no ctx
        assert result["status"] == "input_error"
        assert result["error"] == "missing_text_to_kb_output"
        assert result["formulas"] == []
        assert result["formula_count"] == 0
        # Critically: NO error dict is stored under domain-vocabulary keys.
        assert "dung_framework" not in result
        assert "aspic_system" not in result

    @pytest.mark.asyncio
    async def test_invoke_kb_to_tweety_consumes_kb_from_context(self):
        """#1643 R761 — defect 1 (positive case): when context carries
        phase_text_to_kb_output, the callable consumes it. The pre-fix code
        always returned ``{formulas: [], formula_count: 0}`` on any input
        because it parsed input_text (prose) instead of context — so this
        test is the regression sentinel for the bug as observed in the wild.

        We assert on the **trajectory**, not the absolute count: the plugin
        may legitimately reject some beliefs if the FOL signature is missing
        ``constants`` (it raises ``KeyError('constants')``), and the test
        must not couple to that detail. The contracts that matter:
          - status == "ok" (input was consumed, not bypassed)
          - kb_source carries provenance for downstream readers
          - either formulas > 0 OR batch_item_errors is documented
          - Dung/ASPIC pipelines produced real frameworks (not error dicts)"""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_kb_to_tweety,
        )

        prose = (
            "Un argumentaire construit à partir d'une KB extraite."  # prose not used
        )
        ctx = {
            "phase_text_to_kb_output": {
                "arguments": [
                    {"text": "Argument 1"},
                    {"text": "Argument 2"},
                ],
                "belief_candidates": [
                    "Croissance_3_pct_2026",
                    "Vérifiable",
                ],
                "fol_signature": {
                    "predicates": ["Croissance", "Invérifiable"],
                    "constants": ["c1", "c2"],
                },
            }
        }
        result = await _invoke_kb_to_tweety(prose, ctx)
        assert result["status"] == "ok"
        # Provenance is recorded so Epic #1644 readers can trace the source.
        assert result["kb_source"]["argument_count"] == 2
        assert result["kb_source"]["belief_count"] == 2
        # Either we produced formulas OR we documented why each was rejected.
        # Anti-#1019 — silent 0 with no reason is theater.
        assert (
            result["formula_count"] >= 1 or "batch_item_errors" in result
        ), f"No formulas and no error documentation — silent failure: {result}"
        # defect 2 — every formula in the list is a real dict with a `formula`
        # field, never an error dict masquerading as a formula.
        for f in result["formulas"]:
            assert isinstance(f, dict)
            assert "formula" in f
            assert "error" not in f

    @pytest.mark.asyncio
    async def test_invoke_kb_to_tweety_no_error_dict_in_domain_fields(self):
        """#1643 R761 — defect 3 (caller side): when the plugin returns
        an error dict, the callable must NOT store it under
        dung_framework / aspic_system. Either the field is absent (preferred)
        or the error is exposed under a *_error key."""
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_kb_to_tweety,
        )
        from argumentation_analysis.plugins import kb_to_tweety_plugin as kbp

        real_translate_dung = kbp.KBToTweetyPlugin.translate_dung

        async def boom(self, input):
            return json.dumps({"error": "plugin_simulated_failure"})

        kbp.KBToTweetyPlugin.translate_dung = boom
        try:
            ctx = {
                "phase_text_to_kb_output": {
                    "arguments": [{"text": "a1"}],
                    "belief_candidates": ["b1"],
                    "fol_signature": {
                        "predicates": ["P"],
                        "constants": ["c1"],
                    },
                }
            }
            result = await _invoke_kb_to_tweety("ignored prose", ctx)
            # Critical defect-3 contract: NO error dict under dung_framework.
            assert "dung_framework" not in result or "error" not in result.get(
                "dung_framework", {}
            ), f"Defect 3 leaked: dung_framework = {result.get('dung_framework')}"
            # The error is surfaced explicitly under a *_error key.
            assert result.get("dung_error") == "plugin_simulated_failure"
        finally:
            kbp.KBToTweetyPlugin.translate_dung = real_translate_dung

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
            "status": "ok",
        }
        _write_kb_to_tweety_to_state(output, state, {})
        assert state.add_belief_set.call_count == 2
        assert state.tweety_formulas_from_kb["formula_count"] == 2
        assert state.tweety_formulas_from_kb["status"] == "ok"
        # Real dung_framework from a successful plugin call is preserved.
        state.tweety_formulas_from_kb = {}
        output_with_dung = {
            "formulas": [],
            "formula_count": 0,
            "status": "ok",
            "dung_framework": {"arguments": ["a1"], "attacks": [], "is_valid": True},
        }
        _write_kb_to_tweety_to_state(output_with_dung, state, {})
        assert state.tweety_formulas_from_kb["dung_framework"]["is_valid"] is True

    def test_write_kb_to_tweety_to_state_refuses_error_dicts(self):
        """#1643 R761 — defect 3: writer must NOT store {"error": ...} as a
        domain-vocabulary field (dung_framework / aspic_system). Errors are
        surfaced under *_error keys, never folded into success path."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_kb_to_tweety_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": [],
            "formula_count": 0,
            "dung_framework": {"error": "Invalid JSON input"},  # plugin's error dict
            "aspic_system": {"error": "Invalid JSON input"},
        }
        _write_kb_to_tweety_to_state(output, state, {})
        # Bug-replication-failure: the writer refused to store the error dicts
        # under dung_framework / aspic_system.
        assert "dung_framework" not in state.tweety_formulas_from_kb
        assert "aspic_system" not in state.tweety_formulas_from_kb
        # status defaults to None when not provided — caller-visible signal
        # that the run was not "ok".
        assert "dung_error" not in state.tweety_formulas_from_kb
        assert "aspic_error" not in state.tweety_formulas_from_kb

    def test_write_kb_to_tweety_to_state_input_error_status(self):
        """#1643 R761 — on input_error status, only the explicit error keys
        propagate; the domain fields stay absent rather than populated with
        fallback defaults."""
        from argumentation_analysis.orchestration.state_writers import (
            _write_kb_to_tweety_to_state,
        )

        state = MagicMock()
        output = {
            "formulas": [],
            "formula_count": 0,
            "status": "input_error",
            "dung_error": "missing_arguments",
            "aspic_error": "missing_arguments",
        }
        _write_kb_to_tweety_to_state(output, state, {})
        assert state.tweety_formulas_from_kb["status"] == "input_error"
        assert state.tweety_formulas_from_kb["dung_error"] == "missing_arguments"
        assert state.tweety_formulas_from_kb["aspic_error"] == "missing_arguments"
        assert "dung_framework" not in state.tweety_formulas_from_kb
        assert "aspic_system" not in state.tweety_formulas_from_kb

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
