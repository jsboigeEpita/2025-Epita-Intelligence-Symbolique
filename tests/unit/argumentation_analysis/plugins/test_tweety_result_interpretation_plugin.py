"""Tests for TweetyResultInterpretationPlugin — formal results to NL (#476).

Validates:
- Template-based interpreters for Dung, FOL, ASPIC, ranking, belief revision
- @kernel_function methods parse JSON input and return NL text
- Full analysis synthesis combines multiple interpreters
- write_interpretation_to_state integrates with analysis state
- Registry and factory integration
"""

import json
import pytest
from unittest.mock import MagicMock

from argumentation_analysis.plugins.tweety_result_interpretation_plugin import (
    TweetyResultInterpretationPlugin,
    _interpret_aspic,
    _interpret_belief_revision,
    _interpret_dung,
    _interpret_fol,
    _interpret_ranking,
)


# ---------------------------------------------------------------------------
# Test: Template-based interpreters
# ---------------------------------------------------------------------------


class TestInterpretDung:
    def test_grounded_extension_with_args(self):
        result = _interpret_dung(
            {"grounded": ["a1", "a2"]},
            arguments=["a1", "a2", "a3"],
        )
        assert "groundee" in result.lower() or "grounded" in result.lower()
        assert "2" in result

    def test_grounded_extension_empty(self):
        result = _interpret_dung({"grounded": []})
        assert "aucun" in result.lower()

    def test_grounded_extension_dict_format(self):
        result = _interpret_dung({"grounded": {"set": ["x", "y"]}})
        assert "2" in result

    def test_preferred_extension(self):
        result = _interpret_dung({"preferred": ["a", "b", "c"]})
        assert "preferee" in result.lower() or "3" in result

    def test_preferred_dict_format(self):
        result = _interpret_dung({"preferred": {"set": ["a"]}})
        assert "1" in result

    def test_stable_extension(self):
        result = _interpret_dung({"stable": ["s1", "s2"]})
        assert "stable" in result.lower()

    def test_stable_dict_format(self):
        result = _interpret_dung({"stable": {"set": ["s1"]}})
        assert "1" in result

    def test_no_extensions(self):
        result = _interpret_dung({}, arguments=["a"])
        assert "completee" in result.lower()

    def test_multiple_extensions(self):
        result = _interpret_dung(
            {"grounded": ["a"], "preferred": ["a", "b"], "stable": ["a", "b", "c"]},
            arguments=["a", "b", "c"],
        )
        assert "groundee" in result.lower() or "grounded" in result.lower()
        assert "preferee" in result.lower()
        assert "stable" in result.lower()


class TestInterpretFOL:
    def test_accepted(self):
        result = _interpret_fol({
            "accepted": True,
            "query": "mortal(socrate)",
            "message": "Proof found",
        })
        assert "acceptee" in result.lower()
        assert "mortal(socrate)" in result

    def test_rejected(self):
        result = _interpret_fol({
            "accepted": False,
            "query": "immortal(socrate)",
            "message": "No proof",
        })
        assert "pas acceptee" in result.lower()

    def test_missing_fields(self):
        result = _interpret_fol({})
        assert result  # non-empty even with empty input

    def test_result_field_fallback(self):
        result = _interpret_fol({
            "accepted": True,
            "query": "p",
            "result": "Derived",
        })
        assert "Derived" in result


class TestInterpretAspic:
    def test_with_rules_and_attacks(self):
        result = _interpret_aspic({
            "strict_rules": ["p => q"],
            "defeasible_rules": ["r => s", "t => u"],
            "attacks": [["a1", "a2"], ["a3", "a4"]],
        })
        assert "1" in result  # 1 strict rule
        assert "2" in result  # 2 defeasible rules
        assert "attaque" in result.lower()

    def test_empty(self):
        result = _interpret_aspic({})
        assert "completee" in result.lower()

    def test_only_strict(self):
        result = _interpret_aspic({"strict_rules": ["a => b"]})
        assert "1" in result

    def test_only_attacks(self):
        result = _interpret_aspic({"attacks": [["x", "y"]]})
        assert "attaque" in result.lower()


class TestInterpretRanking:
    def test_with_scores(self):
        result = _interpret_ranking({
            "rankings": {"arg1": 0.9, "arg2": 0.5, "arg3": 0.3},
        })
        assert "arg1" in result
        assert "0.9" in result

    def test_with_list_rankings(self):
        result = _interpret_ranking({"rankings": [0.8, 0.6, 0.4]})
        assert result  # non-empty

    def test_empty(self):
        result = _interpret_ranking({})
        assert "complete" in result.lower()

    def test_scores_field(self):
        result = _interpret_ranking({"scores": {"a": 5, "b": 3}})
        assert "a" in result


class TestInterpretBeliefRevision:
    def test_all_operations(self):
        result = _interpret_belief_revision({
            "removed_beliefs": ["b1"],
            "added_beliefs": ["b2", "b3"],
            "revised_beliefs": ["b4"],
        })
        assert "1" in result  # removed
        assert "2" in result  # added
        assert "1" in result  # revised

    def test_no_changes(self):
        result = _interpret_belief_revision({})
        assert "aucune" in result.lower()

    def test_only_removed(self):
        result = _interpret_belief_revision({"removed_beliefs": ["x"]})
        assert "retiree" in result.lower()


# ---------------------------------------------------------------------------
# Test: Plugin @kernel_function methods
# ---------------------------------------------------------------------------


class TestPluginDungResults:
    def test_interpret_dung_results(self):
        plugin = TweetyResultInterpretationPlugin()
        input_json = json.dumps({
            "extensions": {"grounded": ["a", "b"], "stable": ["a", "b", "c"]},
            "arguments": ["a", "b", "c"],
        })
        result = plugin.interpret_dung_results(input_json)
        assert "groundee" in result.lower() or "grounded" in result.lower()
        assert "stable" in result.lower()

    def test_bad_json(self):
        plugin = TweetyResultInterpretationPlugin()
        result = plugin.interpret_dung_results("not json")
        assert "invalide" in result.lower()


class TestPluginFOLResults:
    def test_interpret_fol_results(self):
        plugin = TweetyResultInterpretationPlugin()
        input_json = json.dumps({
            "accepted": True,
            "query": "p(X)",
            "message": "Proved",
        })
        result = plugin.interpret_fol_results(input_json)
        assert "acceptee" in result.lower()

    def test_bad_json(self):
        plugin = TweetyResultInterpretationPlugin()
        result = plugin.interpret_fol_results("{bad")
        assert "invalide" in result.lower()


class TestPluginASPICResults:
    def test_interpret_aspic_results(self):
        plugin = TweetyResultInterpretationPlugin()
        input_json = json.dumps({
            "strict_rules": ["p => q"],
            "defeasible_rules": ["r => s"],
            "attacks": [["a1", "a2"]],
        })
        result = plugin.interpret_aspic_results(input_json)
        assert "1" in result
        assert "attaque" in result.lower()

    def test_bad_json(self):
        plugin = TweetyResultInterpretationPlugin()
        result = plugin.interpret_aspic_results("bad")
        assert "invalide" in result.lower()


class TestPluginRankingResults:
    def test_interpret_ranking_results(self):
        plugin = TweetyResultInterpretationPlugin()
        input_json = json.dumps({"rankings": {"x": 0.9, "y": 0.5}})
        result = plugin.interpret_ranking_results(input_json)
        assert "x" in result

    def test_bad_json(self):
        plugin = TweetyResultInterpretationPlugin()
        result = plugin.interpret_ranking_results("x")
        assert "invalide" in result.lower()


class TestPluginBeliefRevisionResults:
    def test_interpret_belief_revision_results(self):
        plugin = TweetyResultInterpretationPlugin()
        input_json = json.dumps({
            "removed_beliefs": ["b1"],
            "added_beliefs": ["b2"],
        })
        result = plugin.interpret_belief_revision_results(input_json)
        assert "retiree" in result.lower()
        assert "ajoutee" in result.lower()

    def test_bad_json(self):
        plugin = TweetyResultInterpretationPlugin()
        result = plugin.interpret_belief_revision_results("bad")
        assert "invalide" in result.lower()


class TestPluginFullAnalysis:
    def test_full_analysis_all_sections(self):
        plugin = TweetyResultInterpretationPlugin()
        input_json = json.dumps({
            "dung": {
                "extensions": {"grounded": ["a"]},
                "arguments": ["a"],
            },
            "fol": {"accepted": True, "query": "p", "message": "OK"},
            "aspic": {"strict_rules": ["p => q"], "defeasible_rules": [], "attacks": []},
            "ranking": {"rankings": {"x": 0.8}},
            "belief_revision": {"removed_beliefs": ["b1"], "added_beliefs": [], "revised_beliefs": []},
        })
        result = plugin.interpret_full_analysis(input_json)
        assert "**Analyse Dung**" in result
        assert "**Raisonnement FOL**" in result
        assert "**Analyse ASPIC+**" in result
        assert "**Classement**" in result
        assert "**Revision des croyances**" in result

    def test_full_analysis_partial(self):
        plugin = TweetyResultInterpretationPlugin()
        input_json = json.dumps({
            "dung": {"extensions": {}, "arguments": ["a"]},
            "fol": {"accepted": False, "query": "q", "message": "No proof"},
        })
        result = plugin.interpret_full_analysis(input_json)
        assert "**Analyse Dung**" in result
        assert "**Raisonnement FOL**" in result
        assert "ASPIC" not in result

    def test_full_analysis_empty(self):
        plugin = TweetyResultInterpretationPlugin()
        result = plugin.interpret_full_analysis(json.dumps({}))
        assert "aucun" in result.lower()

    def test_full_analysis_bad_json(self):
        plugin = TweetyResultInterpretationPlugin()
        result = plugin.interpret_full_analysis("bad")
        assert "invalide" in result.lower()


class TestPluginWriteToState:
    def test_writes_via_add_extract(self):
        plugin = TweetyResultInterpretationPlugin()
        state = MagicMock()
        input_json = json.dumps({
            "interpretation": "Dung analysis found 3 accepted arguments.",
        })
        result_json = plugin.write_interpretation_to_state(input_json, state=state)
        result = json.loads(result_json)
        assert result["written"] is True
        state.add_extract.assert_called_once_with(
            "formal_interpretation",
            "Dung analysis found 3 accepted arguments.",
        )

    def test_no_state(self):
        plugin = TweetyResultInterpretationPlugin()
        result_json = plugin.write_interpretation_to_state("{}", state=None)
        result = json.loads(result_json)
        assert "error" in result

    def test_empty_interpretation(self):
        plugin = TweetyResultInterpretationPlugin()
        state = MagicMock()
        result_json = plugin.write_interpretation_to_state(
            json.dumps({"interpretation": ""}), state=state
        )
        result = json.loads(result_json)
        assert "error" in result

    def test_bad_json(self):
        plugin = TweetyResultInterpretationPlugin()
        state = MagicMock()
        result_json = plugin.write_interpretation_to_state("bad", state=state)
        result = json.loads(result_json)
        assert "error" in result

    def test_state_without_add_extract(self):
        plugin = TweetyResultInterpretationPlugin()
        state = MagicMock(spec=[])  # No methods at all
        result_json = plugin.write_interpretation_to_state(
            json.dumps({"interpretation": "test"}), state=state
        )
        result = json.loads(result_json)
        assert result["written"] is False


# ---------------------------------------------------------------------------
# Test: Registry and factory integration
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    def test_plugin_registered(self):
        from argumentation_analysis.orchestration.registry_setup import setup_registry

        registry = setup_registry(include_optional=False)
        reg = registry._registrations.get("tweety_result_interpretation_plugin")
        assert reg is not None
        assert "formal_result_interpretation" in reg.capabilities
        assert "dung_interpretation" in reg.capabilities


class TestFactoryIntegration:
    def test_formal_logic_has_interpretation(self):
        from argumentation_analysis.agents.factory import AGENT_SPECIALITY_MAP

        assert "tweety_interpretation" in AGENT_SPECIALITY_MAP["formal_logic"]

    def test_plugin_registry_entry(self):
        from argumentation_analysis.agents.factory import _PLUGIN_REGISTRY

        assert "tweety_interpretation" in _PLUGIN_REGISTRY
        module_path, class_name = _PLUGIN_REGISTRY["tweety_interpretation"]
        assert "tweety_result_interpretation_plugin" in module_path
        assert class_name == "TweetyResultInterpretationPlugin"
