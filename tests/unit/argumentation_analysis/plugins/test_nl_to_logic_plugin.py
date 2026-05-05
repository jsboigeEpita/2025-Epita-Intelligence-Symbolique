"""Tests for NLToLogicPlugin — SK plugin wrapping NLToLogicTranslator.

Validates that the plugin correctly wraps the translation service
and is properly wired into the agent factory.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from argumentation_analysis.plugins.nl_to_logic_plugin import NLToLogicPlugin


class TestNLToLogicPlugin:
    """Unit tests for NLToLogicPlugin @kernel_function methods."""

    def test_plugin_instantiation(self):
        """Plugin creates without errors."""
        plugin = NLToLogicPlugin()
        assert plugin is not None

    def test_has_kernel_functions(self):
        """Plugin exposes the expected @kernel_function methods."""
        plugin = NLToLogicPlugin()
        assert hasattr(plugin, "translate_to_pl")
        assert hasattr(plugin, "translate_to_fol")
        assert hasattr(plugin, "translate_batch_to_pl")
        assert hasattr(plugin, "translate_batch_to_fol")

    @pytest.mark.asyncio
    async def test_translate_to_pl_success(self):
        """translate_to_pl returns JSON with formula and metadata."""
        plugin = NLToLogicPlugin()

        mock_result = MagicMock()
        mock_result.original_text = "If it rains then the ground is wet"
        mock_result.formula = "rain => wet"
        mock_result.logic_type = "propositional"
        mock_result.is_valid = True
        mock_result.validation_message = "Valid PL"
        mock_result.attempts = 1
        mock_result.variables = {"rain": "it rains", "wet": "ground is wet"}
        mock_result.confidence = 0.85

        with patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator"
        ) as MockTranslator:
            MockTranslator.return_value.translate = AsyncMock(return_value=mock_result)
            result_str = await plugin.translate_to_pl(
                "If it rains then the ground is wet"
            )

        result = json.loads(result_str)
        assert result["formula"] == "rain => wet"
        assert result["is_valid"] is True
        assert result["confidence"] == 0.85
        assert result["logic_type"] == "propositional"

    @pytest.mark.asyncio
    async def test_translate_to_fol_success(self):
        """translate_to_fol returns JSON with FOL formula."""
        plugin = NLToLogicPlugin()

        mock_result = MagicMock()
        mock_result.original_text = "All humans are mortal"
        mock_result.formula = "forall X: (Human(X) => Mortal(X))"
        mock_result.logic_type = "fol"
        mock_result.is_valid = True
        mock_result.validation_message = "Valid FOL"
        mock_result.attempts = 1
        mock_result.variables = {"Human": "is human", "Mortal": "is mortal"}
        mock_result.confidence = 0.9

        with patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator"
        ) as MockTranslator:
            MockTranslator.return_value.translate = AsyncMock(return_value=mock_result)
            result_str = await plugin.translate_to_fol("All humans are mortal")

        result = json.loads(result_str)
        assert "forall" in result["formula"]
        assert result["logic_type"] == "fol"
        assert result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_translate_to_pl_invalid_formula(self):
        """translate_to_pl handles invalid formula gracefully."""
        plugin = NLToLogicPlugin()

        mock_result = MagicMock()
        mock_result.original_text = "bad argument"
        mock_result.formula = "bad syntax ((("
        mock_result.logic_type = "propositional"
        mock_result.is_valid = False
        mock_result.validation_message = "Unmatched parentheses"
        mock_result.attempts = 3
        mock_result.variables = {}
        mock_result.confidence = 0.0

        with patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator"
        ) as MockTranslator:
            MockTranslator.return_value.translate = AsyncMock(return_value=mock_result)
            result_str = await plugin.translate_to_pl("bad argument")

        result = json.loads(result_str)
        assert result["is_valid"] is False
        assert result["attempts"] == 3

    @pytest.mark.asyncio
    async def test_translate_batch_to_pl(self):
        """translate_batch_to_pl translates multiple arguments."""
        plugin = NLToLogicPlugin()

        mock_batch = MagicMock()
        mock_batch.translations = [
            MagicMock(
                original_text="arg1",
                formula="p => q",
                is_valid=True,
                variables={"p": "prem", "q": "conc"},
                confidence=0.8,
            ),
            MagicMock(
                original_text="arg2",
                formula="q => r",
                is_valid=True,
                variables={"q": "prem2", "r": "conc2"},
                confidence=0.7,
            ),
        ]
        mock_batch.overall_consistency = True
        mock_batch.consistency_message = "Consistent"
        mock_batch.method = "llm"

        with patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator"
        ) as MockTranslator:
            MockTranslator.return_value.translate_batch = AsyncMock(
                return_value=mock_batch
            )
            result_str = await plugin.translate_batch_to_pl(
                json.dumps({"arguments": ["arg1", "arg2"]})
            )

        result = json.loads(result_str)
        assert len(result["translations"]) == 2
        assert result["overall_consistency"] is True

    @pytest.mark.asyncio
    async def test_translate_batch_empty_input(self):
        """translate_batch returns error for empty input."""
        plugin = NLToLogicPlugin()

        result_str = await plugin.translate_batch_to_pl("{}")
        result = json.loads(result_str)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_translate_batch_fol(self):
        """translate_batch_to_fol translates multiple arguments to FOL."""
        plugin = NLToLogicPlugin()

        mock_batch = MagicMock()
        mock_batch.translations = [
            MagicMock(
                original_text="Socrates is human",
                formula="Human(socrates)",
                is_valid=True,
                variables={"Human": "is human"},
                confidence=0.9,
            ),
        ]
        mock_batch.overall_consistency = True
        mock_batch.consistency_message = "Consistent"
        mock_batch.method = "llm"

        with patch(
            "argumentation_analysis.services.nl_to_logic.NLToLogicTranslator"
        ) as MockTranslator:
            MockTranslator.return_value.translate_batch = AsyncMock(
                return_value=mock_batch
            )
            result_str = await plugin.translate_batch_to_fol(
                json.dumps({"arguments": ["Socrates is human"]})
            )

        result = json.loads(result_str)
        assert len(result["translations"]) == 1
        assert "Human" in result["translations"][0]["formula"]


class TestFactoryWiring:
    """Verify NLToLogicPlugin is wired into the factory registry."""

    def test_nl_to_logic_in_plugin_registry(self):
        """'nl_to_logic' is in _PLUGIN_REGISTRY."""
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        assert "nl_to_logic" in _PLUGIN_REGISTRY
        module_path, class_name = _PLUGIN_REGISTRY["nl_to_logic"]
        assert "nl_to_logic_plugin" in module_path
        assert class_name == "NLToLogicPlugin"

    def test_formal_logic_speciality_includes_nl_to_logic(self):
        """'formal_logic' speciality includes nl_to_logic plugin."""
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        plugins = AGENT_SPECIALITY_MAP.get("formal_logic", [])
        assert "nl_to_logic" in plugins
        assert "tweety_logic" in plugins

    def test_get_plugin_instances_returns_nl_to_logic(self):
        """get_plugin_instances('formal_logic') returns NLToLogicPlugin instance."""
        from argumentation_analysis.agents.factory import get_plugin_instances

        plugins = get_plugin_instances("formal_logic")
        plugin_types = [type(p).__name__ for p in plugins]
        assert "NLToLogicPlugin" in plugin_types
        assert "TweetyLogicPlugin" in plugin_types
