"""Tests for Tweety-based SK plugins: RankingPlugin, ASPICPlugin, BeliefRevisionPlugin."""

import json
import pytest
from unittest.mock import patch, MagicMock


# =====================================================================
# RankingPlugin Tests
# =====================================================================


class TestRankingPlugin:
    """Test RankingPlugin @kernel_function methods."""

    def test_list_ranking_methods(self):
        with patch(
            "argumentation_analysis.agents.core.logic.ranking_handler.jpype"
        ):
            from argumentation_analysis.plugins.ranking_plugin import RankingPlugin
            plugin = RankingPlugin()
            result = json.loads(plugin.list_ranking_methods())
            assert isinstance(result, list)
            assert "categorizer" in result
            assert "burden" in result
            assert len(result) == 7

    def test_rank_arguments_returns_json(self):
        mock_handler = MagicMock()
        mock_handler.return_value.rank_arguments.return_value = {
            "method": "categorizer",
            "arguments": ["a", "b"],
            "comparisons": [{"a > b": True}],
            "statistics": {"arguments_count": 2},
        }
        with patch(
            "argumentation_analysis.agents.core.logic.ranking_handler.RankingHandler",
            mock_handler,
        ):
            from argumentation_analysis.plugins.ranking_plugin import RankingPlugin
            plugin = RankingPlugin()
            input_json = json.dumps({
                "arguments": ["a", "b"],
                "attacks": [["a", "b"]],
                "method": "categorizer",
            })
            result = json.loads(plugin.rank_arguments(input_json))
            assert result["method"] == "categorizer"
            assert "comparisons" in result

    def test_rank_arguments_default_method(self):
        mock_handler = MagicMock()
        mock_handler.return_value.rank_arguments.return_value = {"method": "categorizer"}
        with patch(
            "argumentation_analysis.agents.core.logic.ranking_handler.RankingHandler",
            mock_handler,
        ):
            from argumentation_analysis.plugins.ranking_plugin import RankingPlugin
            plugin = RankingPlugin()
            input_json = json.dumps({"arguments": ["a"], "attacks": []})
            plugin.rank_arguments(input_json)
            call_kwargs = mock_handler.return_value.rank_arguments.call_args
            # method should default to "categorizer"
            assert call_kwargs[1].get("method", "categorizer") == "categorizer"

    def test_rank_arguments_invalid_json(self):
        from argumentation_analysis.plugins.ranking_plugin import RankingPlugin
        plugin = RankingPlugin()
        with pytest.raises(json.JSONDecodeError):
            plugin.rank_arguments("not valid json")


# =====================================================================
# ASPICPlugin Tests
# =====================================================================


class TestASPICPlugin:
    """Test ASPICPlugin @kernel_function methods."""

    def test_list_reasoner_types(self):
        from argumentation_analysis.plugins.aspic_plugin import ASPICPlugin
        plugin = ASPICPlugin()
        result = json.loads(plugin.list_aspic_reasoner_types())
        assert result == ["simple", "directional"]

    def test_analyze_aspic_returns_json(self):
        mock_handler = MagicMock()
        mock_handler.return_value.analyze_aspic_framework.return_value = {
            "reasoner_type": "simple",
            "extensions": [["a", "b"]],
            "statistics": {"strict_rules_count": 1},
        }
        with patch(
            "argumentation_analysis.agents.core.logic.aspic_handler.ASPICHandler",
            mock_handler,
        ):
            from argumentation_analysis.plugins.aspic_plugin import ASPICPlugin
            plugin = ASPICPlugin()
            input_json = json.dumps({
                "strict_rules": [{"head": "c", "body": ["a", "b"]}],
                "defeasible_rules": [],
                "axioms": ["a", "b"],
            })
            result = json.loads(plugin.analyze_aspic(input_json))
            assert result["reasoner_type"] == "simple"
            assert "extensions" in result

    def test_analyze_aspic_directional(self):
        mock_handler = MagicMock()
        mock_handler.return_value.analyze_aspic_framework.return_value = {
            "reasoner_type": "directional",
            "extensions": [],
            "statistics": {},
        }
        with patch(
            "argumentation_analysis.agents.core.logic.aspic_handler.ASPICHandler",
            mock_handler,
        ):
            from argumentation_analysis.plugins.aspic_plugin import ASPICPlugin
            plugin = ASPICPlugin()
            input_json = json.dumps({
                "strict_rules": [],
                "defeasible_rules": [{"head": "x", "body": ["y"]}],
                "reasoner_type": "directional",
            })
            result = json.loads(plugin.analyze_aspic(input_json))
            assert result["reasoner_type"] == "directional"

    def test_analyze_aspic_invalid_json(self):
        from argumentation_analysis.plugins.aspic_plugin import ASPICPlugin
        plugin = ASPICPlugin()
        with pytest.raises(json.JSONDecodeError):
            plugin.analyze_aspic("{bad")


# =====================================================================
# BeliefRevisionPlugin Tests
# =====================================================================


class TestBeliefRevisionPlugin:
    """Test BeliefRevisionPlugin @kernel_function methods."""

    def test_list_revision_methods(self):
        from argumentation_analysis.plugins.belief_revision_plugin import BeliefRevisionPlugin
        plugin = BeliefRevisionPlugin()
        result = json.loads(plugin.list_revision_methods())
        assert result == ["dalal", "levi"]

    def test_revise_beliefs_returns_json(self):
        mock_handler = MagicMock()
        mock_handler.return_value.revise.return_value = {
            "method": "dalal",
            "original": ["p", "q"],
            "new_belief": "!p",
            "revised": ["!p", "q"],
            "statistics": {"original_size": 2, "revised_size": 2},
        }
        with patch(
            "argumentation_analysis.agents.core.logic.belief_revision_handler.BeliefRevisionHandler",
            mock_handler,
        ):
            from argumentation_analysis.plugins.belief_revision_plugin import BeliefRevisionPlugin
            plugin = BeliefRevisionPlugin()
            input_json = json.dumps({
                "belief_set": ["p", "q"],
                "new_belief": "!p",
                "method": "dalal",
            })
            result = json.loads(plugin.revise_beliefs(input_json))
            assert result["method"] == "dalal"
            assert "revised" in result

    def test_contract_beliefs_returns_json(self):
        mock_handler = MagicMock()
        mock_handler.return_value.contract.return_value = {
            "operation": "contraction",
            "original": ["p", "q"],
            "removed": "p",
            "contracted": ["q"],
            "statistics": {"original_size": 2, "contracted_size": 1},
        }
        with patch(
            "argumentation_analysis.agents.core.logic.belief_revision_handler.BeliefRevisionHandler",
            mock_handler,
        ):
            from argumentation_analysis.plugins.belief_revision_plugin import BeliefRevisionPlugin
            plugin = BeliefRevisionPlugin()
            input_json = json.dumps({
                "belief_set": ["p", "q"],
                "formula_to_remove": "p",
            })
            result = json.loads(plugin.contract_beliefs(input_json))
            assert result["operation"] == "contraction"
            assert "contracted" in result

    def test_revise_beliefs_levi_method(self):
        mock_handler = MagicMock()
        mock_handler.return_value.revise.return_value = {"method": "levi", "revised": ["r"]}
        with patch(
            "argumentation_analysis.agents.core.logic.belief_revision_handler.BeliefRevisionHandler",
            mock_handler,
        ):
            from argumentation_analysis.plugins.belief_revision_plugin import BeliefRevisionPlugin
            plugin = BeliefRevisionPlugin()
            input_json = json.dumps({
                "belief_set": ["p"],
                "new_belief": "r",
                "method": "levi",
            })
            result = json.loads(plugin.revise_beliefs(input_json))
            assert result["method"] == "levi"

    def test_revise_beliefs_invalid_json(self):
        from argumentation_analysis.plugins.belief_revision_plugin import BeliefRevisionPlugin
        plugin = BeliefRevisionPlugin()
        with pytest.raises(json.JSONDecodeError):
            plugin.revise_beliefs("invalid")

    def test_contract_beliefs_invalid_json(self):
        from argumentation_analysis.plugins.belief_revision_plugin import BeliefRevisionPlugin
        plugin = BeliefRevisionPlugin()
        with pytest.raises(json.JSONDecodeError):
            plugin.contract_beliefs("invalid")


# =====================================================================
# ToulminPlugin Tests
# =====================================================================


class TestToulminPlugin:
    """Test ToulminPlugin @kernel_function methods."""

    def test_plugin_instantiation(self):
        from argumentation_analysis.plugins.toulmin_plugin import ToulminPlugin
        plugin = ToulminPlugin()
        assert hasattr(plugin, "analyze_argument")

    async def test_analyze_argument_not_implemented(self):
        from argumentation_analysis.plugins.toulmin_plugin import ToulminPlugin
        plugin = ToulminPlugin()
        with pytest.raises(NotImplementedError, match="not yet implemented"):
            await plugin.analyze_argument("The death penalty should be abolished because it is cruel.")
