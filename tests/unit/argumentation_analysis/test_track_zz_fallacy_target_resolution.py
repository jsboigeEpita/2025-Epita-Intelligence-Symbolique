"""Tests for Track ZZ (#685): populate fallacy target_argument to revive JTMS signal 4.

Follow-up to Track WW (#678) which diagnosed the gap: IdentifiedFallacy
never produces a target_argument field, so _invoke_jtms falls back to
positional matching (unreliable). This track adds text-based resolution
using problematic_quote and explanation as fallbacks.

Covers:
  1. State writer: _write_hierarchical_fallacy_to_state resolves target via
     problematic_quote and explanation when target_argument is absent
  2. _invoke_jtms: fallacy→arg matching uses problematic_quote and
     explanation fallbacks before positional matching
  3. End-to-end: fallacy with quote matching arg → retraction → signal 4
  4. _resolve_target_arg_id integration with fallacy writer
"""

import pytest
from unittest.mock import MagicMock

import importlib.util
from pathlib import Path

_DEMO_ROOT = Path(__file__).resolve().parents[3]
_SPEC = importlib.util.spec_from_file_location(
    "state_writers",
    _DEMO_ROOT / "argumentation_analysis" / "orchestration" / "state_writers.py",
)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

_write_hierarchical_fallacy_to_state = _MOD._write_hierarchical_fallacy_to_state
_resolve_target_arg_id = _MOD._resolve_target_arg_id


def _make_state(**kwargs):
    from argumentation_analysis.core.shared_state import UnifiedAnalysisState

    state = UnifiedAnalysisState("test text")
    if kwargs.get("identified_arguments"):
        state.identified_arguments = kwargs["identified_arguments"]
    if kwargs.get("identified_fallacies"):
        state.identified_fallacies = kwargs["identified_fallacies"]
    if kwargs.get("jtms_beliefs"):
        state.jtms_beliefs = kwargs["jtms_beliefs"]
    return state


class TestFallacyWriterTargetResolution:
    """Verify _write_hierarchical_fallacy_to_state resolves target_arg_id."""

    def test_writer_resolves_problematic_quote_to_arg(self):
        state = _make_state(
            identified_arguments={
                "arg_1": "The policy causes significant harm to communities"
            },
        )
        output = {
            "fallacies": [
                {
                    "fallacy_type": "ad hominem",
                    "taxonomy_pk": "AH.01",
                    "explanation": "The argument attacks the person",
                    "problematic_quote": "policy causes significant harm",
                    "confidence": 0.85,
                    "navigation_trace": [],
                },
            ],
        }
        _write_hierarchical_fallacy_to_state(output, state, {})
        fallacies = state.identified_fallacies
        assert len(fallacies) == 1
        fdata = list(fallacies.values())[0]
        assert fdata.get("target_argument_id") == "arg_1"

    def test_writer_resolves_explanation_to_arg(self):
        state = _make_state(
            identified_arguments={"arg_2": "Economic growth requires deregulation"},
        )
        output = {
            "fallacies": [
                {
                    "fallacy_type": "slippery slope",
                    "explanation": "Economic growth requires deregulation is a false causal chain",
                    "confidence": 0.80,
                },
            ],
        }
        _write_hierarchical_fallacy_to_state(output, state, {})
        fallacies = state.identified_fallacies
        fdata = list(fallacies.values())[0]
        assert fdata.get("target_argument_id") == "arg_2"

    def test_writer_prefers_explicit_target_argument(self):
        state = _make_state(
            identified_arguments={
                "arg_1": "First argument",
                "arg_2": "Second argument",
            },
        )
        output = {
            "fallacies": [
                {
                    "fallacy_type": "straw man",
                    "target_argument": "Second argument",
                    "problematic_quote": "First argument",
                    "explanation": "Misrepresents the first argument",
                    "confidence": 0.75,
                },
            ],
        }
        _write_hierarchical_fallacy_to_state(output, state, {})
        fallacies = state.identified_fallacies
        fdata = list(fallacies.values())[0]
        assert fdata.get("target_argument_id") == "arg_2"

    def test_writer_no_match_still_adds_fallacy(self):
        state = _make_state(
            identified_arguments={"arg_1": "Something unrelated"},
        )
        output = {
            "fallacies": [
                {
                    "fallacy_type": "red herring",
                    "explanation": "Completely unrelated tangent",
                    "confidence": 0.60,
                },
            ],
        }
        _write_hierarchical_fallacy_to_state(output, state, {})
        assert len(state.identified_fallacies) == 1
        fdata = list(state.identified_fallacies.values())[0]
        assert "target_argument_id" not in fdata

    def test_writer_multiple_fallacies_resolve_independently(self):
        state = _make_state(
            identified_arguments={
                "arg_1": "Climate action is urgent",
                "arg_2": "Fossil fuels drive the economy",
                "arg_3": "Renewable energy is too expensive",
            },
        )
        output = {
            "fallacies": [
                {
                    "fallacy_type": "hasty generalization",
                    "problematic_quote": "Climate action is urgent",
                    "confidence": 0.80,
                },
                {
                    "fallacy_type": "false dilemma",
                    "explanation": "Renewable energy is too expensive is a false choice",
                    "confidence": 0.75,
                },
            ],
        }
        _write_hierarchical_fallacy_to_state(output, state, {})
        fallacies = state.identified_fallacies
        vals = list(fallacies.values())
        targets = [v.get("target_argument_id") for v in vals]
        assert "arg_1" in targets
        assert "arg_3" in targets

    def test_writer_uses_target_argument_id_directly(self):
        state = _make_state(
            identified_arguments={"arg_1": "Some argument"},
        )
        output = {
            "fallacies": [
                {
                    "fallacy_type": "ad hominem",
                    "target_argument_id": "arg_1",
                    "confidence": 0.90,
                },
            ],
        }
        _write_hierarchical_fallacy_to_state(output, state, {})
        fdata = list(state.identified_fallacies.values())[0]
        assert fdata["target_argument_id"] == "arg_1"


class TestInvokeJtmsQuoteFallback:
    """Test _invoke_jtms uses problematic_quote/explanation for arg matching."""

    @pytest.mark.asyncio
    async def test_quote_matching_retraction(self):
        from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "The policy causes significant harm to many people"},
                    {"text": "Economic growth requires deregulation"},
                ],
                "claims": [],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "type": "ad hominem",
                        "confidence": 0.9,
                        "problematic_quote": "policy causes significant harm",
                    },
                ],
            },
            "phase_counter_output": {},
            "phase_pl_output": {},
            "phase_fol_output": {},
        }

        result = await _invoke_jtms("Test input text", context)
        beliefs = result["beliefs"]

        arg1_name = [n for n in beliefs if n.startswith("arg_1:")][0]
        assert beliefs[arg1_name]["valid"] is False

    @pytest.mark.asyncio
    async def test_explanation_matching_retraction(self):
        from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument about climate policy"},
                    {
                        "text": "Renewable energy is too expensive for widespread adoption"
                    },
                ],
                "claims": [],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "type": "hasty generalization",
                        "confidence": 0.8,
                        "explanation": "too expensive for widespread adoption",
                    },
                ],
            },
            "phase_counter_output": {},
            "phase_pl_output": {},
            "phase_fol_output": {},
        }

        result = await _invoke_jtms("Test input text", context)
        beliefs = result["beliefs"]

        arg2_name = [n for n in beliefs if n.startswith("arg_2:")][0]
        assert beliefs[arg2_name]["valid"] is False

    @pytest.mark.asyncio
    async def test_target_argument_still_works(self):
        from argumentation_analysis.orchestration.invoke_callables import _invoke_jtms

        context = {
            "phase_extract_output": {
                "arguments": [
                    {"text": "First argument about policy"},
                    {"text": "Second argument about economy"},
                ],
                "claims": [],
            },
            "phase_quality_output": {},
            "phase_hierarchical_fallacy_output": {
                "fallacies": [
                    {
                        "type": "straw man",
                        "confidence": 0.85,
                        "target_argument": "economy",
                    },
                ],
            },
            "phase_counter_output": {},
            "phase_pl_output": {},
            "phase_fol_output": {},
        }

        result = await _invoke_jtms("Test input text", context)
        beliefs = result["beliefs"]

        arg2_name = [n for n in beliefs if n.startswith("arg_2:")][0]
        assert beliefs[arg2_name]["valid"] is False


class TestEndToEndSignal4WithQuoteResolution:
    """End-to-end: fallacy with quote → state writer → convergence signal 4."""

    def test_signal_4_fires_via_quote_resolution(self):
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "The policy causes harm"},
            identified_fallacies={
                "f1": {
                    "type": "ad hominem",
                    "target_argument_id": "arg_1",
                    "justification": "Attacks person [taxonomy:AH.01]",
                },
            },
            jtms_beliefs={
                "jtms_1": {
                    "name": "arg_1:The policy causes harm",
                    "valid": False,
                    "justifications": [],
                },
            },
        )

        result = compute_argument_convergence(state)
        assert "arg_1" in result
        signal_names = [s[0] for s in result["arg_1"]["signals"]]
        assert "JTMS retracte" in signal_names

    def test_signal_4_with_problematic_quote_in_state(self):
        """Full chain: writer resolves quote → state has target_arg_id → signal 4."""
        from argumentation_analysis.plugins.narrative_synthesis_plugin import (
            compute_argument_convergence,
        )

        state = _make_state(
            identified_arguments={"arg_1": "Freedom of speech is absolute"},
        )

        output = {
            "fallacies": [
                {
                    "fallacy_type": "slippery slope",
                    "problematic_quote": "Freedom of speech is absolute",
                    "explanation": "Absolute claim without qualification",
                    "confidence": 0.85,
                },
            ],
        }
        _write_hierarchical_fallacy_to_state(output, state, {})

        # Simulate JTMS retraction
        state.jtms_beliefs = {
            "jtms_1": {
                "name": "arg_1:Freedom of speech is absolute",
                "valid": False,
                "justifications": [],
            },
        }

        result = compute_argument_convergence(state)
        assert "arg_1" in result
        signal_names = [s[0] for s in result["arg_1"]["signals"]]
        assert "JTMS retracte" in signal_names
        assert "sophisme" in signal_names


class TestResolveTargetArgIdEdgeCases:
    """Test _resolve_target_arg_id with various inputs."""

    def test_empty_text_returns_none(self):
        state = MagicMock()
        result = _resolve_target_arg_id(state, "")
        assert result is None

    def test_direct_id_match(self):
        state = MagicMock()
        state.identified_arguments = {"arg_1": "desc"}
        result = _resolve_target_arg_id(state, "arg_1")
        assert result == "arg_1"

    def test_text_substring_match(self):
        state = MagicMock()
        state.identified_arguments = {"arg_1": "The policy causes significant harm"}
        result = _resolve_target_arg_id(state, "policy causes significant harm")
        assert result == "arg_1"

    def test_no_match_returns_none(self):
        state = MagicMock()
        state.identified_arguments = {"arg_1": "Something completely different"}
        result = _resolve_target_arg_id(state, "unrelated text about economy")
        assert result is None
