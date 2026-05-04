"""Tests for NL-to-logic wiring in PL and FOL pipeline phases (#208-H).

Verifies the 3-tier fallback: upstream translations → on-the-fly translator → templates.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

TWEETY_BRIDGE_PATH = (
    "argumentation_analysis.agents.core.logic.tweety_bridge.TweetyBridge"
)


def _make_context_with_args(args_texts, extra=None):
    """Helper: build a context dict with extracted arguments."""
    ctx = {
        "phase_extract_output": {
            "arguments": [{"text": t} for t in args_texts],
        },
    }
    if extra:
        ctx.update(extra)
    return ctx


class TestPropositionalLogicNLWiring:
    """Tests for NL-to-logic in _invoke_propositional_logic."""

    async def test_pl_uses_upstream_translations(self):
        """PL phase uses validated translations from phase_nl_to_logic_output."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        context = _make_context_with_args(
            ["Tax cuts grow the economy", "Free trade reduces prices"],
            extra={
                "phase_nl_to_logic_output": {
                    "translations": [
                        {
                            "logic_type": "propositional",
                            "formula": "p1 => p2",
                            "is_valid": True,
                            "original_text": "Tax cuts grow the economy",
                        },
                        {
                            "logic_type": "propositional",
                            "formula": "p3 => p4",
                            "is_valid": True,
                            "original_text": "Free trade reduces prices",
                        },
                    ]
                }
            },
        )

        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = {
            "consistent": True,
            "model": {"p1": True},
        }
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = await _invoke_propositional_logic("text", context)

        assert result["logic_type"] == "propositional"
        assert "p1 => p2" in result["formulas"]
        assert "p3 => p4" in result["formulas"]

    async def test_pl_skips_invalid_translations(self):
        """PL phase ignores translations where is_valid is False."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        context = _make_context_with_args(
            ["Some argument"],
            extra={
                "phase_nl_to_logic_output": {
                    "translations": [
                        {
                            "logic_type": "propositional",
                            "formula": "bad formula",
                            "is_valid": False,
                            "original_text": "Some argument",
                        },
                    ]
                }
            },
        )

        # Mock TweetyBridge since fallback path calls check_consistency
        with patch(TWEETY_BRIDGE_PATH) as MockBridge:
            MockBridge.return_value.check_consistency.return_value = (
                True,
                "consistent",
            )
            result = await _invoke_propositional_logic("text", context)
        assert result["logic_type"] == "propositional"
        # Invalid translations are skipped → falls back to on-the-fly or template
        # Templates generate p1..pN, on-the-fly may produce other formulas
        assert len(result["formulas"]) >= 1

    async def test_pl_falls_back_to_templates(self):
        """PL phase generates p1, p2, ... templates when no translations available."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        context = _make_context_with_args(["Arg one", "Arg two", "Arg three"])
        result = await _invoke_propositional_logic("text", context)

        assert result["logic_type"] == "propositional"
        assert "p1" in result["formulas"]
        assert "p2" in result["formulas"]
        assert "p3" in result["formulas"]

    async def test_pl_argument_mapping_from_translations(self):
        """argument_mapping is populated from NL-to-logic translations."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        context = _make_context_with_args(
            ["Original text here"],
            extra={
                "phase_nl_to_logic_output": {
                    "translations": [
                        {
                            "logic_type": "propositional",
                            "formula": "p => q",
                            "is_valid": True,
                            "original_text": "Original text here",
                        },
                    ]
                }
            },
        )

        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = {
            "consistent": True,
            "model": {"p": True},
        }
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = await _invoke_propositional_logic("text", context)

        assert result["argument_mapping"]
        mapping_values = list(result["argument_mapping"].values())
        assert any("Original text" in v for v in mapping_values)

    async def test_pl_nl_translator_import_failure(self):
        """PL phase gracefully falls back when NLToLogicTranslator import fails."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_propositional_logic,
        )

        context = _make_context_with_args(["Some argument text here"])

        with patch.dict(
            "sys.modules", {"argumentation_analysis.services.nl_to_logic": None}
        ):
            result = await _invoke_propositional_logic("text", context)

        assert result["logic_type"] == "propositional"
        assert "p1" in result["formulas"]


class TestFOLReasoningNLWiring:
    """Tests for NL-to-logic in _invoke_fol_reasoning."""

    async def test_fol_uses_upstream_translations(self):
        """FOL phase uses validated translations from phase_nl_to_logic_output."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = _make_context_with_args(
            ["All humans are mortal"],
            extra={
                "phase_nl_to_logic_output": {
                    "translations": [
                        {
                            "logic_type": "fol",
                            "formula": "forall X: (Human(X) -> Mortal(X))",
                            "is_valid": True,
                            "original_text": "All humans are mortal",
                        },
                    ]
                }
            },
        )

        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = {
            "consistent": True,
            "model": {},
        }
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = await _invoke_fol_reasoning("text", context)

        assert result["logic_type"] == "first_order"
        assert "forall X: (Human(X) -> Mortal(X))" in result["formulas"]

    async def test_fol_splits_semicolon_formulas(self):
        """FOL phase splits semicolon-separated formulas from translations."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = _make_context_with_args(
            ["Complex argument"],
            extra={
                "phase_nl_to_logic_output": {
                    "translations": [
                        {
                            "logic_type": "fol",
                            "formula": "Human(socrates); Mortal(socrates)",
                            "is_valid": True,
                            "original_text": "Complex argument",
                        },
                    ]
                }
            },
        )

        mock_bridge = MagicMock()
        mock_bridge.check_consistency.return_value = {
            "consistent": True,
            "model": {},
        }
        with patch(TWEETY_BRIDGE_PATH, return_value=mock_bridge):
            result = await _invoke_fol_reasoning("text", context)

        assert "Human(socrates)" in result["formulas"]
        assert "Mortal(socrates)" in result["formulas"]

    async def test_fol_falls_back_to_templates(self):
        """FOL phase generates Asserted(argN) templates when no translations available."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = _make_context_with_args(["Arg one", "Arg two"])
        result = await _invoke_fol_reasoning("text", context)

        assert result["logic_type"] == "first_order"
        assert "Asserted(arg1)" in result["formulas"]
        assert "Asserted(arg2)" in result["formulas"]

    async def test_fol_ignores_propositional_translations(self):
        """FOL phase only uses translations with logic_type='fol'."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = _make_context_with_args(
            ["Some argument"],
            extra={
                "phase_nl_to_logic_output": {
                    "translations": [
                        {
                            "logic_type": "propositional",
                            "formula": "p => q",
                            "is_valid": True,
                            "original_text": "Some argument",
                        },
                    ]
                }
            },
        )

        result = await _invoke_fol_reasoning("text", context)
        assert "Asserted(arg1)" in result["formulas"]

    async def test_fol_nl_translator_import_failure(self):
        """FOL phase gracefully falls back when NLToLogicTranslator import fails."""
        from argumentation_analysis.orchestration.unified_pipeline import (
            _invoke_fol_reasoning,
        )

        context = _make_context_with_args(["Some argument text here"])

        with patch.dict(
            "sys.modules", {"argumentation_analysis.services.nl_to_logic": None}
        ):
            result = await _invoke_fol_reasoning("text", context)

        assert result["logic_type"] == "first_order"
        assert "Asserted(arg1)" in result["formulas"]
